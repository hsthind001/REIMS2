"""Add extraction_task_id to document_uploads

Revision ID: 20251219_extraction_task_id
Revises: 20251126_1500
Create Date: 2025-12-19 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251219_extraction_task_id'
down_revision = '20251126_1500'  # Update to latest revision
branch_labels = None
depends_on = None


def upgrade():
    # Add extraction_task_id column to track Celery task IDs
    op.add_column('document_uploads', 
        sa.Column('extraction_task_id', sa.String(255), nullable=True))
    
    # Create index for faster lookups
    op.create_index('ix_document_uploads_task_id', 'document_uploads', ['extraction_task_id'])


def downgrade():
    op.drop_index('ix_document_uploads_task_id', 'document_uploads')
    op.drop_column('document_uploads', 'extraction_task_id')

