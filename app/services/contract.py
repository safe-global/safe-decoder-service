from typing import Sequence, Tuple

from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.models import Contract
from app.services.pagination import GenericPagination


class ContractService:

    def __init__(self, pagination: GenericPagination):
        self.pagination = pagination

    @staticmethod
    async def get_all(session: AsyncSession) -> Sequence[Contract]:
        """
        Get all contracts

        :param session: passed by the decorator
        :return:
        """
        return await Contract.get_all(session)

    async def get_contracts(
        self, session: AsyncSession, address: bytes, chain_ids: list[int] | None
    ) -> Tuple[list[Contract], int]:
        """
        Get the contract by address and/or chain_ids

        :param session: database session
        :param address: contract address
        :param chain_ids: list of filtered chains
        :return:
        """
        page = await self.pagination.get_page(
            session, Contract.get_contracts_with_abi_query(address, chain_ids)
        )
        count = await self.pagination.get_count(
            session, Contract.get_contracts_with_abi_query(address, chain_ids)
        )
        return page, count
