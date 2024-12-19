from typing import Generic, TypeVar

from fastapi import Request
from pydantic import BaseModel

from sqlalchemy import func
from sqlmodel import select

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    next: str | None
    previous: str | None
    results: list[T]


class GenericPagination:
    def __init__(
        self,
        request: Request,
        model,
        default_page_size: int = 10,
        max_page_size: int = 100,
    ):
        self.max_page_size = max_page_size
        self.model = model
        self.limit = default_page_size
        self.offset = 0
        self.request = request

    def set_limit(self, limit):
        if limit:
            if limit < self.max_page_size:
                self.limit = limit
            else:
                self.limit = self.max_page_size

    def set_offset(self, offset):
        if offset:
            self.offset = offset

    def get_next_page(self, count: int) -> str | None:
        """

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

        :param session:
        :param query:
        :param ResponseSchema:
        :return:
        """
        queryset = await session.exec(query.offset(self.offset).limit(self.limit))
        count_query = await session.exec(
            select(func.count()).select_from(self.model).where(query._whereclause)
        )
        count = count_query.one()
        paginated_response = PaginatedResponse(
            count=count,
            next=self.get_next_page(count),
            previous=self.get_previous_page(),
            results=queryset.all(),
        )
        return paginated_response
