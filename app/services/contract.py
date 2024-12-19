from typing import Any, Sequence

from sqlmodel.ext.asyncio.session import AsyncSession

<<<<<<< HEAD
from ..datasources.db.models import Contract
=======
from app.datasources.db.models import Contract
from app.services.pagination import GenericPagination, PaginatedResponse
>>>>>>> 2433738 (Add pagination)


class ContractService:

    def __init__(self, base_url: str, limit: int | None, offset: int | None):
        self.pagination = GenericPagination(base_url=base_url, model=Contract)
        self.pagination.set_limit(limit)
        self.pagination.set_offset(offset)

    @staticmethod
    async def get_all(session: AsyncSession) -> Sequence[Contract]:
        """
        Get all contracts

        :param session: passed by the decorator
        :return:
        """
        return await Contract.get_all(session)

    async def get_contract(
        self, session: AsyncSession, address: bytes, chain_ids: list[int] | None
    ) -> PaginatedResponse[Any]:
        """
        Get the contract by address and/or chain_ids

        :param session: database session
        :param address: contract address
        :param chain_ids: list of filtered chains
        :return:
        """

        return await self.pagination.paginate(
            session, Contract.get_contract(address, chain_ids)
        )
