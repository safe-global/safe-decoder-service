import json
import unittest
from unittest.mock import MagicMock, patch

from app.services.events import EventsService


class TestEventsService(unittest.TestCase):

    def test_is_event_valid(self):
        valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertTrue(EventsService._is_processable_event(valid_event))

        valid_event = {
            "chainId": "123",
            "type": "transaction",
            "to": "0x6ed857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertFalse(EventsService._is_processable_event(valid_event))

        valid_event = {
            "chainId": "123",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x123456789",
        }
        self.assertFalse(EventsService._is_processable_event(valid_event))

        valid_event = {
            "chainId": "chainId",
            "type": "EXECUTED_MULTISIG_TRANSACTION",
            "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
        }
        self.assertFalse(EventsService._is_processable_event(valid_event))

        invalid_event_missing_chain_id = {"type": "transaction"}
        self.assertFalse(
            EventsService._is_processable_event(invalid_event_missing_chain_id)
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

    @patch("logging.error")
    def test_process_event_invalid_json(self, mock_log):
        invalid_message = '{"chainId": "123", "type": "transaction"'

        EventsService().process_event(invalid_message)

        mock_log.assert_called_with(
            'Unsupported message. Cannot parse as JSON: {"chainId": "123", "type": "transaction"'
        )

    @patch("app.workers.tasks.get_contract_metadata_task.send")
    def test_process_event_calls_send(self, mock_get_contract_metadata_task):
        mock_get_contract_metadata_task.send = MagicMock()

        valid_message = json.dumps(
            {
                "chainId": "1",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
            }
        )

        EventsService().process_event(valid_message)

        mock_get_contract_metadata_task.assert_called_once_with(
            "0x6ED857dc1da2c41470A95589bB482152000773e9", 1
        )
