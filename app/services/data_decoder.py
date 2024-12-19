import logging
from functools import cache, cached_property, lru_cache
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    NotRequired,
    Sequence,
    TypedDict,
    cast,
)

from eth_abi import decode as decode_abi
from eth_abi.exceptions import DecodingError
from eth_typing import ABIFunction, Address, HexStr
from eth_utils import function_abi_to_4byte_selector
from hexbytes import HexBytes
from safe_eth.eth.contracts import get_multi_send_contract
from safe_eth.safe.multi_send import MultiSend
from sqlmodel.ext.asyncio.session import AsyncSession
from web3 import Web3
from web3._utils.abi import get_abi_input_names, get_abi_input_types, map_abi_data
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS

from app.datasources.db.database import get_engine
from app.datasources.db.models import Abi, Contract

logger = logging.getLogger(__name__)


class DataDecoderException(Exception):
    pass


class UnexpectedProblemDecoding(DataDecoderException):
    pass


class CannotDecode(DataDecoderException):
    pass


class ParameterDecoded(TypedDict):
    name: str
    type: str
    value: Any
    value_decoded: NotRequired["ParameterDecoded"]


class DataDecoded(TypedDict):
    method: str
    parameters: list[ParameterDecoded]


class MultisendDecoded(TypedDict):
    operation: int
    to: Address
    value: str
    data: HexStr | None
    data_decoded: DataDecoded | None


@cache
def get_data_decoder_service() -> "DataDecoderService":
    d = DataDecoderService()
    d.init()
    return d


class DataDecoderService:
    EXEC_TRANSACTION_SELECTOR = HexBytes("0x6a761202")

    dummy_w3 = Web3()

    async def init(self):
        """
        Initialize the data decoder service, loading the ABIs from the database and storing the 4byte selectors
        in memory
        """
        logger.info("%s: Loading contract ABIs for decoding", self.__class__.__name__)
        self.fn_selectors_with_abis: dict[bytes, ABIFunction] = (
            await self._generate_selectors_with_abis_from_abis(
                await self.get_supported_abis()
            )
        )
        logger.info(
            "%s: Contract ABIs for decoding were loaded", self.__class__.__name__
        )

    @cached_property
    def multisend_abis(self) -> list[Sequence[ABIFunction]]:
        return [get_multi_send_contract(self.dummy_w3).abi]

    @cached_property
    def multisend_fn_selectors_with_abis(self) -> dict[bytes, ABIFunction]:
        return self._generate_selectors_with_abis_from_abis(self.multisend_abis)

    def _generate_selectors_with_abis_from_abi(
        self, abi: Sequence[ABIFunction]
    ) -> dict[bytes, ABIFunction]:
        """
        :param abi: ABI
        :return: Dictionary with function selector as bytes and the ContractFunction
        """
        return {
            function_abi_to_4byte_selector(fn_abi): fn_abi
            for fn_abi in abi
            if fn_abi["type"] == "function"
        }

    async def _generate_selectors_with_abis_from_abis(
        self, abis: AsyncIterator[Sequence[ABIFunction]]
    ) -> dict[bytes, ABIFunction]:
        """
        :param abis: Contract ABIs. Last ABIs on the Sequence have preference if there's a collision on the
        selector
        :return: Dictionary with function selector as bytes and the function abi
        """
        return {
            fn_selector: fn_abi
            async for supported_abi in abis
            for fn_selector, fn_abi in self._generate_selectors_with_abis_from_abi(
                supported_abi
            ).items()
        }

    async def get_supported_abis(self) -> AsyncIterator[Sequence[ABIFunction]]:
        """
        :return: Every ABI in the database
        """
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            return Abi.get_abis_sorted_by_relevance(session)

    @lru_cache(maxsize=2048)
    async def get_contract_abi(self, address: Address) -> list[ABIFunction] | None:
        """
        Retrieves the ABI for the contract at the given address.

        :param address: Contract address
        :return: List of ABI data if found, `None` otherwise.
        """
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            return Contract.get_abis_sorted_by_relevance(session, HexBytes(address))

    @lru_cache(maxsize=2048)
    def get_contract_fallback_function(self, address: Address) -> ABIFunction | None:
        """
        :param address: Contract address
        :return: Fallback ABIFunction if found, `None` otherwise.
        """
        abi = self.get_contract_abi(address)
        if abi:
            return next(
                (
                    dict(fn_abi, name="fallback")
                    for fn_abi in abi
                    if fn_abi.get("type") == "fallback"
                ),
                None,
            )

    @lru_cache(maxsize=2048)
    def get_contract_abi_selectors_with_functions(
        self, address: Address
    ) -> dict[bytes, ABIFunction] | None:
        """
        :param address: Contract address
        :return: Dictionary of function selects with ABIFunction if found, `None` otherwise
        """
        abi = self.get_contract_abi(address)
        if abi:
            return self._generate_selectors_with_abis_from_abi(abi)

    def get_abi_function(
        self, data: bytes, address: Address | None = None
    ) -> ABIFunction | None:
        """
        :param data: transaction data
        :param address: contract address in case of ABI colliding
        :return: Abi function for data if it can be decoded, `None` if not found
        """
        selector = data[:4]
        # Check first that selector is supported on our database
        if selector in self.fn_selectors_with_abis:
            # Try to use specific ABI if address provided
            if address:
                contract_selectors_with_abis = (
                    self.get_contract_abi_selectors_with_functions(address)
                )
                if (
                    contract_selectors_with_abis
                    and selector in contract_selectors_with_abis
                ):
                    # If the selector is available in the abi specific for the address we will use that one
                    # Otherwise we fall back to the general abi that matches the selector
                    return contract_selectors_with_abis[selector]
            return self.fn_selectors_with_abis[selector]
        # Check if the contract has a fallback call and return a minimal ABIFunction for fallback call
        elif address:
            return self.get_contract_fallback_function(address)

    def _parse_decoded_arguments(self, value_decoded: Any) -> Any:
        """
        Parse decoded arguments. In this case converting `bytes` to hexadecimal `str` to
        prevent problems when deserializing in another languages like JavaScript

        :param value_decoded:
        :return: dict[str, Any]
        """
        if isinstance(value_decoded, bytes):
            value_decoded = HexBytes(value_decoded).hex()
        return value_decoded

    def _decode_data(
        self, data: bytes | str, address: Address | None = None
    ) -> tuple[str, list[tuple[str, str, Any]]]:
        """
        Decode tx data

        :param data: Tx data as `hex string` or `bytes`
        :param address: contract address in case of ABI colliding
        :return: Tuple with the `function name` and a List of sorted tuples with
            the `name` of the argument, `type` and `value`
        :raises: CannotDecode if data cannot be decoded. You should catch this exception when using this function
        :raises: UnexpectedProblemDecoding if there's an unexpected problem decoding (it shouldn't happen)
        """

        if not data:
            raise CannotDecode(data)

        data = HexBytes(data)
        params = data[4:]
        fn_abi = self.get_abi_function(data, address)
        if not fn_abi:
            raise CannotDecode(data.hex())
        try:
            names = get_abi_input_names(fn_abi)
            types = get_abi_input_types(fn_abi)
            decoded = decode_abi(types, cast(HexBytes, params))
            normalized = map_abi_data(BASE_RETURN_NORMALIZERS, types, decoded)
            values = map(self._parse_decoded_arguments, normalized)
        except (ValueError, DecodingError) as exc:
            logger.warning("Cannot decode %s", data.hex())
            raise UnexpectedProblemDecoding(data) from exc

        return fn_abi["name"], list(zip(names, types, values))

    def decode_multisend_data(self, data: bytes | str) -> list[MultisendDecoded]:
        """
        Decodes Multisend raw data to Multisend dictionary

        :param data:
        :return:
        """
        try:
            multisend_txs = MultiSend.from_transaction_data(data)
            return [
                MultisendDecoded(
                    operation=multisend_tx.operation.value,
                    to=multisend_tx.to,
                    value=str(multisend_tx.value),
                    data=multisend_tx.data.hex() if multisend_tx.data else None,
                    data_decoded=self.get_data_decoded(
                        multisend_tx.data, address=multisend_tx.to
                    ),
                )
                for multisend_tx in multisend_txs
            ]
        except ValueError:
            logger.warning(
                "Problem decoding multisend transaction with data=%s",
                HexBytes(data).hex(),
                exc_info=True,
            )

    def get_data_decoded(
        self, data: bytes | str, address: Address | None = None
    ) -> DataDecoded | None:
        """
        Return data prepared for serializing

        :param data:
        :param address: contract address in case of ABI colliding
        :return:
        """
        if not data:
            return None
        try:
            fn_name, parameters = self.decode_transaction_with_types(
                data, address=address
            )
            return {"method": fn_name, "parameters": parameters}
        except DataDecoderException:
            return None

    def decode_parameters_data(
        self, data: bytes, parameters: list[ParameterDecoded]
    ) -> list[ParameterDecoded]:
        """
        Decode inner data for function parameters for:
            - Multisend `data`
            - Safe `execTransaction` `data`

        :param data:
        :param parameters:
        :return: Parameters with an extra object with key `value_decoded` if decoding is possible
        """
        fn_selector = data[:4]
        if fn_selector in self.multisend_fn_selectors_with_abis:
            # If MultiSend, decode the transactions
            parameters[0]["value_decoded"] = self.decode_multisend_data(data)

        elif (
            fn_selector == self.EXEC_TRANSACTION_SELECTOR
            and len(parameters) > 2
            and (data := HexBytes(parameters[2]["value"]))
        ):
            # If data belongs to Safe `execTransaction` decode the inner transaction
            # function execTransaction(address to, uint256 value, bytes calldata data...)
            # selector is `0x6a761202` and parameters[2] is data
            try:
                parameters[2]["value_decoded"] = self.get_data_decoded(
                    data, address=parameters[0]["value"]
                )
            except DataDecoderException:
                logger.warning("Cannot decode `execTransaction`", exc_info=True)
        return parameters

    def decode_transaction_with_types(
        self, data: bytes | str, address: Address | None = None
    ) -> tuple[str, list[ParameterDecoded]]:
        """
        Decode tx data and return a list of dictionaries

        :param data: Tx data as `hex string` or `bytes`
        :param address: contract address in case of ABI colliding
        :return: Tuple with the `function name` and a list of dictionaries
            [{'name': str, 'type': str, 'value': `depending on type`}...]
        :raises: CannotDecode if data cannot be decoded. You should catch this exception when using this function
        :raises: UnexpectedProblemDecoding if there's an unexpected problem decoding (it shouldn't happen)
        """
        data = HexBytes(data)
        fn_name, raw_parameters = self._decode_data(data, address=address)
        # Parameters are returned as tuple, convert it to a dictionary
        parameters = [
            ParameterDecoded(name=name, type=argument_type, value=value)
            for name, argument_type, value in raw_parameters
        ]
        nested_parameters = self.decode_parameters_data(data, parameters)
        return fn_name, nested_parameters
