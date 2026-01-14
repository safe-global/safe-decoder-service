"""change chain_id to bigint

Revision ID: 0da35e86b777
Revises: 03d30b614dc0
Create Date: 2026-01-09 13:25:11.520520

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0da35e86b777"
down_revision: str | None = "03d30b614dc0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # alter column chain_id from Integer to BigInteger
    op.alter_column(
        "contract",
        "chain_id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # back column chain_id from BigInteger to Integer
    op.alter_column(
        "contract",
        "chain_id",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
