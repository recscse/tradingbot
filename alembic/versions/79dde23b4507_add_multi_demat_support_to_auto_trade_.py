"""add_multi_demat_support_to_auto_trade_execution

Revision ID: 79dde23b4507
Revises: 65096d87f51c
Create Date: 2025-10-04 12:31:56.908709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79dde23b4507'
down_revision: Union[str, None] = '65096d87f51c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add multi-demat support columns to auto_trade_executions table
    op.add_column('auto_trade_executions', sa.Column('broker_name', sa.String(50), nullable=True))
    op.add_column('auto_trade_executions', sa.Column('broker_config_id', sa.Integer(), nullable=True))
    op.add_column('auto_trade_executions', sa.Column('allocated_capital', sa.Numeric(15, 2), nullable=True))
    op.add_column('auto_trade_executions', sa.Column('parent_trade_id', sa.String(100), nullable=True))
    op.add_column('auto_trade_executions', sa.Column('trading_mode', sa.String(20), nullable=True, server_default='paper'))

    # Create indexes for performance
    op.create_index('ix_auto_trade_executions_broker_name', 'auto_trade_executions', ['broker_name'])
    op.create_index('ix_auto_trade_executions_parent_trade_id', 'auto_trade_executions', ['parent_trade_id'])
    op.create_index('ix_auto_trade_executions_trading_mode', 'auto_trade_executions', ['trading_mode'])

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_auto_trade_executions_broker_config',
        'auto_trade_executions',
        'broker_configs',
        ['broker_config_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_auto_trade_executions_broker_config', 'auto_trade_executions', type_='foreignkey')

    # Drop indexes
    op.drop_index('ix_auto_trade_executions_trading_mode', 'auto_trade_executions')
    op.drop_index('ix_auto_trade_executions_parent_trade_id', 'auto_trade_executions')
    op.drop_index('ix_auto_trade_executions_broker_name', 'auto_trade_executions')

    # Drop columns
    op.drop_column('auto_trade_executions', 'trading_mode')
    op.drop_column('auto_trade_executions', 'parent_trade_id')
    op.drop_column('auto_trade_executions', 'allocated_capital')
    op.drop_column('auto_trade_executions', 'broker_config_id')
    op.drop_column('auto_trade_executions', 'broker_name')
