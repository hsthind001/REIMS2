"""Create self-learning forensic reconciliation tables

Revision ID: 20251224_0007
Revises: 20251224_0006
Create Date: 2025-12-24 21:00:00.000000

Creates tables for the self-learning forensic reconciliation system:
- discovered_account_codes: Stores discovered account codes with metadata
- account_code_patterns: Stores learned patterns and rules
- account_semantic_mappings: Maps account names to codes using NLP
- learned_match_patterns: Stores successful match patterns for learning
- account_code_synonyms: Learned synonyms and variations
- match_confidence_models: ML model metadata and parameters
- reconciliation_learning_log: Tracks learning activities and improvements
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0007'
down_revision = '20251224_0006'
branch_labels = None
depends_on = None


def upgrade():
    """Create self-learning forensic reconciliation tables"""
    
    # Create discovered_account_codes table
    op.create_table(
        'discovered_account_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('source_table', sa.String(length=100), nullable=False),
        sa.Column('source_record_id', sa.Integer(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('property_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('period_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('account_type', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('code_pattern', sa.String(length=100), nullable=True),
        sa.Column('code_range_start', sa.String(length=50), nullable=True),
        sa.Column('code_range_end', sa.String(length=50), nullable=True),
        sa.Column('confidence_score', sa.DECIMAL(5, 2), nullable=False, server_default='100.0'),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_discovered_account_codes_account_code', 'discovered_account_codes', ['account_code'])
    op.create_index('ix_discovered_account_codes_account_name', 'discovered_account_codes', ['account_name'])
    op.create_index('ix_discovered_account_codes_document_type', 'discovered_account_codes', ['document_type'])
    op.create_index('idx_discovered_code_doc_type', 'discovered_account_codes', ['account_code', 'document_type'])
    op.create_index('idx_discovered_code_pattern', 'discovered_account_codes', ['code_pattern'])
    
    # Create account_code_patterns table
    op.create_table(
        'account_code_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern_name', sa.String(length=255), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('pattern_definition', sa.Text(), nullable=False),
        sa.Column('pattern_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('match_rule', sa.Text(), nullable=True),
        sa.Column('match_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='100.0'),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('account_type', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('examples', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discovered_from', sa.String(length=100), nullable=True),
        sa.Column('learning_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='50.0'),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_account_code_patterns_pattern_name', 'account_code_patterns', ['pattern_name'])
    op.create_index('ix_account_code_patterns_pattern_type', 'account_code_patterns', ['pattern_type'])
    op.create_index('ix_account_code_patterns_document_type', 'account_code_patterns', ['document_type'])
    op.create_index('ix_account_code_patterns_is_active', 'account_code_patterns', ['is_active'])
    op.create_index('idx_pattern_type_doc', 'account_code_patterns', ['pattern_type', 'document_type'])
    op.create_index('idx_pattern_active_priority', 'account_code_patterns', ['is_active', 'priority'])
    
    # Create account_semantic_mappings table
    op.create_table(
        'account_semantic_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('semantic_embedding', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('semantic_similarity', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('fuzzy_match_score', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('combined_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('alternative_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('alternative_names', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_account_semantic_mappings_account_name', 'account_semantic_mappings', ['account_name'])
    op.create_index('ix_account_semantic_mappings_account_code', 'account_semantic_mappings', ['account_code'])
    op.create_index('ix_account_semantic_mappings_document_type', 'account_semantic_mappings', ['document_type'])
    op.create_index('ix_account_semantic_mappings_is_active', 'account_semantic_mappings', ['is_active'])
    op.create_index('idx_semantic_name_code', 'account_semantic_mappings', ['account_name', 'account_code'])
    op.create_index('idx_semantic_doc_type', 'account_semantic_mappings', ['document_type', 'is_active'])
    op.create_index('idx_semantic_confidence', 'account_semantic_mappings', ['combined_confidence', 'is_active'])
    
    # Create learned_match_patterns table
    op.create_table(
        'learned_match_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern_name', sa.String(length=255), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=False),
        sa.Column('source_document_type', sa.String(length=50), nullable=False),
        sa.Column('source_account_code', sa.String(length=50), nullable=True),
        sa.Column('source_account_name', sa.String(length=255), nullable=True),
        sa.Column('target_document_type', sa.String(length=50), nullable=False),
        sa.Column('target_account_code', sa.String(length=50), nullable=True),
        sa.Column('target_account_name', sa.String(length=255), nullable=True),
        sa.Column('relationship_type', sa.String(length=50), nullable=True),
        sa.Column('relationship_formula', sa.Text(), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('average_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('min_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('max_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('pattern_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('conditions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('first_discovered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_learned_match_patterns_pattern_name', 'learned_match_patterns', ['pattern_name'])
    op.create_index('ix_learned_match_patterns_pattern_type', 'learned_match_patterns', ['pattern_type'])
    op.create_index('ix_learned_match_patterns_source_document_type', 'learned_match_patterns', ['source_document_type'])
    op.create_index('ix_learned_match_patterns_target_document_type', 'learned_match_patterns', ['target_document_type'])
    op.create_index('ix_learned_match_patterns_is_active', 'learned_match_patterns', ['is_active'])
    op.create_index('idx_learned_pattern_source_target', 'learned_match_patterns', ['source_document_type', 'target_document_type'])
    op.create_index('idx_learned_pattern_active_priority', 'learned_match_patterns', ['is_active', 'priority'])
    op.create_index('idx_learned_pattern_success_rate', 'learned_match_patterns', ['success_rate', 'is_active'])
    
    # Create account_code_synonyms table
    op.create_table(
        'account_code_synonyms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('canonical_account_code', sa.String(length=50), nullable=False),
        sa.Column('canonical_account_name', sa.String(length=255), nullable=False),
        sa.Column('synonym_code', sa.String(length=50), nullable=True),
        sa.Column('synonym_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('code_similarity', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('name_similarity', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('combined_confidence', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('discovered_from', sa.String(length=100), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_account_code_synonyms_canonical_account_code', 'account_code_synonyms', ['canonical_account_code'])
    op.create_index('ix_account_code_synonyms_synonym_name', 'account_code_synonyms', ['synonym_name'])
    op.create_index('ix_account_code_synonyms_document_type', 'account_code_synonyms', ['document_type'])
    op.create_index('ix_account_code_synonyms_is_active', 'account_code_synonyms', ['is_active'])
    op.create_index('idx_synonym_canonical', 'account_code_synonyms', ['canonical_account_code', 'is_active'])
    op.create_index('idx_synonym_name', 'account_code_synonyms', ['synonym_name', 'document_type'])
    op.create_index('idx_synonym_confidence', 'account_code_synonyms', ['combined_confidence', 'is_active'])
    
    # Create match_confidence_models table
    op.create_table(
        'match_confidence_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('model_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('feature_list', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_path', sa.String(length=500), nullable=True),
        sa.Column('model_binary', sa.Text(), nullable=True),
        sa.Column('training_accuracy', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('validation_accuracy', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('test_accuracy', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('training_samples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prediction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_prediction_time', sa.DECIMAL(10, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_production', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('trained_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('trained_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_match_confidence_models_model_name', 'match_confidence_models', ['model_name'])
    op.create_index('ix_match_confidence_models_model_type', 'match_confidence_models', ['model_type'])
    op.create_index('ix_match_confidence_models_is_active', 'match_confidence_models', ['is_active'])
    op.create_index('idx_model_type_active', 'match_confidence_models', ['model_type', 'is_active'])
    op.create_index('idx_model_production', 'match_confidence_models', ['is_production', 'is_active'])
    
    # Create reconciliation_learning_log table
    op.create_table(
        'reconciliation_learning_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('activity_name', sa.String(length=255), nullable=False),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('period_id', sa.Integer(), sa.ForeignKey('financial_periods.id', ondelete='SET NULL'), nullable=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('forensic_reconciliation_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result_type', sa.String(length=50), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('result_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('matches_improved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rules_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('patterns_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('confidence_improvement', sa.DECIMAL(5, 2), nullable=False, server_default='0.0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(length=50), nullable=True),
        sa.Column('is_successful', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reconciliation_learning_log_activity_type', 'reconciliation_learning_log', ['activity_type'])
    op.create_index('ix_reconciliation_learning_log_property_id', 'reconciliation_learning_log', ['property_id'])
    op.create_index('ix_reconciliation_learning_log_period_id', 'reconciliation_learning_log', ['period_id'])
    op.create_index('ix_reconciliation_learning_log_session_id', 'reconciliation_learning_log', ['session_id'])
    op.create_index('ix_reconciliation_learning_log_is_successful', 'reconciliation_learning_log', ['is_successful'])
    op.create_index('idx_learning_log_type_date', 'reconciliation_learning_log', ['activity_type', 'created_at'])
    op.create_index('idx_learning_log_property_period', 'reconciliation_learning_log', ['property_id', 'period_id'])
    op.create_index('idx_learning_log_success', 'reconciliation_learning_log', ['is_successful', 'created_at'])


def downgrade():
    """Drop self-learning forensic reconciliation tables"""
    op.drop_table('reconciliation_learning_log')
    op.drop_table('match_confidence_models')
    op.drop_table('account_code_synonyms')
    op.drop_table('learned_match_patterns')
    op.drop_table('account_semantic_mappings')
    op.drop_table('account_code_patterns')
    op.drop_table('discovered_account_codes')

