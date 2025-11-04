"""add balance sheet template v1.0 fields

Revision ID: 20251104_1203
Revises: c8f9e7a6b5d4
Create Date: 2025-11-04 12:03:00

Adds comprehensive fields for Balance Sheet Extraction Requirements v1.0:
- Header metadata (report_title, period_ending, accounting_basis, report_date, page_number)
- Hierarchical structure (is_subtotal, is_total, account_level, account_category, account_subcategory)
- Quality tracking (match_confidence, extraction_method)
- Financial specifics (is_contra_account, expected_sign)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251104_1203'
down_revision = 'c8f9e7a6b5d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Balance Sheet Template v1.0 fields"""
    
    # ==================== HEADER METADATA ====================
    op.add_column('balance_sheet_data', 
        sa.Column('report_title', sa.String(100), server_default='Balance Sheet'))
    op.add_column('balance_sheet_data', 
        sa.Column('period_ending', sa.String(50), nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('accounting_basis', sa.String(20), nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('report_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('page_number', sa.Integer, nullable=True))
    
    # ==================== HIERARCHICAL STRUCTURE ====================
    op.add_column('balance_sheet_data', 
        sa.Column('is_subtotal', sa.Boolean, server_default='false'))
    op.add_column('balance_sheet_data', 
        sa.Column('is_total', sa.Boolean, server_default='false'))
    op.add_column('balance_sheet_data', 
        sa.Column('account_level', sa.Integer, nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('account_category', sa.String(100), nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('account_subcategory', sa.String(100), nullable=True))
    
    # ==================== FINANCIAL SPECIFICS ====================
    op.add_column('balance_sheet_data', 
        sa.Column('is_contra_account', sa.Boolean, server_default='false'))
    op.add_column('balance_sheet_data', 
        sa.Column('expected_sign', sa.String(10), nullable=True))
    
    # ==================== EXTRACTION QUALITY ====================
    op.add_column('balance_sheet_data', 
        sa.Column('match_confidence', sa.DECIMAL(5, 2), nullable=True))
    op.add_column('balance_sheet_data', 
        sa.Column('extraction_method', sa.String(50), nullable=True))
    
    # Create indexes for performance
    op.create_index('idx_bs_is_subtotal', 'balance_sheet_data', ['is_subtotal'])
    op.create_index('idx_bs_is_total', 'balance_sheet_data', ['is_total'])
    op.create_index('idx_bs_page_number', 'balance_sheet_data', ['page_number'])


def downgrade() -> None:
    """Remove Balance Sheet Template v1.0 fields"""
    
    # Drop indexes
    op.drop_index('idx_bs_page_number', 'balance_sheet_data')
    op.drop_index('idx_bs_is_total', 'balance_sheet_data')
    op.drop_index('idx_bs_is_subtotal', 'balance_sheet_data')
    
    # Drop columns (in reverse order)
    op.drop_column('balance_sheet_data', 'extraction_method')
    op.drop_column('balance_sheet_data', 'match_confidence')
    op.drop_column('balance_sheet_data', 'expected_sign')
    op.drop_column('balance_sheet_data', 'is_contra_account')
    op.drop_column('balance_sheet_data', 'account_subcategory')
    op.drop_column('balance_sheet_data', 'account_category')
    op.drop_column('balance_sheet_data', 'account_level')
    op.drop_column('balance_sheet_data', 'is_total')
    op.drop_column('balance_sheet_data', 'is_subtotal')
    op.drop_column('balance_sheet_data', 'page_number')
    op.drop_column('balance_sheet_data', 'report_date')
    op.drop_column('balance_sheet_data', 'accounting_basis')
    op.drop_column('balance_sheet_data', 'period_ending')
    op.drop_column('balance_sheet_data', 'report_title')

