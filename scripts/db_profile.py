# SPDX-License-Identifier: FSL-1.1-MIT
"""
Ipython profile to enable on startup database interactions
"""

import uuid

from app.datasources.db.database import _db_session_context, db_session
from app.datasources.db.models import *  # noqa: F401, F403

# Set a session scope so `db_session` is usable interactively
_db_session_context.set(str(uuid.uuid4()))


async def restore_session():
    """
    Restore the current session

    :return:
    """
    await db_session.remove()  # New session will created
