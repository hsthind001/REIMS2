"""Remove old cash flow unique constraint

Revision ID: 20251219_remove_old_cf_constraint
Revises: 20251219_extraction_task_id
Create Date: 2025-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251219_remove_old_cf_constraint'
down_revision = '20251219_extraction_task_id'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove old unique constraint that doesn't include line_number.
    
    The old constraint uq_cf_property_period_account on (property_id, period_id, account_code)
    prevents inserting multiple line items with the same account_code but different line_numbers.
    
    We keep only uq_cf_property_period_account_name_line which includes line_number,
    allowing proper hierarchical cash flow data structure.
    """
    # Drop the old constraint that doesn't include line_number
    op.drop_constraint('uq_cf_property_period_account', 'cash_flow_data', type_='unique')


def downgrade():
    """
    Restore the old constraint (may fail if duplicate data exists).
    """
    op.create_unique_constraint(
        'uq_cf_property_period_account',
        'cash_flow_data',
        ['property_id', 'period_id', 'account_code']
    )

