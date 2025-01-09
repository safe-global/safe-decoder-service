import json
import logging
from typing import Dict

from safe_eth.eth.utils import fast_is_checksum_address

from ..workers.tasks import get_contract_metadata_task


class EventsService:

    def process_event(self, message: str) -> None:
        """
        Processes the incoming event message.

        :param message: The incoming message to process, expected to be a JSON string.
        """
        try:
            tx_service_event = json.loads(message)
            if self._is_processable_event(tx_service_event):
                chain_id = int(tx_service_event["chainId"])
                contract_address = tx_service_event["to"]
                get_contract_metadata_task.send(
                    address=contract_address, chain_id=chain_id
                )
        except json.JSONDecodeError:
            logging.error(f"Unsupported message. Cannot parse as JSON: {message}")

    @staticmethod
    def _is_processable_event(tx_service_event: Dict) -> bool:
        """
        Validates if the event has the required fields 'chainId', 'type', and 'to' as strings,
        and if the event type and address meet the expected criteria.

        :param tx_service_event: The event object to validate.
        :return: True if the event is valid, False otherwise.
        """
        chain_id = tx_service_event.get("chainId")
        event_type = tx_service_event.get("type")
        address = tx_service_event.get("to")

        return (
            isinstance(chain_id, str)
            and chain_id.isdigit()
            and isinstance(event_type, str)
            and event_type == "EXECUTED_MULTISIG_TRANSACTION"
            and isinstance(address, str)
            and fast_is_checksum_address(address)
        )
