from sqlmodel import select

from app.datasources.db.models import Contract
from app.tests.db.db_async_conn import DbAsyncConn


class TestModel(DbAsyncConn):

    async def test_contract(self):
        contract = Contract(address=b"a", name="A Test Contracts")
        self.session.add(contract)
        await self.session.commit()
        statement = select(Contract).where(Contract.address == b"a")
        result = await self.session.exec(statement)
        self.assertEqual(result.one(), contract)
