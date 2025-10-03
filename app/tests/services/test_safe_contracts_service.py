import unittest
from unittest.mock import AsyncMock, patch

from hexbytes import HexBytes

from app.services.safe_contracts_service import (
    _generate_safe_contract_display_name,
    update_safe_contracts_info,
)


class TestContractMetadataService(unittest.IsolatedAsyncioTestCase):
    def test_generate_safe_contract_display_name(self):
        test_cases = [
            ("GnosisSafe", "1.3.0", "Safe 1.3.0"),  # removes Gnosis, keeps Safe
            ("GnosisMultiSend", "1.0.0", "Safe: MultiSend 1.0.0"),  # adds Safe:
            ("SignMessageLib", "1.0.0", "Safe: SignMessageLib 1.0.0"),  # adds Safe:
            ("SafeMigration", "1.1.1", "SafeMigration 1.1.1"),  # already has Safe
            (
                "GnosisSafeProxyFactory",
                "1.2.0",
                "SafeProxyFactory 1.2.0",
            ),  # removes Gnosis, keeps Safe
        ]
        for name, version, expected_result in test_cases:
            self.assertEqual(
                _generate_safe_contract_display_name(name, version), expected_result
            )

    @patch("app.services.safe_contracts_service._get_default_deployments_by_version")
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

        # First contract gets updated, second does not
        mock_update.side_effect = [2, 0]
        await update_safe_contracts_info()
        self.assertEqual(mock_update.call_count, 2)

        mock_update.assert_any_call(
            address=HexBytes("0x9641d764fc13c8B624c04430C7356C1C7C8102e2"),
            name="MultiSendCallOnly",
            display_name="Safe: MultiSendCallOnly 1.4.1",
            trusted_for_delegate_call=True,  # Trusted contract
        )
        mock_update.assert_any_call(
            address=HexBytes("0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526"),
            name="MultiSend",
            display_name="Safe: MultiSend 1.4.1",
            trusted_for_delegate_call=False,  # Not trusted
        )

        mock_logger.info.assert_called_once_with(
            "Updated contract with address: 0x9641d764fc13c8B624c04430C7356C1C7C8102e2 in 2 chains"
        )
        mock_logger.warning.assert_called_once_with(
            "Could not find any contract with address: 0x38869bf66a61cF6bDB996A6aE40D5853Fd43B526"
        )
