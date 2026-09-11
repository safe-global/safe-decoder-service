# SPDX-License-Identifier: FSL-1.1-MIT
from typing import Literal

from fastapi import APIRouter
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.requests import Request

from app.services.data_decoder import is_data_decoder_ready

router = APIRouter()


@router.get("/", include_in_schema=False)
async def home(req: Request):
    forwarded_prefix = req.headers.get("x-forwarded-prefix", "")
    return get_swagger_ui_html(
        openapi_url=f"{forwarded_prefix}/openapi.json",
        title="Safe Decoder Service - Swagger UI",
        swagger_favicon_url=f"{forwarded_prefix}/static/favicon.ico",
    )


@router.get("/docs", include_in_schema=False)
async def swagger_ui_html() -> RedirectResponse:
    return RedirectResponse(url="/")


@router.get("/redoc", include_in_schema=False)
async def redoc_html(req: Request):
    forwarded_prefix = req.headers.get("x-forwarded-prefix", "")
    return get_redoc_html(
        openapi_url=f"{forwarded_prefix}/openapi.json",
        title="Safe Decoder Service - ReDoc",
        redoc_favicon_url=f"{forwarded_prefix}/static/favicon.ico",
    )


@router.get("/health", include_in_schema=False)
@router.get("/health/live", include_in_schema=False)
async def health() -> Literal["OK"]:
    return "OK"


@router.get("/health/ready", include_in_schema=False)
async def health_ready() -> JSONResponse:
    """
    Readiness probe.

    Decoding is served from an in-memory selector map built at startup, so the
    service is ready only once that map is loaded. The database is not part of
    the check: while it is unreachable the service keeps decoding from that map
    and reports a lower accuracy, instead of failing the request.
    """
    decoder_ready = is_data_decoder_ready()
    return JSONResponse(
        content={"ready": decoder_ready},
        status_code=200 if decoder_ready else 503,
    )
