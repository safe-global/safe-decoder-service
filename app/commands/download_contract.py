from hexbytes import HexBytes

from app.commands.styles import error, print_command_title, success
from app.datasources.db.models import Contract
from app.services.contract_metadata_service import get_contract_metadata_service
from app.workers.tasks import get_contract_metadata_task


async def download_contract_command(address: str, chain_id: int):
    print_command_title(f"Downloading contract {address}")
    contract = await Contract.get_contract(HexBytes(address), chain_id)
    if contract:
        print(
            f"Contract: {address}, retries: {contract.fetch_retries}, contains ABI: {True if contract.abi_id else False}"
        )
    else:
        print(f"Contract {address} was never retrieved")

    contract_metadata_service = get_contract_metadata_service()
    contract_metadata = await contract_metadata_service.get_contract_metadata(
        contract_address=address, chain_id=chain_id
    )
    result = await contract_metadata_service.process_contract_metadata(
        contract_metadata
    )
    if result:
        success("Success download contract metadata")
        if proxy_implementation_address := contract_metadata_service.get_proxy_implementation_address(
            contract_metadata
        ):
            print("The contract is a proxy.")
            print(
                f"Adding task to download proxy implementation metadata with address {proxy_implementation_address}"
            )
            get_contract_metadata_task.send(
                address=proxy_implementation_address, chain_id=chain_id
            )
    else:
        error("Failed to download contract metadata")
