from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.models import Contract


class ContractService:

    @staticmethod
    async def get_all(session: AsyncSession) -> Sequence[Contract]:
        """
        Get all contracts

        :param session: passed by the decorator
        :return:
        """
        result = await session.exec(select(Contract))
        return result.all()

    @staticmethod
    async def create(contract: Contract, session: AsyncSession) -> Contract:
        """
        Create a new contract

        :param contract:
        :param session:
        :return:
        """
        session.add(contract)
        await session.commit()
        return contract
