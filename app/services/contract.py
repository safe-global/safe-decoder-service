from typing import Sequence

from app.datasources.db.models import Contract
from app.services.pagination import GenericPagination


class ContractService:

    def __init__(self, pagination: GenericPagination):
        self.pagination = pagination

    @staticmethod
    async def get_all() -> Sequence[Contract]:
        """
        Get all contracts

        :return:
        """
        return await Contract.get_all()

    async def get_contracts(
        self, address: bytes, chain_ids: list[int] | None
    ) -> tuple[list[Contract], int]:
        """
        Get the contract by address and/or chain_ids

        :param address: contract address
        :param chain_ids: list of filtered chains
        :return: Paginated tuple of contracts with total number of contracts
        """
        query = Contract.get_contracts_query(address, chain_ids)
        page = await self.pagination.get_page(query)
        count = await self.pagination.get_count(query)

        return page, count
