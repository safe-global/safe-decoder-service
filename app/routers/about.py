from fastapi import APIRouter

from .. import VERSION
from .models import AboutPublic

router = APIRouter(
    prefix="/about",
    tags=["about"],
)


@router.get("", response_model=AboutPublic)
async def about() -> AboutPublic:
    return AboutPublic(version=VERSION)
