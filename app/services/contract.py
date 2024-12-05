from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import get_database_session
from app.datasources.db.models import Contract


class ContractService:

    @staticmethod
    @get_database_session
    async def get_all(session: AsyncSession) -> Sequence[Contract]:
        """
        Get all contracts

        :param session: passed by the decorator
        :return:
        """
        result = await session.exec(select(Contract))
        return result.all()

    @staticmethod
    @get_database_session
    async def create(contract: Contract, session: AsyncSession) -> Contract:
        session.add(contract)
        await session.commit()
        return contract
