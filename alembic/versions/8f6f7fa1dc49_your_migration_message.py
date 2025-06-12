"""Your migration message

Revision ID: 8f6f7fa1dc49
Revises: f06e34fd3062
Create Date: 2025-06-12 11:20:35.978479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f6f7fa1dc49'
down_revision: Union[str, None] = 'f06e34fd3062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
