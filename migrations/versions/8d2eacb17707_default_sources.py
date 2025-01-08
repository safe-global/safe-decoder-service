"""default_sources

Revision ID: 8d2eacb17707
Revises: e4e2e62601d2
Create Date: 2025-01-08 12:32:30.338594

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d2eacb17707"
down_revision: Union[str, None] = "e4e2e62601d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        """
        INSERT INTO abisource (name, url)
        VALUES ('Etherscan', ''),
               ('Sourcify', ''),
               ('Blockscout', '');
        """
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute(
        """
        DELETE FROM abisource
        WHERE (name = 'Etherscan' AND url = '')
           OR (name = 'Sourcify' AND url = '')
           OR (name = 'Blockscout' AND url = '');
        """
    )
    # ### end Alembic commands ###
