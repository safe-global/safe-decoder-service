import logging
from collections.abc import AsyncGenerator
from functools import cache, wraps

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from ...config import settings

pool_classes = {
    NullPool.__name__: NullPool,
    AsyncAdaptedQueuePool.__name__: AsyncAdaptedQueuePool,
}


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


async def get_database_session() -> AsyncGenerator:
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        yield session


def database_session(func):
    """
    Decorator that creates a new database session for the given function

    :param func:
    :return:
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            try:
                return await func(*args, **kwargs, session=session)
            except Exception as e:
                # Rollback errors
                await session.rollback()
                logging.error(f"Error occurred: {e}")
                raise

    return wrapper
