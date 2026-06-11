# SPDX-License-Identifier: FSL-1.1-MIT
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import cache, wraps

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from ...config import settings

logger = logging.getLogger(__name__)

pool_classes = {
    NullPool.__name__: NullPool,
    AsyncAdaptedQueuePool.__name__: AsyncAdaptedQueuePool,
}

_db_session_context: ContextVar[str] = ContextVar("db_session_context")


@cache
def get_engine() -> AsyncEngine:
    """
    Establish connection to database
    :return:
    """
    if settings.TEST:
        return create_async_engine(
            settings.DATABASE_URL,
            future=True,
            poolclass=NullPool,
        )
    else:
        return create_async_engine(
            settings.DATABASE_URL,
            future=True,
            poolclass=pool_classes.get(settings.DATABASE_POOL_CLASS),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "idle_in_transaction_session_timeout": str(
                        settings.DATABASE_IDLE_IN_TRANSACTION_SESSION_TIMEOUT_MS
                    )
                }
            },
        )


def _get_database_session_context() -> str:
    """
    Get the database session id from the ContextVar.
    Used as a scope function on `async_scoped_session`.

    :return: session_id for the current context
    :raises LookupError: when the session id was not created
    """
    return _db_session_context.get()


@asynccontextmanager
async def transactional_session_context(
    session_id: str | None = None,
) -> AsyncGenerator[None]:
    """
    Define the lifecycle of a database session scope.

    Explicit transactional context:
    - Commits on success
    - Rolls back on exception
    - Re-raises exceptions
    - Reuses an existing session context if already set
    - Creates a new context (and removes it on exit) if it created it

    Bounds a unit of database work so the connection is returned to the pool as
    soon as the transaction completes, before any post-query work (response
    serialization, cache writes).

    :param session_id: Optional session ID. If not provided, a UUID is generated.
    :return:
    """
    token = None
    created_context = False

    try:
        _get_database_session_context()
    except LookupError:
        token = _db_session_context.set(session_id or str(uuid.uuid4()))
        created_context = True

    try:
        yield
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise
    finally:
        if created_context and token:
            await db_session.remove()
            _db_session_context.reset(token)


def db_session_context(func):
    """
    Wrap the decorated function in the `transactional_session_context` context.
    Decorated function will share the same database session.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with transactional_session_context():
            return await func(*args, **kwargs)

    return wrapper


async_session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
db_session = async_scoped_session(
    session_factory=async_session_factory, scopefunc=_get_database_session_context
)
