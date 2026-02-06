import json
import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

from eth_typing import HexStr
from safe_eth.util.util import to_0x_hex_str

from app.services.events import EventsService, logger
from app.tests.services.mocks_multisend import multisend_data


class TestEventsService(unittest.IsolatedAsyncioTestCase):
    def test_get_contracts_from_data(self):
        events_service = EventsService()
        self.assertEqual(events_service.get_contracts_from_data(None), set())
        self.assertEqual(events_service.get_contracts_from_data(HexStr("0x")), set())
        self.assertEqual(events_service.get_contracts_from_data(HexStr("0x8")), set())
        self.assertEqual(
            events_service.get_contracts_from_data(to_0x_hex_str(multisend_data)),
            {"0x5B9ea52Aaa931D4EEf74C8aEaf0Fe759434FeD74"},
        )

    def test_is_processable_event(self):
        not_valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertFalse(EventsService._is_processable_event(not_valid_event))

        valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
            "data": None,
        }
        self.assertTrue(EventsService._is_processable_event(valid_event))

        valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
            "data": "0x1234",
        }
        self.assertTrue(EventsService._is_processable_event(valid_event))

        not_valid_event = {
            "chainId": "123",
            "type": "transaction",
            "to": "0x6ed857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertFalse(EventsService._is_processable_event(not_valid_event))

        not_valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x123456789",
        }
        self.assertFalse(EventsService._is_processable_event(not_valid_event))

        not_valid_event = {
            "chainId": "chainId",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertFalse(EventsService._is_processable_event(not_valid_event))

        not_valid_event_missing_chain_id = {"type": "transaction"}
        self.assertFalse(
            EventsService._is_processable_event(not_valid_event_missing_chain_id)
        )

        invalid_event_missing_type = {"chainId": "123"}
        self.assertFalse(
            EventsService._is_processable_event(invalid_event_missing_type)
        )

        invalid_event_invalid_chain_id = {"chainId": 123, "type": "transaction"}
        self.assertFalse(
            EventsService._is_processable_event(invalid_event_invalid_chain_id)
        )

        invalid_event_invalid_type = {"chainId": "123", "type": 123}
        self.assertFalse(
            EventsService._is_processable_event(invalid_event_invalid_type)
        )

    @patch.object(logger, "error")
    async def test_process_event_invalid_json(self, mock_log: MagicMock):
        invalid_message = '{"chainId": "123", "type": "transaction"'

        await EventsService().process_event(invalid_message)

        mock_log.assert_called_with(
            "Unsupported message. Cannot parse as JSON: %s", invalid_message
        )

    @patch("app.workers.tasks.get_contract_metadata_task.send")
    @patch("app.services.events.get_safe_contract_service")
    async def test_process_event_calls_send(
        self,
        mock_get_safe_contract_service: MagicMock,
        mock_get_contract_metadata_task: MagicMock,
    ):
        mock_safe_contract_service = AsyncMock()
        mock_safe_contract_service.safe_contracts_exist.return_value = True
        mock_get_safe_contract_service.return_value = mock_safe_contract_service

        not_valid_message = json.dumps(
            {
                "chainId": "1",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": None,
            }
        )

        # Events with no data should not be indexed, as `to` should be a EOA
        mock_get_contract_metadata_task.assert_not_called()
        await EventsService().process_event(not_valid_message)
        mock_get_contract_metadata_task.assert_not_called()

        valid_message = json.dumps(
            {
                "chainId": "1",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": HexStr("0x4815"),
            }
        )

        await EventsService().process_event(valid_message)
        mock_get_contract_metadata_task.assert_called_once_with(
            address="0x6ED857dc1da2c41470A95589bB482152000773e9", chain_id=1
        )

    @patch("app.workers.tasks.get_contract_metadata_task.send")
    @patch("app.services.events.get_safe_contract_service")
    async def test_process_event_with_multisend_calls_send(
        self,
        mock_get_safe_contract_service: MagicMock,
        mock_get_contract_metadata_task: MagicMock,
    ):
        mock_safe_contract_service = AsyncMock()
        mock_safe_contract_service.safe_contracts_exist.return_value = True
        mock_get_safe_contract_service.return_value = mock_safe_contract_service

        valid_message = json.dumps(
            {
                "chainId": "1",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": to_0x_hex_str(multisend_data),
            }
        )

        mock_get_contract_metadata_task.assert_not_called()
        events_service = EventsService()
        await events_service.process_event(valid_message)
        self.assertEqual(mock_get_contract_metadata_task.call_count, 2)
        mock_get_contract_metadata_task.assert_has_calls(
            [
                call(address="0x6ED857dc1da2c41470A95589bB482152000773e9", chain_id=1),
                call(address="0x5B9ea52Aaa931D4EEf74C8aEaf0Fe759434FeD74", chain_id=1),
            ],
            any_order=True,
        )

    @patch("app.workers.tasks.create_safe_contracts_task_for_new_chains.send")
    @patch("app.services.events.get_safe_contract_service")
    async def test_process_event_calls_create_safe_contracts_task(
        self,
        mock_get_safe_contract_service: MagicMock,
        mock_create_safe_contracts_task: MagicMock,
    ):
        mock_safe_contract_service = AsyncMock()
        mock_safe_contract_service.safe_contracts_exist.return_value = False
        mock_get_safe_contract_service.return_value = mock_safe_contract_service

        valid_message = json.dumps(
            {
                "chainId": "42161",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": HexStr("0x4815"),
            }
        )

        mock_create_safe_contracts_task.assert_not_called()
        await EventsService().process_event(valid_message)
        mock_create_safe_contracts_task.assert_called_once_with(chain_id=42161)

    @patch("app.workers.tasks.create_safe_contracts_task_for_new_chains.send")
    @patch("app.services.events.get_safe_contract_service")
    async def test_process_event_does_not_call_create_safe_contracts_task_when_contracts_exist(
        self,
        mock_get_safe_contract_service: MagicMock,
        mock_create_safe_contracts_task: MagicMock,
    ):
        mock_safe_contract_service = AsyncMock()
        mock_safe_contract_service.safe_contracts_exist.return_value = True
        mock_get_safe_contract_service.return_value = mock_safe_contract_service

        valid_message = json.dumps(
            {
                "chainId": "42161",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": HexStr("0x4815"),
            }
        )

        mock_create_safe_contracts_task.assert_not_called()
        await EventsService().process_event(valid_message)
        mock_create_safe_contracts_task.assert_not_called()
