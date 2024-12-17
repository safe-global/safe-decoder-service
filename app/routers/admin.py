import secrets

from fastapi import FastAPI

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from ..config import settings
from ..datasources.cache.redis import get_redis
from ..datasources.db.database import get_engine
from ..datasources.db.models import Contract


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        # Validate username/password credentials
        if username == settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
            # And update session
            secret = secrets.token_hex(nbytes=16)
            request.session.update({"token": secret})

            # Use redis to store the token
            get_redis().set(
                f"admin:token:{secret}", 1, ex=settings.ADMIN_TOKEN_EXPIRATION_SECONDS
            )

            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        secret = request.session.get("token")

        if not secret:
            return False

        return bool(get_redis().exists(f"admin:token:{secret}"))


class ContractAdmin(ModelView, model=Contract):
    column_list = [Contract.address, Contract.name, Contract.description]  # type: ignore
    form_include_pk = True
    icon = "fa-solid fa-file-contract"

    async def on_model_change(
        self, data: dict, model: Contract, is_created: bool, request: Request
    ) -> None:
        data["address"] = bytes.fromhex(data["address"].strip().replace("0x", ""))
        return await super().on_model_change(data, model, is_created, request)


def load_admin(app: FastAPI):
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        get_engine(),
        base_url="/admin",
        authentication_backend=authentication_backend,
    )
    admin.add_view(ContractAdmin)
