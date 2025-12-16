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
    # Add chunk_type column
    op.add_column(
        'document_chunks',
        sa.Column('chunk_type', sa.String(length=20), nullable=True)
    )
    
    # Add parent_chunk_id column (self-referencing FK)
    op.add_column(
        'document_chunks',
        sa.Column('parent_chunk_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint for parent_chunk_id
    op.create_foreign_key(
        'fk_document_chunks_parent_chunk',
        'document_chunks',
        'document_chunks',
        ['parent_chunk_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for performance
    op.create_index(
        'ix_document_chunks_chunk_type',
        'document_chunks',
        ['chunk_type'],
        unique=False
    )
    
    op.create_index(
        'ix_document_chunks_parent_chunk_id',
        'document_chunks',
        ['parent_chunk_id'],
        unique=False
    )
    
    # Create composite index for common queries
    op.create_index(
        'idx_chunk_type_document',
        'document_chunks',
        ['document_id', 'chunk_type'],
        unique=False
    )


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

