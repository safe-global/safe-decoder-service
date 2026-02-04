from app.commands.styles import print_command_title
from app.services.safe_contracts_service import (
    get_safe_contract_service,
)


async def setup_safe_contracts():
    print_command_title("Configuring Safe contracts metadata")
    service = get_safe_contract_service()
    await service.update_safe_contracts_info()
