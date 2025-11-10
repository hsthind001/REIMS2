"""Fix cash_flow_data schema to match model

Revision ID: fix_cash_flow_schema
Revises: 20251104_1400_seed_chart_of_accounts
Create Date: 2025-11-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5a2f9c1d8b3'
down_revision = 'c8f9e7a6b5d4'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix cash_flow_data table to match CashFlowData model:
    - Add 7 missing columns for Template v1.0 support
    - Make account_id nullable for unmatched accounts
    - Update unique constraint to include line_number
    - Add proper indexes
    """
    
    # Add missing columns
    op.add_column('cash_flow_data', sa.Column('line_category', sa.String(length=100), nullable=True))
    op.add_column('cash_flow_data', sa.Column('line_subcategory', sa.String(length=100), nullable=True))
    op.add_column('cash_flow_data', sa.Column('line_number', sa.Integer(), nullable=True))
    op.add_column('cash_flow_data', sa.Column('is_subtotal', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('cash_flow_data', sa.Column('is_total', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('cash_flow_data', sa.Column('parent_line_id', sa.Integer(), nullable=True))
    op.add_column('cash_flow_data', sa.Column('page_number', sa.Integer(), nullable=True))
    
    # Make account_id nullable to allow unmatched accounts (consistent with balance_sheet_data)
    op.alter_column('cash_flow_data', 'account_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # Drop old unique constraint (if exists)
    # Note: In fresh DB, this constraint won't exist yet, so we can skip this
    
    # Add new unique constraint with line_number
    op.create_unique_constraint(
        'uq_cf_property_period_account_line',
        'cash_flow_data',
        ['property_id', 'period_id', 'account_code', 'line_number']
    )
    
    # Add foreign key for parent_line_id (self-referential)
    op.create_foreign_key(
        'cash_flow_data_parent_line_id_fkey',
        'cash_flow_data', 'cash_flow_data',
        ['parent_line_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for better query performance
    op.create_index('idx_cf_data_line_category', 'cash_flow_data', ['line_category'], unique=False)
    # Note: In fresh DB, we can create idx_cf_data_line_section safely
    op.create_index('idx_cf_data_line_section', 'cash_flow_data', ['line_section'], unique=False)


def downgrade():
    """
    Revert cash_flow_data schema changes
    """
    
    # Drop indexes
    op.drop_index('idx_cf_data_line_category', table_name='cash_flow_data')
    op.drop_index('idx_cf_data_line_section', table_name='cash_flow_data')
    
    # Drop foreign key
    op.drop_constraint('cash_flow_data_parent_line_id_fkey', 'cash_flow_data', type_='foreignkey')
    
    # Drop new unique constraint
    op.drop_constraint('uq_cf_property_period_account_line', 'cash_flow_data', type_='unique')
    
    # Restore old unique constraint
    op.create_unique_constraint(
        'uq_cf_property_period_account',
        'cash_flow_data',
        ['property_id', 'period_id', 'account_code']
    )
    
    # Make account_id NOT NULL again
    op.alter_column('cash_flow_data', 'account_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Drop added columns
    op.drop_column('cash_flow_data', 'page_number')
    op.drop_column('cash_flow_data', 'parent_line_id')
    op.drop_column('cash_flow_data', 'is_total')
    op.drop_column('cash_flow_data', 'is_subtotal')
    op.drop_column('cash_flow_data', 'line_number')
    op.drop_column('cash_flow_data', 'line_subcategory')
    op.drop_column('cash_flow_data', 'line_category')

