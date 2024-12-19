from hexbytes import HexBytes
from safe_eth.eth.contracts import get_safe_V1_4_1_contract
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
        safe_v1_4_1_contract = get_safe_V1_4_1_contract(Web3())

        # Add Safe Contract Abi and decode it
        abi = Abi(
            abi_hash=b"A Test Abi", abi_json=safe_v1_4_1_contract.abi, relevance=100
        )
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
        function_name, arguments = data_decoder.decode_transaction(data)
        self.assertEqual(function_name, "execTransaction")
        self.assertIn("baseGas", arguments)
        self.assertEqual(type(arguments["data"]), str)
        self.assertEqual(
            type(arguments["baseGas"]), str
        )  # DataDecoderService casts numbers to strings

        function_name, arguments = data_decoder.decode_transaction(data)
        self.assertEqual(function_name, "execTransaction")
        self.assertIn("baseGas", arguments)
        self.assertEqual(type(arguments["data"]), str)
        self.assertEqual(
            type(arguments["baseGas"]), str
        )  # DataDecoderService casts numbers to strings
