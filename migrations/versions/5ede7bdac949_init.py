"""init

Revision ID: 5ede7bdac949
Revises:
Create Date: 2024-12-26 13:29:11.879091

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ede7bdac949"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "abisource",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("logo_file", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "abi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("abi_hash", sa.LargeBinary(), nullable=False),
        sa.Column("relevance", sa.Integer(), nullable=False),
        sa.Column("abi_json", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["abisource.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_abi_abi_hash"), "abi", ["abi_hash"], unique=True)
    op.create_table(
        "contract",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("address", sa.LargeBinary(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("trusted_for_delegate", sa.Boolean(), nullable=False),
        sa.Column("proxy", sa.Boolean(), nullable=False),
        sa.Column("fetch_retries", sa.Integer(), nullable=False),
        sa.Column("abi_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["abi_id"],
            ["abi.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("address", "chain_id", name="address_chain_unique"),
    )
    op.create_index(op.f("ix_contract_address"), "contract", ["address"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_contract_address"), table_name="contract")
    op.drop_table("contract")
    op.drop_index(op.f("ix_abi_abi_hash"), table_name="abi")
    op.drop_table("abi")
    op.drop_table("project")
    op.drop_table("abisource")
    # ### end Alembic commands ###
