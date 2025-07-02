from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from hexbytes import HexBytes
from safe_eth.eth.utils import fast_is_checksum_address

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
    "",
    response_model=PaginatedResponse[ContractsPublic],
    summary="List contracts",
    response_description="Paginated list of contracts",
)
async def list_all_contracts(
    request: Request,
    pagination_params: PaginationQueryParams = Depends(),
    chain_ids: Annotated[list[int] | None, Query()] = None,
    trusted_for_delegate_call: bool | None = None,
) -> PaginatedResponse[ContractsPublic]:
    """
    List all contracts
    Args:
        request:
        address:
        pagination_params:
        chain_ids:
        trusted_for_delegate_call:

    Returns:

    """
    pagination = GenericPagination(pagination_params.limit, pagination_params.offset)
    contracts_service = ContractService(pagination=pagination)
    contracts_page, count = await contracts_service.get_contracts(
        chain_ids=chain_ids, trusted_for_delegate_call=trusted_for_delegate_call
    )
    return pagination.serialize(request.url, contracts_page, count)


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
) -> PaginatedResponse[ContractsPublic]:
    """
    :param request:
    :param address: Contract address
    :param pagination_params:
    :param chain_ids: Only list contracts for the provided `chain_ids`
    :return: Contracts for all chains if found, empty response otherwise
    """
    if not fast_is_checksum_address(address):
        raise HTTPException(status_code=400, detail="Address is not checksummed")

    pagination = GenericPagination(pagination_params.limit, pagination_params.offset)
    contracts_service = ContractService(pagination=pagination)
    contracts_page, count = await contracts_service.get_contracts(
        address=HexBytes(address), chain_ids=chain_ids
    )
    return pagination.serialize(request.url, contracts_page, count)
