from hexbytes import HexBytes
from safe_eth.eth.contracts import get_safe_V1_4_1_contract, get_safe_V1_1_1_contract
from safe_eth.safe.multi_send import MultiSendOperation
from sqlmodel.ext.asyncio.session import AsyncSession
from web3 import Web3

from ...datasources.db.database import database_session
from ...datasources.db.models import Abi
from ...services.data_decoder import DataDecoderService, get_data_decoder_service
from ..db.db_async_conn import DbAsyncConn


class TestDataDecoderService(DbAsyncConn):
    async def test_get_data_decoder_service(self):
        data_decoder_service = await get_data_decoder_service()
        assert data_decoder_service.fn_selectors_with_abis == {}

    @database_session
    async def test_init_without_abi(self, session: AsyncSession):
        empty_decoder_service = DataDecoderService()
        await empty_decoder_service.init(session)
        assert empty_decoder_service.fn_selectors_with_abis == {}

    @staticmethod
    async def _store_safe_contract_abi(session: AsyncSession):
        safe_v1_1_1_contract = get_safe_V1_1_1_contract(Web3())
        safe_v1_4_1_contract = get_safe_V1_4_1_contract(Web3())

        # Add Safe Contract Abi and decode it
        for abi in (
                Abi(
                    abi_hash=b"SafeContractV1_1_1_ABI", abi_json=safe_v1_1_1_contract.abi, relevance=100
                ),
                Abi(
                    abi_hash=b"SafeContractV1_4_1_ABI", abi_json=safe_v1_4_1_contract.abi, relevance=100
                )
        ):
            await abi.create(session)

    @database_session
    async def test_init_with_abi(self, session: AsyncSession):
        await self._store_safe_contract_abi(session)

        decoder_service = DataDecoderService()
        await decoder_service.init(session)
        exec_transaction_bytes = bytes.fromhex("6a761202")
        name = decoder_service.fn_selectors_with_abis[exec_transaction_bytes]["name"]
        assert name == "execTransaction"

    @database_session
    async def test_decode_execute_transaction(self, session: AsyncSession):
        await self._store_safe_contract_abi(session)

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
        await data_decoder.init(session)
        function_name, arguments = await data_decoder.decode_transaction(data)
        self.assertEqual(function_name, "execTransaction")
        self.assertIn("baseGas", arguments)
        self.assertEqual(type(arguments["data"]), str)
        self.assertEqual(
            type(arguments["baseGas"]), str
        )  # DataDecoderService casts numbers to strings

    @database_session
    async def test_decode_execute_transaction_with_types(self, session: AsyncSession):
        await self._store_safe_contract_abi(session)
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
        await data_decoder.init(session)
        function_name, arguments = await data_decoder.decode_transaction_with_types(data)
        self.assertEqual(function_name, "execTransaction")
        self.assertEqual(
            arguments,
            [
                {
                    "name": "to",
                    "type": "address",
                    "value": "0x5592EC0cfb4dbc12D3aB100b257153436a1f0FEa",
                },
                {"name": "value", "type": "uint256", "value": '0'},
                {
                    "name": "data",
                    "type": "bytes",
                    "value": "0xa9059cbb0000000000000000000000000dc0dfd22c6beab74672eade5f9be5234aaa4"
                             "3cc00000000000000000000000000000000000000000000000000005af3107a4000",
                    "value_decoded": None,
                },
                {"name": "operation", "type": "uint8", "value": '0'},
                {"name": "safeTxGas", "type": "uint256", "value": '0'},
                {"name": "baseGas", "type": "uint256", "value": '0'},
                {"name": "gasPrice", "type": "uint256", "value": '0'},
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

    @database_session
    async def test_decode_multisend(self, session: AsyncSession):
        await self._store_safe_contract_abi(session)

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
        await data_decoder.init(session)
        expected = [
            {
                "operation": operation,
                "to": safe_contract_address,
                "value": value,
                "data": change_master_copy_data.hex(),
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
                "data": change_fallback_manager_data.hex(),
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
        expected = (
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
                            "data": change_master_copy_data.hex(),
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
                            "data": change_fallback_manager_data.hex(),
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
        self.assertEqual(await data_decoder.decode_transaction_with_types(data), expected)
