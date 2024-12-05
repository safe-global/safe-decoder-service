import logging
from functools import wraps

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

pool_classes = {
    NullPool.__name__: NullPool,
    AsyncAdaptedQueuePool.__name__: AsyncAdaptedQueuePool,
}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    poolclass=pool_classes.get(settings.DATABASE_POOL_CLASS),
)


def get_database_session(func):
    """
    Decorator that creates a new database session for the given function

    :param func:
    :return:
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with AsyncSession(engine) as session:
            try:
                return await func(*args, **kwargs, session=session)
            except Exception as e:
                # Rollback errors
                await session.rollback()
                logging.error(f"Error occurred: {e}")
                raise
            finally:
                # Ensure that session is closed
                await session.close()

    return wrapper
