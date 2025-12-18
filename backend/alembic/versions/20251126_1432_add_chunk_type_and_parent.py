"""add chunk_type and parent_chunk_id to document_chunks

Revision ID: 20251126_1432_chunk_enhancements
Revises: 20251125_anomaly_thresholds
Create Date: 2025-11-26 14:32:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251126_1432_chunk_enhancements'
down_revision = '20251125_thresholds'  # anomaly_thresholds table migration
branch_labels = None
depends_on = None


def upgrade():
    # Check if document_chunks table exists before modifying it
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'document_chunks'
    """))
    
    if result.scalar() == 0:
        print("⚠️  document_chunks table does not exist. Skipping chunk enhancements migration.")
        return
    
    # Add chunk_type column (if it doesn't already exist)
    try:
        op.add_column(
            'document_chunks',
            sa.Column('chunk_type', sa.String(length=20), nullable=True)
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  chunk_type column already exists, skipping...")
    
    # Add parent_chunk_id column (if it doesn't already exist)
    try:
        op.add_column(
            'document_chunks',
            sa.Column('parent_chunk_id', sa.Integer(), nullable=True)
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  parent_chunk_id column already exists, skipping...")
    
    # Add foreign key constraint for parent_chunk_id (if it doesn't already exist)
    try:
        op.create_foreign_key(
            'fk_document_chunks_parent_chunk',
            'document_chunks',
            'document_chunks',
            ['parent_chunk_id'],
            ['id'],
            ondelete='SET NULL'
        )
    except Exception as e:
        if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
            raise
        print("ℹ️  Foreign key constraint already exists, skipping...")
    
    # Create indexes for performance (if they don't already exist)
    try:
        op.create_index(
            'ix_document_chunks_chunk_type',
            'document_chunks',
            ['chunk_type'],
            unique=False
        )
    except Exception:
        pass  # Index might already exist
    
    try:
        op.create_index(
            'ix_document_chunks_parent_chunk_id',
            'document_chunks',
            ['parent_chunk_id'],
            unique=False
        )
    except Exception:
        pass  # Index might already exist
    
    # Create composite index for common queries (if it doesn't already exist)
    try:
        op.create_index(
            'idx_chunk_type_document',
            'document_chunks',
            ['document_id', 'chunk_type'],
            unique=False
        )
    except Exception:
        pass  # Index might already exist


def downgrade():
    # Drop indexes
    op.drop_index('idx_chunk_type_document', table_name='document_chunks')
    op.drop_index('ix_document_chunks_parent_chunk_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_chunk_type', table_name='document_chunks')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_document_chunks_parent_chunk', 'document_chunks', type_='foreignkey')
    
    # Drop columns
    op.drop_column('document_chunks', 'parent_chunk_id')
    op.drop_column('document_chunks', 'chunk_type')

