# SPDX-License-Identifier: FSL-1.1-MIT
from fastapi import APIRouter

from .. import VERSION
from ..config import settings
from .models import AboutPublic

router = APIRouter(
    prefix="/about",
    tags=["about"],
)


@router.get("", response_model=AboutPublic)
async def about() -> AboutPublic:
    return AboutPublic(version=VERSION, build_commit=settings.BUILD_COMMIT or None)
