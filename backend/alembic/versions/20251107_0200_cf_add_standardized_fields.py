"""add_standardized_fields_to_cash_flow

Revision ID: cf002std0002
Revises: cf001aadd001
Create Date: 2025-11-07 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf002std0002'
down_revision: Union[str, Sequence[str], None] = 'cf001aadd001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add standardized fields to cash_flow_data for consistency with balance_sheet and income_statement."""
    # Add account_level column (1-4 hierarchy depth)
    op.add_column('cash_flow_data', sa.Column('account_level', sa.Integer(), nullable=True))
    
    # Add extraction_method column ("table", "text", "template")
    op.add_column('cash_flow_data', sa.Column('extraction_method', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove standardized fields."""
    op.drop_column('cash_flow_data', 'extraction_method')
    op.drop_column('cash_flow_data', 'account_level')

