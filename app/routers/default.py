from typing import Literal

from fastapi import APIRouter
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import RedirectResponse

from starlette.requests import Request

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
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Safe Decoder Service - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.ico",
    )


@router.get("/health", include_in_schema=False)
async def health() -> Literal["OK"]:
    return "OK"
