"""merge add_funds_margin_fields and cea74a18a738

Revision ID: e43786963138
Revises: add_funds_margin_fields, cea74a18a738
Create Date: 2025-08-30 13:06:45.619454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e43786963138'
down_revision: Union[str, None] = ('add_funds_margin_fields', 'cea74a18a738')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
