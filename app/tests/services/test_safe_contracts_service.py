import unittest
from unittest.mock import AsyncMock, patch

from hexbytes import HexBytes

from app.datasources.db.database import db_session_context
from app.services.safe_contracts_service import (
    SafeContractsService,
    get_safe_contract_service,
)
from app.tests.datasources.db.async_db_test_case import AsyncDbTestCase
from app.tests.datasources.db.factory import contract_factory


class TestSafeContractsService(unittest.IsolatedAsyncioTestCase):
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
        )
        mock_update.assert_any_call(
            address=HexBytes("0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526"),
            name="MultiSend",
            display_name="Safe: MultiSend 1.4.1",
            trusted_for_delegate_call=False,
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


class TestSafeContractsServiceIntegration(AsyncDbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = get_safe_contract_service()
        self.service._chain_exists_cache.clear()

    @db_session_context
    async def test_is_new_chain(self):
        is_new = await self.service.is_new_chain(999)
        self.assertTrue(is_new)

        await contract_factory(chain_id=1)

        is_new = await self.service.is_new_chain(1)
        self.assertFalse(is_new)

        is_new = await self.service.is_new_chain(1)
        self.assertFalse(is_new)

        is_new = await self.service.is_new_chain(999)
        self.assertTrue(is_new)

    @db_session_context
    async def test_is_new_chain_singleton_cache_shared(self):
        await contract_factory(chain_id=5)

        service1 = get_safe_contract_service()
        is_new = await service1.is_new_chain(5)
        self.assertFalse(is_new)

        service2 = get_safe_contract_service()
        is_new = await service2.is_new_chain(5)
        self.assertFalse(is_new)

        self.assertIs(service1, service2)
        self.assertIn(5, service1._chain_exists_cache)
