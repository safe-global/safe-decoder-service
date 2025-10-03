from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from hexbytes import HexBytes
from safe_eth.eth.utils import fast_is_checksum_address

from ..datasources.cache.redis import cache_response, get_key_for_contract
from ..services.contract import ContractService
from ..services.pagination import (
    GenericPagination,
    PaginatedResponse,
    PaginationQueryParams,
)
from ..utils import get_proxy_aware_url
from .models import ContractsPublic

router = APIRouter(
    prefix="/contracts",
    tags=["contracts"],
)


@router.get(
    "",
    response_model=PaginatedResponse[ContractsPublic],
    summary="List all contracts",
    response_description="Paginated list of contracts",
    description="""Returns a **paginated** list of contracts, optionally filtered by `chain_ids` and the
    `trusted_for_delegate_call` flag.

    **Parameters:**
    - `chain_ids`: Filter contracts by specific chain IDs. Repeat the param to filter by multiple chains (e.g. `?chain_ids=1&chain_ids=137`).
    - `trusted_for_delegate_call`: Filter contracts by trusted delegate call flag.

    **Response:**
    - Paginated list of contracts matching the criteria.

    **Notes**
    - Pagination is controlled by `PaginationQueryParams` (`limit`, `offset`).
    - When `chain_ids` is provided, only contracts deployed on those chains are returned.
    """,
)
async def list_all_contracts(
    request: Request,
    pagination_params: PaginationQueryParams = Depends(),
    chain_ids: Annotated[
        list[int] | None,
        Query(
            description="Filter by chain IDs. Repeat to pass multiple values.",
        ),
    ] = None,
    trusted_for_delegate_call: Annotated[
        bool | None,
        Query(
            description="If true, only return contracts trusted for delegate calls. "
            "If false, only return those not trusted. Omit to return all.",
        ),
    ] = None,
) -> PaginatedResponse[ContractsPublic]:
    """
    Returns a paginated list of contracts, optionally filtered by `chain_ids` and
    `trusted_for_delegate_call`.

    Pagination is controlled by `PaginationQueryParams` (`limit`, `offset`).
    When `chain_ids` is provided, only contracts deployed on those chains are returned.

    :param request:
    :param pagination_params: Pagination parameters.
    :param chain_ids: Filter contracts by specific chain IDs.
    :param trusted_for_delegate_call: Filter contracts by trusted delegate call flag.
    :return: Paginated list of contracts matching the criteria.
    """
    pagination = GenericPagination(pagination_params.limit, pagination_params.offset)
    contracts_service = ContractService(pagination=pagination)
    contracts_page, count = await contracts_service.get_contracts(
        chain_ids=chain_ids, trusted_for_delegate_call=trusted_for_delegate_call
    )
    return pagination.serialize(get_proxy_aware_url(request), contracts_page, count)


@router.get(
    "/{address}",
    response_model=PaginatedResponse[ContractsPublic],
    summary="List contracts for a checksummed address",
    response_description="Paginated list of contracts matching the provided address",
    description="""
    Return a **paginated** list of contracts that match the provided **EIP-55 checksummed** address.

    **Parameters:**
    - `address`: Contract address in checksum format (required).
    - `chain_ids`: List of chain IDs to filter contracts (optional).

    **Returns:**
    - Paginated response containing contracts matching the address.
    """,
)
@cache_response(get_key_for_contract, PaginatedResponse[ContractsPublic])
async def list_contracts(
    request: Request,
    address: Annotated[
        str,
        Path(description="EIP-55 checksummed contract address."),
    ],
    pagination_params: PaginationQueryParams = Depends(),
    chain_ids: Annotated[
        list[int] | None,
        Query(
            description="Filter by chain IDs. Repeat to pass multiple values.",
        ),
    ] = None,
) -> PaginatedResponse[ContractsPublic]:
    """
    Return a paginated list of contracts that match the provided EIP-55 checksummed address.

    :param request:
    :param address: Contract address in checksum format. (Required)
    :param pagination_params: Pagination query parameters.
    :param chain_ids: List of chain IDs to filter contracts. (Optional)
    :return: Paginated response containing contracts matching the address.
    """
    if not fast_is_checksum_address(address):
        raise HTTPException(status_code=400, detail="Address is not checksummed")

    pagination = GenericPagination(pagination_params.limit, pagination_params.offset)
    contracts_service = ContractService(pagination=pagination)
    contracts_page, count = await contracts_service.get_contracts(
        address=HexBytes(address), chain_ids=chain_ids
    )
    return pagination.serialize(get_proxy_aware_url(request), contracts_page, count)
