from typing import AsyncIterator, cast, Sequence

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
from web3.types import ABI


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


class AbiSource(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    url: str = Field(nullable=False)

    abis: list["Abi"] = Relationship(back_populates="source")


class Abi(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    abi_hash: bytes = Field(nullable=False, index=True, unique=True)
    relevance: int | None = Field(nullable=False, default=0)
    abi_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_id: int | None = Field(
        nullable=True, default=None, foreign_key="abisource.id"
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


class Project(SqlQueryBase, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    description: str = Field(nullable=False)
    logo_file: str = Field(nullable=False)
    contracts: list["Contract"] = Relationship(back_populates="project")


class Contract(SqlQueryBase, SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("address", "chain_id", name="address_chain_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
    address: bytes = Field(nullable=False, index=True)
    name: str = Field(nullable=False)
    display_name: str | None = None
    description: str | None = None
    trusted_for_delegate: bool = Field(nullable=False, default=False)
    proxy: bool = Field(nullable=False, default=False)
    fetch_retries: int = Field(nullable=False, default=0)
    abi_id: bytes | None = Field(
        nullable=True, default=None, foreign_key="abi.abi_hash"
    )
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
    def get_contract(
        cls, address: bytes, chain_ids: list[int] | None = None
    ) -> SelectBase["Contract"]:
        query = select(cls).where(cls.address == address)
        if chain_ids:
            query = query.where(col(cls.chain_id).in_(chain_ids))

        return query

    @classmethod
    async def get_abi_by_contract_address(
        cls, session: AsyncSession, address: bytes
    ) -> ABI | None:
        # TODO Add chain_id filter to support multichain
        results = await session.exec(
            select(Abi.abi_json)
            .join(cls)
            .where(cls.address == address)
            .where(cls.abi_id == Abi.abi_hash)
        )
        if result := results.first():
            return cast(ABI, result)
        return None
