"""Add conversation fields to nlq_queries

Revision ID: add_conversation_fields
Revises: 
Create Date: 2024-11-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_conversation_fields'
down_revision = '20251126_1500_semantic_cache'  # Points to semantic cache migration
branch_labels = None
depends_on = None


def upgrade():
    """Add conversation_id and turn_number columns to nlq_queries table"""
    # Check if nlq_queries table exists before modifying it
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'nlq_queries'
    """))
    
    if result.scalar() == 0:
        print("⚠️  nlq_queries table does not exist. Skipping conversation fields migration.")
        return
    
    # Check if columns already exist
    columns_result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'nlq_queries' 
        AND column_name IN ('conversation_id', 'turn_number')
    """))
    existing_columns = {row[0] for row in columns_result}
    
    # Add conversation_id column if it doesn't exist
    if 'conversation_id' not in existing_columns:
        op.add_column('nlq_queries', sa.Column('conversation_id', sa.String(64), nullable=True))
    
    # Add turn_number column if it doesn't exist
    if 'turn_number' not in existing_columns:
        op.add_column('nlq_queries', sa.Column('turn_number', sa.Integer(), nullable=True))
    
    # Create index on conversation_id for faster lookups (if it doesn't exist)
    try:
        op.create_index(
            'idx_nlq_queries_conversation_id',
            'nlq_queries',
            ['conversation_id']
        )
    except Exception:
        # Index might already exist
        pass
    
    # Create composite index for conversation queries (if it doesn't exist)
    try:
        op.create_index(
            'idx_nlq_queries_conv_turn',
            'nlq_queries',
            ['conversation_id', 'turn_number']
        )
    except Exception:
        # Index might already exist
        pass


def downgrade():
    """Remove conversation fields from nlq_queries table"""
    # Drop indexes
    op.drop_index('idx_nlq_queries_conv_turn', table_name='nlq_queries')
    op.drop_index('idx_nlq_queries_conversation_id', table_name='nlq_queries')
    
    # Drop columns
    op.drop_column('nlq_queries', 'turn_number')
    op.drop_column('nlq_queries', 'conversation_id')

