from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint


class AbiSource(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    url: str = Field(nullable=False)


class Abi(SQLModel, table=True):
    abi_hash: bytes = Field(nullable=False, primary_key=True)
    relevance: int = Field(nullable=False, default=0)
    abi_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source_id: int = Field(default=None, foreign_key="abisource.id")


class Chain(SQLModel, table=True):
    id: int = Field(primary_key=True)  # Chain ID
    name: str = Field(nullable=False)


class Contract(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("address", "chain_id", name="address_chain_unique"),
    )

    address: bytes = Field(nullable=False, primary_key=True)
    name: str = Field(nullable=False)
    display_name: str | None = None
    description: str | None = None
    trusted_for_delegate: bool = Field(nullable=False, default=False)
    proxy: bool = Field(nullable=False, default=False)
    fetch_retries: int = Field(nullable=False, default=0)
    abi_id: bytes | None = Field(
        nullable=True, default=None, foreign_key="abi.abi_hash"
    )
    chain_id: int = Field(default=None, foreign_key="chain.id")
