from app.datasources.db.models import Contract
from app.services.pagination import GenericPagination


class ContractService:
    def __init__(self, pagination: GenericPagination):
        self.pagination = pagination

    async def get_contracts(
        self,
        address: bytes | None = None,
        chain_ids: list[int] | None = None,
        trusted_for_delegate_call: bool | None = None,
    ) -> tuple[list[Contract], int]:
        """
        Get the contract by address and/or chain_ids

        :param address: contract address
        :param chain_ids: list of filtered chains
        :param trusted_for_delegate_call: whether to return only contracts trusted for delegate
        :return: Paginated tuple of contracts with total number of contracts
        """
        query = Contract.get_contracts_query(
            address=address,
            chain_ids=chain_ids,
            trusted_for_delegate_call=trusted_for_delegate_call,
        )
        page = await self.pagination.get_page(query)
        count = await self.pagination.get_count(query)

        return page, count
