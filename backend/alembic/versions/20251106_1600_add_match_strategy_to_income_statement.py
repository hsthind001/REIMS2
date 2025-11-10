"""add match strategy to income statement data

Revision ID: 20251106_1600
Revises: 20251106_1500
Create Date: 2025-11-06 16:00:00

Adds match strategy tracking for income statement data:
- match_strategy: Strategy used (exact_code, fuzzy_code, exact_name, fuzzy_name, unmatched)

This enables separate tracking of extraction quality vs matching quality for income statements,
providing better insight into manual review requirements.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251106_1600'
down_revision = '20251106_1500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add match strategy tracking field to income_statement_data"""
    
    # Add match_strategy column
    op.add_column('income_statement_data', 
        sa.Column('match_strategy', sa.String(50), nullable=True))
    
    # Backfill existing records: set match_strategy based on account_id
    # This ensures backward compatibility with existing data
    op.execute("""
        UPDATE income_statement_data 
        SET match_strategy = CASE 
            WHEN account_id IS NOT NULL THEN 'legacy_match'
            ELSE 'unmatched'
        END
        WHERE match_strategy IS NULL
    """)
    
    # Create index for match_strategy for query performance
    op.create_index('idx_is_match_strategy', 'income_statement_data', ['match_strategy'])


def downgrade() -> None:
    """Remove match strategy tracking field from income_statement_data"""
    
    # Drop index
    op.drop_index('idx_is_match_strategy', 'income_statement_data')
    
    # Drop column
    op.drop_column('income_statement_data', 'match_strategy')

