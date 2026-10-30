# SPDX-License-Identifier: FSL-1.1-MIT
from unittest.mock import AsyncMock, patch

from hexbytes import HexBytes
from safe_eth.util.util import to_0x_hex_str

from app.config import settings
from app.datasources.db.database import db_session, db_session_context
from app.datasources.db.models import Abi, AbiSource, Contract
from app.services.safe_contracts_service import (
    SafeContractsService,
    get_safe_contract_service,
)
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase


class TestSafeContractsServiceIntegration(AsyncDbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = get_safe_contract_service()
        self.service._safe_contracts_cache.clear()

    def test_generate_safe_contract_display_name(self):
        service = SafeContractsService()
        test_cases = [
            ("GnosisSafe", "1.3.0", "Safe 1.3.0"),
            ("GnosisMultiSend", "1.0.0", "Safe: MultiSend 1.0.0"),
            ("SignMessageLib", "1.0.0", "Safe: SignMessageLib 1.0.0"),
            ("SafeMigration", "1.1.1", "SafeMigration 1.1.1"),
            ("GnosisSafeProxyFactory", "1.2.0", "SafeProxyFactory 1.2.0"),
        ]
        for name, version, expected_result in test_cases:
            self.assertEqual(
                service._generate_safe_contract_display_name(name, version),
                expected_result,
            )

    @patch(
        "app.services.safe_contracts_service.SafeContractsService._get_default_deployments_by_version"
    )
    @patch(
        "app.services.safe_contracts_service.Contract.update_contract_info",
        new_callable=AsyncMock,
    )
    @patch("app.services.safe_contracts_service.logger")
    async def test_update_safe_contracts_info(
        self, mock_logger, mock_update, mock_get_deployments
    ):
        mock_get_deployments.return_value = [
            (
                "1.4.1",
                "MultiSendCallOnly",
                "0x9641d764fc13c8B624c04430C7356C1C7C8102e2",
            ),
            ("1.4.1", "MultiSend", "0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526"),
        ]

        mock_update.side_effect = [2, 0]
        service = SafeContractsService()
        await service.update_safe_contracts_info()
        self.assertEqual(mock_update.call_count, 2)

        mock_update.assert_any_call(
            address=HexBytes("0x9641d764fc13c8B624c04430C7356C1C7C8102e2"),
            name="MultiSendCallOnly",
            display_name="Safe: MultiSendCallOnly 1.4.1",
            trusted_for_delegate_call=True,
            chain_id=None,
        )
        mock_update.assert_any_call(
            address=HexBytes("0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526"),
            name="MultiSend",
            display_name="Safe: MultiSend 1.4.1",
            trusted_for_delegate_call=False,
            chain_id=None,
        )

        mock_logger.info.assert_called_once_with(
            "Updated contract with address: %s in %d chains",
            "0x9641d764fc13c8B624c04430C7356C1C7C8102e2",
            2,
        )
        mock_logger.warning.assert_called_once_with(
            "Could not find any contract with address: %s",
            "0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526",
        )

    @db_session_context
    async def test_safe_contracts_exist(self):
        exists = await self.service.safe_contracts_exist(999)
        self.assertFalse(exists)

        await self.service.create_safe_contracts(chain_id=1)

        exists = await self.service.safe_contracts_exist(1)
        self.assertTrue(exists)

        exists = await self.service.safe_contracts_exist(1)
        self.assertTrue(exists)

        exists = await self.service.safe_contracts_exist(999)
        self.assertFalse(exists)

    @db_session_context
    async def test_safe_contracts_exist_partial(self):
        from hexbytes import HexBytes

        deployments = self.service._get_default_deployments_by_version()
        chain_id = 100

        _, first_contract_name, first_address = deployments[0]
        await Contract(
            address=HexBytes(first_address),
            chain_id=chain_id,
            name=first_contract_name,
        ).create()

        exists = await self.service.safe_contracts_exist(chain_id)
        self.assertFalse(exists)

    @db_session_context
    async def test_safe_contracts_exist_singleton_cache_shared(self):
        await self.service.create_safe_contracts(chain_id=5)

        service1 = get_safe_contract_service()
        exists = await service1.safe_contracts_exist(5)
        self.assertTrue(exists)

        service2 = get_safe_contract_service()
        exists = await service2.safe_contracts_exist(5)
        self.assertTrue(exists)

        self.assertIs(service1, service2)
        self.assertIn(5, service1._safe_contracts_cache)

    @db_session_context
    async def test_create_safe_contracts(self):
        new_chain_id = 100

        deployments = self.service._get_default_deployments_by_version()
        expected_count = len(deployments)

        created_count = await self.service.create_safe_contracts(new_chain_id)

        self.assertEqual(created_count, expected_count)

        for version, contract_name, contract_address in deployments:
            contract = await Contract.get_contract(
                address=HexBytes(contract_address), chain_id=new_chain_id
            )
            self.assertIsNotNone(contract, f"Contract {contract_name} not found")
            self.assertEqual(contract.name, contract_name)
            self.assertIsNotNone(contract.display_name)
            expected_display_name = self.service._generate_safe_contract_display_name(
                contract_name, version
            )
            self.assertEqual(contract.display_name, expected_display_name)
            expected_trusted = (
                contract_name in settings.CONTRACTS_TRUSTED_FOR_DELEGATE_CALL
            )
            self.assertEqual(contract.trusted_for_delegate_call, expected_trusted)

        # Try to create again should return 0
        created_count = await self.service.create_safe_contracts(new_chain_id)
        assert created_count == 0

    @db_session_context
    async def test_update_safe_contracts_info_for_chain(self):
        address = HexBytes("0x6439e7ABD8Bb915A5263094784C5CF561c4172AC")
        await Contract(address=address, chain_id=480).create()
        await Contract(address=address, chain_id=1).create()

        await self.service.update_safe_contracts_info(chain_id=480)

        updated_contract = await Contract.get_contract(address=address, chain_id=480)
        self.assertEqual(updated_contract.name, "SafeMigration")
        self.assertEqual(updated_contract.display_name, "SafeMigration 1.5.0")
        self.assertTrue(updated_contract.trusted_for_delegate_call)

        other_chain_contract = await Contract.get_contract(address=address, chain_id=1)
        self.assertIsNone(other_chain_contract.name)
        self.assertFalse(other_chain_contract.trusted_for_delegate_call)

    @db_session_context
    async def test_sync_safe_contracts(self):
        chain_id = 480
        safe_addresses = [
            HexBytes(address)
            for _, _, address in self.service._get_default_deployments_by_version()
        ]
        non_safe_address = HexBytes("0x0000000000000000000000000000000000000001")
        source, _ = await AbiSource.get_or_create("Etherscan", "")
        abi, _ = await Abi.get_or_create_abi(abi_json=[], source_id=source.id)
        await Contract(
            address=safe_addresses[0],
            chain_id=chain_id,
            abi_id=abi.id,
            fetch_retries=91,
        ).create()
        await Contract(
            address=safe_addresses[1], chain_id=chain_id, fetch_retries=91
        ).create()
        await Contract(address=safe_addresses[1], chain_id=1, fetch_retries=91).create()
        await Contract(
            address=non_safe_address, chain_id=chain_id, fetch_retries=91
        ).create()

        created_count, addresses = await self.service.sync_safe_contracts(chain_id)

        self.assertEqual(created_count, len(safe_addresses) - 2)
        self.assertCountEqual(
            addresses, [to_0x_hex_str(address) for address in safe_addresses[1:]]
        )
        db_session.expire_all()
        fetch_retries = {
            (bytes(contract.address), contract.chain_id): contract.fetch_retries
            for contract in await Contract.get_all()
        }
        self.assertEqual(fetch_retries[(safe_addresses[0], chain_id)], 91)
        self.assertEqual(fetch_retries[(safe_addresses[1], chain_id)], 0)
        self.assertEqual(fetch_retries[(safe_addresses[1], 1)], 91)
        self.assertEqual(fetch_retries[(non_safe_address, chain_id)], 91)
