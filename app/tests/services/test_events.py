import json
import unittest
from unittest.mock import MagicMock, call, patch

from eth_typing import HexStr
from safe_eth.util.util import to_0x_hex_str

from app.services.events import EventsService
from app.tests.services.mocks_multisend import multisend_data


class TestEventsService(unittest.TestCase):

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

    @patch("logging.error")
    def test_process_event_invalid_json(self, mock_log):
        invalid_message = '{"chainId": "123", "type": "transaction"'

        EventsService().process_event(invalid_message)

        mock_log.assert_called_with(
            'Unsupported message. Cannot parse as JSON: {"chainId": "123", "type": "transaction"'
        )

    @patch("app.workers.tasks.get_contract_metadata_task.send")
    def test_process_event_calls_send(self, mock_get_contract_metadata_task: MagicMock):
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
        EventsService().process_event(not_valid_message)
        mock_get_contract_metadata_task.assert_not_called()

        valid_message = json.dumps(
            {
                "chainId": "1",
                "type": "EXECUTED_MULTISIG_TRANSACTION",
                "to": "0x6ED857dc1da2c41470A95589bB482152000773e9",
                "data": HexStr("0x4815"),
            }
        )

        EventsService().process_event(valid_message)
        mock_get_contract_metadata_task.assert_called_once_with(
            address="0x6ED857dc1da2c41470A95589bB482152000773e9", chain_id=1
        )

    @patch("app.workers.tasks.get_contract_metadata_task.send")
    def test_process_event_with_multisend_calls_send(
        self, mock_get_contract_metadata_task: MagicMock
    ):
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
        events_service.process_event(valid_message)
        self.assertEqual(mock_get_contract_metadata_task.call_count, 2)
        mock_get_contract_metadata_task.assert_has_calls(
            [
                call(address="0x6ED857dc1da2c41470A95589bB482152000773e9", chain_id=1),
                call(address="0x5B9ea52Aaa931D4EEf74C8aEaf0Fe759434FeD74", chain_id=1),
            ],
            any_order=True,
        )
