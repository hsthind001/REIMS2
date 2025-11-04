"""Add CHECK constraints to core tables

Revision ID: a9a5178a1b3f
Revises: 61e979087abb
Create Date: 2025-11-03 13:17:55.234224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9a5178a1b3f'
down_revision: Union[str, Sequence[str], None] = '61e979087abb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add CHECK constraint for properties.status
    op.create_check_constraint(
        'ck_properties_status',
        'properties',
        "status IN ('active', 'sold', 'under_contract')"
    )
    
    # Add CHECK constraint for financial_periods.period_month
    op.create_check_constraint(
        'ck_financial_periods_month',
        'financial_periods',
        'period_month BETWEEN 1 AND 12'
    )
    
    # Add CHECK constraint for financial_periods.fiscal_quarter
    op.create_check_constraint(
        'ck_financial_periods_quarter',
        'financial_periods',
        'fiscal_quarter IS NULL OR (fiscal_quarter BETWEEN 1 AND 4)'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop CHECK constraints
    op.drop_constraint('ck_financial_periods_quarter', 'financial_periods', type_='check')
    op.drop_constraint('ck_financial_periods_month', 'financial_periods', type_='check')
    op.drop_constraint('ck_properties_status', 'properties', type_='check')
