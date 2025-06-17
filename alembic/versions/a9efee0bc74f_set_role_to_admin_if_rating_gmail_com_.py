"""Set role to admin if rating@gmail.com exists

Revision ID: a9efee0bc74f
Revises: 8f6f7fa1dc49
Create Date: 2025-06-18 02:59:14.631365

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9efee0bc74f"
down_revision: Union[str, None] = "8f6f7fa1dc49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if user with email exists and update role to 'admin'
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM users WHERE email = 'rating@gmail.com'
            ) THEN
                UPDATE users
                SET role = 'admin'
                WHERE email = 'rating@gmail.com';
            END IF;
        END $$;
    """
    )


def downgrade() -> None:
    # Revert role back to 'user' if user exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM users WHERE email = 'rating@gmail.com'
            ) THEN
                UPDATE users
                SET role = 'user'
                WHERE email = 'rating@gmail.com';
            END IF;
        END $$;
    """
    )
  
