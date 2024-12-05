from typing import Sequence

from fastapi import APIRouter, Depends

from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_session
from ..datasources.db.models import Contract
from ..services.contract import ContractService

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


@router.get("", response_model=Sequence[Contract])
async def list_contracts(
    session: AsyncSession = Depends(get_session),
) -> Sequence[Contract]:
    contract_service = ContractService()
    return await contract_service.get_all()
