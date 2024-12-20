from typing import Any, Sequence

from fastapi import Request

from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.models import Contract
from app.services.pagination import GenericPagination, PaginatedResponse


class ContractService:

    def __init__(self, request: Request):
        self.pagination = GenericPagination(request=request)

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
            session, Contract.get_contracts_query(address, chain_ids)
        )
