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
    # Check if nlq_queries table exists before modifying it
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'nlq_queries'
    """))
    
    if result.scalar() == 0:
        print("⚠️  nlq_queries table does not exist. Skipping semantic cache fields migration.")
        return
    
    # Add question_embedding column (FLOAT array for 1536 dimensions)
    try:
        op.add_column(
            'nlq_queries',
            sa.Column('question_embedding', postgresql.ARRAY(sa.Float()), nullable=True)
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  question_embedding column already exists, skipping...")
    
    # Add question_hash column (VARCHAR(64) for SHA256 hash)
    try:
        op.add_column(
            'nlq_queries',
            sa.Column('question_hash', sa.String(length=64), nullable=True)
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  question_hash column already exists, skipping...")
    
    # Add from_cache column (BOOLEAN)
    try:
        op.add_column(
            'nlq_queries',
            sa.Column('from_cache', sa.Boolean(), nullable=False, server_default=sa.text('false'))
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  from_cache column already exists, skipping...")
    
    # Add cache_similarity column (DECIMAL(5,2) for similarity score)
    try:
        op.add_column(
            'nlq_queries',
            sa.Column('cache_similarity', sa.Numeric(5, 2), nullable=True)
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  cache_similarity column already exists, skipping...")
    
    # Create indexes for performance
    try:
        op.create_index(
            'idx_nlq_queries_question_hash',
            'nlq_queries',
            ['question_hash'],
            unique=False
        )
    except Exception:
        pass  # Index might already exist
    
    # Index on created_at already exists (idx_nlq_date), but ensure it's there
    # Check if index exists, if not create it
    try:
        op.create_index(
            'idx_nlq_queries_created_at',
            'nlq_queries',
            ['created_at'],
            unique=False
        )
    except Exception:
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

