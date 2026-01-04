"""Add Mortgage Statement Tables

Revision ID: 20251219_1901_add_mortgage_statement_tables
Revises: 20251219_rm_cf_constraint
Create Date: 2025-12-19 19:01:00.000000

Adds tables for mortgage statement data:
- mortgage_statement_data: Core mortgage statement information
- mortgage_payment_history: Payment history tracking
- Updates financial_metrics with mortgage-specific columns
- Updates document_uploads constraint to include mortgage_statement
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20251219_1901'  # Shortened to fit VARCHAR(32) limit
down_revision = '20251219_1900'
branch_labels = None
depends_on = None


def upgrade():
    """Create mortgage statement tables and update existing tables."""
    
    # Check if tables already exist (for cases where tables were created manually)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Create mortgage_statement_data table
    if 'mortgage_statement_data' not in existing_tables:
        op.create_table(
            'mortgage_statement_data',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Foreign Keys
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        sa.Column('lender_id', sa.Integer(), nullable=True),
        
        # Loan Identification
        sa.Column('loan_number', sa.String(50), nullable=False),
        sa.Column('loan_type', sa.String(50), nullable=True),  # 'first_mortgage', 'mezzanine', 'line_of_credit'
        sa.Column('property_address', sa.Text(), nullable=True),
        sa.Column('borrower_name', sa.String(255), nullable=True),
        
        # Statement Metadata
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('payment_due_date', sa.Date(), nullable=True),
        sa.Column('statement_period_start', sa.Date(), nullable=True),
        sa.Column('statement_period_end', sa.Date(), nullable=True),
        
        # Current Balances (as of statement date)
        sa.Column('principal_balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('tax_escrow_balance', sa.Numeric(15, 2), server_default='0'),
        sa.Column('insurance_escrow_balance', sa.Numeric(15, 2), server_default='0'),
        sa.Column('reserve_balance', sa.Numeric(15, 2), server_default='0'),
        sa.Column('other_escrow_balance', sa.Numeric(15, 2), server_default='0'),
        sa.Column('suspense_balance', sa.Numeric(15, 2), server_default='0'),
        sa.Column('total_loan_balance', sa.Numeric(15, 2), nullable=True),  # Generated column handled separately
        
        # Current Period Payment Breakdown
        sa.Column('principal_due', sa.Numeric(12, 2), nullable=True),
        sa.Column('interest_due', sa.Numeric(12, 2), nullable=True),
        sa.Column('tax_escrow_due', sa.Numeric(12, 2), nullable=True),
        sa.Column('insurance_escrow_due', sa.Numeric(12, 2), nullable=True),
        sa.Column('reserve_due', sa.Numeric(12, 2), nullable=True),
        sa.Column('late_fees', sa.Numeric(10, 2), server_default='0'),
        sa.Column('other_fees', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_payment_due', sa.Numeric(12, 2), nullable=True),
        
        # Year-to-Date Totals
        sa.Column('ytd_principal_paid', sa.Numeric(15, 2), server_default='0'),
        sa.Column('ytd_interest_paid', sa.Numeric(15, 2), server_default='0'),
        sa.Column('ytd_taxes_disbursed', sa.Numeric(15, 2), server_default='0'),
        sa.Column('ytd_insurance_disbursed', sa.Numeric(15, 2), server_default='0'),
        sa.Column('ytd_reserve_disbursed', sa.Numeric(15, 2), server_default='0'),
        sa.Column('ytd_total_paid', sa.Numeric(15, 2), nullable=True),  # Generated column handled separately
        
        # Loan Terms (from loan documents or statements)
        sa.Column('original_loan_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('interest_rate', sa.Numeric(6, 4), nullable=True),  # e.g., 5.25% stored as 5.2500
        sa.Column('loan_term_months', sa.Integer(), nullable=True),
        sa.Column('maturity_date', sa.Date(), nullable=True),
        sa.Column('origination_date', sa.Date(), nullable=True),
        sa.Column('payment_frequency', sa.String(20), nullable=True),  # 'monthly', 'quarterly', 'annual'
        sa.Column('amortization_type', sa.String(50), nullable=True),  # 'fully_amortizing', 'interest_only', 'balloon'
        
        # Calculated Fields
        sa.Column('remaining_term_months', sa.Integer(), nullable=True),  # Generated column handled separately
        sa.Column('ltv_ratio', sa.Numeric(10, 4), nullable=True),  # To be calculated from property value
        sa.Column('annual_debt_service', sa.Numeric(15, 2), nullable=True),  # Annual P+I payments
        sa.Column('monthly_debt_service', sa.Numeric(12, 2), nullable=True),  # Monthly P+I payments
        
        # Extraction Quality
        sa.Column('extraction_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('extraction_method', sa.String(50), nullable=True),
        sa.Column('extraction_coordinates', JSONB, nullable=True),  # Store bounding boxes for all extracted fields
        
        # Review Workflow
        sa.Column('needs_review', sa.Boolean(), server_default='false'),
        sa.Column('reviewed', sa.Boolean(), server_default='false'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        
        # Validation
        sa.Column('validation_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('has_errors', sa.Boolean(), server_default='false'),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lender_id'], ['lenders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Primary Key
        sa.PrimaryKeyConstraint('id'),
        
        # Unique Constraint
        sa.UniqueConstraint('property_id', 'period_id', 'loan_number', name='uq_mortgage_property_period_loan')
        )
        
        # Create indexes for mortgage_statement_data
        op.create_index('idx_mortgage_property_period', 'mortgage_statement_data', ['property_id', 'period_id'])
        op.create_index('idx_mortgage_lender', 'mortgage_statement_data', ['lender_id'])
        op.create_index('idx_mortgage_review', 'mortgage_statement_data', ['needs_review', 'property_id'])
        op.create_index('idx_mortgage_statement_date', 'mortgage_statement_data', ['statement_date'])
        op.create_index('idx_mortgage_maturity', 'mortgage_statement_data', ['maturity_date'])
    
    # 2. Create mortgage_payment_history table
    if 'mortgage_payment_history' not in existing_tables:
        op.create_table(
        'mortgage_payment_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mortgage_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        
        # Payment Details
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_number', sa.Integer(), nullable=True),  # Payment sequence (e.g., payment 60 of 360)
        
        # Payment Breakdown
        sa.Column('principal_paid', sa.Numeric(12, 2), nullable=False),
        sa.Column('interest_paid', sa.Numeric(12, 2), nullable=False),
        sa.Column('escrow_paid', sa.Numeric(12, 2), server_default='0'),
        sa.Column('fees_paid', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_payment', sa.Numeric(12, 2), nullable=False),
        
        # Balance After Payment
        sa.Column('principal_balance_after', sa.Numeric(15, 2), nullable=True),
        sa.Column('escrow_balance_after', sa.Numeric(12, 2), nullable=True),
        
        # Status
        sa.Column('payment_status', sa.String(50), nullable=True),  # 'on_time', 'late', 'missed', 'prepayment'
        sa.Column('days_late', sa.Integer(), server_default='0'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['mortgage_id'], ['mortgage_statement_data.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        
        # Primary Key
        sa.PrimaryKeyConstraint('id'),
        
        # Unique Constraint
        sa.UniqueConstraint('mortgage_id', 'payment_date', name='uq_mortgage_payment')
        )
        
        # Create indexes for mortgage_payment_history
        op.create_index('idx_payment_mortgage', 'mortgage_payment_history', ['mortgage_id'])
        op.create_index('idx_payment_date', 'mortgage_payment_history', ['payment_date'])
    
    # 3. Add mortgage-specific columns to financial_metrics table (if they don't exist)
    from sqlalchemy import text
    existing_columns = [col['name'] for col in inspector.get_columns('financial_metrics')]
    
    if 'total_mortgage_debt' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_mortgage_debt', sa.Numeric(15, 2), nullable=True))
    if 'weighted_avg_interest_rate' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('weighted_avg_interest_rate', sa.Numeric(6, 4), nullable=True))
    if 'total_monthly_debt_service' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_monthly_debt_service', sa.Numeric(12, 2), nullable=True))
    if 'total_annual_debt_service' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('total_annual_debt_service', sa.Numeric(15, 2), nullable=True))
    if 'dscr' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('dscr', sa.Numeric(10, 4), nullable=True))
    if 'interest_coverage_ratio' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('interest_coverage_ratio', sa.Numeric(10, 4), nullable=True))
    if 'debt_yield' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('debt_yield', sa.Numeric(10, 4), nullable=True))
    if 'break_even_occupancy' not in existing_columns:
        op.add_column('financial_metrics', sa.Column('break_even_occupancy', sa.Numeric(5, 2), nullable=True))
    
    # 4. Update document_uploads constraint to include mortgage_statement
    # First, drop the existing constraint if it exists
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'check_document_type'
            ) THEN
                ALTER TABLE document_uploads DROP CONSTRAINT check_document_type;
            END IF;
        END $$;
    """)
    
    # Add new constraint with mortgage_statement
    op.create_check_constraint(
        'check_document_type',
        'document_uploads',
        "document_type IN ('balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement')"
    )
    
    # Note: Generated columns (total_loan_balance, ytd_total_paid, remaining_term_months)
    # will be calculated in application code using SQLAlchemy hybrid properties or computed columns
    # This avoids complexity with Alembic migration and NULL handling


def downgrade():
    """Remove mortgage statement tables and revert changes."""
    
    # Revert document_uploads constraint
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'check_document_type'
            ) THEN
                ALTER TABLE document_uploads DROP CONSTRAINT check_document_type;
            END IF;
        END $$;
    """)
    
    # Restore original constraint (without mortgage_statement)
    op.create_check_constraint(
        'check_document_type',
        'document_uploads',
        "document_type IN ('balance_sheet', 'income_statement', 'cash_flow', 'rent_roll')"
    )
    
    # Remove columns from financial_metrics
    op.drop_column('financial_metrics', 'break_even_occupancy')
    op.drop_column('financial_metrics', 'debt_yield')
    op.drop_column('financial_metrics', 'interest_coverage_ratio')
    op.drop_column('financial_metrics', 'dscr')
    op.drop_column('financial_metrics', 'total_annual_debt_service')
    op.drop_column('financial_metrics', 'total_monthly_debt_service')
    op.drop_column('financial_metrics', 'weighted_avg_interest_rate')
    op.drop_column('financial_metrics', 'total_mortgage_debt')
    
    # Drop mortgage_payment_history table
    op.drop_index('idx_payment_date', table_name='mortgage_payment_history')
    op.drop_index('idx_payment_mortgage', table_name='mortgage_payment_history')
    op.drop_table('mortgage_payment_history')
    
    # Drop mortgage_statement_data table
    op.drop_index('idx_mortgage_maturity', table_name='mortgage_statement_data')
    op.drop_index('idx_mortgage_statement_date', table_name='mortgage_statement_data')
    op.drop_index('idx_mortgage_review', table_name='mortgage_statement_data')
    op.drop_index('idx_mortgage_lender', table_name='mortgage_statement_data')
    op.drop_index('idx_mortgage_property_period', table_name='mortgage_statement_data')
    op.drop_table('mortgage_statement_data')

