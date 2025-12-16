"""Add conversation fields to nlq_queries

Revision ID: add_conversation_fields
Revises: 
Create Date: 2024-11-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_conversation_fields'
down_revision = None  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add conversation_id and turn_number columns to nlq_queries table"""
    # Add conversation_id column
    op.add_column('nlq_queries', sa.Column('conversation_id', sa.String(64), nullable=True))
    
    # Add turn_number column
    op.add_column('nlq_queries', sa.Column('turn_number', sa.Integer(), nullable=True))
    
    # Create index on conversation_id for faster lookups
    op.create_index(
        'idx_nlq_queries_conversation_id',
        'nlq_queries',
        ['conversation_id']
    )
    
    # Create composite index for conversation queries
    op.create_index(
        'idx_nlq_queries_conv_turn',
        'nlq_queries',
        ['conversation_id', 'turn_number']
    )


def downgrade():
    """Remove conversation fields from nlq_queries table"""
    # Drop indexes
    op.drop_index('idx_nlq_queries_conv_turn', table_name='nlq_queries')
    op.drop_index('idx_nlq_queries_conversation_id', table_name='nlq_queries')
    
    # Drop columns
    op.drop_column('nlq_queries', 'turn_number')
    op.drop_column('nlq_queries', 'conversation_id')

