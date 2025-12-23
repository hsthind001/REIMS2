"""Create review_approval_chains table

Revision ID: 20251222_0004
Revises: 20251222_0003
Create Date: 2025-12-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251222_0004'
down_revision = '20251222_0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'review_approval_chains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'first_approved', 'second_approved', 'rejected', 'cancelled', name='approvalstatus'), nullable=False, server_default='pending'),
        sa.Column('first_approver_id', sa.Integer(), nullable=True),
        sa.Column('first_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_approval_notes', sa.Text(), nullable=True),
        sa.Column('second_approver_id', sa.Integer(), nullable=True),
        sa.Column('second_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('second_approval_notes', sa.Text(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['first_approver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['second_approver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_approval_chains_id'), 'review_approval_chains', ['id'], unique=False)
    op.create_index(op.f('ix_review_approval_chains_table_name'), 'review_approval_chains', ['table_name'], unique=False)
    op.create_index(op.f('ix_review_approval_chains_record_id'), 'review_approval_chains', ['record_id'], unique=False)
    op.create_index(op.f('ix_review_approval_chains_status'), 'review_approval_chains', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_review_approval_chains_status'), table_name='review_approval_chains')
    op.drop_index(op.f('ix_review_approval_chains_record_id'), table_name='review_approval_chains')
    op.drop_index(op.f('ix_review_approval_chains_table_name'), table_name='review_approval_chains')
    op.drop_index(op.f('ix_review_approval_chains_id'), table_name='review_approval_chains')
    op.drop_table('review_approval_chains')
    op.execute("DROP TYPE IF EXISTS approvalstatus")
