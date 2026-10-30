# SPDX-License-Identifier: FSL-1.1-MIT
import asyncio
import inspect
from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any

from typer import Option, Typer

from app.commands.download_contract import download_contract_command
from app.commands.safe_contracts import (
    setup_safe_contracts,
    sync_safe_contracts_command,
)


def async_command(func: Callable) -> Callable:
    """
    Wrap an async function so it can be used as a synchronous Typer command.
    Each command scopes its own database work with `transactional_session_context`.

    :param func:
    :return:
    """
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            return asyncio.run(func(*args, **kwargs))

        return wrapper
    return func


def register_commands(app: Typer):
    """
    Add the commands to the Typer instance.

    :param app:
    """

    @app.command(help="Load Safe Contracts")
    @async_command
    async def load_safe_contracts():
        await setup_safe_contracts()

    @app.command(
        help="Create the missing Safe contracts of the given chains and download "
        "again the ones without ABI"
    )
    @async_command
    async def sync_safe_contracts(
        chain_ids: Annotated[
            list[int], Option("--chain-id", help="Chain id, can be repeated")
        ],
    ):
        await sync_safe_contracts_command(chain_ids)

    @app.command(help="Force to download a contract")
    @async_command
    async def download_contract(address: str, chain_id: int):
        await download_contract_command(address, chain_id)
