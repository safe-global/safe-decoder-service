from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, Query

from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_database_session
from ..datasources.db.models import Contract
from ..services.contract import ContractService
from .models import ContractsPublic

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get("/{address}", response_model=Sequence[ContractsPublic])
async def list_contracts(
    address: str,
    chain_ids: Annotated[list[int] | None, Query()] = None,
    session: AsyncSession = Depends(get_database_session),
) -> Sequence[Contract]:
    return await ContractService.get_contract(session, address, chain_ids)
