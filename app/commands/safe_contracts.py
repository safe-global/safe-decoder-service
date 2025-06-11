import asyncio

import requests
from hexbytes import HexBytes
from safe_eth.safe.safe_deployments import default_safe_deployments
from sqlalchemy import update
from sqlmodel import col

from app.commands.styles import error, print_command_title, success
from app.datasources.db.database import db_session
from app.datasources.db.models import Abi, AbiSource, Contract

TRUSTED_FOR_DELEGATE_CALL = [
    "MultiSendCallOnly",
    "SignMessageLib",
    "SafeMigration",
]


def generate_safe_contract_display_name(contract_name: str, version: str) -> str:
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


def _get_default_deployments_by_version() -> list[tuple[str, str, str]]:
    """
    Get the default deployments by version that are inserted on database.

    :return: list of (version, contract_name, contract_address)
    """
    chain_deployments: list[tuple[str, str, str]] = []
    versions = list(default_safe_deployments.keys())
    for version in versions:
        for contract_name, addresses in default_safe_deployments[version].items():
            for contract_address in addresses:
                chain_deployments.append((version, contract_name, contract_address))

    return chain_deployments


async def _update_contracts_from_deployments(
    deployments: list[tuple[str, str, str]],
) -> None:
    """
    Update contracts from given deployments list.
    """
    for version, contract_name, contract_address in deployments:
        display_name = generate_safe_contract_display_name(contract_name, version)
        query = (
            update(Contract)
            .where(col(Contract.address) == HexBytes(contract_address))
            .values(
                name=contract_name,
                display_name=display_name,
                trusted_for_delegate=contract_name in TRUSTED_FOR_DELEGATE_CALL,
            )
        )
        result = await db_session.execute(query)
        await db_session.commit()
        if result.rowcount == 0:
            error(f"Could not find any contract with address: {contract_address}")
        else:
            success(
                f"Updated contract with address: {contract_address} in {result.rowcount} chains"
            )


async def setup_safe_contracts():
    print_command_title("Configuring Safe contracts metadata")
    deployments = _get_default_deployments_by_version()
    await _update_contracts_from_deployments(deployments)


# Remove, just for test
async def download_contracts_from_prod_decoder():
    deployments = _get_default_deployments_by_version()
    abi_source, _ = await AbiSource.get_or_create(name="Safe", url="https://safe.eth")
    for version, contract_name, contract_address in deployments:
        response = requests.get(
            f"https://safe-decoder.safe.global/api/v1/contracts/{contract_address}?limit=30"
        )
        response_json = response.json()
        for downloaded_contract in response_json["results"]:
            abi, _ = await Abi.get_or_create_abi(
                abi_json=response_json["results"][0]["abi"]["abiJson"],
                source_id=abi_source.id,
            )
            contract = await Contract.get_or_create(
                address=HexBytes(contract_address),
                chain_id=downloaded_contract["chainId"],
                abi_id=abi.id,
            )
            print(contract)

        # Avoid rate limit
        await asyncio.sleep(0.1)
