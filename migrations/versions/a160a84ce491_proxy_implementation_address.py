"""proxy_implementation_address

Revision ID: a160a84ce491
Revises: 148330712a84
Create Date: 2024-12-27 15:50:29.338693

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a160a84ce491"
down_revision: Union[str, None] = "148330712a84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "contract", sa.Column("implementation", sa.LargeBinary(), nullable=True)
    )
    op.drop_column("contract", "proxy")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "contract",
        sa.Column("proxy", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.drop_column("contract", "implementation")
    # ### end Alembic commands ###
