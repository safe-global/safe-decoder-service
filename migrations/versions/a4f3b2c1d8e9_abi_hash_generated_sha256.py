"""abi_hash_generated_sha256

Replace the manually-computed 4-byte MD5 abi_hash column with a PostgreSQL
GENERATED ALWAYS AS column that stores sha256(abi_json::jsonb::text::bytea).
JSONB normalises key ordering, making the hash stable regardless of insertion
order. The unique constraint continues to enforce ABI deduplication.

Revision ID: a4f3b2c1d8e9
Revises: 0da35e86b777
Create Date: 2026-04-16

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a4f3b2c1d8e9"
down_revision: str | None = "0da35e86b777"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX ix_abi_abi_hash")
    op.execute("ALTER TABLE abi DROP COLUMN abi_hash")
    op.execute(
        "ALTER TABLE abi ADD COLUMN abi_hash bytea"
        " GENERATED ALWAYS AS (sha256(abi_json::jsonb::text::bytea)) STORED"
    )
    op.execute("CREATE UNIQUE INDEX ix_abi_abi_hash ON abi (abi_hash)")


def downgrade() -> None:
    op.execute("DROP INDEX ix_abi_abi_hash")
    op.execute("ALTER TABLE abi DROP COLUMN abi_hash")
    op.execute("ALTER TABLE abi ADD COLUMN abi_hash bytea")
    op.execute("CREATE UNIQUE INDEX ix_abi_abi_hash ON abi (abi_hash)")
    # Note: downgrade leaves abi_hash NULL for all existing rows.
    # Full reversal would require recomputing get_md5_abi_hash per row in Python.
