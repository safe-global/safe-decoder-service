from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Chain, Contract
from app.tests.db.db_async_conn import DbAsyncConn


class TestModel(DbAsyncConn):
    @database_session
    async def test_contract(self, session: AsyncSession):
        chain = Chain(id=1, name="mainnet")
        session.add(chain)
        contract = Contract(address=b"a", name="A Test Contracts", chain_id=chain.id)
        session.add(contract)
        await session.commit()
        statement = select(Contract).where(Contract.address == b"a")
        result = await session.exec(statement)
        self.assertEqual(result.one(), contract)
