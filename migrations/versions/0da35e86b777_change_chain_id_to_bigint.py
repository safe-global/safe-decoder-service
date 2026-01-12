"""change chain_id to bigint

Revision ID: 0da35e86b777
Revises: 03d30b614dc0
Create Date: 2026-01-09 13:25:11.520520

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0da35e86b777"
down_revision: Union[str, None] = "03d30b614dc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # alter column chain_id from Integer to BigInteger
    op.alter_column(
        "contract",
        "chain_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # back column chain_id from BigInteger to Integer
    op.alter_column(
        "contract",
        "chain_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )

