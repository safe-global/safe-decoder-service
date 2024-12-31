import enum
import logging
from dataclasses import dataclass
from functools import cache

from eth_typing import ChecksumAddress
from safe_eth.eth import EthereumNetwork
from safe_eth.eth.clients import (
    AsyncBlockscoutClient,
    AsyncSourcifyClient,
    BlockScoutConfigurationProblem,
    ContractMetadata,
    EtherscanClientConfigurationProblem,
    EtherscanRateLimitError,
    SourcifyClientConfigurationProblem,
)
from safe_eth.eth.clients.etherscan_client_v2 import AsyncEtherscanClientV2

from app.config import settings

logger = logging.getLogger(__name__)


class ClientSource(enum.Enum):
    ETHERSCAN = "Etherscan"
    SOURCIFY = "Sourcify"
    BLOCKSCOUT = "Blockscout"


@dataclass
class EnhancedContractMetadata:
    address: ChecksumAddress
    metadata: ContractMetadata | None
    source: ClientSource | None
    chain_id: int


@cache
def get_contract_metadata_service():
    return ContractMetadataService(settings.ETHERSCAN_API_KEY)


class ContractMetadataService:
    def __init__(self, etherscan_api_key: str):
        self.etherscan_api_key = etherscan_api_key

    def _get_etherscan_client(self, chain_id: int) -> AsyncEtherscanClientV2 | None:
        try:
            return AsyncEtherscanClientV2(
                EthereumNetwork(chain_id),
                api_key=self.etherscan_api_key,
                max_requests=settings.ETHERSCAN_MAX_REQUESTS,
            )
        except EtherscanClientConfigurationProblem:
            logger.warning(
                "Etherscan client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    def _get_blockscout_client(self, chain_id: int) -> AsyncBlockscoutClient | None:
        try:
            return AsyncBlockscoutClient(
                EthereumNetwork(chain_id), max_requests=settings.BLOCKSCOUT_MAX_REQUESTS
            )
        except BlockScoutConfigurationProblem:
            logger.warning(
                "Blockscout client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    def _get_sourcify_client(self, chain_id: int) -> AsyncSourcifyClient | None:
        try:
            return AsyncSourcifyClient(
                EthereumNetwork(chain_id), max_requests=settings.SOURCIFY_MAX_REQUESTS
            )
        except SourcifyClientConfigurationProblem:
            logger.warning(
                "Sourcify client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    @cache
    def enabled_clients(
        self, chain_id: int
    ) -> list[AsyncEtherscanClientV2 | AsyncBlockscoutClient | AsyncSourcifyClient]:
        """
        Return a list of available chains for the provided chain_id.
        First etherscan, second sourcify, third blockscout.

        :param chain_id:
        :return:
        """
        enabled_clients: list[
            AsyncEtherscanClientV2 | AsyncBlockscoutClient | AsyncSourcifyClient
        ] = []
        if etherscan_client := self._get_etherscan_client(chain_id):
            enabled_clients.append(etherscan_client)
        if sourcify_client := self._get_sourcify_client(chain_id):
            enabled_clients.append(sourcify_client)
        if blockscout_client := self._get_blockscout_client(chain_id):
            enabled_clients.append(blockscout_client)
        return enabled_clients

    @staticmethod
    @cache
    def get_client_enum(
        client: AsyncEtherscanClientV2 | AsyncSourcifyClient | AsyncBlockscoutClient,
    ) -> ClientSource:
        if isinstance(client, AsyncEtherscanClientV2):
            return ClientSource.ETHERSCAN
        elif isinstance(client, AsyncSourcifyClient):
            return ClientSource.SOURCIFY
        elif isinstance(client, AsyncBlockscoutClient):
            return ClientSource.BLOCKSCOUT

    async def get_contract_metadata(
        self, contract_address: ChecksumAddress, chain_id: int
    ) -> EnhancedContractMetadata:
        """
        Get contract metadata from every enabled client

        :param chain_id:
        :param contract_address: Contract address
        :return: Contract Metadata if found from any client, otherwise None
        """
        for client in self.enabled_clients(chain_id):
            try:
                contract_metadata = await client.async_get_contract_metadata(
                    contract_address
                )
                if contract_metadata:

                    return EnhancedContractMetadata(
                        address=contract_address,
                        metadata=contract_metadata,
                        source=self.get_client_enum(client),
                        chain_id=chain_id,
                    )

            except (IOError, EtherscanRateLimitError):
                logger.debug(
                    "Cannot get metadata for contract=%s on network=%s using client=%s",
                    contract_address,
                    EthereumNetwork(chain_id),
                    client.__class__.__name__,
                )

        return EnhancedContractMetadata(
            address=contract_address, metadata=None, source=None, chain_id=chain_id
        )

    async def process_contract_metadata(
        self, metadata: EnhancedContractMetadata
    ) -> bool:
        # TODO process and insert ABI if exist otherwise update the fetch retries
        if metadata:
            return True
        return False
