"""
Ipython profile to enable on startup database interactions
"""

import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import get_engine
from app.datasources.db.models import *  # noqa: F401, F403

session: AsyncSession | None = None


async def restore_session():
    """
    Close default session an open a new one.

    :return:
    """
    global session
    if session:
        await session.close()

    session = AsyncSession(get_engine(), expire_on_commit=False)


asyncio.run(restore_session())
