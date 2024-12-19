from fastapi.testclient import TestClient

from eth_account import Account
from hexbytes import HexBytes
from safe_eth.eth.utils import fast_to_checksum_address
from sqlmodel.ext.asyncio.session import AsyncSession

from ...datasources.db.database import database_session
from ...datasources.db.models import Abi, Contract
from ...main import app
from ..db.db_async_conn import DbAsyncConn
from ..mocks.abi_mock import mock_abi_json


class TestRouterContract(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @database_session
    async def test_view_contracts(self, session: AsyncSession):

        abi = Abi(abi_json=mock_abi_json)
        await abi.create(session)
        address = HexBytes(Account.create().address)
        contract = Contract(
            address=address, name="A Test Contracts", chain_id=1, abi_id=abi.abi_hash
        )
        await contract.create(session)
        response = self.client.get(
            f"/api/v1/contracts/{fast_to_checksum_address(address.hex())}",
        )
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        results = response_json["results"]
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(response_json["previous"], None)
        self.assertEqual(response_json["next"], None)
        self.assertEqual(results[0]["name"], "A Test Contracts")
        self.assertEqual(results[0]["address"], address.hex())
        self.assertEqual(results[0]["abi"]["abi_json"], mock_abi_json)
        self.assertEqual(results[0]["abi"]["abi_hash"], "0xb4b61541")
        self.assertEqual(results[0]["display_name"], None)
        self.assertEqual(results[0]["chain_id"], 1)
        self.assertEqual(results[0]["project"], None)
