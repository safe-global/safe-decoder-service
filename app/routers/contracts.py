from typing import Sequence

from fastapi import APIRouter, Depends

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_session
from ..datasources.db.models import Contract

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


@router.get("", response_model=Sequence[Contract])
async def contracts(session: AsyncSession = Depends(get_session)) -> Sequence[Contract]:
    result = await session.exec(select(Contract))

    return result.all()
