from typing import Sequence

from fastapi import APIRouter

from ..datasources.db.models import Contract
from ..services.contract import ContractService

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


@router.get("", response_model=Sequence[Contract])
async def list_contracts() -> Sequence[Contract]:
    contract_service = ContractService()
    return await contract_service.get_all()
