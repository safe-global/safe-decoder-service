from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Contract
from app.tests.db.db_async_conn import DbAsyncConn


class TestModel(DbAsyncConn):
    @database_session
    async def test_contract(self, session: AsyncSession):
        contract = Contract(address=b"a", name="A Test Contracts", chain_id=1)
        await contract.create(session)
        statement = select(Contract).where(Contract.address == b"a")
        result = await session.exec(statement)
        self.assertEqual(result.one(), contract)
