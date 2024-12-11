from typing import Sequence

from fastapi import APIRouter, Depends

from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_database_session
from ..datasources.db.models import Contract
from ..services.contract import ContractService

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get("", response_model=Sequence[Contract])
async def list_contracts(
    session: AsyncSession = Depends(get_database_session),
) -> Sequence[Contract]:
    return await ContractService.get_all(session)
