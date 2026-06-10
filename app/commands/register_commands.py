# SPDX-License-Identifier: FSL-1.1-MIT
import asyncio
import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from typer import Typer

from app.commands.download_contract import download_contract_command
from app.commands.safe_contracts import (
    setup_safe_contracts,
)
from app.datasources.db.database import with_db_session_context


def async_command(func: Callable) -> Callable:
    """
    Wrap a function so:
        - Async functions are supported
        - A database session is open and closed

    :param func:
    :return:
    """
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            async def run_with_context():
                async with with_db_session_context():
                    return await func(*args, **kwargs)

            return asyncio.run(run_with_context())

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

    @app.command(help="Force to download a contract")
    @async_command
    async def download_contract(address: str, chain_id: int):
        await download_contract_command(address, chain_id)
