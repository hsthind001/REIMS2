"""add income statement template v1.0 fields

Revision ID: 20251104_1205
Revises: 20251104_1203
Create Date: 2025-11-04 12:05:00

Adds comprehensive fields for Income Statement Extraction Requirements v1.0:
- Header metadata (period_type, period_start_date, period_end_date, accounting_basis, report_generation_date, page_number)
- Hierarchical structure (is_subtotal, is_total, line_category, line_subcategory, line_number, account_level)
- Quality tracking (match_confidence, extraction_method)
- Classification (is_below_the_line for depreciation, amortization, mortgage interest)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251104_1205'
down_revision = '20251104_1203'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Income Statement Template v1.0 fields"""
    
    # ==================== HEADER METADATA ====================
    op.add_column('income_statement_data', 
        sa.Column('period_type', sa.String(20), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('period_start_date', sa.String(50), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('period_end_date', sa.String(50), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('accounting_basis', sa.String(20), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('report_generation_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('page_number', sa.Integer, nullable=True))
    
    # ==================== HIERARCHICAL STRUCTURE ====================
    op.add_column('income_statement_data', 
        sa.Column('is_subtotal', sa.Boolean, server_default='false'))
    op.add_column('income_statement_data', 
        sa.Column('is_total', sa.Boolean, server_default='false'))
    op.add_column('income_statement_data', 
        sa.Column('line_category', sa.String(100), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('line_subcategory', sa.String(100), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('line_number', sa.Integer, nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('account_level', sa.Integer, nullable=True))
    
    # ==================== CLASSIFICATION ====================
    op.add_column('income_statement_data', 
        sa.Column('is_below_the_line', sa.Boolean, server_default='false'))
    
    # ==================== EXTRACTION QUALITY ====================
    op.add_column('income_statement_data', 
        sa.Column('match_confidence', sa.DECIMAL(5, 2), nullable=True))
    op.add_column('income_statement_data', 
        sa.Column('extraction_method', sa.String(50), nullable=True))
    
    # Create indexes for performance
    op.create_index('idx_is_is_subtotal', 'income_statement_data', ['is_subtotal'])
    op.create_index('idx_is_is_total', 'income_statement_data', ['is_total'])
    op.create_index('idx_is_line_category', 'income_statement_data', ['line_category'])
    op.create_index('idx_is_page_number', 'income_statement_data', ['page_number'])
    op.create_index('idx_is_line_number', 'income_statement_data', ['line_number'])


def downgrade() -> None:
    """Remove Income Statement Template v1.0 fields"""
    
    # Drop indexes
    op.drop_index('idx_is_line_number', 'income_statement_data')
    op.drop_index('idx_is_page_number', 'income_statement_data')
    op.drop_index('idx_is_line_category', 'income_statement_data')
    op.drop_index('idx_is_is_total', 'income_statement_data')
    op.drop_index('idx_is_is_subtotal', 'income_statement_data')
    
    # Drop columns (in reverse order)
    op.drop_column('income_statement_data', 'extraction_method')
    op.drop_column('income_statement_data', 'match_confidence')
    op.drop_column('income_statement_data', 'is_below_the_line')
    op.drop_column('income_statement_data', 'account_level')
    op.drop_column('income_statement_data', 'line_number')
    op.drop_column('income_statement_data', 'line_subcategory')
    op.drop_column('income_statement_data', 'line_category')
    op.drop_column('income_statement_data', 'is_total')
    op.drop_column('income_statement_data', 'is_subtotal')
    op.drop_column('income_statement_data', 'page_number')
    op.drop_column('income_statement_data', 'report_generation_date')
    op.drop_column('income_statement_data', 'accounting_basis')
    op.drop_column('income_statement_data', 'period_end_date')
    op.drop_column('income_statement_data', 'period_start_date')
    op.drop_column('income_statement_data', 'period_type')

