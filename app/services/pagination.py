from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

from sqlalchemy import func
from sqlmodel import select
from starlette.datastructures import URL
from starlette.requests import Request

from app.datasources.db.database import db_session

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    next: str | None
    previous: str | None
    results: list[T]


class PaginationQueryParams(BaseModel):
    limit: int | None = Query(None, ge=1)
    offset: int | None = Query(0, ge=0)


class GenericPagination:
    def __init__(
        self,
        limit: int | None,
        offset: int | None,
        default_page_size: int = 10,
        max_page_size: int = 100,
    ):
        self.max_page_size = max_page_size
        self.limit = min(limit, max_page_size) if limit else default_page_size
        self.offset = offset if offset else 0

    @staticmethod
    def _get_url(request: Request) -> URL:
        """
        Constructs a URL from the request, handling proxy forwarding headers.

        When behind a proxy, uses x-forwarded-* headers to reconstruct the original URL
        with the correct scheme, host, port, and path prefix.

        :param request: The FastAPI/Starlette request object
        :return: URL object with proxy-aware scheme, host, port, and path
        """
        prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
        if prefix:
            host = request.headers.get("x-forwarded-host", request.url.hostname)
            protocol = request.headers.get("x-forwarded-proto", request.url.scheme)
            port = request.headers.get("x-forwarded-port", request.url.port)
            return request.url.replace(
                scheme=protocol,
                hostname=host,
                port=port,
                path=prefix + request.url.path,
            )
        return request.url

    def get_next_page(self, url: URL, count: int) -> str | None:
        """
        Calculates the next page of results. If there are no more pages return None

        :param url:
        :param count:
        :return:
        """
        if self.offset + self.limit < count:
            next_offset = self.offset + self.limit
            return str(url.include_query_params(limit=self.limit, offset=next_offset))
        return None

    def get_previous_page(self, url: URL) -> str | None:
        """
        Calculates the previous page of results. If there are no more pages return None

        :param url:
        :return:
        """
        if self.offset > 0:
            prev_offset = max(0, self.offset - self.limit)  # Prevent negative offset
            return str(url.include_query_params(limit=self.limit, offset=prev_offset))
        return None

    async def get_page(self, query) -> list[Any]:
        """
        Get from database the requested page

        :param query:
        :return:
        """
        queryset = await db_session.execute(query.offset(self.offset).limit(self.limit))
        return queryset.scalars().all()

    async def get_count(self, query) -> int:
        """
        Get from database the count of rows that fit the query

        :param query:
        :return:
        """
        # We dont need sort the query to get the count, so we remove the order section
        query = query.order_by(None)
        count_query = await db_session.execute(
            select(func.count()).select_from(query.alias())
        )
        return count_query.scalars().one()

    def serialize(self, url: URL, results: list[Any], count: int) -> PaginatedResponse:
        """
        Get serialized page of results.

        :param url:
        :param results:
        :param count:
        :return:
        """
        paginated_response = PaginatedResponse(
            count=count,
            next=self.get_next_page(url, count),
            previous=self.get_previous_page(url),
            results=results,
        )
        return paginated_response
