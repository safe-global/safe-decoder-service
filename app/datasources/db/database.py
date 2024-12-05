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


async def get_session() -> AsyncSession:
    async_session = AsyncSession(engine)
    return async_session
