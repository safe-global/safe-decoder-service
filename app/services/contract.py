from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.database import engine
from app.datasources.db.models import Contract


class ContractService:

    def __init__(self):
        self.session = AsyncSession(engine)

    async def get_all(self) -> Sequence[Contract]:
        async with self.session as session:
            result = await session.exec(select(Contract))
            return result.all()

    async def create(self, address: bytes, name: str) -> Contract:
        async with self.session as session:
            contract = Contract(address=address, name=name)
            session.add(contract)
            await session.commit()
            return contract
