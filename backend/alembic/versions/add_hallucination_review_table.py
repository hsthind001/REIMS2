"""Add hallucination review table

Revision ID: add_hallucination_review
Revises: 
Create Date: 2024-11-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'add_hallucination_review'
down_revision = 'add_conversation_fields'  # Points to conversation fields migration
branch_labels = None
depends_on = None


def upgrade():
    """Create hallucination_reviews table"""
    # Check if nlq_queries table exists before creating foreign key
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'nlq_queries'
    """))
    
    nlq_queries_exists = result.scalar() > 0
    
    # Create table with conditional foreign key
    table_args = [
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nlq_query_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('original_answer', sa.Text(), nullable=False),
        sa.Column('original_confidence', sa.Numeric(5, 4), nullable=True),
        sa.Column('adjusted_confidence', sa.Numeric(5, 4), nullable=True),
        sa.Column('total_claims', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified_claims', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unverified_claims', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('flagged_claims', JSONB(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        # NOTE: Foreign key to users table removed - users table doesn't exist yet
        # sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], )
    ]
    
    # Only add foreign key to nlq_queries if the table exists
    if nlq_queries_exists:
        table_args.append(sa.ForeignKeyConstraint(['nlq_query_id'], ['nlq_queries.id']))
    else:
        print("⚠️  nlq_queries table does not exist. Creating hallucination_reviews without foreign key constraint.")
    
    op.create_table('hallucination_reviews', *table_args)
    
    # Create indexes
    op.create_index('idx_hallucination_reviews_nlq_query_id', 'hallucination_reviews', ['nlq_query_id'])
    op.create_index('idx_hallucination_reviews_user_id', 'hallucination_reviews', ['user_id'])
    op.create_index('idx_hallucination_reviews_status', 'hallucination_reviews', ['status'])
    op.create_index('idx_hallucination_reviews_property_id', 'hallucination_reviews', ['property_id'])
    op.create_index('idx_hallucination_reviews_created_at', 'hallucination_reviews', ['created_at'])


def downgrade():
    """Drop hallucination_reviews table"""
    op.drop_index('idx_hallucination_reviews_created_at', table_name='hallucination_reviews')
    op.drop_index('idx_hallucination_reviews_property_id', table_name='hallucination_reviews')
    op.drop_index('idx_hallucination_reviews_status', table_name='hallucination_reviews')
    op.drop_index('idx_hallucination_reviews_user_id', table_name='hallucination_reviews')
    op.drop_index('idx_hallucination_reviews_nlq_query_id', table_name='hallucination_reviews')
    op.drop_table('hallucination_reviews')

