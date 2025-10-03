"""rename_trusted_for_delegate_field

Revision ID: 03d30b614dc0
Revises: 66c1eb4456de
Create Date: 2025-06-12 16:21:34.126552

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03d30b614dc0"
down_revision: str | None = "66c1eb4456de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename column name
    op.alter_column(
        "contract", "trusted_for_delegate", new_column_name="trusted_for_delegate_call"
    )


def downgrade() -> None:
    # Back to previous column name
    op.alter_column(
        "contract", "trusted_for_delegate_call", new_column_name="trusted_for_delegate"
    )
