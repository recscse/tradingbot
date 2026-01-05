"""update_user_role_to_admin

Revision ID: d4b665073e28
Revises: 6b1d6e0fe6fa
Create Date: 2026-01-04 21:04:35.142096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b665073e28'
down_revision: Union[str, None] = '6b1d6e0fe6fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'Admin' WHERE email = 'brijeshyadav30599@gmail.com'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'trader' WHERE email = 'brijeshyadav30599@gmail.com'")
