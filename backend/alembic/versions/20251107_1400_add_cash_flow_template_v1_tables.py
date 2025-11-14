"""Add Cash Flow Template v1.0 tables

Revision ID: 20251107_1400
Revises: cf002std0002
Create Date: 2025-11-07 14:00:00

Creates the missing Cash Flow Template v1.0 tables:
- cash_flow_headers: Summary metrics and header metadata
- cash_flow_adjustments: Non-cash adjustments section
- cash_account_reconciliations: Cash account movements

Also adds missing Template v1.0 fields to cash_flow_data table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251107_1400'
down_revision = 'cf002std0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Cash Flow Template v1.0 tables and enhance cash_flow_data"""
    
    # ==================== CREATE cash_flow_headers TABLE ====================
    op.create_table('cash_flow_headers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        
        # Property Identification
        sa.Column('property_name', sa.String(length=255), nullable=False),
        sa.Column('property_code', sa.String(length=50), nullable=False),
        
        # Period Information
        sa.Column('report_period_start', sa.Date(), nullable=False),
        sa.Column('report_period_end', sa.Date(), nullable=False),
        sa.Column('accounting_basis', sa.String(length=50), nullable=False),
        sa.Column('report_generation_date', sa.Date(), nullable=True),
        
        # Income Section Totals
        sa.Column('total_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('base_rentals', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_recovery_income', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_other_income', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Expense Section Totals
        sa.Column('total_operating_expenses', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('total_property_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_utility_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_contracted_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_rm_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_admin_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Additional Expenses
        sa.Column('total_additional_operating_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_management_fees', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_ll_expenses', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Total Expenses
        sa.Column('total_expenses', sa.DECIMAL(precision=15, scale=2), nullable=False),
        
        # Performance Metrics
        sa.Column('net_operating_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('noi_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # Other Income/Expenses
        sa.Column('mortgage_interest', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('depreciation', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('amortization', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('total_other_income_expense', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Net Income
        sa.Column('net_income', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('net_income_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # Adjustments
        sa.Column('total_adjustments', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Cash Flow
        sa.Column('cash_flow', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('cash_flow_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # Cash Account Summary
        sa.Column('beginning_cash_balance', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('ending_cash_balance', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('cash_difference', sa.DECIMAL(precision=15, scale=2), nullable=True),
        
        # Extraction quality
        sa.Column('extraction_confidence', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('validation_passed', sa.Boolean(), nullable=True, server_default='false'),
        
        # Review workflow
        sa.Column('needs_review', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign Keys
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('property_id', 'period_id', name='uq_cf_header_property_period')
    )
    op.create_index('ix_cash_flow_headers_id', 'cash_flow_headers', ['id'])
    op.create_index('ix_cash_flow_headers_property_id', 'cash_flow_headers', ['property_id'])
    op.create_index('ix_cash_flow_headers_period_id', 'cash_flow_headers', ['period_id'])
    
    # ==================== CREATE cash_flow_adjustments TABLE ====================
    op.create_table('cash_flow_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('header_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        
        # Adjustment Classification
        sa.Column('adjustment_category', sa.String(length=100), nullable=False),
        sa.Column('adjustment_name', sa.String(length=255), nullable=False),
        sa.Column('adjustment_description', sa.Text(), nullable=True),
        
        # Financial Data
        sa.Column('amount', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('is_increase', sa.Boolean(), nullable=True),
        
        # Specific Adjustment Details
        sa.Column('account_code', sa.String(length=50), nullable=True),
        sa.Column('related_property', sa.String(length=100), nullable=True),
        sa.Column('related_entity', sa.String(length=255), nullable=True),
        
        # Line positioning
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('is_subtotal', sa.Boolean(), nullable=True, server_default='false'),
        
        # Extraction quality
        sa.Column('extraction_confidence', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # Review workflow
        sa.Column('needs_review', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign Keys
        sa.ForeignKeyConstraint(['header_id'], ['cash_flow_headers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cash_flow_adjustments_id', 'cash_flow_adjustments', ['id'])
    op.create_index('ix_cash_flow_adjustments_header_id', 'cash_flow_adjustments', ['header_id'])
    op.create_index('ix_cash_flow_adjustments_property_id', 'cash_flow_adjustments', ['property_id'])
    op.create_index('ix_cash_flow_adjustments_period_id', 'cash_flow_adjustments', ['period_id'])
    op.create_index('ix_cash_flow_adjustments_category', 'cash_flow_adjustments', ['adjustment_category'])
    
    # ==================== CREATE cash_account_reconciliations TABLE ====================
    op.create_table('cash_account_reconciliations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('header_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('period_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        
        # Account Information
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=True),
        
        # Cash Balances
        sa.Column('beginning_balance', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('ending_balance', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('difference', sa.DECIMAL(precision=15, scale=2), nullable=False),
        
        # Validation
        sa.Column('difference_calculated', sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column('difference_matches', sa.Boolean(), nullable=True, server_default='true'),
        
        # Special Flags
        sa.Column('is_negative_balance', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_escrow_account', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_total_row', sa.Boolean(), nullable=True, server_default='false'),
        
        # Line positioning
        sa.Column('line_number', sa.Integer(), nullable=True),
        
        # Extraction quality
        sa.Column('extraction_confidence', sa.DECIMAL(precision=5, scale=2), nullable=True),
        
        # Review workflow
        sa.Column('needs_review', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Foreign Keys
        sa.ForeignKeyConstraint(['header_id'], ['cash_flow_headers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cash_account_reconciliations_id', 'cash_account_reconciliations', ['id'])
    op.create_index('ix_cash_account_reconciliations_header_id', 'cash_account_reconciliations', ['header_id'])
    op.create_index('ix_cash_account_reconciliations_property_id', 'cash_account_reconciliations', ['property_id'])
    op.create_index('ix_cash_account_reconciliations_period_id', 'cash_account_reconciliations', ['period_id'])
    op.create_index('ix_cash_account_reconciliations_account_type', 'cash_account_reconciliations', ['account_type'])
    
    # ==================== ENHANCE cash_flow_data TABLE ====================
    # Add missing Template v1.0 fields to cash_flow_data if they don't exist
    
    # Add header_id reference
    op.add_column('cash_flow_data', sa.Column('header_id', sa.Integer(), nullable=True))
    op.create_foreign_key('cash_flow_data_header_id_fkey', 'cash_flow_data', 'cash_flow_headers', 
                         ['header_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_cash_flow_data_header_id', 'cash_flow_data', ['header_id'])
    
    # Add Template v1.0 classification fields
    op.add_column('cash_flow_data', sa.Column('line_section', sa.String(length=50), nullable=True))
    op.add_column('cash_flow_data', sa.Column('line_category', sa.String(length=100), nullable=True))
    op.add_column('cash_flow_data', sa.Column('line_subcategory', sa.String(length=100), nullable=True))
    
    # Add hierarchical structure fields
    op.add_column('cash_flow_data', sa.Column('line_number', sa.Integer(), nullable=True))
    op.add_column('cash_flow_data', sa.Column('is_subtotal', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('cash_flow_data', sa.Column('is_total', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('cash_flow_data', sa.Column('parent_line_id', sa.Integer(), nullable=True))
    
    # Add page tracking
    op.add_column('cash_flow_data', sa.Column('page_number', sa.Integer(), nullable=True))
    
    # Create indexes
    op.create_index('ix_cash_flow_data_line_section', 'cash_flow_data', ['line_section'])
    op.create_index('ix_cash_flow_data_line_category', 'cash_flow_data', ['line_category'])
    
    # Add self-referential foreign key for parent_line_id
    op.create_foreign_key('cash_flow_data_parent_line_id_fkey', 'cash_flow_data', 'cash_flow_data',
                         ['parent_line_id'], ['id'], ondelete='SET NULL')
    
    # Make account_id nullable (for unmatched accounts)
    op.alter_column('cash_flow_data', 'account_id', nullable=True)


def downgrade() -> None:
    """Remove Cash Flow Template v1.0 tables and fields"""
    
    # Drop enhanced fields from cash_flow_data
    op.drop_constraint('cash_flow_data_parent_line_id_fkey', 'cash_flow_data', type_='foreignkey')
    op.drop_index('ix_cash_flow_data_line_category', 'cash_flow_data')
    op.drop_index('ix_cash_flow_data_line_section', 'cash_flow_data')
    
    op.drop_column('cash_flow_data', 'page_number')
    op.drop_column('cash_flow_data', 'parent_line_id')
    op.drop_column('cash_flow_data', 'is_total')
    op.drop_column('cash_flow_data', 'is_subtotal')
    op.drop_column('cash_flow_data', 'line_number')
    op.drop_column('cash_flow_data', 'line_subcategory')
    op.drop_column('cash_flow_data', 'line_category')
    op.drop_column('cash_flow_data', 'line_section')
    
    op.drop_constraint('cash_flow_data_header_id_fkey', 'cash_flow_data', type_='foreignkey')
    op.drop_index('ix_cash_flow_data_header_id', 'cash_flow_data')
    op.drop_column('cash_flow_data', 'header_id')
    
    # Make account_id NOT NULL again
    op.alter_column('cash_flow_data', 'account_id', nullable=False)
    
    # Drop tables
    op.drop_index('ix_cash_account_reconciliations_account_type', 'cash_account_reconciliations')
    op.drop_index('ix_cash_account_reconciliations_period_id', 'cash_account_reconciliations')
    op.drop_index('ix_cash_account_reconciliations_property_id', 'cash_account_reconciliations')
    op.drop_index('ix_cash_account_reconciliations_header_id', 'cash_account_reconciliations')
    op.drop_index('ix_cash_account_reconciliations_id', 'cash_account_reconciliations')
    op.drop_table('cash_account_reconciliations')
    
    op.drop_index('ix_cash_flow_adjustments_category', 'cash_flow_adjustments')
    op.drop_index('ix_cash_flow_adjustments_period_id', 'cash_flow_adjustments')
    op.drop_index('ix_cash_flow_adjustments_property_id', 'cash_flow_adjustments')
    op.drop_index('ix_cash_flow_adjustments_header_id', 'cash_flow_adjustments')
    op.drop_index('ix_cash_flow_adjustments_id', 'cash_flow_adjustments')
    op.drop_table('cash_flow_adjustments')
    
    op.drop_index('ix_cash_flow_headers_period_id', 'cash_flow_headers')
    op.drop_index('ix_cash_flow_headers_property_id', 'cash_flow_headers')
    op.drop_index('ix_cash_flow_headers_id', 'cash_flow_headers')
    op.drop_table('cash_flow_headers')

