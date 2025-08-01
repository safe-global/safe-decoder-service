import datetime
from typing import cast

from eth_account import Account
from hexbytes import HexBytes
from safe_eth.eth.utils import fast_to_checksum_address

from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract, Project
from app.services.contract_metadata_service import (
    ContractMetadataService,
    ContractSource,
    EnhancedContractMetadata,
)

from ...mocks.contract_metadata_mocks import etherscan_proxy_metadata_mock
from .async_db_test_case import AsyncDbTestCase


class TestModels(AsyncDbTestCase):

    @db_session_context
    async def test_contract(self):
        contract = Contract(
            address=b"a", name="A test contract", chain_id=1, implementation=b"a"
        )
        await contract.create()
        result = await contract.get_all()
        self.assertEqual(result[0], contract)

    @db_session_context
    async def test_get_contracts_query(self):
        address = b"a"
        expected_contract = Contract(
            address=address,
            name="A test contract",
            chain_id=1,
            implementation=b"a",
            abi=None,
        )
        await expected_contract.create()
        query = Contract.get_contracts_query(
            address, chain_ids=None, only_with_abi=False
        )
        contract = (await db_session.execute(query)).scalars().first()
        assert contract == expected_contract

        query = Contract.get_contracts_query(
            chain_ids=None, only_with_abi=False, trusted_for_delegate_call=False
        )
        contract = (await db_session.execute(query)).scalars().first()
        assert contract == expected_contract

        query = Contract.get_contracts_query(
            chain_ids=None, only_with_abi=False, trusted_for_delegate_call=True
        )
        contract = (await db_session.execute(query)).scalars().first()
        assert contract is None

        query = Contract.get_contracts_query(
            address, chain_ids=None, only_with_abi=True
        )
        contract = (await db_session.execute(query)).scalars().first()
        assert contract is None

    @db_session_context
    async def test_contract_get_abi_by_contract_address(self):
        abi_json = {"name": "A Test Project with relevance 10"}
        source = AbiSource(name="local", url="")
        await source.create()
        abi = Abi(
            abi_hash=b"A Test Abi", abi_json=abi_json, relevance=10, source_id=source.id
        )
        await abi.create()
        contract = Contract(address=b"a", name="A test contract", chain_id=1, abi=abi)
        await contract.create()
        result = await contract.get_abi_by_contract_address(contract.address, 1)
        self.assertEqual(result, abi_json)

        # Check chain_id not matching
        result = await contract.get_abi_by_contract_address(contract.address, 2)
        self.assertIsNone(result)

        # Ignoring chain_id
        result = await contract.get_abi_by_contract_address(contract.address, None)
        self.assertEqual(result, abi_json)

        # Check address not matching
        self.assertIsNone(await contract.get_abi_by_contract_address(b"b", None))

    @db_session_context
    async def test_project(self):
        project = Project(
            name="Safe", description="A Test Project", logo_file="logo.jpg"
        )
        await project.create()
        result = await project.get_all()
        self.assertEqual(result[0], project)

    @db_session_context
    async def test_abi(self):
        abi_source = AbiSource(name="A Test Source", url="https://test.com")
        abi_source = await abi_source.create()
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json={"name": "A Test Project"},
            source_id=abi_source.id,
        )
        await abi.create()
        result = await abi.get_all()
        self.assertEqual(result[0], abi)

    @db_session_context
    async def test_abi_get_creation_date_for_last_inserted(self):
        self.assertIsNone(await Abi.get_creation_date_for_last_inserted())

        abi_jsons = [
            {"name": "A Test Project with relevance 100"},
            {"name": "A Test Project with relevance 10"},
        ]
        source = AbiSource(name="A Test Source", url="https://test.com")
        await source.create()
        abi = Abi(
            abi_hash=abi_jsons[0]["name"].encode(),
            abi_json=abi_jsons[0],
            relevance=100,
            source_id=source.id,
        )
        await abi.create()

        last_abi = Abi(
            abi_hash=abi_jsons[1]["name"].encode(),
            abi_json=abi_jsons[1],
            relevance=100,
            source_id=source.id,
        )
        await last_abi.create()

        last_inserted = await Abi.get_creation_date_for_last_inserted()
        self.assertEqual(last_inserted, last_abi.created)

    @db_session_context
    async def test_abi_get_abis_sorted_by_relevance(self):
        abi_jsons = [
            {"name": "A Test Project with relevance 100"},
            {"name": "A Test Project with relevance 10"},
        ]
        source = AbiSource(name="A Test Source", url="https://test.com")
        await source.create()
        abi_by_abi_json = await Abi.get_abi(abi_jsons[0])
        self.assertIsNone(abi_by_abi_json)
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json=abi_jsons[0],
            relevance=100,
            source_id=source.id,
        )
        await abi.create()
        abi_by_abi_json = await Abi.get_abi(abi_jsons[0])
        self.assertEqual(abi_by_abi_json, abi)
        abi = Abi(
            abi_hash=b"A Test Abi2",
            abi_json=abi_jsons[1],
            relevance=10,
            source_id=source.id,
        )
        await abi.create()
        results = abi.get_abis_sorted_by_relevance()
        result = await anext(results)
        self.assertEqual(result, abi_jsons[1])
        result = await anext(results)
        self.assertEqual(result, abi_jsons[0])

    @db_session_context
    async def test_abi_get_abi_newer_than(self):
        initial_datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        self.assertListEqual(
            [x async for x in Abi.get_abi_newer_than(initial_datetime)], []
        )

        abi_jsons = [
            {"name": "A Test Project with relevance 100"},
            {"name": "A Test Project with relevance 10"},
        ]
        source = AbiSource(name="A Test Source", url="https://test.com")
        await source.create()
        abi = Abi(
            abi_hash=abi_jsons[0]["name"].encode(),
            abi_json=abi_jsons[0],
            relevance=100,
            source_id=source.id,
        )
        await abi.create()

        last_abi = Abi(
            abi_hash=abi_jsons[1]["name"].encode(),
            abi_json=abi_jsons[1],
            relevance=100,
            source_id=source.id,
        )
        await last_abi.create()

        self.assertListEqual(
            [
                x
                async for x in Abi.get_abi_newer_than(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                )
            ],
            [],
        )
        self.assertListEqual(
            [x async for x in Abi.get_abi_newer_than(last_abi.created)],
            [],
        )
        self.assertListEqual(
            [x async for x in Abi.get_abi_newer_than(abi.created)],
            [last_abi.abi_json],
        )
        self.assertListEqual(
            [x async for x in Abi.get_abi_newer_than(initial_datetime)],
            [abi.abi_json, last_abi.abi_json],
        )

    @db_session_context
    async def test_abi_source(self):
        abi_source = AbiSource(name="A Test Source", url="https://test.com")
        await abi_source.create()
        result = await abi_source.get_all()
        self.assertEqual(result[0], abi_source)
        abi = Abi(
            abi_hash=b"A Test Abi",
            abi_json={"name": "A Test Project"},
            source_id=abi_source.id,
        )
        await abi.create()
        result = await abi.get_all()
        self.assertEqual(result[0], abi)
        self.assertEqual(result[0].source_id, abi_source.id)

        abi_source = AbiSource(name="A Test Source2", url="https://test-2.com")
        created_abi_source, created = await AbiSource.get_or_create(
            name="A Test Source2", url="https://test-2.com"
        )
        self.assertEqual(created_abi_source.name, abi_source.name)
        self.assertEqual(created_abi_source.url, abi_source.url)
        self.assertTrue(created)
        retrieved_abi_source, created = await AbiSource.get_or_create(
            name="A Test Source2", url="https://test-2.com"
        )
        self.assertEqual(retrieved_abi_source.name, abi_source.name)
        self.assertEqual(retrieved_abi_source.url, abi_source.url)
        self.assertFalse(created)

    @db_session_context
    async def test_timestamped_model(self):
        contract = Contract(address=b"a", name="A test contract", chain_id=1)
        contract_created_date = contract.created
        contract_modified_date = contract.modified
        await contract.create()
        result = await contract.get_all()
        self.assertEqual(result[0], contract)
        self.assertEqual(result[0].created, contract_created_date)
        self.assertEqual(result[0].modified, contract_modified_date)

        contract_modified_name = "A test contract updated"
        contract.name = contract_modified_name
        await contract.update()
        result_updated = await contract.get_all()

        self.assertEqual(result_updated[0].name, contract_modified_name)
        self.assertEqual(result_updated[0].created, contract_created_date)
        self.assertNotEqual(result_updated[0].modified, contract_modified_date)
        self.assertTrue(contract_modified_date < result_updated[0].modified)

    @db_session_context
    async def test_get_contracts_without_abi(self):
        random_address = HexBytes(Account.create().address)
        abi_json = {"name": "A Test ABI"}
        source = AbiSource(name="local", url="")
        await source.create()
        abi = Abi(abi_json=abi_json, source_id=source.id)
        await abi.create()
        # Should return the contract
        expected_contract = await Contract(
            address=random_address, name="A test contract", chain_id=1
        ).create()
        async for contract in Contract.get_contracts_without_abi(0):
            self.assertEqual(expected_contract, contract)

        # Contracts with more retries shouldn't be returned
        expected_contract.fetch_retries = 1
        await expected_contract.update()
        async for contract in Contract.get_contracts_without_abi(0):
            self.fail("Expected no contracts, but found one.")

        # Contracts with abi shouldn't be returned
        expected_contract.abi_id = abi.id
        await expected_contract.update()
        async for contract in Contract.get_contracts_without_abi(10):
            self.fail("Expected no contracts, but found one.")

    @db_session_context
    async def test_get_proxy_contracts(self):
        # Test empty case
        async for proxy_contract in Contract.get_proxy_contracts():
            self.fail("Expected no proxies, but found one.")

        random_address = Account.create().address
        await AbiSource(name="Etherscan", url="").create()
        enhanced_contract_metadata = EnhancedContractMetadata(
            address=random_address,
            metadata=etherscan_proxy_metadata_mock,
            source=ContractSource.ETHERSCAN,
            chain_id=1,
        )
        result = await ContractMetadataService.process_contract_metadata(
            enhanced_contract_metadata
        )
        self.assertTrue(result)
        async for proxy_contract in Contract.get_proxy_contracts():
            self.assertEqual(
                fast_to_checksum_address(proxy_contract.address), random_address
            )
            self.assertEqual(
                fast_to_checksum_address(cast(bytes, proxy_contract.implementation)),
                "0x43506849D7C04F9138D1A2050bbF3A0c054402dd",
            )

    @db_session_context
    async def test_update_contract_info(self):
        address_to_be_updated = HexBytes("0xd53cd0aB83D845Ac265BE939c57F53AD838012c9")
        other_address = HexBytes("0x43506849D7C04F9138D1A2050bbF3A0c054402dd")

        contract_name = "SignMessageLib"
        contract_display_name = "Sign Message Library"
        rows_affected = await Contract.update_contract_info(
            address=address_to_be_updated,
            name=contract_name,
            display_name=contract_display_name,
        )
        self.assertEqual(rows_affected, 0)
        contracts_to_be_updated = [
            await Contract(address=address_to_be_updated, chain_id=chain_id).create()
            for chain_id in range(5)
        ]
        other_contract = await Contract(address=other_address, chain_id=1).create()

        for contract in contracts_to_be_updated:
            self.assertIsNone(contract.name)
            self.assertIsNone(contract.display_name)
            self.assertFalse(contract.trusted_for_delegate_call)

        self.assertIsNone(other_contract.name)
        self.assertIsNone(other_contract.display_name)

        rows_affected = await Contract.update_contract_info(
            address=address_to_be_updated,
            name=contract_name,
            display_name=contract_display_name,
            trusted_for_delegate_call=True,
        )
        self.assertEqual(rows_affected, 5)
        # Other contract remains not updated
        not_updated_contract = await Contract.get_contract(
            address=other_address, chain_id=1
        )
        self.assertIsNone(not_updated_contract.name)
        self.assertIsNone(not_updated_contract.display_name)
        # contracts_to_be_updated should be updated
        for contract in contracts_to_be_updated:
            updated_contract = await Contract.get_contract(
                address=address_to_be_updated, chain_id=contract.chain_id
            )
            self.assertEqual(updated_contract.name, contract_name)
            self.assertEqual(updated_contract.display_name, contract_display_name)
            self.assertTrue(updated_contract.trusted_for_delegate_call)
