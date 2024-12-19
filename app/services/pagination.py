from typing import Generic, TypeVar

from fastapi import Query, Request
from pydantic import BaseModel

from sqlalchemy import func
from sqlmodel import select

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    next: str | None
    previous: str | None
    results: list[T]


class PaginationParams(BaseModel):
    limit: int | None = Query(None, ge=1)
    offset: int | None = Query(0, ge=0)


class GenericPagination:
    def __init__(
        self,
        request: Request,
        default_page_size: int = 10,
        max_page_size: int = 100,
    ):
        self.request = request
        self.max_page_size = max_page_size
        self.limit = min(
            int(self.request.query_params.get("limit", default_page_size)),
            max_page_size,
        )
        self.offset = int(self.request.query_params.get("offset", 0))

    def get_next_page(self, count: int) -> str | None:
        """
        Calculates the next page of results. If there are no more pages return None

        :param base_url:
        :param count:
        :return:
        """
        if self.offset + self.limit < count:
            next_offset = self.offset + self.limit
            return str(
                self.request.url.include_query_params(
                    limit=self.limit, offset=next_offset
                )
            )
        return None

    def get_previous_page(self) -> str | None:
        """
        Calculates the previous page of results. If there are no more pages return None

        :param base_url:
        :return:
        """
        if self.offset > 0:
            prev_offset = max(0, self.offset - self.limit)  # Prevent negative offset
            return str(
                self.request.url.include_query_params(
                    limit=self.limit, offset=prev_offset
                )
            )
        return None

    async def paginate(self, session, query) -> PaginatedResponse:
        """
        Get the paginated response for the provided query

        :param session:
        :param query:
        :param ResponseSchema:
        :return:
        """
        queryset = await session.exec(query.offset(self.offset).limit(self.limit))
        count_query = await session.exec(select(func.count()).where(query._whereclause))
        count = count_query.one()
        paginated_response = PaginatedResponse(
            count=count,
            next=self.get_next_page(count),
            previous=self.get_previous_page(),
            results=queryset.all(),
        )
        return paginated_response
