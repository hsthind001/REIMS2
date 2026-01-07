"""add missing financial metrics columns

Revision ID: 20260106_1722
Revises: 45d5e95beac4, 20260102_0001
Create Date: 2026-01-06 17:22:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DECIMAL


# revision identifiers, used by Alembic.
revision = '20260106_1722'
down_revision = ('45d5e95beac4', '20260102_0001')
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to financial_metrics table"""

    # Get existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('financial_metrics')}

    # Balance Sheet Totals
    if 'total_current_assets' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_current_assets', DECIMAL(15, 2), nullable=True))
    if 'total_property_equipment' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_property_equipment', DECIMAL(15, 2), nullable=True))
    if 'total_other_assets' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_other_assets', DECIMAL(15, 2), nullable=True))
    if 'total_current_liabilities' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_current_liabilities', DECIMAL(15, 2), nullable=True))
    if 'total_long_term_liabilities' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_long_term_liabilities', DECIMAL(15, 2), nullable=True))

    # Liquidity Metrics
    if 'quick_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('quick_ratio', DECIMAL(10, 4), nullable=True))
    if 'cash_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('cash_ratio', DECIMAL(10, 4), nullable=True))
    if 'working_capital' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('working_capital', DECIMAL(15, 2), nullable=True))

    # Leverage Metrics
    if 'debt_to_assets_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('debt_to_assets_ratio', DECIMAL(10, 4), nullable=True))
    if 'equity_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('equity_ratio', DECIMAL(10, 4), nullable=True))
    if 'ltv_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('ltv_ratio', DECIMAL(10, 4), nullable=True))

    # Property Metrics
    if 'gross_property_value' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('gross_property_value', DECIMAL(15, 2), nullable=True))
    if 'accumulated_depreciation' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('accumulated_depreciation', DECIMAL(15, 2), nullable=True))
    if 'net_property_value' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('net_property_value', DECIMAL(15, 2), nullable=True))
    if 'depreciation_rate' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('depreciation_rate', DECIMAL(10, 4), nullable=True))
    if 'land_value' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('land_value', DECIMAL(15, 2), nullable=True))
    if 'building_value_net' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('building_value_net', DECIMAL(15, 2), nullable=True))
    if 'improvements_value_net' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('improvements_value_net', DECIMAL(15, 2), nullable=True))

    # Cash Position Analysis
    if 'operating_cash' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('operating_cash', DECIMAL(15, 2), nullable=True))
    if 'restricted_cash' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('restricted_cash', DECIMAL(15, 2), nullable=True))
    if 'total_cash_position' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_cash_position', DECIMAL(15, 2), nullable=True))

    # Receivables Analysis
    if 'tenant_receivables' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('tenant_receivables', DECIMAL(15, 2), nullable=True))
    if 'intercompany_receivables' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('intercompany_receivables', DECIMAL(15, 2), nullable=True))
    if 'other_receivables' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('other_receivables', DECIMAL(15, 2), nullable=True))
    if 'total_receivables' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_receivables', DECIMAL(15, 2), nullable=True))
    if 'ar_percentage_of_assets' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('ar_percentage_of_assets', DECIMAL(10, 4), nullable=True))

    # Debt Analysis
    if 'short_term_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('short_term_debt', DECIMAL(15, 2), nullable=True))
    if 'institutional_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('institutional_debt', DECIMAL(15, 2), nullable=True))
    if 'mezzanine_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('mezzanine_debt', DECIMAL(15, 2), nullable=True))
    if 'shareholder_loans' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('shareholder_loans', DECIMAL(15, 2), nullable=True))
    if 'long_term_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('long_term_debt', DECIMAL(15, 2), nullable=True))
    if 'total_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_debt', DECIMAL(15, 2), nullable=True))

    # Equity Analysis
    if 'partners_contribution' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('partners_contribution', DECIMAL(15, 2), nullable=True))
    if 'beginning_equity' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('beginning_equity', DECIMAL(15, 2), nullable=True))
    if 'partners_draw' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('partners_draw', DECIMAL(15, 2), nullable=True))
    if 'distributions' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('distributions', DECIMAL(15, 2), nullable=True))
    if 'current_period_earnings' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('current_period_earnings', DECIMAL(15, 2), nullable=True))
    if 'ending_equity' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('ending_equity', DECIMAL(15, 2), nullable=True))
    if 'equity_change' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('equity_change', DECIMAL(15, 2), nullable=True))


def downgrade():
    """Remove added columns from financial_metrics table"""

    # Get existing columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('financial_metrics')}

    # Remove columns in reverse order
    columns_to_remove = [
        'equity_change', 'ending_equity', 'current_period_earnings', 'distributions',
        'partners_draw', 'beginning_equity', 'partners_contribution',
        'total_debt', 'long_term_debt', 'shareholder_loans', 'mezzanine_debt',
        'institutional_debt', 'short_term_debt',
        'ar_percentage_of_assets', 'total_receivables', 'other_receivables',
        'intercompany_receivables', 'tenant_receivables',
        'total_cash_position', 'restricted_cash', 'operating_cash',
        'improvements_value_net', 'building_value_net', 'land_value',
        'depreciation_rate', 'net_property_value', 'accumulated_depreciation',
        'gross_property_value',
        'ltv_ratio', 'equity_ratio', 'debt_to_assets_ratio',
        'working_capital', 'cash_ratio', 'quick_ratio',
        'total_long_term_liabilities', 'total_current_liabilities',
        'total_other_assets', 'total_property_equipment', 'total_current_assets'
    ]

    for col in columns_to_remove:
        if col in existing_columns:
            op.drop_column('financial_metrics', col)
