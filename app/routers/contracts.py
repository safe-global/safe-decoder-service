from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hexbytes import HexBytes
from safe_eth.eth.utils import fast_is_checksum_address
from sqlmodel.ext.asyncio.session import AsyncSession

from ..datasources.db.database import get_database_session
from ..datasources.db.models import Contract
from ..services.contract import ContractService
from ..services.pagination import PaginatedResponse, PaginationParams
from .models import ContractsPublic

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get("/{address}", response_model=PaginatedResponse[ContractsPublic])
async def list_contracts(
    request: Request,
    address: str,
    pagination_params: PaginationParams = Depends(),
    chain_ids: Annotated[list[int] | None, Query()] = None,
    session: AsyncSession = Depends(get_database_session),
) -> PaginatedResponse[Contract]:
    if not fast_is_checksum_address(address):
        raise HTTPException(status_code=400, detail="Address is not checksumed")

    contracts_service = ContractService(request)
    return await contracts_service.get_contract(session, HexBytes(address), chain_ids)
