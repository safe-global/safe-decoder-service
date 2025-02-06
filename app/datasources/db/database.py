import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache, wraps
from typing import Generator

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
        )


@contextmanager
def set_database_session_context(
    session_id: str | None = None,
) -> Generator[None, None, None]:
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


def db_session_context(func):
    """
    Wrap the decorated function in the `set_database_session_context` context.
    Decorated function will share the same database session.
    Remove the session at the end of the context.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        with set_database_session_context():
            try:
                return await func(*args, **kwargs)
            finally:
                logger.debug(
                    f"Removing session context: {_get_database_session_context()}"
                )
                await db_session.remove()

    return wrapper


async_session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
db_session = async_scoped_session(
    session_factory=async_session_factory, scopefunc=_get_database_session_context
)
