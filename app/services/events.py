import json
import logging
from typing import Dict


class EventsService:

    def process_event(self, message: str) -> None:
        """
        Processes the incoming event message.

        :param message: The incoming message to process, expected to be a JSON string.
        """
        try:
            tx_service_event = json.loads(message)

            if self.is_event_valid(tx_service_event):
                # TODO: process event!
                pass
            else:
                logging.error(
                    f"Unsupported message. A valid message should have at least 'chainId' and 'type': {message}"
                )
        except json.JSONDecodeError:
            logging.error(f"Unsupported message. Cannot parse as JSON: {message}")

    def is_event_valid(self, tx_service_event: Dict) -> bool:
        """
        Validates if the event has the required fields 'chainId' and 'type' as strings.

        :param tx_service_event: The event object to validate.
        :return: True if the event is valid (both 'chainId' and 'type' are strings), False otherwise.
        """
        return isinstance(tx_service_event.get("chainId"), str) and isinstance(
            tx_service_event.get("type"), str
        )
