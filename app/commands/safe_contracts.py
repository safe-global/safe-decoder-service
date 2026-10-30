# SPDX-License-Identifier: FSL-1.1-MIT
from app.commands.styles import print_command_title, success
from app.services.safe_contracts_service import (
    get_safe_contract_service,
)
from app.workers.tasks import broker_connection, get_contract_metadata_task


async def setup_safe_contracts():
    print_command_title("Configuring Safe contracts metadata")
    service = get_safe_contract_service()
    await service.update_safe_contracts_info()


async def sync_safe_contracts_command(chain_ids: list[int]):
    print_command_title("Syncing Safe contracts")
    service = get_safe_contract_service()
    async with broker_connection():
        for chain_id in chain_ids:
            created_count, addresses = await service.sync_safe_contracts(chain_id)
            for address in addresses:
                await get_contract_metadata_task.kiq(
                    address=address, chain_id=chain_id, skip_attempt_download=True
                )
            success(
                f"Chain {chain_id}: created {created_count} Safe contracts, "
                f"enqueued {len(addresses)} without ABI"
            )
