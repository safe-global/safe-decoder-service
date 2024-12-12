from fastapi import APIRouter, FastAPI

from . import VERSION
from .routers import about, admin, contracts, default

app = FastAPI(
    title="Safe Decoder Service",
    description="Safe Core{API} decoder service",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
)

admin.load_admin(app)

# Router configuration
api_v1_router = APIRouter(
    prefix="/api/v1",
)
api_v1_router.include_router(about.router)
api_v1_router.include_router(contracts.router)
app.include_router(api_v1_router)
app.include_router(default.router)
