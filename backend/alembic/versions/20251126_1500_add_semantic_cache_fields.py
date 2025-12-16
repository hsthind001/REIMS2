"""add semantic cache fields to nlq_queries

Revision ID: 20251126_1500_semantic_cache
Revises: 20251126_1432_chunk_enhancements
Create Date: 2025-11-26 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251126_1500_semantic_cache'
down_revision = '20251126_1432_chunk_enhancements'
branch_labels = None
depends_on = None


def upgrade():
    # Add question_embedding column (FLOAT array for 1536 dimensions)
    op.add_column(
        'nlq_queries',
        sa.Column('question_embedding', postgresql.ARRAY(sa.Float()), nullable=True)
    )
    
    # Add question_hash column (VARCHAR(64) for SHA256 hash)
    op.add_column(
        'nlq_queries',
        sa.Column('question_hash', sa.String(length=64), nullable=True)
    )
    
    # Add from_cache column (BOOLEAN)
    op.add_column(
        'nlq_queries',
        sa.Column('from_cache', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    
    # Add cache_similarity column (DECIMAL(5,2) for similarity score)
    op.add_column(
        'nlq_queries',
        sa.Column('cache_similarity', sa.Numeric(5, 2), nullable=True)
    )
    
    # Create indexes for performance
    op.create_index(
        'idx_nlq_queries_question_hash',
        'nlq_queries',
        ['question_hash'],
        unique=False
    )
    
    # Index on created_at already exists (idx_nlq_date), but ensure it's there
    # Check if index exists, if not create it
    try:
        op.create_index(
            'idx_nlq_queries_created_at',
            'nlq_queries',
            ['created_at'],
            unique=False
        )
    except:
        # Index might already exist, that's okay
        pass


def downgrade():
    # Drop indexes
    try:
        op.drop_index('idx_nlq_queries_created_at', table_name='nlq_queries')
    except:
        pass
    
    op.drop_index('idx_nlq_queries_question_hash', table_name='nlq_queries')
    
    # Drop columns
    op.drop_column('nlq_queries', 'cache_similarity')
    op.drop_column('nlq_queries', 'from_cache')
    op.drop_column('nlq_queries', 'question_hash')
    op.drop_column('nlq_queries', 'question_embedding')

