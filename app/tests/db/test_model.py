from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Abi, AbiSource, Contract, Project
from app.tests.db.db_async_conn import DbAsyncConn


class TestModel(DbAsyncConn):
    @database_session
    async def test_contract(self, session: AsyncSession):
        contract = Contract(address=b"a", name="A test contract", chain_id=1)
        await contract.create(session)
        await contract.create(session)
        result = await contract.get_all(session)
        self.assertEqual(result[0], contract)

    @database_session
    async def test_project(self, session: AsyncSession):
        project = Project(description="A Test Project", logo_file="logo.jpg")
        await project.create(session)
        result = await project.get_all(session)
        self.assertEqual(result[0], project)

    @database_session
    async def test_abi(self, session: AsyncSession):
        abi = Abi(abi_hash=b"A Test Abi", abi_json={"name": "A Test Project"})
        await abi.create(session)
        result = await abi.get_all(session)
        self.assertEqual(result[0], abi)

    @database_session
    async def test_abi_source(self, session: AsyncSession):
        abi_source = AbiSource(name="A Test Source", url="https://test.com")
        await abi_source.create(session)
        result = await abi_source.get_all(session)
        self.assertEqual(result[0], abi_source)
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json={"name": "A Test Project"},
            source_id=abi_source.id,
        )
        await abi.create(session)
        result = await abi.get_all(session)
        self.assertEqual(result[0], abi)
        self.assertEqual(result[0].source, abi_source)
