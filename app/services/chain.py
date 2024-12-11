from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import get_database_session
from app.datasources.db.models import Chain


class ChainService:

    @staticmethod
    @get_database_session
    async def get_all(session: AsyncSession) -> Sequence[Chain]:
        """
        Get all chains

        :param session: passed by the decorator
        :return:
        """
        result = await session.exec(select(Chain))
        return result.all()

    @staticmethod
    @get_database_session
    async def create(chain: Chain, session: AsyncSession) -> Chain:
        """
        Create a new chain

        :param chain:
        :param session:
        :return:
        """
        session.add(chain)
        await session.commit()
        return chain
