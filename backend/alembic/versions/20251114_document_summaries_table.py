"""Document summaries table

Revision ID: 20251114_003
Revises: 20251114_002
Create Date: 2025-11-14 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20251114_003'
down_revision = '20251114_002'
branch_labels = None
depends_on = None


def upgrade():
    # Create DocumentType enum (check if it exists first)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM pg_type 
        WHERE typname = 'documenttype'
    """))
    
    if result.scalar() == 0:
        # Use raw SQL to create enum
        try:
            connection.execute(sa.text("""
                CREATE TYPE documenttype AS ENUM ('LEASE', 'OFFERING_MEMORANDUM', 'FINANCIAL_STATEMENT',
                    'APPRAISAL', 'INSPECTION_REPORT', 'LEGAL_DOCUMENT', 'OTHER')
            """))
        except Exception as e:
            # Enum might have been created by another migration
            if 'already exists' not in str(e).lower():
                raise
    
    # Get the enum type for use in table creation
    document_type = postgresql.ENUM(
        'LEASE', 'OFFERING_MEMORANDUM', 'FINANCIAL_STATEMENT',
        'APPRAISAL', 'INSPECTION_REPORT', 'LEGAL_DOCUMENT', 'OTHER',
        name='documenttype',
        create_type=False  # Don't try to create it, it already exists or was created above
    )

    # Create SummaryStatus enum (check if it exists first)
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM pg_type 
        WHERE typname = 'summarystatus'
    """))
    
    if result.scalar() == 0:
        # Use raw SQL to create enum
        try:
            connection.execute(sa.text("""
                CREATE TYPE summarystatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
            """))
        except Exception as e:
            # Enum might have been created by another migration
            if 'already exists' not in str(e).lower():
                raise
    
    # Get the enum type for use in table creation
    summary_status = postgresql.ENUM(
        'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
        name='summarystatus',
        create_type=False  # Don't try to create it, it already exists or was created above
    )

    # Create document_summaries table
    op.create_table(
        'document_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('document_type', document_type, nullable=False),
        sa.Column('document_name', sa.String(length=300), nullable=False),
        sa.Column('document_path', sa.String(length=500), nullable=True),
        sa.Column('summary_type', sa.String(length=50), nullable=False),
        sa.Column('status', summary_status, nullable=False),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('detailed_summary', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extracted_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('lease_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('om_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('has_hallucination_flag', sa.Boolean(), nullable=True),
        sa.Column('hallucination_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llm_provider', sa.String(length=50), nullable=True),
        sa.Column('llm_model', sa.String(length=100), nullable=True),
        sa.Column('processing_time_seconds', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add foreign key to documents table if it exists
    documents_result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'documents'
    """))
    if documents_result.scalar() > 0:
        try:
            op.create_foreign_key(
                'fk_document_summaries_document_id',
                'document_summaries',
                'documents',
                ['document_id'],
                ['id']
            )
        except Exception:
            pass  # Foreign key might already exist

    # Create indexes
    op.create_index(op.f('ix_document_summaries_property_id'), 'document_summaries', ['property_id'], unique=False)
    op.create_index(op.f('ix_document_summaries_document_id'), 'document_summaries', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_summaries_document_type'), 'document_summaries', ['document_type'], unique=False)
    op.create_index(op.f('ix_document_summaries_status'), 'document_summaries', ['status'], unique=False)
    op.create_index(op.f('ix_document_summaries_created_at'), 'document_summaries', ['created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_document_summaries_created_at'), table_name='document_summaries')
    op.drop_index(op.f('ix_document_summaries_status'), table_name='document_summaries')
    op.drop_index(op.f('ix_document_summaries_document_type'), table_name='document_summaries')
    op.drop_index(op.f('ix_document_summaries_document_id'), table_name='document_summaries')
    op.drop_index(op.f('ix_document_summaries_property_id'), table_name='document_summaries')

    # Drop table
    op.drop_table('document_summaries')

    # Drop enums
    sa.Enum(name='summarystatus').drop(op.get_bind())
    sa.Enum(name='documenttype').drop(op.get_bind())
