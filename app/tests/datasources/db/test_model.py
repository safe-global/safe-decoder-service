from eth_account import Account
from hexbytes import HexBytes
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import database_session
from app.datasources.db.models import Abi, AbiSource, Contract, Project

from .db_async_conn import DbAsyncConn


class TestModel(DbAsyncConn):
    @database_session
    async def test_contract(self, session: AsyncSession):
        contract = Contract(
            address=b"a", name="A test contract", chain_id=1, implementation=b"a"
        )
        await contract.create(session)
        result = await contract.get_all(session)
        self.assertEqual(result[0], contract)

    @database_session
    async def test_contract_get_abi_by_contract_address(self, session: AsyncSession):
        abi_json = {"name": "A Test Project with relevance 10"}
        source = AbiSource(name="local", url="")
        await source.create(session)
        abi = Abi(
            abi_hash=b"A Test Abi", abi_json=abi_json, relevance=10, source_id=source.id
        )
        await abi.create(session)
        contract = Contract(address=b"a", name="A test contract", chain_id=1, abi=abi)
        await contract.create(session)
        result = await contract.get_abi_by_contract_address(session, contract.address)
        self.assertEqual(result, abi_json)

        self.assertIsNone(await contract.get_abi_by_contract_address(session, b"b"))

    @database_session
    async def test_project(self, session: AsyncSession):
        project = Project(description="A Test Project", logo_file="logo.jpg")
        await project.create(session)
        result = await project.get_all(session)
        self.assertEqual(result[0], project)

    @database_session
    async def test_abi(self, session: AsyncSession):
        abi_source = AbiSource(name="A Test Source", url="https://test.com")
        await abi_source.create(session)
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json={"name": "A Test Project"},
            source_id=abi_source.id,
        )
        await abi.create(session)
        result = await abi.get_all(session)
        self.assertEqual(result[0], abi)

    @database_session
    async def test_abi_get_abis_sorted_by_relevance(self, session: AsyncSession):
        abi_jsons = [
            {"name": "A Test Project with relevance 100"},
            {"name": "A Test Project with relevance 10"},
        ]
        source = AbiSource(name="A Test Source", url="https://test.com")
        await source.create(session)
        abi_by_abi_json = await Abi.get_abi(session, abi_jsons[0])
        self.assertIsNone(abi_by_abi_json)
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json=abi_jsons[0],
            relevance=100,
            source_id=source.id,
        )
        await abi.create(session)
        abi_by_abi_json = await Abi.get_abi(session, abi_jsons[0])
        self.assertEqual(abi_by_abi_json, abi)
        abi = Abi(
            abi_hash=b"A Test Abi2",
            abi_json=abi_jsons[1],
            relevance=10,
            source_id=source.id,
        )
        await abi.create(session)
        results = abi.get_abis_sorted_by_relevance(session)
        result = await anext(results)
        self.assertEqual(result, abi_jsons[1])
        result = await anext(results)
        self.assertEqual(result, abi_jsons[0])

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

        abi_source = AbiSource(name="A Test Source2", url="https://test-2.com")
        created_abi_source, created = await AbiSource.get_or_create(
            session, name="A Test Source2", url="https://test-2.com"
        )
        self.assertEqual(created_abi_source.name, abi_source.name)
        self.assertEqual(created_abi_source.url, abi_source.url)
        self.assertTrue(created)
        retrieved_abi_source, created = await AbiSource.get_or_create(
            session, name="A Test Source2", url="https://test-2.com"
        )
        self.assertEqual(retrieved_abi_source.name, abi_source.name)
        self.assertEqual(retrieved_abi_source.url, abi_source.url)
        self.assertFalse(created)

    @database_session
    async def test_timestamped_model(self, session: AsyncSession):
        contract = Contract(address=b"a", name="A test contract", chain_id=1)
        contract_created_date = contract.created
        contract_modified_date = contract.modified
        await contract.create(session)
        result = await contract.get_all(session)
        self.assertEqual(result[0], contract)
        self.assertEqual(result[0].created, contract_created_date)
        self.assertEqual(result[0].modified, contract_modified_date)

        contract_modified_name = "A test contract updated"
        contract.name = contract_modified_name
        await contract.update(session)
        result_updated = await contract.get_all(session)

        self.assertEqual(result_updated[0].name, contract_modified_name)
        self.assertEqual(result_updated[0].created, contract_created_date)
        self.assertNotEqual(result_updated[0].modified, contract_modified_date)
        self.assertTrue(contract_modified_date < result_updated[0].modified)

    @database_session
    async def test_get_contracts_without_abi(self, session: AsyncSession):
        random_address = HexBytes(Account.create().address)
        abi_json = {"name": "A Test ABI"}
        source = AbiSource(name="local", url="")
        await source.create(session)
        abi = Abi(abi_json=abi_json, source_id=source.id)
        await abi.create(session)
        # Should return the contract
        expected_contract = await Contract(
            address=random_address, name="A test contract", chain_id=1
        ).create(session)
        async for contract in Contract.get_contracts_without_abi(session, 0):
            self.assertEqual(expected_contract, contract[0])

        # Contracts with more retries shouldn't be returned
        expected_contract.fetch_retries = 1
        await expected_contract.update(session)
        async for contract in Contract.get_contracts_without_abi(session, 0):
            self.fail("Expected no contracts, but found one.")

        # Contracts with abi shouldn't be returned
        expected_contract.abi_id = abi.id
        await expected_contract.update(session)
        async for contract in Contract.get_contracts_without_abi(session, 10):
            self.fail("Expected no contracts, but found one.")
