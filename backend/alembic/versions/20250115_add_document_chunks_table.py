"""add document chunks table for RAG

Revision ID: 20250115_document_chunks
Revises: 20251114_document_summaries
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250115_document_chunks'
down_revision = '20251114_003'  # document_summaries table
branch_labels = None
depends_on = None


def upgrade():
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('extraction_log_id', sa.Integer(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=True),
        sa.Column('embedding', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_dimension', sa.Integer(), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['document_uploads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extraction_log_id'], ['extraction_logs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_extraction_log_id'), 'document_chunks', ['extraction_log_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_property_id'), 'document_chunks', ['property_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_period_id'), 'document_chunks', ['period_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_document_type'), 'document_chunks', ['document_type'], unique=False)
    op.create_index('idx_chunk_document_index', 'document_chunks', ['document_id', 'chunk_index'], unique=False)
    op.create_index('idx_chunk_property_period', 'document_chunks', ['property_id', 'period_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_chunk_property_period', table_name='document_chunks')
    op.drop_index('idx_chunk_document_index', table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_type'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_period_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_property_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_extraction_log_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    
    # Drop table
    op.drop_table('document_chunks')

