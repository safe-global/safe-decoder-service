import datetime
from collections.abc import AsyncIterator
from typing import Self, cast

from eth_typing import ABI
from sqlalchemy import BigInteger, CursorResult, DateTime, update
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
from sqlmodel.sql._expression_select_cls import SelectBase

from .database import db_session
from .utils import get_md5_abi_hash


class SqlQueryBase:
    @classmethod
    async def get_all(cls):
        result = await db_session.execute(select(cls))
        return result.scalars().all()

    async def _save(self):
        db_session.add(self)
        await db_session.commit()
        return self

    async def update(self):
        return await self._save()

    async def create(self):
        return await self._save()


class TimeStampedSQLModel(SQLModel):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.

    """

    created: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )

    modified: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
        sa_type=DateTime(timezone=True),  # type: ignore
        sa_column_kwargs={
            "onupdate": lambda: datetime.datetime.now(datetime.UTC),
        },
    )


class AbiSource(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    url: str = Field(nullable=False)

    abis: list["Abi"] = Relationship(back_populates="source")

    @classmethod
    async def get_or_create(cls, name: str, url: str) -> tuple["AbiSource", bool]:
        """
        Checks if an AbiSource with the given 'name' and 'url' exists.
        If found, returns it with False. If not, creates and returns it with True.

        :param name: The name to check or create.
        :param url: The URL to check or create.
        :return: A tuple containing the AbiSource object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        query = select(cls).where(cls.name == name, cls.url == url).limit(1)
        results = await db_session.execute(query)
        if result := results.scalars().first():
            return result, False
        else:
            new_item = cls(name=name, url=url)
            await new_item.create()
            return new_item, True

    @classmethod
    async def get_abi_source(cls, name: str):
        query = select(cls).where(cls.name == name).limit(1)
        results = await db_session.execute(query)
        if result := results.scalars().first():
            return result
        return None


class Abi(SqlQueryBase, TimeStampedSQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    abi_hash: bytes | None = Field(nullable=False, index=True, unique=True)
    relevance: int | None = Field(nullable=False, default=0, index=True)
    abi_json: list[dict] | dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_id: int | None = Field(
        nullable=False, default=None, foreign_key="abisource.id"
    )

    source: AbiSource | None = Relationship(back_populates="abis")
    contracts: list["Contract"] = Relationship(back_populates="abi")

    @classmethod
    async def get_creation_date_for_last_inserted(cls) -> datetime.datetime | None:
        """
        :return: Creation date for last inserted ABI, `None` if table is empty
        """
        results = await db_session.execute(
            select(cls.created).order_by(col(cls.created).desc()).limit(1)
        )
        if result := results.first():
            return result[0]
        return None

    @classmethod
    async def get_abis_sorted_by_relevance(cls) -> AsyncIterator[ABI]:
        """
        :return: Abi JSON, with the ones with less relevance first
        """
        results = await db_session.execute(
            select(cls.abi_json).order_by(col(cls.relevance))
        )
        for result in results.scalars().all():
            yield cast(ABI, result)

    @classmethod
    async def get_abi_newer_than(cls, when: datetime.datetime) -> AsyncIterator[ABI]:
        """
        Get ABI json with `created` newer than provided `when` parameter.

        :param when: It will be compared with ABI `created` field
        :return: Abi JSONs, sorted by the oldest ones first
        """
        results = await db_session.execute(
            select(cls.abi_json)
            .where(col(cls.created) > when)
            .order_by(col(cls.created).asc())
        )
        for result in results.scalars().all():
            yield cast(ABI, result)

    async def create(self):
        self.abi_hash = get_md5_abi_hash(self.abi_json)
        return await self._save()

    @classmethod
    async def get_abi(
        cls,
        abi_json: list[dict] | dict,
    ):
        """
        Checks if an Abi exists based on the 'abi_json' by its calculated 'abi_hash'.
        If it exists, returns the existing Abi. If not,
        returns None.

        :param abi_json: The ABI JSON to check.
        :return: The Abi object if it exists, or None if it doesn't.
        """
        abi_hash = get_md5_abi_hash(abi_json)
        query = select(cls).where(cls.abi_hash == abi_hash).limit(1)
        result = await db_session.execute(query)

        if existing_abi := result.scalars().first():
            return existing_abi

        return None

    @classmethod
    async def get_or_create_abi(
        cls,
        abi_json: list[dict] | dict,
        source_id: int | None,
        relevance: int | None = 0,
    ) -> tuple["Abi", bool]:
        """
        Checks if an Abi with the given 'abi_json' exists.
        If found, returns it with False. If not, creates and returns it with True.

        :param abi_json: The ABI JSON to check.
        :param relevance:
        :param source_id:
        :return: A tuple containing the Abi object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        if abi := await cls.get_abi(abi_json):
            return abi, False
        else:
            new_item = cls(abi_json=abi_json, relevance=relevance, source_id=source_id)
            await new_item.create()
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
    trusted_for_delegate_call: bool = Field(nullable=False, default=False)
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
    chain_id: int = Field(default=None, sa_type=BigInteger)

    @classmethod
    def get_contracts_query(
        cls,
        address: bytes | None = None,
        chain_ids: list[int] | None = None,
        trusted_for_delegate_call: bool | None = None,
        only_with_abi: bool = False,
    ) -> SelectBase["Contract"]:
        """
        Return a statement to get contracts with abi for the provided address and chain_id

        :param address:
        :param chain_ids: list of chain_ids, `None` for all chains
        :param trusted_for_delegate_call: only return contracts trusted for delegate call
        :param only_with_abi: only return contracts with ABI
        :return:
        """
        query = select(cls)
        if address:  # Filter by the provided address
            query = query.where(cls.address == address)

        if trusted_for_delegate_call is not None:
            query = query.where(
                cls.trusted_for_delegate_call == trusted_for_delegate_call
            )

        if chain_ids:
            query = query.where(col(cls.chain_id).in_(chain_ids))
        if only_with_abi:
            query = query.where(cls.abi_id.isnot(None))  # type: ignore

        # Sort by address
        query = query.order_by(col(cls.address), col(cls.chain_id))
        return query

    @classmethod
    async def get_contract(cls, address: bytes, chain_id: int):
        query = (
            select(cls).where(cls.address == address).where(cls.chain_id == chain_id)
        )
        results = await db_session.execute(query)
        if result := results.scalars().first():
            return result
        return None

    @classmethod
    async def get_or_create(
        cls,
        address: bytes,
        chain_id: int,
        **kwargs,
    ) -> tuple["Contract", bool]:
        """
        Update or create the given params.

        :param address:
        :param chain_id:
        :param kwargs:
        :return: A tuple containing the Contract object and a boolean indicating
                 whether it was created `True` or already exists `False`.
        """
        if contract := await cls.get_contract(address, chain_id):
            return contract, False
        else:
            contract = cls(address=address, chain_id=chain_id)
            # Add optional fields
            for key, value in kwargs.items():
                setattr(contract, key, value)

            await contract.create()
            return contract, True

    @classmethod
    async def get_abi_by_contract_address(
        cls, address: bytes, chain_id: int | None
    ) -> ABI | None:
        """
        :return: Json ABI given the contract `address` and `chain_id`. If `chain_id` is not given,
            sort the ABIs by `chain_id` and return the first one.
        """
        query = (
            select(Abi.abi_json)
            .join(cls)
            .where(cls.address == address)
            .where(cls.abi_id == Abi.id)
        )
        if chain_id is not None:
            query = query.where(cls.chain_id == chain_id)
        else:
            query = query.order_by(col(cls.chain_id))

        results = await db_session.execute(query)
        if result := results.scalars().first():
            return cast(ABI, result)
        return None

    @classmethod
    async def get_contracts_without_abi(
        cls, max_retries: int = 0
    ) -> AsyncIterator[Self]:
        """
        Fetches contracts without an ABI and fewer retries than max_retries,
        streaming results in batches to reduce memory usage for large datasets.
        More information about streaming results can be found here:
        https://docs.sqlalchemy.org/en/20/core/connections.html#streaming-with-a-dynamically-growing-buffer-using-stream-results

        :param max_retries:
        :return:
        """
        query = (
            select(cls)
            .where(cls.abi_id == None)  # noqa: E711
            .where(cls.fetch_retries <= max_retries)
        )
        result = await db_session.stream(query)
        async for (contract,) in result:
            yield contract

    @classmethod
    async def get_proxy_contracts(cls) -> AsyncIterator[Self]:
        """
        Return all the contracts with implementation address, so proxy contracts.

        :return:
        """
        query = select(cls).where(cls.implementation.isnot(None))  # type: ignore
        result = await db_session.stream(query)
        async for (contract,) in result:
            yield contract

    @classmethod
    async def update_contract_info(
        cls,
        address: bytes,
        name: str,
        display_name: str,
        trusted_for_delegate_call: bool | None = False,
    ) -> int:
        """
        Update the contract metadata for all the chains

        :param address:
        :param name:
        :param display_name:
        :param trusted_for_delegate_call:
        :return: number of affected rows
        """
        query = (
            update(cls)
            .where(col(cls.address) == address)
            .values(
                name=name,
                display_name=display_name,
                trusted_for_delegate_call=trusted_for_delegate_call,
            )
        )
        result = cast(CursorResult, await db_session.execute(query))
        await db_session.commit()
        return result.rowcount
