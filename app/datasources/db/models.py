from typing import Optional

from sqlmodel import Field, SQLModel


class Contract(SQLModel, table=True):
    address: bytes = Field(nullable=False, primary_key=True)
    name: str = Field(nullable=False)
    description: Optional[str] = None
