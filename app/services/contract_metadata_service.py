import asyncio
import logging
from functools import cache
from typing import Optional, Type

from eth_typing import ChecksumAddress
from safe_eth.eth import EthereumNetwork
from safe_eth.eth.clients import (
    BlockscoutClient,
    BlockScoutConfigurationProblem,
    ContractMetadata,
    EtherscanClient,
    EtherscanClientConfigurationProblem,
    SourcifyClient,
    SourcifyClientConfigurationProblem,
)
from safe_eth.eth.utils import fast_to_checksum_address

from app.config import settings

logger = logging.getLogger(__name__)


class PoolContractClient:

    def __init__(
        self,
        client_class: (
            Type[EtherscanClient] | Type[BlockscoutClient] | Type[SourcifyClient]
        ),
        api_key,
        max_requests: int,
    ):
        self.client_class = client_class
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_requests)

    def _get_etherscan_client(self, chain_id: int) -> Optional[EtherscanClient]:
        try:
            return EtherscanClient(EthereumNetwork(chain_id), api_key=self.api_key)
        except EtherscanClientConfigurationProblem:
            logger.warning(
                "Etherscan client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    def _get_blockscout_client(self, chain_id: int) -> Optional[BlockscoutClient]:
        try:
            return BlockscoutClient(EthereumNetwork(chain_id))
        except BlockScoutConfigurationProblem:
            logger.warning(
                "Blockscout client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    def _get_sourcify_client(self, chain_id: int) -> Optional[SourcifyClient]:
        try:
            return SourcifyClient(EthereumNetwork(chain_id))
        except SourcifyClientConfigurationProblem:
            logger.warning(
                "Sourcify client is not available for current network %s",
                EthereumNetwork(chain_id),
            )
            return None

    @cache
    def get_client(
        self, chain_id: int
    ) -> EtherscanClient | BlockscoutClient | SourcifyClient | None:
        if self.client_class is EtherscanClient:
            return self._get_etherscan_client(chain_id)
        elif self.client_class is BlockscoutClient:
            return self._get_blockscout_client(chain_id)
        elif self.client_class is SourcifyClient:
            return self._get_sourcify_client(chain_id)

        return None

    async def get_contract_metadata(
        self, contract_address: ChecksumAddress | str, chain_id: int
    ) -> Optional[ContractMetadata]:
        if not (client := self.get_client(chain_id)):
            return None
        async with self.semaphore:
            contract_metadata = client.get_contract_metadata(
                fast_to_checksum_address(contract_address)
            )
            return contract_metadata


@cache
def get_contract_metadata_service():
    return ContractMetadataService()


class ContractMetadataService:
    def __init__(self):
        self.etherscan_client = PoolContractClient(
            EtherscanClient,
            api_key=settings.ETHERSCAN_API_KEY,
            max_requests=settings.ETHERSCAN_MAX_REQUESTS,
        )
        self.blockscout_client = PoolContractClient(
            BlockscoutClient,
            api_key=settings.BLOCKSCOUT_API_KEY,
            max_requests=settings.BLOCKSCOUT_MAX_REQUESTS,
        )
        self.sourcify_client = PoolContractClient(
            SourcifyClient,
            api_key=settings.SOURCIFY_API_KEY,
            max_requests=settings.SOURCIFY_MAX_REQUESTS,
        )
        self.enabled_clients = [
            client
            for client in (
                self.sourcify_client,
                self.etherscan_client,
                self.blockscout_client,
            )
            if client
        ]

    async def get_contract_metadata(
        self, contract_address: ChecksumAddress | str, chain_id: int
    ) -> Optional[ContractMetadata]:
        """
        Get contract metadata from every enabled client

        :param contract_address: Contract address
        :return: Contract Metadata if found from any client, otherwise None
        """
        for client in self.enabled_clients:
            try:
                contract_metadata = await client.get_contract_metadata(
                    contract_address, chain_id
                )
                if contract_metadata:
                    return contract_metadata
            except IOError:
                logger.debug(
                    "Cannot get metadata for contract=%s on network=%s using client=%s",
                    contract_address,
                    EthereumNetwork(chain_id),
                    client.__class__.__name__,
                )

        return None
