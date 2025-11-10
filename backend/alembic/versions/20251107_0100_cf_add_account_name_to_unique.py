"""update_cash_flow_unique_constraint_add_account_name

Revision ID: cf001aadd001
Revises: 1186759f52b9
Create Date: 2025-11-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf001aadd001'
down_revision: Union[str, Sequence[str], None] = '1186759f52b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account_name to cash flow unique constraint for hierarchical support (zero data loss)."""
    # Drop old constraint (property_id, period_id, account_code, line_number)
    op.drop_constraint('uq_cf_property_period_account_line', 'cash_flow_data', type_='unique')
    
    # Add new constraint including account_name (property_id, period_id, account_code, account_name, line_number)
    # This allows: "Base Rentals", "Base Rentals - Retail", "Base Rentals - Office" to coexist
    op.create_unique_constraint(
        'uq_cf_property_period_account_name_line',
        'cash_flow_data',
        ['property_id', 'period_id', 'account_code', 'account_name', 'line_number']
    )


def downgrade() -> None:
    """Restore original constraint (may fail if hierarchical data exists)."""
    op.drop_constraint('uq_cf_property_period_account_name_line', 'cash_flow_data', type_='unique')
    op.create_unique_constraint(
        'uq_cf_property_period_account_line',
        'cash_flow_data',
        ['property_id', 'period_id', 'account_code', 'line_number']
    )

