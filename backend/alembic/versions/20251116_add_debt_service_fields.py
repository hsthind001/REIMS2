"""Add debt service fields to financial_metrics

Revision ID: 20251116_add_debt_service
Revises: 20251114_next_level_features
Create Date: 2025-11-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251116_add_debt_service'
down_revision = '20251114_next_level_features'
branch_labels = None
depends_on = None


def upgrade():
    """Add debt service related fields to financial_metrics table"""

    # Add debt service fields
    op.add_column('financial_metrics', sa.Column('annual_interest_expense', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('financial_metrics', sa.Column('annual_principal_payment', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('financial_metrics', sa.Column('annual_debt_service', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('financial_metrics', sa.Column('monthly_debt_service', sa.Numeric(precision=15, scale=2), nullable=True))

    # Add DSCR calculation fields
    op.add_column('financial_metrics', sa.Column('dscr', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('financial_metrics', sa.Column('dscr_status', sa.String(20), nullable=True))

    # Add loan/debt fields for context
    op.add_column('financial_metrics', sa.Column('total_long_term_debt', sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column('financial_metrics', sa.Column('debt_calculation_method', sa.String(50), nullable=True))
    op.add_column('financial_metrics', sa.Column('debt_service_calculated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    """Remove debt service fields from financial_metrics table"""

    op.drop_column('financial_metrics', 'debt_service_calculated_at')
    op.drop_column('financial_metrics', 'debt_calculation_method')
    op.drop_column('financial_metrics', 'total_long_term_debt')
    op.drop_column('financial_metrics', 'dscr_status')
    op.drop_column('financial_metrics', 'dscr')
    op.drop_column('financial_metrics', 'monthly_debt_service')
    op.drop_column('financial_metrics', 'annual_debt_service')
    op.drop_column('financial_metrics', 'annual_principal_payment')
    op.drop_column('financial_metrics', 'annual_interest_expense')
