"""Add funds and margin fields to broker_configs table

Revision ID: add_funds_margin_fields
Revises: 
Create Date: 2024-12-30 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_funds_margin_fields'
down_revision = None  # Replace with actual latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add funds and margin fields to broker_configs table"""
    # Add new columns for funds and margin data
    op.add_column('broker_configs', sa.Column('available_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('used_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('payin_amount', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('span_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('adhoc_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('notional_cash', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('exposure_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('commodity_available_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('commodity_used_margin', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('funds_last_updated', sa.DateTime(), nullable=True))
    op.add_column('broker_configs', sa.Column('total_portfolio_value', sa.Float(), nullable=True))
    op.add_column('broker_configs', sa.Column('margin_utilization_percent', sa.Float(), nullable=True))
    
    # Add user profile fields
    op.add_column('broker_configs', sa.Column('user_name', sa.String(), nullable=True))
    op.add_column('broker_configs', sa.Column('email', sa.String(), nullable=True))
    op.add_column('broker_configs', sa.Column('user_type', sa.String(), nullable=True))
    op.add_column('broker_configs', sa.Column('exchanges', sa.JSON(), nullable=True))
    op.add_column('broker_configs', sa.Column('products', sa.JSON(), nullable=True))
    op.add_column('broker_configs', sa.Column('order_types', sa.JSON(), nullable=True))
    op.add_column('broker_configs', sa.Column('poa_enabled', sa.Boolean(), nullable=True))
    op.add_column('broker_configs', sa.Column('ddpi_enabled', sa.Boolean(), nullable=True))
    op.add_column('broker_configs', sa.Column('account_status', sa.String(), nullable=True))
    op.add_column('broker_configs', sa.Column('profile_last_updated', sa.DateTime(), nullable=True))


def downgrade():
    """Remove funds and margin fields from broker_configs table"""
    # Remove profile fields
    op.drop_column('broker_configs', 'profile_last_updated')
    op.drop_column('broker_configs', 'account_status')
    op.drop_column('broker_configs', 'ddpi_enabled')
    op.drop_column('broker_configs', 'poa_enabled')
    op.drop_column('broker_configs', 'order_types')
    op.drop_column('broker_configs', 'products')
    op.drop_column('broker_configs', 'exchanges')
    op.drop_column('broker_configs', 'user_type')
    op.drop_column('broker_configs', 'email')
    op.drop_column('broker_configs', 'user_name')
    
    # Remove funds and margin fields
    op.drop_column('broker_configs', 'margin_utilization_percent')
    op.drop_column('broker_configs', 'total_portfolio_value')
    op.drop_column('broker_configs', 'funds_last_updated')
    op.drop_column('broker_configs', 'commodity_used_margin')
    op.drop_column('broker_configs', 'commodity_available_margin')
    op.drop_column('broker_configs', 'exposure_margin')
    op.drop_column('broker_configs', 'notional_cash')
    op.drop_column('broker_configs', 'adhoc_margin')
    op.drop_column('broker_configs', 'span_margin')
    op.drop_column('broker_configs', 'payin_amount')
    op.drop_column('broker_configs', 'used_margin')
    op.drop_column('broker_configs', 'available_margin')