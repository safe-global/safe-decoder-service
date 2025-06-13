from app.commands.styles import print_command_title
from app.services.safe_contracts_service import (
    update_safe_contracts_info,
)


async def setup_safe_contracts():
    print_command_title("Configuring Safe contracts metadata")
    await update_safe_contracts_info()
