import unittest
from unittest.mock import patch

from app.services.events import EventsService


class TestEventsService(unittest.TestCase):

    def test_is_event_valid(self):
        valid_event = {"chainId": "123", "type": "transaction"}
        self.assertTrue(EventsService().is_event_valid(valid_event))

    def test_is_event_invalid(self):
        invalid_event_missing_chain_id = {"type": "transaction"}
        self.assertFalse(EventsService().is_event_valid(invalid_event_missing_chain_id))

        invalid_event_missing_type = {"chainId": "123"}
        self.assertFalse(EventsService().is_event_valid(invalid_event_missing_type))

        invalid_event_invalid_chain_id = {"chainId": 123, "type": "transaction"}
        self.assertFalse(EventsService().is_event_valid(invalid_event_invalid_chain_id))

        invalid_event_invalid_type = {"chainId": "123", "type": 123}
        self.assertFalse(EventsService().is_event_valid(invalid_event_invalid_type))

    @patch("logging.error")
    def test_process_event_valid_message(self, mock_log):
        valid_message = '{"chainId": "123", "type": "transaction"}'

        EventsService().process_event(valid_message)

        mock_log.assert_not_called()

    @patch("logging.error")
    def test_process_event_invalid_json(self, mock_log):
        invalid_message = '{"chainId": "123", "type": "transaction"'

        EventsService().process_event(invalid_message)

        mock_log.assert_called_with(
            'Unsupported message. Cannot parse as JSON: {"chainId": "123", "type": "transaction"'
        )

        invalid_message_invalid_type = '{"chainId": "123", "type": 123}'

        EventsService().process_event(invalid_message_invalid_type)

        mock_log.assert_called_with(
            'Unsupported message. A valid message should have at least \'chainId\' and \'type\': {"chainId": "123", "type": 123}'
        )
