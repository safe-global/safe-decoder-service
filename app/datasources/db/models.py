from datetime import datetime, timezone
from typing import AsyncIterator, Self, cast

from sqlalchemy import DateTime, Row
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
    UniqueConstraint,
    col,
    select,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql._expression_select_cls import SelectBase
from web3.types import ABI

from .utils import get_md5_abi_hash


class SqlQueryBase:

    @classmethod
    async def get_all(cls, session: AsyncSession):
        result = await session.exec(select(cls))
        return result.all()

    async def _save(self, session: AsyncSession):
        session.add(self)
        await session.commit()
        return self

    async def update(self, session: AsyncSession):
        return await self._save(session)

    async def create(self, session: AsyncSession):
        return await self._save(session)


class TimeStampedSQLModel(SQLModel):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """

    created: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    modified: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),  # type: ignore
        sa_column_kwargs={
            "onupdate": lambda: datetime.now(timezone.utc),
        },
    )


class AbiSource(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    url: str = Field(nullable=False)

    abis: list["Abi"] = Relationship(back_populates="source")

    @classmethod
    async def get_or_create(
        cls, session: AsyncSession, name: str, url: str
    ) -> tuple["AbiSource", bool]:
        """
        Checks if an AbiSource with the given 'name' and 'url' exists.
        If found, returns it with False. If not, creates and returns it with True.

        :param session: The database session.
        :param name: The name to check or create.
        :param url: The URL to check or create.
        :return: A tuple containing the AbiSource object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        query = select(cls).where(cls.name == name, cls.url == url)
        results = await session.exec(query)
        if result := results.first():
            return result, False
        else:
            new_item = cls(name=name, url=url)
            await new_item.create(session)
            return new_item, True

    @classmethod
    async def get_abi_source(cls, session: AsyncSession, name: str):
        query = select(cls).where(cls.name == name)
        results = await session.exec(query)
        if result := results.first():
            return result
        return None


class Abi(SqlQueryBase, TimeStampedSQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    abi_hash: bytes | None = Field(nullable=False, index=True, unique=True)
    relevance: int | None = Field(nullable=False, default=0)
    abi_json: list[dict] | dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_id: int | None = Field(
        nullable=False, default=None, foreign_key="abisource.id"
    )

    source: AbiSource | None = Relationship(back_populates="abis")
    contracts: list["Contract"] = Relationship(back_populates="abi")

    @classmethod
    async def get_abis_sorted_by_relevance(
        cls, session: AsyncSession
    ) -> AsyncIterator[ABI]:
        """
        :return: Abi JSON, with the ones with less relevance first
        """
        results = await session.exec(select(cls.abi_json).order_by(col(cls.relevance)))
        for result in results:
            yield cast(ABI, result)

    async def create(self, session):
        self.abi_hash = get_md5_abi_hash(self.abi_json)
        return await self._save(session)

    @classmethod
    async def get_abi(
        cls,
        session: AsyncSession,
        abi_json: list[dict] | dict,
    ):
        """
        Checks if an Abi exists based on the 'abi_json' by its calculated 'abi_hash'.
        If it exists, returns the existing Abi. If not,
        returns None.

        :param session: The database session.
        :param abi_json: The ABI JSON to check.
        :return: The Abi object if it exists, or None if it doesn't.
        """
        abi_hash = get_md5_abi_hash(abi_json)
        query = select(cls).where(cls.abi_hash == abi_hash)
        result = await session.exec(query)

        if existing_abi := result.first():
            return existing_abi

        return None

    @classmethod
    async def get_or_create_abi(
        cls,
        session: AsyncSession,
        abi_json: list[dict] | dict,
        source_id: int | None,
        relevance: int | None = 0,
    ) -> tuple["Abi", bool]:
        """
        Checks if an Abi with the given 'abi_json' exists.
        If found, returns it with False. If not, creates and returns it with True.

        :param session: The database session.
        :param abi_json: The ABI JSON to check.
        :param relevance:
        :param source_id:
        :return: A tuple containing the Abi object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        if abi := await cls.get_abi(session, abi_json):
            return abi, False
        else:
            new_item = cls(abi_json=abi_json, relevance=relevance, source_id=source_id)
            await new_item.create(session)
            return new_item, True


class Project(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    description: str = Field(nullable=False)
    logo_file: str = Field(nullable=False)
    contracts: list["Contract"] = Relationship(back_populates="project")


class Contract(SqlQueryBase, TimeStampedSQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("address", "chain_id", name="address_chain_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
    address: bytes = Field(nullable=False, index=True)
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    trusted_for_delegate: bool = Field(nullable=False, default=False)
    implementation: bytes | None = None
    fetch_retries: int = Field(nullable=False, default=0)
    abi_id: int | None = Field(nullable=True, default=None, foreign_key="abi.id")
    abi: Abi | None = Relationship(
        back_populates="contracts", sa_relationship_kwargs={"lazy": "joined"}
    )
    project_id: int | None = Field(
        nullable=True, default=None, foreign_key="project.id"
    )
    project: Project | None = Relationship(
        back_populates="contracts", sa_relationship_kwargs={"lazy": "joined"}
    )
    chain_id: int = Field(default=None)

    @classmethod
    def get_contracts_query(
        cls, address: bytes, chain_ids: list[int] | None = None
    ) -> SelectBase["Contract"]:
        """
        Return a statement to get contracts for the provided address and chain_id

        :param address:
        :param chain_ids: list of chain_ids, `None` for all chains
        :return:
        """
        query = select(cls).where(cls.address == address)
        if chain_ids:
            query = query.where(col(cls.chain_id).in_(chain_ids)).order_by(
                col(cls.chain_id).desc()
            )

        return query

    @classmethod
    async def get_contract(cls, session: AsyncSession, address: bytes, chain_id: int):
        query = (
            select(cls).where(cls.address == address).where(cls.chain_id == chain_id)
        )
        results = await session.exec(query)
        if result := results.first():
            return result
        return None

    @classmethod
    async def get_or_create(
        cls,
        session: AsyncSession,
        address: bytes,
        chain_id: int,
        **kwargs,
    ) -> tuple["Contract", bool]:
        """
        Update or create the given params.

        :param session: The database session.
        :param address:
        :param chain_id:
        :param kwargs:
        :return: A tuple containing the Contract object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        if contract := await cls.get_contract(session, address, chain_id):
            return contract, False
        else:
            contract = cls(address=address, chain_id=chain_id)
            # Add optional fields
            for key, value in kwargs.items():
                setattr(contract, key, value)

            await contract.create(session)
            return contract, True

    @classmethod
    async def get_abi_by_contract_address(
        cls, session: AsyncSession, address: bytes
    ) -> ABI | None:
        # TODO Add chain_id filter to support multichain
        results = await session.exec(
            select(Abi.abi_json)
            .join(cls)
            .where(cls.address == address)
            .where(cls.abi_id == Abi.id)
        )
        if result := results.first():
            return cast(ABI, result)
        return None

    @classmethod
    async def get_contracts_without_abi(
        cls, session: AsyncSession, max_retries: int = 0
    ) -> AsyncIterator[Row[tuple[Self]]]:
        """
        Fetches contracts without an ABI and fewer retries than max_retries,
        streaming results in batches to reduce memory usage for large datasets.
        More information about streaming results can be found here:
        https://docs.sqlalchemy.org/en/20/core/connections.html#streaming-with-a-dynamically-growing-buffer-using-stream-results

        :param session:
        :param max_retries:
        :return:
        """
        query = (
            select(cls)
            .where(cls.abi_id == None)  # noqa: E711
            .where(cls.fetch_retries <= max_retries)
        )
        result = await session.stream(query)
        async for contract in result:
            yield contract
