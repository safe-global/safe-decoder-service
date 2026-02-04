import logging
from functools import cache

from hexbytes import HexBytes
from safe_eth.safe.safe_deployments import default_safe_deployments

from app.config import settings
from app.datasources.db.models import Contract

logger = logging.getLogger(__name__)


class SafeContractsService:
    def __init__(self):
        self._chain_exists_cache: set[int] = set()

    @staticmethod
    @cache
    def _get_default_deployments_by_version() -> list[tuple[str, str, str]]:
        """
        Get the default deployments by version that are inserted on database.

        :return: list of (version, contract_name, contract_address)
        """
        chain_deployments: list[tuple[str, str, str]] = []
        for version in default_safe_deployments:
            for contract_name, addresses in default_safe_deployments[version].items():
                for contract_address in addresses:
                    chain_deployments.append((version, contract_name, contract_address))

        return chain_deployments

    @staticmethod
    def _generate_safe_contract_display_name(contract_name: str, version: str) -> str:
        """
        Generates the display name for Safe contract.
        Append Safe at the beginning if the contract name doesn't contain Safe word and append the contract version at the end.

        :param contract_name:
        :param version:
        :return: display_name
        """
        contract_name = contract_name.replace("Gnosis", "")
        if "safe" not in contract_name.lower():
            return f"Safe: {contract_name} {version}"
        else:
            return f"{contract_name} {version}"

    async def is_new_chain(self, chain_id: int) -> bool:
        """
        Check if the given chain_id is new (has no contracts yet).

        Results are cached when the chain is not new, as once a chain has contracts,
        it will always have contracts (they are never deleted).

        Args:
            chain_id: The chain ID to check.

        Returns:
            True if the chain is new (no contracts exist), False if contracts already exist.
        """
        if chain_id in self._chain_exists_cache:
            return False

        exists = await Contract.get_chain_exists(chain_id)

        if exists:
            self._chain_exists_cache.add(chain_id)
            return False

        return True

    async def create_safe_contracts_for_new_chain(self, chain_id: int) -> int:
        """
        Create Safe contracts for a new chain if it doesn't exist yet.

        Args:
            chain_id: The chain ID to check and create contracts for.

        Returns:
            Number of contracts created, 0 if chain already exists.
        """
        if not await self.is_new_chain(chain_id):
            logger.debug(
                "Chain %d already exists, skipping Safe contract creation", chain_id
            )
            return 0

        created_count = 0
        for (
            version,
            contract_name,
            contract_address,
        ) in self._get_default_deployments_by_version():
            display_name = self._generate_safe_contract_display_name(
                contract_name, version
            )
            contract, created = await Contract.get_or_create(
                address=HexBytes(contract_address),
                chain_id=chain_id,
                name=contract_name,
                display_name=display_name,
                trusted_for_delegate_call=contract_name
                in settings.CONTRACTS_TRUSTED_FOR_DELEGATE_CALL,
            )
            if created:
                created_count += 1
                logger.info(
                    "Created Safe contract %s (%s) for chain %d",
                    contract_name,
                    contract_address,
                    chain_id,
                )

        if created_count:
            logger.info(
                "Created %d Safe contracts for new chain %d", created_count, chain_id
            )

        return created_count

    async def update_safe_contracts_info(self) -> None:
        """
        Update contracts from given deployments list.
        """
        for (
            version,
            contract_name,
            contract_address,
        ) in self._get_default_deployments_by_version():
            display_name = self._generate_safe_contract_display_name(
                contract_name, version
            )
            affected_rows = await Contract.update_contract_info(
                address=HexBytes(contract_address),
                name=contract_name,
                display_name=display_name,
                trusted_for_delegate_call=contract_name
                in settings.CONTRACTS_TRUSTED_FOR_DELEGATE_CALL,
            )
            if affected_rows:
                logger.info(
                    "Updated contract with address: %s in %d chains",
                    contract_address,
                    affected_rows,
                )
            else:
                logger.warning(
                    "Could not find any contract with address: %s", contract_address
                )


@cache
def get_safe_contract_service() -> SafeContractsService:
    return SafeContractsService()
