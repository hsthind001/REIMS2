"""Create lenders table

Revision ID: 20251219_1900
Revises: 20251219_rm_cf_constraint
Create Date: 2025-12-19 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251219_1900'
down_revision = '20251219_rm_cf_constraint'
branch_labels = None
depends_on = None


def upgrade():
    """Create lenders table"""
    # Check if table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'lenders' not in existing_tables:
        op.create_table(
            'lenders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lender_name', sa.String(255), nullable=False),
            sa.Column('lender_code', sa.String(50), nullable=True),
            sa.Column('contact_name', sa.String(255), nullable=True),
            sa.Column('contact_email', sa.String(255), nullable=True),
            sa.Column('contact_phone', sa.String(50), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('website', sa.String(255), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indices
        op.create_index('idx_lenders_name', 'lenders', ['lender_name'])
        op.create_index('idx_lenders_code', 'lenders', ['lender_code'])


def downgrade():
    """Drop lenders table"""
    op.drop_index('idx_lenders_code', 'lenders')
    op.drop_index('idx_lenders_name', 'lenders')
    op.drop_table('lenders')
