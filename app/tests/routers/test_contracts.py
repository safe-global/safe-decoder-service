from fastapi.testclient import TestClient

from ...datasources.db.models import Contract
from ...main import app
from ..db.db_async_conn import DbAsyncConn


class TestRouterContract(DbAsyncConn):
    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    async def test_view_contracts(self):
        contract = Contract(address=b"a", name="A Test Contracts")
        self.session.add(contract)
        await self.session.commit()
        response = self.client.get("/api/v1/contracts")
        self.assertEqual(response.status_code, 200)
