from app.datasources.db.database import db_session_context
from app.services.contract import ContractService
from app.services.pagination import GenericPagination
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase
from app.tests.datasources.db.factory import contract_factory


class TestContractService(AsyncDbTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        pagination = GenericPagination(limit=None, offset=None)
        self.service = ContractService(pagination=pagination)

    @db_session_context
    async def test_get_contracts_by_address_and_chain_id(self):
        # Create 3 contracts
        target_contract = await contract_factory()

        # Call the method
        page, count = await self.service.get_contracts(
            address=target_contract.address,
            chain_ids=[target_contract.chain_id],
        )

        # Assertions
        self.assertEqual(count, 1)
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0].address, target_contract.address)
        self.assertEqual(page[0].chain_id, target_contract.chain_id)

    @db_session_context
    async def test_get_contracts_without_address_sorted(self):
        trusted_contract_1 = await contract_factory(
            address="0x0000000000000000000000000000000000000001",
            trusted_for_delegate_call=True,
            chain_id=1,
        )
        trusted_contract_2 = await contract_factory(
            address="0x0000000000000000000000000000000000000002",
            trusted_for_delegate_call=True,
            chain_id=2,
        )
        trusted_contract_3 = await contract_factory(
            address="0x0000000000000000000000000000000000000003",
            trusted_for_delegate_call=True,
            chain_id=3,
        )
        untrusted_contract_1 = await contract_factory(
            address="0x0000000000000000000000000000000000000001",
            trusted_for_delegate_call=False,
            chain_id=2,
        )

        # Filter: trusted_for_delegate_call=True, chain_ids=[1, 2]
        page, count = await self.service.get_contracts(
            trusted_for_delegate_call=True, chain_ids=[1, 2]
        )

        # Should return trusted_contracts, sorted by address
        expected_contracts = sorted(
            [trusted_contract_1, trusted_contract_2],
            key=lambda contract: (contract.address, contract.chain_id),
        )

        self.assertEqual(count, 2)
        self.assertEqual(len(page), 2)
        self.assertEqual(
            [contract.address for contract in page],
            [contract.address for contract in expected_contracts],
        )

        # Get just the untrusted delegate call contracts
        page, count = await self.service.get_contracts(
            trusted_for_delegate_call=False, chain_ids=None
        )

        # Should return untrusted_contracts, sorted by address
        expected_contracts = [untrusted_contract_1]

        self.assertEqual(count, 1)
        self.assertEqual(len(page), 1)
        self.assertEqual([page], [expected_contracts])

        page, count = await self.service.get_contracts(
            trusted_for_delegate_call=None, chain_ids=None
        )

        expected_sorted = sorted(
            [
                trusted_contract_1,
                trusted_contract_2,
                untrusted_contract_1,
                trusted_contract_3,
            ],
            key=lambda contract: (contract.address, contract.chain_id),
        )

        self.assertEqual(count, 4)
        self.assertEqual(len(page), 4)
        self.assertEqual(
            [c.address for c in page], [c.address for c in expected_sorted]
        )
