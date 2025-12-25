"""Add extraction learning and adaptive threshold models

Revision ID: 20251225_0008
Revises: 20251224_0007
Create Date: 2025-12-25 00:55:00.000000

Creates tables for intelligent self-learning extraction system:
- extraction_learning_patterns: Learn from user reviews and enable auto-approval
- adaptive_confidence_thresholds: Account-specific confidence thresholds
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251225_0008'
down_revision = '20251224_0007'
branch_labels = None
depends_on = None


def upgrade():
    """Create extraction learning tables"""

    # Create extraction_learning_patterns table
    op.create_table(
        'extraction_learning_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=True),

        # Pattern statistics
        sa.Column('total_occurrences', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('approved_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_approved_count', sa.Integer(), nullable=False, server_default='0'),

        # Confidence metrics
        sa.Column('min_confidence_seen', sa.Float(), nullable=True),
        sa.Column('max_confidence_seen', sa.Float(), nullable=True),
        sa.Column('avg_confidence', sa.Float(), nullable=True),

        # Learning thresholds
        sa.Column('learned_confidence_threshold', sa.Float(), nullable=False, server_default='85.0'),
        sa.Column('auto_approve_threshold', sa.Float(), nullable=True),

        # Pattern strength
        sa.Column('pattern_strength', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('reliability_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_trustworthy', sa.Boolean(), nullable=False, server_default='false'),

        # Metadata
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('common_variations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for extraction_learning_patterns
    op.create_index('ix_elp_account_code', 'extraction_learning_patterns', ['account_code'])
    op.create_index('ix_elp_account_name', 'extraction_learning_patterns', ['account_name'])
    op.create_index('ix_elp_document_type', 'extraction_learning_patterns', ['document_type'])
    op.create_index('ix_elp_property_id', 'extraction_learning_patterns', ['property_id'])
    op.create_index('ix_elp_is_trustworthy', 'extraction_learning_patterns', ['is_trustworthy'])
    op.create_index('ix_elp_compound', 'extraction_learning_patterns', ['account_code', 'document_type', 'property_id'])

    # Create adaptive_confidence_thresholds table
    op.create_table(
        'adaptive_confidence_thresholds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('account_category', sa.String(length=100), nullable=True),

        # Current threshold
        sa.Column('current_threshold', sa.Float(), nullable=False, server_default='85.0'),
        sa.Column('original_threshold', sa.Float(), nullable=False, server_default='85.0'),

        # Learning statistics
        sa.Column('total_extractions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_extractions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_extractions', sa.Integer(), nullable=False, server_default='0'),

        # Accuracy tracking
        sa.Column('historical_accuracy', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('avg_extraction_confidence', sa.Float(), nullable=True),
        sa.Column('min_successful_confidence', sa.Float(), nullable=True),

        # Complexity assessment
        sa.Column('complexity_score', sa.Float(), nullable=False, server_default='50.0'),
        sa.Column('is_simple_account', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_complex_account', sa.Boolean(), nullable=False, server_default='false'),

        # Adaptive learning
        sa.Column('adjustment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_adjustment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_adjustment_amount', sa.Float(), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_code', name='uq_act_account_code')
    )

    # Create indexes for adaptive_confidence_thresholds
    op.create_index('ix_act_account_code', 'adaptive_confidence_thresholds', ['account_code'], unique=True)
    op.create_index('ix_act_account_category', 'adaptive_confidence_thresholds', ['account_category'])
    op.create_index('ix_act_is_simple', 'adaptive_confidence_thresholds', ['is_simple_account'])
    op.create_index('ix_act_is_complex', 'adaptive_confidence_thresholds', ['is_complex_account'])


def downgrade():
    """Drop extraction learning tables"""

    # Drop adaptive_confidence_thresholds
    op.drop_index('ix_act_is_complex', table_name='adaptive_confidence_thresholds')
    op.drop_index('ix_act_is_simple', table_name='adaptive_confidence_thresholds')
    op.drop_index('ix_act_account_category', table_name='adaptive_confidence_thresholds')
    op.drop_index('ix_act_account_code', table_name='adaptive_confidence_thresholds')
    op.drop_table('adaptive_confidence_thresholds')

    # Drop extraction_learning_patterns
    op.drop_index('ix_elp_compound', table_name='extraction_learning_patterns')
    op.drop_index('ix_elp_is_trustworthy', table_name='extraction_learning_patterns')
    op.drop_index('ix_elp_property_id', table_name='extraction_learning_patterns')
    op.drop_index('ix_elp_document_type', table_name='extraction_learning_patterns')
    op.drop_index('ix_elp_account_name', table_name='extraction_learning_patterns')
    op.drop_index('ix_elp_account_code', table_name='extraction_learning_patterns')
    op.drop_table('extraction_learning_patterns')
