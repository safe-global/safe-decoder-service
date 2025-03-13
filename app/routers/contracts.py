from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hexbytes import HexBytes
from safe_eth.eth.utils import fast_is_checksum_address

from ..datasources.db.models import Contract
from ..services.contract import ContractService
from ..services.pagination import (
    GenericPagination,
    PaginatedResponse,
    PaginationQueryParams,
)
from .models import ContractsPublic

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get(
    "/{address}",
    response_model=PaginatedResponse[ContractsPublic],
    summary="List matching contracts",
    response_description="Paginated list of contracts",
)
async def list_contracts(
    request: Request,
    address: str,
    pagination_params: PaginationQueryParams = Depends(),
    chain_ids: Annotated[list[int] | None, Query()] = None,
) -> PaginatedResponse[Contract]:
    """
    List all contracts for all the chains, or for specific chains if provided.
    Empty response indicate that no contract was found
    """
    if not fast_is_checksum_address(address):
        raise HTTPException(status_code=400, detail="Address is not checksumed")

    pagination = GenericPagination(pagination_params.limit, pagination_params.offset)
    contracts_service = ContractService(pagination=pagination)
    results, count = await contracts_service.get_contracts(HexBytes(address), chain_ids)
    return pagination.serialize(request.url, results, count)
