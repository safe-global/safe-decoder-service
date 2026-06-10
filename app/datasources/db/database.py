# SPDX-License-Identifier: FSL-1.1-MIT
import logging
import uuid
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
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


@contextmanager
def set_database_session_context(
    session_id: str | None = None,
) -> Generator[None]:
    """
    Set session ContextVar, at the end it will be removed.
    This context is designed to be used with `async_scoped_session` to define a context scope.

    :param session_id:
    :return:
    """
    _session_id: str = session_id or str(uuid.uuid4())
    logger.debug("Storing db_session context")
    token = _db_session_context.set(_session_id)
    try:
        yield
    finally:
        logger.debug("Removing db_session context")
        _db_session_context.reset(token)


def _get_database_session_context() -> str:
    """
    Get the database session id from the ContextVar.
    Used as a scope function on `async_scoped_session`.

    :return: session_id for the current context
    """
    return _db_session_context.get()


@asynccontextmanager
async def with_db_session_context(
    session_id: str | None = None,
) -> AsyncGenerator[None]:
    """
    Async context manager that opens a database session scope and guarantees the
    scoped session (and its connection) is released on exit via `db_session.remove()`.

    Use it to bound a unit of database work so the connection is returned to the
    pool as soon as that work is done, instead of being held until the end of the
    surrounding request/task.

    :param session_id:
    :return:
    """
    with set_database_session_context(session_id):
        try:
            yield
        finally:
            logger.debug(
                "Removing session context: %s", _get_database_session_context()
            )
            await db_session.remove()


def db_session_context(func):
    """
    Wrap the decorated function in the `with_db_session_context` context.
    Decorated function will share the same database session.
    Remove the session at the end of the context.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with with_db_session_context():
            return await func(*args, **kwargs)

    return wrapper


async_session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
db_session = async_scoped_session(
    session_factory=async_session_factory, scopefunc=_get_database_session_context
)
