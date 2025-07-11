import enum
import logging
from dataclasses import dataclass
from functools import cache
from typing import cast

from eth_typing import ChecksumAddress
from hexbytes import HexBytes
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
from safe_eth.eth.utils import fast_to_checksum_address

from app.config import settings
from app.datasources.cache.redis import get_redis
from app.datasources.db.models import Abi, AbiSource, Contract

logger = logging.getLogger(__name__)


class ContractSource(enum.Enum):
    ETHERSCAN = "Etherscan"
    SOURCIFY = "Sourcify"
    BLOCKSCOUT = "Blockscout"


@dataclass
class EnhancedContractMetadata:
    address: ChecksumAddress
    metadata: ContractMetadata | None
    source: ContractSource | None
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
        :param chain_id:
        :return: List of available clients for the provided `chain_id`.
            First Etherscan, second Sourcify, third Blockscout.
        """
        clients = (
            self._get_etherscan_client(chain_id),
            self._get_sourcify_client(chain_id),
            self._get_blockscout_client(chain_id),
        )
        return [client for client in clients if client]

    @staticmethod
    @cache
    def get_client_enum(
        client: AsyncEtherscanClientV2 | AsyncSourcifyClient | AsyncBlockscoutClient,
    ) -> ContractSource:
        if isinstance(client, AsyncEtherscanClientV2):
            return ContractSource.ETHERSCAN
        if isinstance(client, AsyncSourcifyClient):
            return ContractSource.SOURCIFY
        if isinstance(client, AsyncBlockscoutClient):
            return ContractSource.BLOCKSCOUT

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

    @staticmethod
    async def process_contract_metadata(
        contract_metadata: EnhancedContractMetadata,
    ) -> bool:
        """
        Store ABI and contract if exists, otherwise update contract fetch_retries.

        :param contract_metadata:
        :return:
        """
        contract, _ = await Contract.get_or_create(
            address=HexBytes(contract_metadata.address),
            chain_id=contract_metadata.chain_id,
        )

        if contract_metadata.metadata:
            if contract_metadata.source:
                source = await AbiSource.get_abi_source(
                    name=contract_metadata.source.value
                )
                if source is None:
                    logging.error(
                        f"Abi source {contract_metadata.source.value} does not exist"
                    )
                    return False
            abi, _ = await Abi.get_or_create_abi(
                abi_json=contract_metadata.metadata.abi,
                source_id=source.id,
            )
            contract.abi_id = abi.id
            contract.name = contract_metadata.metadata.name
            if contract_metadata.metadata.implementation:
                contract.implementation = HexBytes(
                    contract_metadata.metadata.implementation
                )

        contract.fetch_retries += 1
        await contract.update()
        return bool(contract_metadata.metadata)

    @staticmethod
    def get_proxy_implementation_address(
        contract_metadata: EnhancedContractMetadata,
    ) -> ChecksumAddress | None:
        if contract_metadata.metadata and contract_metadata.metadata.implementation:
            return fast_to_checksum_address(contract_metadata.metadata.implementation)
        return None

    @staticmethod
    async def should_attempt_download(
        contract_address: ChecksumAddress,
        chain_id: int,
        max_retries: int,
    ) -> bool:
        """
        :param contract_address:
        :param chain_id:
        :param max_retries:
        :return: `True` if `fetch retries` are less than the number of `max_retries` and there is not ABI, `False` otherwise.
            `False` is being cached to avoid query the database in the future for the same number of retries.
        """
        redis = get_redis()
        cache_key = (
            f"should_attempt_download:{contract_address}:{chain_id}:{max_retries}"
        )
        # Try from cache first
        cached_retries: bytes = cast(bytes, redis.get(cache_key))
        if cached_retries is not None:
            return bool(int(cached_retries.decode()))
        else:
            contract = await Contract.get_contract(
                address=HexBytes(contract_address), chain_id=chain_id
            )

            if contract and (contract.fetch_retries > max_retries or contract.abi_id):
                redis.set(cache_key, 0)
                return False

            return True
