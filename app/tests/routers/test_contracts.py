from fastapi.testclient import TestClient

from sqlmodel.ext.asyncio.session import AsyncSession
from ...datasources.db.database import database_session
from ...datasources.db.models import Chain, Contract
from ...main import app
from ...services.chain import ChainService
from ...services.contract import ContractService
from ..db.db_async_conn import DbAsyncConn


class TestRouterContract(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)


    @database_session
    async def test_view_contracts(self, session: AsyncSession):
        chain = Chain(id=1, name="mainnet")
        await ChainService.create(chain)
        contract = Contract(address=b"a", name="A Test Contracts", chain_id=1)
        expected_response = {
            "name": "A Test Contracts",
            "description": None,
            "address": "a",
        }
        await ContractService.create(contract=contract, session=session)
        response = self.client.get("/api/v1/contracts")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()[0], expected_response)
