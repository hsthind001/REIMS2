"""Create self-learning system tables

Revision ID: 20251224_0006
Revises: 20251224_0005
Create Date: 2025-12-24 20:00:00.000000

Creates tables for the self-learning system:
- issue_knowledge_base: Stores learned issues, patterns, and fixes
- issue_captures: Captures individual issue occurrences with context
- prevention_rules: Rules for preventing known issues
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0006'
down_revision = '20251224_0005'
branch_labels = None
depends_on = None


def upgrade():
    """Create self-learning system tables"""
    
    # Create issue_knowledge_base table
    op.create_table(
        'issue_knowledge_base',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_type', sa.String(length=100), nullable=False),
        sa.Column('issue_category', sa.String(length=50), nullable=False),
        sa.Column('error_pattern', sa.Text(), nullable=True),
        sa.Column('error_message_pattern', sa.Text(), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('prevention_strategy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fix_applied', sa.Text(), nullable=True),
        sa.Column('fix_code_location', sa.String(length=500), nullable=True),
        sa.Column('fix_implementation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.DECIMAL(5, 4), nullable=False, server_default='0.5'),
        sa.Column('auto_fix_success_rate', sa.DECIMAL(5, 4), nullable=True),
        sa.Column('prevention_success_rate', sa.DECIMAL(5, 4), nullable=True),
        sa.Column('mcp_task_id', sa.String(length=100), nullable=True),
        sa.Column('mcp_task_status', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_issue_knowledge_base_id'), 'issue_knowledge_base', ['id'], unique=False)
    op.create_index(op.f('ix_issue_knowledge_base_issue_type'), 'issue_knowledge_base', ['issue_type'], unique=False)
    op.create_index(op.f('ix_issue_knowledge_base_issue_category'), 'issue_knowledge_base', ['issue_category'], unique=False)
    op.create_index(op.f('ix_issue_knowledge_base_status'), 'issue_knowledge_base', ['status'], unique=False)
    op.create_index(op.f('ix_issue_knowledge_base_mcp_task_id'), 'issue_knowledge_base', ['mcp_task_id'], unique=False)
    
    # Create issue_captures table
    op.create_table(
        'issue_captures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_kb_id', sa.Integer(), nullable=True),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('property_id', sa.Integer(), nullable=True),
        sa.Column('period_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='error'),
        sa.Column('issue_category', sa.String(length=50), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('auto_fix_attempted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_fix_successful', sa.Boolean(), nullable=True),
        sa.Column('auto_fix_method', sa.String(length=100), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['issue_kb_id'], ['issue_knowledge_base.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['upload_id'], ['document_uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['period_id'], ['financial_periods.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_issue_captures_id'), 'issue_captures', ['id'], unique=False)
    op.create_index(op.f('ix_issue_captures_issue_kb_id'), 'issue_captures', ['issue_kb_id'], unique=False)
    op.create_index(op.f('ix_issue_captures_upload_id'), 'issue_captures', ['upload_id'], unique=False)
    op.create_index(op.f('ix_issue_captures_document_type'), 'issue_captures', ['document_type'], unique=False)
    op.create_index(op.f('ix_issue_captures_property_id'), 'issue_captures', ['property_id'], unique=False)
    op.create_index(op.f('ix_issue_captures_severity'), 'issue_captures', ['severity'], unique=False)
    op.create_index(op.f('ix_issue_captures_issue_category'), 'issue_captures', ['issue_category'], unique=False)
    op.create_index(op.f('ix_issue_captures_resolved'), 'issue_captures', ['resolved'], unique=False)
    op.create_index(op.f('ix_issue_captures_captured_at'), 'issue_captures', ['captured_at'], unique=False)
    
    # Create prevention_rules table
    op.create_table(
        'prevention_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_kb_id', sa.Integer(), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('rule_condition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('rule_action', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['issue_kb_id'], ['issue_knowledge_base.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prevention_rules_id'), 'prevention_rules', ['id'], unique=False)
    op.create_index(op.f('ix_prevention_rules_issue_kb_id'), 'prevention_rules', ['issue_kb_id'], unique=False)
    op.create_index(op.f('ix_prevention_rules_rule_type'), 'prevention_rules', ['rule_type'], unique=False)
    op.create_index(op.f('ix_prevention_rules_is_active'), 'prevention_rules', ['is_active'], unique=False)
    op.create_index(op.f('ix_prevention_rules_priority'), 'prevention_rules', ['priority'], unique=False)


def downgrade():
    """Drop self-learning system tables"""
    op.drop_index(op.f('ix_prevention_rules_priority'), table_name='prevention_rules')
    op.drop_index(op.f('ix_prevention_rules_is_active'), table_name='prevention_rules')
    op.drop_index(op.f('ix_prevention_rules_rule_type'), table_name='prevention_rules')
    op.drop_index(op.f('ix_prevention_rules_issue_kb_id'), table_name='prevention_rules')
    op.drop_index(op.f('ix_prevention_rules_id'), table_name='prevention_rules')
    op.drop_table('prevention_rules')
    
    op.drop_index(op.f('ix_issue_captures_captured_at'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_resolved'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_issue_category'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_severity'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_property_id'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_document_type'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_upload_id'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_issue_kb_id'), table_name='issue_captures')
    op.drop_index(op.f('ix_issue_captures_id'), table_name='issue_captures')
    op.drop_table('issue_captures')
    
    op.drop_index(op.f('ix_issue_knowledge_base_mcp_task_id'), table_name='issue_knowledge_base')
    op.drop_index(op.f('ix_issue_knowledge_base_status'), table_name='issue_knowledge_base')
    op.drop_index(op.f('ix_issue_knowledge_base_issue_category'), table_name='issue_knowledge_base')
    op.drop_index(op.f('ix_issue_knowledge_base_issue_type'), table_name='issue_knowledge_base')
    op.drop_index(op.f('ix_issue_knowledge_base_id'), table_name='issue_knowledge_base')
    op.drop_table('issue_knowledge_base')

