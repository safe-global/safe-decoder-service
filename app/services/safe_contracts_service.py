import logging
from functools import cache

from hexbytes import HexBytes
from safe_eth.safe.safe_deployments import default_safe_deployments

from app.config import settings
from app.datasources.db.models import Contract

logger = logging.getLogger(__name__)


def _generate_safe_contract_display_name(contract_name: str, version: str) -> str:
    """
    Generates the display name for Safe contract.
    Append Safe at the beginning if the contract name doesn't contain Safe word and append the contract version at the end.

    :param contract_name:
    :param version:
    :return: display_name
    """
    # Remove gnosis word
    contract_name = contract_name.replace("Gnosis", "")
    if "safe" not in contract_name.lower():
        return f"Safe: {contract_name} {version}"
    else:
        return f"{contract_name} {version}"


@cache
def _get_default_deployments_by_version() -> list[tuple[str, str, str]]:
    """
    Get the default deployments by version that are inserted on database.

    :return: list of (version, contract_name, contract_address)
    """
    chain_deployments: list[tuple[str, str, str]] = []
    # versions = list(default_safe_deployments.keys())
    for version in default_safe_deployments:
        for contract_name, addresses in default_safe_deployments[version].items():
            for contract_address in addresses:
                chain_deployments.append((version, contract_name, contract_address))

    return chain_deployments


async def update_safe_contracts_info() -> None:
    """
    Update contracts from given deployments list.
    """
    for (
        version,
        contract_name,
        contract_address,
    ) in _get_default_deployments_by_version():
        display_name = _generate_safe_contract_display_name(contract_name, version)
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
