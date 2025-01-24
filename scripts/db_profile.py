"""
Ipython profile to enable on startup database interactions
"""

from app.datasources.db.database import db_session, set_database_session_context
from app.datasources.db.models import *  # noqa: F401, F403

session_context = set_database_session_context()

session_context.__enter__()  # Uses session context


async def restore_session():
    """
    Restore the current session

    :return:
    """
    await db_session.remove()  # New session will created
