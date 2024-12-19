from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_database_session
from ..datasources.db.models import Contract
from ..services.contract import ContractService
from ..services.pagination import PaginatedResponse
from .models import ContractsPublic

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get("/{address}", response_model=PaginatedResponse[ContractsPublic])
async def list_contracts(
    address: str,
    chain_ids: Annotated[list[int] | None, Query()] = None,
    limit: int = Query(None),
    offset: int = Query(None),
    session: AsyncSession = Depends(get_database_session),
) -> PaginatedResponse[Contract]:
    contracts_service = ContractService(limit, offset)
    return await contracts_service.get_contract(session, address, chain_ids)
