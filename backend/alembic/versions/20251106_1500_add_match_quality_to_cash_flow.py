"""add match quality fields to cash flow data

Revision ID: 20251106_1500
Revises: 20251106_merge_heads
Create Date: 2025-11-06 15:00:00

Adds match confidence and strategy tracking for cash flow data:
- match_confidence: Confidence score from account matching (0-100)
- match_strategy: Strategy used (exact_code, fuzzy_code, exact_name, fuzzy_name, unmatched)

This enables separate tracking of extraction quality vs matching quality,
providing better insight into manual review requirements.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import DECIMAL


# revision identifiers, used by Alembic.
revision = '20251106_1500'
down_revision = 'merge_heads_2025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add match quality tracking fields to cash_flow_data"""
    
    # Add match_confidence column
    op.add_column('cash_flow_data', 
        sa.Column('match_confidence', DECIMAL(5, 2), nullable=True))
    
    # Add match_strategy column
    op.add_column('cash_flow_data', 
        sa.Column('match_strategy', sa.String(50), nullable=True))
    
    # Backfill existing records: set match_confidence = extraction_confidence
    # This ensures backward compatibility with existing data
    op.execute("""
        UPDATE cash_flow_data 
        SET match_confidence = extraction_confidence,
            match_strategy = CASE 
                WHEN account_id IS NOT NULL THEN 'legacy_match'
                ELSE 'unmatched'
            END
        WHERE match_confidence IS NULL
    """)
    
    # Create index for match_strategy for query performance
    op.create_index('idx_cf_match_strategy', 'cash_flow_data', ['match_strategy'])


def downgrade() -> None:
    """Remove match quality tracking fields from cash_flow_data"""
    
    # Drop index
    op.drop_index('idx_cf_match_strategy', 'cash_flow_data')
    
    # Drop columns
    op.drop_column('cash_flow_data', 'match_strategy')
    op.drop_column('cash_flow_data', 'match_confidence')

