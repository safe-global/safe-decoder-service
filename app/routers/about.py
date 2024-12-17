from fastapi import APIRouter

from app.routers.models import About

from .. import VERSION

router = APIRouter(
    prefix="/about",
    tags=["about"],
)


@router.get("", response_model=About)
async def about() -> "About":
    return About(version=VERSION)
