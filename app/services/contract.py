from typing import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.datasources.db.models import Contract


class ContractService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> Sequence[Contract]:
        result = await self.session.exec(select(Contract))
        return result.all()
