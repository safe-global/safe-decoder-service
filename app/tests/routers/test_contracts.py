from fastapi.testclient import TestClient

from ...datasources.db.models import Contract
from ...main import app
from ...services.contract import ContractService
from ..db.db_async_conn import DbAsyncConn


class TestRouterContract(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    async def test_view_contracts(self):
        contract = Contract(address=b"a", name="A Test Contracts")
        expected_response = {
            "name": "A Test Contracts",
            "description": None,
            "address": "a",
        }
        await ContractService.create(contract=contract)
        response = self.client.get("/api/v1/contracts")
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json()[0], expected_response)