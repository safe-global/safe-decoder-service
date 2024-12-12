from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint, select


class SqlQueryBase:
    @classmethod
    async def get_all(cls, session):
        result = await session.exec(select(cls))
        return result.all()

    async def _save(self, session):
        session.add(self)
        await session.commit()
        return self

    async def update(self, session):
        return await self._save(session)

    async def create(self, session):
        return await self._save(session)


class AbiSource(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    url: str = Field(nullable=False)


class Abi(SqlQueryBase, SQLModel, table=True):
    abi_hash: bytes = Field(nullable=False, primary_key=True)
    relevance: int = Field(nullable=False, default=0)
    abi_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_id: int = Field(default=None, foreign_key="abisource.id")


class Contract(SqlQueryBase, SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("address", "chain_id", name="address_chain_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
    address: bytes = Field(nullable=False)
    name: str = Field(nullable=False)
    display_name: str | None = None
    description: str | None = None
    trusted_for_delegate: bool = Field(nullable=False, default=False)
    proxy: bool = Field(nullable=False, default=False)
    fetch_retries: int = Field(nullable=False, default=0)
    abi_id: bytes | None = Field(
        nullable=True, default=None, foreign_key="abi.abi_hash"
    )
    chain_id: int = Field(default=None)
