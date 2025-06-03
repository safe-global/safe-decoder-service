import json
import logging

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from safe_eth.eth.utils import fast_is_checksum_address
from safe_eth.safe.multi_send import MultiSend

from ..workers.tasks import get_contract_metadata_task

logger = logging.getLogger(__name__)


class EventsService:

    def get_contracts_from_data(self, data: HexStr | None) -> set[ChecksumAddress]:
        """
        Extract contract addresses involved in the transaction from `data`.
        Currently only MultiSend calls are decoded

        :param data:
        :return: Contract addresses involved in the transaction
        """
        if not data:
            return set()
        return {
            multisend_tx.to
            for multisend_tx in MultiSend.from_transaction_data(HexBytes(data))
        }

    def process_event(self, message: str) -> None:
        """
        Processes the incoming event message.

        :param message: The incoming message to process, expected to be a JSON string.
        """
        logger.debug("Received event %s", message)
        try:
            tx_service_event = json.loads(message)
            if self._is_processable_event(tx_service_event):
                data: HexStr | None = tx_service_event["data"]
                if data:
                    # If data is not available, it should be an ether transfer to a EOA
                    chain_id: int = int(tx_service_event["chainId"])
                    to: ChecksumAddress = tx_service_event["to"]
                    contracts_from_data: set[ChecksumAddress] = (
                        self.get_contracts_from_data(data)
                    )

                    for contract_address in {to, *contracts_from_data}:
                        get_contract_metadata_task.send(
                            address=contract_address, chain_id=chain_id
                        )
        except json.JSONDecodeError:
            logger.error("Unsupported message. Cannot parse as JSON: %s", message)

    @staticmethod
    def _is_processable_event(tx_service_event: dict) -> bool:
        """
        Validates if the event has the required fields 'chainId', 'type', and 'to' as strings,
        and if the event type and address meet the expected criteria.

        :param tx_service_event: The event object to validate.
        :return: `True` if the event is valid, `False` otherwise.
        """
        event_type = tx_service_event.get("type")
        chain_id = tx_service_event.get("chainId")
        address = tx_service_event.get("to")
        data = tx_service_event.get("data", 0)  # Data must be present

        return (
            isinstance(event_type, str)
            and event_type == "EXECUTED_MULTISIG_TRANSACTION"
            and isinstance(chain_id, str)
            and chain_id.isdigit()
            and (data is None or isinstance(data, str))
            and isinstance(address, str)
            and fast_is_checksum_address(address)
        )
