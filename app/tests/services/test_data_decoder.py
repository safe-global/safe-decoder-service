from eth_typing import Address
from hexbytes import HexBytes
from safe_eth.eth.constants import NULL_ADDRESS
from safe_eth.eth.contracts import (
    get_erc20_contract,
    get_multi_send_contract,
    get_safe_V1_1_1_contract,
    get_safe_V1_4_1_contract,
)
from safe_eth.eth.utils import fast_keccak_text, get_empty_tx_params
from safe_eth.safe.multi_send import MultiSendOperation
from safe_eth.util.util import to_0x_hex_str
from web3 import Web3

from app.datasources.abis.compound import comptroller_abi, ctoken_abi
from app.datasources.abis.gnosis_protocol import (
    fleet_factory_abi,
    fleet_factory_deterministic_abi,
    gnosis_protocol_abi,
)

from ...datasources.db.database import db_session_context
from ...datasources.db.models import Abi, AbiSource, Contract
from ...services.data_decoder import (
    CannotDecode,
    DataDecoderService,
    DecodingAccuracyEnum,
    UnexpectedProblemDecoding,
    get_data_decoder_service,
)
from ..datasources.db.async_db_test_case import AsyncDbTestCase
from .mocks_data_decoder import (
    example_abi,
    example_swapped_abi,
    exec_transaction_data_mock,
    exec_transaction_decoded_mock,
    insufficient_data_bytes_mock,
    tuple_abi,
)


class TestDataDecoderService(AsyncDbTestCase):
    @staticmethod
    async def _store_safe_contract_abi():
        dummy_web3 = Web3()
        source = AbiSource(name="local", url="")
        await source.create()
        erc20_contract = get_erc20_contract(dummy_web3)
        safe_v1_1_1_contract = get_safe_V1_1_1_contract(dummy_web3)
        safe_v1_4_1_contract = get_safe_V1_4_1_contract(dummy_web3)
        multisend_contract = get_multi_send_contract(dummy_web3)

        # Add Safe Contract Abi and decode it
        for abi in (
            Abi(
                abi_hash=b"ERC20Contract",
                abi_json=erc20_contract.abi,
                relevance=150,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"SafeContractV1_1_1_ABI",
                abi_json=safe_v1_1_1_contract.abi,
                relevance=100,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"SafeContractV1_4_1_ABI",
                abi_json=safe_v1_4_1_contract.abi,
                relevance=100,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"MultiSendContractABI",
                abi_json=multisend_contract.abi,
                relevance=100,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"GnosisProtocolABI",
                abi_json=gnosis_protocol_abi,
                relevance=50,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"FleetFactoryDeterministic",
                abi_json=fleet_factory_deterministic_abi,
                relevance=50,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"FleetFactory",
                abi_json=fleet_factory_abi,
                relevance=50,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"cTokenABI",
                abi_json=ctoken_abi,
                relevance=50,
                source_id=source.id,
            ),
            Abi(
                abi_hash=b"comptrollerABI",
                abi_json=comptroller_abi,
                relevance=50,
                source_id=source.id,
            ),
        ):
            await abi.create()

    @db_session_context
    async def test_get_data_decoder_service(self):
        get_data_decoder_service.cache_clear()
        data_decoder_service = await get_data_decoder_service()
        assert data_decoder_service.fn_selectors_with_abis == {}

    @db_session_context
    async def test_init_without_abi(self):
        empty_decoder_service = DataDecoderService()
        await empty_decoder_service.init()
        assert empty_decoder_service.fn_selectors_with_abis == {}

    @db_session_context
    async def test_init_with_abi(self):
        await self._store_safe_contract_abi()

        decoder_service = DataDecoderService()
        await decoder_service.init()
        exec_transaction_bytes = bytes.fromhex("6a761202")
        name = decoder_service.fn_selectors_with_abis[exec_transaction_bytes]["name"]
        assert name == "execTransaction"

    @db_session_context
    async def test_decode_execute_transaction(self):
        await self._store_safe_contract_abi()

        # Call to Safe `execTransaction`
        data = HexBytes(
            "0x6a761202000000000000000000000000d9ab7371432d7cc74503290412618c948cddacf200000000000000000"
            "0000000000000000000000000000000002386f26fc1000000000000000000000000000000000000000000000000"
            "0000000000000000014000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000030d400000000000000000000000000000000000"
            "0000000000000000000000000186a000000000000000000000000000000000000000000000000000000004a817c"
            "8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000180000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "00000000000000000000041512215e7f982c8f8e8429c9008068366dcb96bb3abd9c969f3bf2f97f013da6941e1"
            "59f13ca524a6b449accf1ce6765ad811ee7b7151f74749e38ac8bc94fb3b1c00000000000000000000000000000"
            "000000000000000000000000000000000"
        )

        data_decoder = DataDecoderService()
        await data_decoder.init()
        function_name, arguments = await data_decoder.decode_transaction(data)
        self.assertEqual(function_name, "execTransaction")
        self.assertIn("baseGas", arguments)
        self.assertEqual(type(arguments["data"]), str)
        self.assertEqual(
            type(arguments["baseGas"]), str
        )  # DataDecoderService casts numbers to strings

    @db_session_context
    async def test_decode_execute_transaction_with_types(self):
        await self._store_safe_contract_abi()
        data = HexBytes(
            "0x6a7612020000000000000000000000005592ec0cfb4dbc12d3ab100b257153436a1f0fea0000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000014000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000001c00000000000000000000000000000000000000000000000000000"
            "000000000044a9059cbb0000000000000000000000000dc0dfd22c6beab74672eade5f9be5234a"
            "aa43cc00000000000000000000000000000000000000000000000000005af3107a400000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "00000000000000000000000000000000820000000000000000000000000dc0dfd22c6beab74672"
            "eade5f9be5234aaa43cc0000000000000000000000000000000000000000000000000000000000"
            "00000001000000000000000000000000c791cb32ddb43de8260e6a2762b3b03498b615e5000000"
            "000000000000000000000000000000000000000000000000000000000001000000000000000000"
            "000000000000000000000000000000000000000000"
        )

        data_decoder = DataDecoderService()
        await data_decoder.init()
        function_name, arguments = await data_decoder.decode_transaction_with_types(
            data
        )
        self.assertEqual(function_name, "execTransaction")
        self.assertEqual(
            arguments,
            [
                {
                    "name": "to",
                    "type": "address",
                    "value": "0x5592EC0cfb4dbc12D3aB100b257153436a1f0FEa",
                },
                {"name": "value", "type": "uint256", "value": "0"},
                {
                    "name": "data",
                    "type": "bytes",
                    "value": "0xa9059cbb0000000000000000000000000dc0dfd22c6beab74672eade5f9be5234aaa4"
                    "3cc00000000000000000000000000000000000000000000000000005af3107a4000",
                    "value_decoded": {
                        "method": "transfer",
                        "parameters": [
                            {
                                "name": "to",
                                "type": "address",
                                "value": "0x0dc0dfD22C6Beab74672EADE5F9Be5234AAa43cC",
                            },
                            {
                                "name": "value",
                                "type": "uint256",
                                "value": "100000000000000",
                            },
                        ],
                    },
                },
                {"name": "operation", "type": "uint8", "value": "0"},
                {"name": "safeTxGas", "type": "uint256", "value": "0"},
                {"name": "baseGas", "type": "uint256", "value": "0"},
                {"name": "gasPrice", "type": "uint256", "value": "0"},
                {
                    "name": "gasToken",
                    "type": "address",
                    "value": "0x0000000000000000000000000000000000000000",
                },
                {
                    "name": "refundReceiver",
                    "type": "address",
                    "value": "0x0000000000000000000000000000000000000000",
                },
                {
                    "name": "signatures",
                    "type": "bytes",
                    "value": "0x0000000000000000000000000dc0dfd22c6beab74672eade5f9be5234aaa43cc00000"
                    "00000000000000000000000000000000000000000000000000000000000010000000000"
                    "00000000000000c791cb32ddb43de8260e6a2762b3b03498b615e500000000000000000"
                    "0000000000000000000000000000000000000000000000001",
                },
            ],
        )

    @db_session_context
    async def test_decode_multisend(self):
        await self._store_safe_contract_abi()

        # Change Safe contract master copy and set fallback manager multisend transaction
        safe_contract_address = "0x5B9ea52Aaa931D4EEf74C8aEaf0Fe759434FeD74"
        value = "0"
        operation = MultiSendOperation.CALL.value
        data = HexBytes(
            "0x8d80ff0a0000000000000000000000000000000000000000000000000000000000000020000000000000000000"
            "00000000000000000000000000000000000000000000f2005b9ea52aaa931d4eef74c8aeaf0fe759434fed740000"
            "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000247de7edef00000000000000000000000034cfac646f301356faa8b21e9422"
            "7e3583fe3f5f005b9ea52aaa931d4eef74c8aeaf0fe759434fed7400000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024f0"
            "8a0323000000000000000000000000d5d82b6addc9027b22dca772aa68d5d74cdbdf440000000000000000000000"
            "000000"
        )
        change_master_copy_data = HexBytes(
            "0x7de7edef00000000000000000000000034cfac646f301356faa8b21e94227e3583fe3f5f"
        )
        change_fallback_manager_data = HexBytes(
            "0xf08a0323000000000000000000000000d5d82b6addc9027b22dca772aa68d5d74cd"
            "bdf44"
        )

        data_decoder = DataDecoderService()
        await data_decoder.init()
        expected = [
            {
                "operation": operation,
                "to": safe_contract_address,
                "value": value,
                "data": to_0x_hex_str(change_master_copy_data),
                "data_decoded": {
                    "method": "changeMasterCopy",
                    "parameters": [
                        {
                            "name": "_masterCopy",
                            "type": "address",
                            "value": "0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
                        }
                    ],
                },
            },
            {
                "operation": operation,
                "to": safe_contract_address,
                "value": value,
                "data": to_0x_hex_str(change_fallback_manager_data),
                "data_decoded": {
                    "method": "setFallbackHandler",
                    "parameters": [
                        {
                            "name": "handler",
                            "type": "address",
                            "value": "0xd5D82B6aDDc9027B22dCA772Aa68D5d74cdBdF44",
                        }
                    ],
                },
            },
        ]
        # Get just the MultiSend object
        self.assertEqual(await data_decoder.decode_multisend_data(data), expected)

        # Now decode all the data
        expected_2 = (
            "multiSend",
            [
                {
                    "name": "transactions",
                    "type": "bytes",
                    "value": "0x005b9ea52aaa931d4eef74c8aeaf0fe759434fed74000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000247de7edef00000000000000000000000034cfac646f301356faa8b21e94227e3583fe3f5f005b9ea52aaa931d4eef74c8aeaf0fe759434fed7400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024f08a0323000000000000000000000000d5d82b6addc9027b22dca772aa68d5d74cdbdf44",
                    "value_decoded": [
                        {
                            "operation": operation,
                            "to": safe_contract_address,
                            "value": value,
                            "data": to_0x_hex_str(change_master_copy_data),
                            "data_decoded": {
                                "method": "changeMasterCopy",
                                "parameters": [
                                    {
                                        "name": "_masterCopy",
                                        "type": "address",
                                        "value": "0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
                                    }
                                ],
                            },
                        },
                        {
                            "operation": operation,
                            "to": safe_contract_address,
                            "value": value,
                            "data": to_0x_hex_str(change_fallback_manager_data),
                            "data_decoded": {
                                "method": "setFallbackHandler",
                                "parameters": [
                                    {
                                        "name": "handler",
                                        "type": "address",
                                        "value": "0xd5D82B6aDDc9027B22dCA772Aa68D5d74cdBdF44",
                                    }
                                ],
                            },
                        },
                    ],
                }
            ],
        )
        self.assertEqual(
            await data_decoder.decode_transaction_with_types(data), expected_2
        )

    @db_session_context
    async def test_decode_multisend_not_valid(self):
        await self._store_safe_contract_abi()

        # Same data with some stuff deleted
        data = HexBytes(
            "0x8d80ff0a0000000000000000000000000000000000000000000000000000000000000020000000000000000000"
            "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000247de7edef00000000000000000000000034cfac646f301356faa8b21e9422"
            "7e3583fe3f5f005b9ea52aaa931d4eef74c8aeaf0fe759434fed7400000000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024f0"
            "8a0323000000000000000000000000d5d82b6addc9027b22dca772aa68d5d74cdbdf440000000000000000000000"
            "000000"
        )
        decoder_service = DataDecoderService()
        await decoder_service.init()
        self.assertEqual(await decoder_service.decode_multisend_data(data), [])
        self.assertEqual(
            await decoder_service.decode_transaction_with_types(data),
            (
                "multiSend",
                [
                    {
                        "name": "transactions",
                        "type": "bytes",
                        "value": "0x",
                        "value_decoded": [],
                    }
                ],
            ),
        )

    @db_session_context
    async def test_decode_safe_exec_transaction(self):
        await self._store_safe_contract_abi()

        data = exec_transaction_data_mock
        decoder_service = DataDecoderService()
        await decoder_service.init()

        self.assertIn(bytes.fromhex("c2998238"), decoder_service.fn_selectors_with_abis)
        # Cowswap ABI is required for this test
        self.assertEqual(
            await decoder_service.get_data_decoded(data), exec_transaction_decoded_mock
        )

    @db_session_context
    async def test_unexpected_problem_decoding(self):
        await self._store_safe_contract_abi()

        data = insufficient_data_bytes_mock
        decoder_service = DataDecoderService()
        await decoder_service.init()

        with self.assertRaises(UnexpectedProblemDecoding):
            await decoder_service.decode_transaction(data)

    @db_session_context
    async def test_db_tx_decoder(self):
        example_data = (
            Web3()
            .eth.contract(abi=example_abi)
            .functions.buyDroid(4, 10)
            .build_transaction(
                get_empty_tx_params() | {"to": NULL_ADDRESS, "chainId": 1}
            )["data"]
        )

        decoder_service = DataDecoderService()
        await decoder_service.init()

        with self.assertRaises(CannotDecode):
            await decoder_service.decode_transaction(example_data)

        # Test `add_abi`
        await decoder_service.add_abi(example_abi)
        fn_name, arguments = await decoder_service.decode_transaction(example_data)
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, {"droidId": "4", "numberOfDroids": "10"})
        source = AbiSource(name="local", url="")
        await source.create()
        # Test load a new DbTxDecoder
        abi = Abi(
            abi_hash=b"ExampleABI",
            abi_json=example_abi,
            relevance=100,
            source_id=source.id,
        )
        await abi.create()
        decoder_service = DataDecoderService()
        await decoder_service.init()
        fn_name, arguments = await decoder_service.decode_transaction(example_data)
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, {"droidId": "4", "numberOfDroids": "10"})

        abi = Abi(
            abi_hash=b"SwappedABI",
            abi_json=example_swapped_abi,
            relevance=100,
            source_id=source.id,
        )
        await abi.create()
        contract = Contract(address=b"c", abi=abi, name="SwappedContract", chain_id=1)
        await contract.create()

        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=Address(contract.address)
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, {"numberOfDroids": "4", "droidId": "10"})

    @db_session_context
    async def test_db_tx_decoder_multichain(self):
        example_data = (
            Web3()
            .eth.contract(abi=example_abi)
            .functions.buyDroid(4, 10)
            .build_transaction(
                get_empty_tx_params() | {"to": NULL_ADDRESS, "chainId": 1}
            )["data"]
        )

        source = AbiSource(name="local", url="")
        await source.create()

        # Both ABIs generate the same function selector, but with differently ordered parameter names, so
        # decoding will be different
        abi = Abi(
            abi_hash=b"ExampleABI",
            abi_json=example_abi,
            relevance=1,
            source_id=source.id,
        )
        await abi.create()

        abi_reversed = Abi(
            abi_hash=b"ExampleABIReversed",
            abi_json=example_swapped_abi,
            relevance=100,
            source_id=source.id,
        )
        await abi_reversed.create()

        contract = Contract(address=b"a", abi=abi, name="ExampleContract", chain_id=1)
        await contract.create()
        contract_reversed = Contract(
            address=b"a", abi=abi_reversed, name="ExampleContractReversed", chain_id=2
        )
        await contract_reversed.create()

        decoder_service = DataDecoderService()
        await decoder_service.init()

        expected_arguments = {"droidId": "4", "numberOfDroids": "10"}
        expected_arguments_reversed = {"numberOfDroids": "4", "droidId": "10"}

        contract_address = Address(b"a")
        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=contract_address, chain_id=1
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=1
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments)
        self.assertEqual(accuracy, DecodingAccuracyEnum.FULL_MATCH)

        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=Address(contract.address), chain_id=2
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=2
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments_reversed)
        self.assertEqual(accuracy, DecodingAccuracyEnum.FULL_MATCH)

        # If chain_id is not matching, lower chain_id contract must be used
        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=contract_address, chain_id=5
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=5
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments)
        self.assertEqual(accuracy, DecodingAccuracyEnum.PARTIAL_MATCH)

        # If chain_id is not provided, lower chain_id contract must be used
        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=contract_address, chain_id=None
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=None
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments)
        self.assertEqual(accuracy, DecodingAccuracyEnum.PARTIAL_MATCH)

        # If no contract is matching but abi is on the database, it should be decoded using the more relevant ABI
        contract.address = b"b"
        await contract.update()
        contract_reversed.address = b"b"
        await contract_reversed.update()

        # Check caches are working even if contract was updated on DB
        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=contract_address, chain_id=1
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=1
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments)
        self.assertEqual(accuracy, DecodingAccuracyEnum.FULL_MATCH)

        # Init a new service to remove caches
        decoder_service = DataDecoderService()
        await decoder_service.init()

        fn_name, arguments = await decoder_service.decode_transaction(
            example_data, address=contract_address, chain_id=1
        )
        accuracy = await decoder_service.get_decoding_accuracy(
            example_data, address=contract_address, chain_id=1
        )
        self.assertEqual(fn_name, "buyDroid")
        self.assertEqual(arguments, expected_arguments_reversed)
        self.assertEqual(accuracy, DecodingAccuracyEnum.ONLY_FUNCTION_MATCH)

    @db_session_context
    async def test_decode_tuples(self):
        """
        Test tuple parameters are decoded as expected
        """
        example_data = (
            Web3()
            .eth.contract(abi=tuple_abi)
            .functions.createWithContext(
                (fast_keccak_text("Sakamoto"), fast_keccak_text("Days"), b"48")
            )
            .build_transaction(
                get_empty_tx_params() | {"to": NULL_ADDRESS, "chainId": 1}
            )["data"]
        )

        source = AbiSource(name="local", url="")
        await source.create()
        contract_fallback_abi = Abi(
            abi_hash=b"TupleABI",
            abi_json=tuple_abi,
            relevance=100,
            source_id=source.id,
        )
        await contract_fallback_abi.create()

        decoder_service = DataDecoderService()
        await decoder_service.init()
        fn_name, arguments = await decoder_service.decode_transaction(example_data)
        self.assertEqual(fn_name, "createWithContext")
        self.assertEqual(
            arguments,
            {
                "params": (
                    "0x3c03deed836a997bb67d3caa6aaf378dcc5bba915aecc2ec4c7c927d85166a19",
                    "0x319604e0f5da98581a5c25a5003b1a257b40012bc0012ff4e5350e11a280d610",
                    "0x3438",
                )
            },
        )

    @db_session_context
    async def test_load_new_abis(self):
        decoder_service = DataDecoderService()
        await decoder_service.init()

        # Service should not have any ABI loaded
        self.assertEqual(decoder_service.fn_selectors_with_abis, {})
        self.assertIsNone(decoder_service.last_abi_created)

        # Try to load new ABIs, none should be loaded
        self.assertEqual(await decoder_service.load_new_abis(), 0)
        self.assertEqual(decoder_service.fn_selectors_with_abis, {})
        self.assertIsNone(decoder_service.last_abi_created)

        # Store ABIs in the database and load them
        await self._store_safe_contract_abi()
        self.assertGreater(await decoder_service.load_new_abis(), 0)
        self.assertNotEqual(decoder_service.fn_selectors_with_abis, {})
        self.assertIsNotNone(decoder_service.last_abi_created)

        # No new ABIs to load
        # Store ABIs in the database and load them
        self.assertEqual(await decoder_service.load_new_abis(), 0)

        # Add a new ABI
        source = AbiSource(name="local", url="")
        await source.create()
        abi = Abi(
            abi_hash=b"ExampleABI",
            abi_json=example_abi,
            relevance=1,
            source_id=source.id,
        )
        await abi.create()
        len_previous_selectors = len(decoder_service.fn_selectors_with_abis)
        self.assertEqual(await decoder_service.load_new_abis(), 1)
        self.assertGreater(
            len(decoder_service.fn_selectors_with_abis), len_previous_selectors
        )
        self.assertEqual(decoder_service.last_abi_created, abi.created)
