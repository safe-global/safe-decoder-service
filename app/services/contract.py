from typing import Sequence

from hexbytes import HexBytes
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

    @staticmethod
    async def get_contract(
        session: AsyncSession, address: str, chain_ids: list[int] | None
    ) -> Sequence[Contract]:
        """
        Get the contract by address and/or chain_ids

        :param session: database session
        :param address: contract address
        :param chain_ids: list of filtered chains
        :return:
        """
        return await Contract.get_contract(session, HexBytes(address), chain_ids)
