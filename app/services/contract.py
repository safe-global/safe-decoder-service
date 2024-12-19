from typing import Sequence

from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.models import Contract


class ContractService:

    @staticmethod
    async def get_all(session: AsyncSession) -> Sequence[Contract]:
        """
        Get all contracts

        :param session: passed by the decorator
        :return:
        """
        return await Contract.get_all(session)
