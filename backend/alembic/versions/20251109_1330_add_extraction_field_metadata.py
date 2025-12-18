"""add extraction field metadata table

Revision ID: 20251109_1330
Revises: 20251108_1306
Create Date: 2025-11-09 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251109_1330'
down_revision = 'cf002std0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types first
    op.execute("""
        CREATE TYPE extraction_engine_type AS ENUM (
            'pymupdf', 
            'pdfplumber', 
            'camelot', 
            'tesseract', 
            'easyocr', 
            'layoutlm', 
            'ensemble'
        )
    """)
    
    op.execute("""
        CREATE TYPE resolution_method_type AS ENUM (
            'consensus', 
            'weighted_vote', 
            'ai_override', 
            'human_review', 
            'single_engine'
        )
    """)
    
    op.execute("""
        CREATE TYPE review_priority_type AS ENUM (
            'critical', 
            'high', 
            'medium', 
            'low'
        )
    """)
    
    # Create extraction_field_metadata table
    op.create_table(
        'extraction_field_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        
        # Confidence and provenance
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('extraction_engine', sa.String(50), nullable=False),
        
        # Conflict resolution
        sa.Column('conflicting_values', postgresql.JSONB, nullable=True),
        sa.Column('resolution_method', sa.String(50), nullable=True),
        
        # Quality flags
        sa.Column('needs_review', sa.Boolean(), server_default='false'),
        sa.Column('review_priority', sa.String(20), nullable=True),
        sa.Column('flagged_reason', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(
            ['document_id'], 
            ['document_uploads.id'], 
            name='fk_metadata_document',
            ondelete='CASCADE'
        ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # TODO: Add foreign key in a later migration after users table is created
        # sa.ForeignKeyConstraint(
        #     ['reviewed_by'], 
        #     ['users.id'], 
        #     name='fk_metadata_reviewer',
        #     ondelete='SET NULL'
        # )
    )
    
    # Create performance indexes
    op.create_index(
        'ix_extraction_metadata_document_id',
        'extraction_field_metadata',
        ['document_id']
    )
    
    op.create_index(
        'ix_extraction_metadata_field_name',
        'extraction_field_metadata',
        ['field_name']
    )
    
    op.create_index(
        'ix_extraction_metadata_confidence',
        'extraction_field_metadata',
        ['confidence_score']
    )
    
    op.create_index(
        'ix_extraction_metadata_needs_review',
        'extraction_field_metadata',
        ['needs_review'],
        postgresql_where=sa.text('needs_review = true')
    )
    
    # Composite index for common queries
    op.create_index(
        'ix_extraction_metadata_doc_table_record',
        'extraction_field_metadata',
        ['document_id', 'table_name', 'record_id']
    )
    
    # Add helpful comment
    op.execute("""
        COMMENT ON TABLE extraction_field_metadata IS 
        'Stores field-level confidence scores and metadata for all extracted data. 
        Enables quality tracking, conflict detection, and targeted review workflows.'
    """)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_extraction_metadata_doc_table_record', table_name='extraction_field_metadata')
    op.drop_index('ix_extraction_metadata_needs_review', table_name='extraction_field_metadata')
    op.drop_index('ix_extraction_metadata_confidence', table_name='extraction_field_metadata')
    op.drop_index('ix_extraction_metadata_field_name', table_name='extraction_field_metadata')
    op.drop_index('ix_extraction_metadata_document_id', table_name='extraction_field_metadata')
    
    # Drop table
    op.drop_table('extraction_field_metadata')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS review_priority_type')
    op.execute('DROP TYPE IF EXISTS resolution_method_type')
    op.execute('DROP TYPE IF EXISTS extraction_engine_type')

