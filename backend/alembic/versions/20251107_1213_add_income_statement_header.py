"""Add income_statement_headers table for Template v1.0

Revision ID: 20251107_1213
Revises: 20251107_0200_cf_add_standardized_fields
Create Date: 2025-11-07 12:13:00

Creates comprehensive income_statement_headers table with:
- Property and period identification
- Report metadata (dates, accounting basis, period type)
- Income section totals (Base Rentals, Recovery Income, Other Income)
- Operating expense totals (Property, Utility, Contracted, R&M, Admin)
- Additional expense totals (Management, Leasing, Landlord)
- Performance metrics (NOI, Net Income with percentages)
- Other income/expenses (Mortgage Interest, Depreciation, Amortization)
- Quality tracking and review workflow

Also adds header_id column to income_statement_data for linking.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251107_1213'
down_revision = '20251107_0200_cf_add_standardized_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create income_statement_headers table and add header_id to income_statement_data"""
    
    # ==================== CREATE INCOME_STATEMENT_HEADERS TABLE ====================
    op.create_table(
        'income_statement_headers',
        
        # Primary Key
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Foreign Keys
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        
        # ==================== PROPERTY IDENTIFICATION ====================
        sa.Column('property_name', sa.String(length=255), nullable=False),
        sa.Column('property_code', sa.String(length=50), nullable=False),
        
        # ==================== PERIOD INFORMATION ====================
        sa.Column('report_period_start', sa.Date(), nullable=False),
        sa.Column('report_period_end', sa.Date(), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('accounting_basis', sa.String(length=50), nullable=False),
        sa.Column('report_generation_date', sa.Date(), nullable=True),
        
        # ==================== INCOME SECTION TOTALS ====================
        sa.Column('total_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('base_rentals', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_recovery_income', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_other_income', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # ==================== OPERATING EXPENSES TOTALS ====================
        sa.Column('total_operating_expenses', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('total_property_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_utility_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_contracted_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_rm_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_admin_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # ==================== ADDITIONAL OPERATING EXPENSES ====================
        sa.Column('total_additional_operating_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_management_fees', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_leasing_costs', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_ll_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # ==================== TOTAL EXPENSES ====================
        sa.Column('total_expenses', sa.DECIMAL(precision=15, scale=2), nullable=False),
        
        # ==================== NET OPERATING INCOME (NOI) ====================
        sa.Column('net_operating_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('noi_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # ==================== OTHER INCOME/EXPENSES (BELOW THE LINE) ====================
        sa.Column('mortgage_interest', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('depreciation', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('amortization', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_other_income_expense', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # ==================== NET INCOME (BOTTOM LINE) ====================
        sa.Column('net_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('net_income_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # ==================== EXTRACTION QUALITY ====================
        sa.Column('extraction_confidence', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('validation_passed', sa.Boolean(), server_default='false'),
        
        # ==================== REVIEW WORKFLOW ====================
        sa.Column('needs_review', sa.Boolean(), server_default='false'),
        sa.Column('reviewed', sa.Boolean(), server_default='false'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        
        # ==================== METADATA ====================
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Primary Key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], )
    )
    
    # Create indexes for better query performance
    op.create_index('ix_income_statement_headers_property_id', 'income_statement_headers', ['property_id'])
    op.create_index('ix_income_statement_headers_period_id', 'income_statement_headers', ['period_id'])
    op.create_index('ix_income_statement_headers_id', 'income_statement_headers', ['id'])
    
    # ==================== ADD HEADER_ID TO INCOME_STATEMENT_DATA ====================
    op.add_column('income_statement_data',
        sa.Column('header_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_income_statement_data_header_id',
        'income_statement_data',
        'income_statement_headers',
        ['header_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on header_id for better query performance
    op.create_index('ix_income_statement_data_header_id', 'income_statement_data', ['header_id'])


def downgrade() -> None:
    """Remove income_statement_headers table and header_id from income_statement_data"""
    
    # Drop index and foreign key from income_statement_data
    op.drop_index('ix_income_statement_data_header_id', 'income_statement_data')
    op.drop_constraint('fk_income_statement_data_header_id', 'income_statement_data', type_='foreignkey')
    op.drop_column('income_statement_data', 'header_id')
    
    # Drop indexes from income_statement_headers
    op.drop_index('ix_income_statement_headers_id', 'income_statement_headers')
    op.drop_index('ix_income_statement_headers_period_id', 'income_statement_headers')
    op.drop_index('ix_income_statement_headers_property_id', 'income_statement_headers')
    
    # Drop income_statement_headers table
    op.drop_table('income_statement_headers')

