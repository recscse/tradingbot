"""add_total_investment_and_lots_traded_columns

Revision ID: 6b1d6e0fe6fa
Revises: 5d88855a7fd3
Create Date: 2025-11-14 09:20:42.609798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b1d6e0fe6fa'
down_revision: Union[str, None] = '5d88855a7fd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add total_investment and lots_traded columns to auto_trade_executions table
    """
    op.add_column('auto_trade_executions', sa.Column('lots_traded', sa.Integer(), nullable=True))
    op.add_column('auto_trade_executions', sa.Column('total_investment', sa.Numeric(precision=15, scale=2), nullable=True))

    # Backfill total_investment for existing records
    op.execute("""
        UPDATE auto_trade_executions
        SET total_investment = entry_price * quantity,
            lots_traded = CASE
                WHEN lot_size > 0 THEN CAST(quantity / lot_size AS INTEGER)
                ELSE 1
            END
        WHERE total_investment IS NULL
    """)


def downgrade() -> None:
    """
    Remove total_investment and lots_traded columns from auto_trade_executions table
    """
    op.drop_column('auto_trade_executions', 'total_investment')
    op.drop_column('auto_trade_executions', 'lots_traded')
