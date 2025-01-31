import datetime
import logging
from enum import Enum
from typing import Any, AsyncIterator, NotRequired, TypedDict, Union, cast

from async_lru import alru_cache
from eth_abi import decode as decode_abi
from eth_abi.exceptions import DecodingError
from eth_typing import Address, ChecksumAddress, HexStr
from eth_utils import function_abi_to_4byte_selector
from hexbytes import HexBytes
from safe_eth.eth.contracts import get_multi_send_contract
from safe_eth.safe.multi_send import MultiSend
from sqlmodel.ext.asyncio.session import AsyncSession
from web3 import Web3
from web3._utils.abi import get_abi_input_names, get_abi_input_types, map_abi_data
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
from web3.types import ABI, ABIFunction

from ..datasources.db.models import Abi, Contract

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
    value_decoded: NotRequired[Union[list["MultisendDecoded"], "DataDecoded", None]]


class DataDecoded(TypedDict):
    method: str
    parameters: list[ParameterDecoded]


class DecodingAccuracyEnum(Enum):
    FULL_MATCH = "FULL_MATCH"  # Matched contract and chain id
    PARTIAL_MATCH = "PARTIAL_MATCH"  # Matched contract
    ONLY_FUNCTION_MATCH = (
        "ONLY_FUNCTION_MATCH"  # Matched function from another contract
    )
    NO_MATCH = "NO_MATCH"  # Selector cannot be decoded


class MultisendDecoded(TypedDict):
    operation: int
    to: ChecksumAddress
    value: str
    data: HexStr | None
    data_decoded: DataDecoded | None


@alru_cache
async def get_data_decoder_service() -> "DataDecoderService":
    data_decoder_service = DataDecoderService()
    await data_decoder_service.init()
    return data_decoder_service


class DataDecoderService:
    EXEC_TRANSACTION_SELECTOR = HexBytes("0x6a761202")

    dummy_w3 = Web3()
    session: AsyncSession | None

    fn_selectors_with_abis: dict[bytes, ABIFunction]
    multisend_abis: list[ABI]
    multisend_fn_selectors_with_abis: dict[bytes, ABIFunction]
    last_abi_created: datetime.datetime | None

    async def init(self) -> None:
        """
        Initialize the data decoder service, loading the ABIs from the database and storing the 4byte selectors
        in memory
        """

        # last_abi_created will be used to reload ABIs on the database only getting the newer ones
        self.last_abi_created = await Abi.get_creation_date_for_last_inserted()
        logger.info(
            "%s: Loading contract ABIs for decoding. Last inserted ABI on the database: %s",
            self.__class__.__name__,
            self.last_abi_created,
        )
        self.fn_selectors_with_abis: dict[bytes, ABIFunction] = (
            await self._generate_selectors_with_abis_from_abis(
                await self.get_supported_abis()
            )
        )
        logger.info(
            "%s: Contract ABIs for decoding were loaded", self.__class__.__name__
        )
        self.multisend_abis: list[ABI] = [m async for m in self.get_multisend_abis()]
        self.multisend_fn_selectors_with_abis: dict[bytes, ABIFunction] = (
            await self._generate_selectors_with_abis_from_abis(
                self.get_multisend_abis()
            )
        )

    def _generate_selectors_with_abis_from_abi(
        self, abi: ABI
    ) -> dict[bytes, ABIFunction]:
        """
        :param abi: ABI
        :return: Dictionary with function selector as bytes and the ContractFunction
        """
        return {
            function_abi_to_4byte_selector(cast(dict[str, Any], fn_abi)): fn_abi
            for fn_abi in abi
            if fn_abi["type"] == "function"
        }

    async def _generate_selectors_with_abis_from_abis(
        self, abis: AsyncIterator[ABI]
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

    async def get_supported_abis(self) -> AsyncIterator[ABI]:
        """
        :return: Every ABI in the database
        """
        return Abi.get_abis_sorted_by_relevance()

    async def get_multisend_abis(self) -> AsyncIterator[ABI]:
        yield get_multi_send_contract(self.dummy_w3).abi

    @alru_cache(maxsize=2048)
    async def get_contract_abi(
        self,
        address: Address,
        chain_id: int | None,
    ) -> ABI | None:
        """
        Retrieves the ABI for the contract at the given address.

        :param address: Contract address
        :param chain_id: Chain id for the contract
        :return: List of ABI data if found, `None` otherwise.
        """
        return await Contract.get_abi_by_contract_address(HexBytes(address), chain_id)

    @alru_cache(maxsize=2048)
    async def get_contract_fallback_function(
        self, address: Address, chain_id: int | None
    ) -> ABIFunction | None:
        """
        :param address: Contract address
        :param chain_id: Chain for the contract
        :return: Fallback `ABIFunction` if found, `None` otherwise.
            If contract is not found for the chain, return the first one that matches in other chain.
        """
        abi = await self.get_contract_abi(address, chain_id)
        if not abi and chain_id is not None:
            # Try to find an ABI in other network
            abi = await self.get_contract_abi(address, None)
        if abi:
            return next(
                (
                    cast(ABIFunction, dict(fn_abi, name="fallback"))
                    for fn_abi in abi
                    if fn_abi.get("type") == "fallback"
                ),
                None,
            )
        return None

    @alru_cache(maxsize=2048)
    async def get_contract_abi_selectors_with_functions(
        self, address: Address, chain_id: int | None
    ) -> dict[bytes, ABIFunction] | None:
        """
        :param address: Contract address
        :param chain_id: Chain for the contract
        :return: Dictionary of function selects with `ABIFunction` if found, `None` otherwise
            If contract is not found for the chain, return the first one that matches in other chain.
        """
        abi = await self.get_contract_abi(address, chain_id)
        if not abi and chain_id is not None:
            # Try to find an ABI in other network
            abi = await self.get_contract_abi(address, None)
        if abi:
            return self._generate_selectors_with_abis_from_abi(abi)
        return None

    async def get_abi_function(
        self, data: bytes, address: Address | None = None, chain_id: int | None = None
    ) -> ABIFunction | None:
        """
        :param data: transaction data
        :param address: contract address in case of ABI colliding
        :param chain_id: Chain for the contract
        :return: Abi function for data if it can be decoded, `None` if not found
        """
        selector = data[:4]
        # Check first that selector is supported on our database
        if selector in self.fn_selectors_with_abis:
            # Try to use specific ABI if address provided
            if address:
                contract_selectors_with_abis = (
                    await self.get_contract_abi_selectors_with_functions(
                        address, chain_id
                    )
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
            return await self.get_contract_fallback_function(address, chain_id)
        return None

    def _parse_decoded_arguments(self, value_decoded: Any) -> Any:
        """
        Parse decoded arguments. In this case converting `bytes` to hexadecimal `str` to
        prevent problems when deserializing in another languages like JavaScript

        :param value_decoded:
        :return: dict[str, Any]
        """
        if isinstance(value_decoded, tuple):
            value_decoded = tuple(
                self._parse_decoded_arguments(value) for value in value_decoded
            )
        elif isinstance(value_decoded, list):
            value_decoded = [
                self._parse_decoded_arguments(value) for value in value_decoded
            ]
        elif isinstance(value_decoded, bytes):
            value_decoded = HexBytes(value_decoded).hex()
        elif isinstance(value_decoded, int):
            value_decoded = str(value_decoded)
        return value_decoded

    async def _decode_data(
        self,
        data: bytes | str,
        address: Address | None = None,
        chain_id: int | None = None,
    ) -> tuple[str, list[tuple[str, str, Any]]]:
        """
        Decode tx data

        :param data: Tx data as `hex string` or `bytes`
        :param address: contract address in case of ABI colliding
        :param chain_id: Chain for the contract
        :return: Tuple with the `function name` and a List of sorted tuples with
            the `name` of the argument, `type` and `value`
        :raises: CannotDecode if data cannot be decoded. You should catch this exception when using this function
        :raises: UnexpectedProblemDecoding if there's an unexpected problem decoding (it shouldn't happen)
        """

        if not data:
            raise CannotDecode(data)

        data = HexBytes(data)
        params = data[4:]
        fn_abi = await self.get_abi_function(data, address, chain_id)
        if not fn_abi:
            raise CannotDecode(data.hex())
        try:
            names = get_abi_input_names(fn_abi)
            types = get_abi_input_types(fn_abi)
            decoded = decode_abi(types, params)
            normalized = map_abi_data(BASE_RETURN_NORMALIZERS, types, decoded)
            values = map(self._parse_decoded_arguments, normalized)
        except (ValueError, DecodingError) as exc:
            logger.warning("Cannot decode %s", data.hex())
            raise UnexpectedProblemDecoding(data) from exc

        return fn_abi["name"], list(zip(names, types, values))

    async def decode_multisend_data(
        self, data: bytes | str, chain_id: int | None = None
    ) -> list[MultisendDecoded] | None:
        """
        Decodes Multisend raw data to Multisend dictionary

        :param data:
        :param chain_id:
        :return:
        """
        try:
            multisend_txs = MultiSend.from_transaction_data(data)
            return [
                MultisendDecoded(
                    operation=multisend_tx.operation.value,
                    to=multisend_tx.to,
                    value=str(multisend_tx.value),
                    data=HexStr(multisend_tx.data.hex()) if multisend_tx.data else None,
                    data_decoded=await self.get_data_decoded(
                        multisend_tx.data,
                        address=cast(Address, multisend_tx.to),
                        chain_id=chain_id,
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
        return None

    async def get_data_decoded(
        self,
        data: bytes | str,
        address: Address | None = None,
        chain_id: int | None = None,
    ) -> DataDecoded | None:
        """
        Return data prepared for serializing

        :param data:
        :param address: contract address in case of ABI colliding
        :param chain_id: chain for contract
        :return:
        """
        if not data:
            return None
        try:
            fn_name, parameters = await self.decode_transaction_with_types(
                data, address=address, chain_id=chain_id
            )
            return {"method": fn_name, "parameters": parameters}
        except DataDecoderException:
            return None

    async def decode_parameters_data(
        self,
        data: bytes,
        parameters: list[ParameterDecoded],
        chain_id: int | None = None,
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
            parameters[0]["value_decoded"] = await self.decode_multisend_data(
                data, chain_id=chain_id
            )

        elif (
            fn_selector == self.EXEC_TRANSACTION_SELECTOR
            and len(parameters) > 2
            and (data := HexBytes(parameters[2]["value"]))
        ):
            # If data belongs to Safe `execTransaction` decode the inner transaction
            # function execTransaction(address to, uint256 value, bytes calldata data...)
            # selector is `0x6a761202` and parameters[2] is data
            try:
                parameters[2]["value_decoded"] = await self.get_data_decoded(
                    data, address=parameters[0]["value"], chain_id=chain_id
                )
            except DataDecoderException:
                logger.warning("Cannot decode `execTransaction`", exc_info=True)
        return parameters

    async def decode_transaction_with_types(
        self,
        data: bytes | str,
        address: Address | None = None,
        chain_id: int | None = None,
    ) -> tuple[str, list[ParameterDecoded]]:
        """
        Decode tx data and return a list of dictionaries

        :param data: Tx data as `hex string` or `bytes`
        :param address: contract address in case of ABI colliding
        :param chain_id: chain for the contract
        :return: Tuple with the `function name` and a list of dictionaries
            [{'name': str, 'type': str, 'value': `depending on type`}...]
        :raises: CannotDecode if data cannot be decoded. You should catch this exception when using this function
        :raises: UnexpectedProblemDecoding if there's an unexpected problem decoding (it shouldn't happen)
        """
        data = HexBytes(data)
        fn_name, raw_parameters = await self._decode_data(
            data, address=address, chain_id=chain_id
        )
        # Parameters are returned as tuple, convert it to a dictionary
        parameters = [
            ParameterDecoded(name=name, type=argument_type, value=value)
            for name, argument_type, value in raw_parameters
        ]
        nested_parameters = await self.decode_parameters_data(
            data, parameters, chain_id=chain_id
        )
        return fn_name, nested_parameters

    async def decode_transaction(
        self,
        data: bytes | str,
        address: Address | None = None,
        chain_id: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Decode tx data and return all the parameters in the same dictionary

        :param data: Tx data as `hex string` or `bytes`
        :param address: contract address in case of ABI colliding
        :param chain_id: chain for the contract
        :return: Tuple with the `function name` and a dictionary with the arguments of the function
        :raises: CannotDecode if data cannot be decoded. You should catch this exception when using this function
        :raises: UnexpectedProblemDecoding if there's an unexpected problem decoding (it shouldn't happen)
        """
        fn_name, decoded_transactions_with_types = (
            await self.decode_transaction_with_types(
                data, address=address, chain_id=chain_id
            )
        )
        decoded_transactions = {
            d["name"]: d["value"] for d in decoded_transactions_with_types
        }
        return fn_name, decoded_transactions

    async def get_decoding_accuracy(
        self,
        data: bytes | str,
        address: Address | None = None,
        chain_id: int | None = None,
    ) -> DecodingAccuracyEnum:
        """
        Get decoding accuracy:
            - FULL_MATCH: Contract `address` and `chain_id` matching
            - PARTIAL_MATCH: Only contract `address` matching
            - ONLY_FUNCTION_MATCH: Match with a function of another contract
            - NO_MATCH: Cannot decode `data`

        :param data:
        :param address:
        :param chain_id:
        :return: DecodingAccuracyEnum
        """
        selector = HexBytes(data)[:4]
        if selector not in self.fn_selectors_with_abis:
            return DecodingAccuracyEnum.NO_MATCH
        if address is not None:
            if chain_id is not None and await self.get_contract_abi(
                address, chain_id=chain_id
            ):
                return DecodingAccuracyEnum.FULL_MATCH
            if await self.get_contract_abi(address, None):
                return DecodingAccuracyEnum.PARTIAL_MATCH
        return DecodingAccuracyEnum.ONLY_FUNCTION_MATCH

    def add_abi(self, abi: ABI) -> bool:
        """
        Add a new abi without rebuilding the entire decoder

        :return: True if decoder updated, False otherwise
        """
        updated = False
        for selector, new_abi in self._generate_selectors_with_abis_from_abi(
            abi
        ).items():
            if selector not in self.fn_selectors_with_abis:
                self.fn_selectors_with_abis[selector] = new_abi
                updated = True
        return updated

    async def load_new_abis(self) -> int:
        """
        Load new ABIs stored on the database after the decoder was started.
        Use `last_abi_created` property to only load the latest ABIs

        :return: Number of new ABIs loaded
        """

        last_abi_created = self.last_abi_created
        self.last_abi_created = await Abi.get_creation_date_for_last_inserted()
        if last_abi_created is not None:
            abis = Abi.get_abi_newer_equal_than(last_abi_created)
        else:
            abis = Abi.get_abis_sorted_by_relevance()

        loaded_abis = 0
        async for abi in abis:
            if self.add_abi(abi):
                loaded_abis += 1
        return loaded_abis
