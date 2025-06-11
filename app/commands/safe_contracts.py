import asyncio

import requests
from hexbytes import HexBytes

from app.commands.styles import print_command_title
from app.datasources.db.models import Abi, AbiSource, Contract
from app.services.safe_contracts_service import (
    _get_default_deployments_by_version,
    update_safe_contracts_info,
)


async def setup_safe_contracts():
    print_command_title("Configuring Safe contracts metadata")
    await update_safe_contracts_info()


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
