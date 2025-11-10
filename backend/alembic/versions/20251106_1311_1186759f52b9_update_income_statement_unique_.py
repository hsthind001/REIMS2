"""update_income_statement_unique_constraint_with_account_name

Revision ID: 1186759f52b9
Revises: a103c3096fdd
Create Date: 2025-11-06 13:11:32.265863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1186759f52b9'
down_revision: Union[str, Sequence[str], None] = 'a103c3096fdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account_name to unique constraint for zero data loss - allows hierarchical data (details + totals)."""
    # Drop old constraint (property_id, period_id, account_code)
    op.drop_constraint('uq_is_property_period_account', 'income_statement_data', type_='unique')
    
    # Add new constraint including account_name (property_id, period_id, account_code, account_name)
    # This allows: "Base Rentals", "Base Rentals - Retail", "Base Rentals - Office" to coexist
    op.create_unique_constraint(
        'uq_is_property_period_account_name',
        'income_statement_data',
        ['property_id', 'period_id', 'account_code', 'account_name']
    )


def downgrade() -> None:
    """Restore original constraint (may fail if hierarchical data exists)."""
    op.drop_constraint('uq_is_property_period_account_name', 'income_statement_data', type_='unique')
    op.create_unique_constraint(
        'uq_is_property_period_account',
        'income_statement_data',
        ['property_id', 'period_id', 'account_code']
    )
