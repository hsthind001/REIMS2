"""Add Chart of Accounts Mapping and Calculated Rules Tables

Revision ID: 20251224_0002
Revises: 20251224_0001
Create Date: 2025-12-24 12:00:00.000000

Creates tables for:
- account_synonyms: Account name synonyms for fuzzy matching
- account_mappings: Historical mapping decisions (learned from approvals)
- calculated_rules: Versioned calculated matching rules
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0002'
down_revision = '20251224_0001'
branch_labels = None
depends_on = None


def upgrade():
    """Create chart of accounts and calculated rules tables"""
    
    # 1. Create account_synonyms table
    op.create_table(
        'account_synonyms',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Account Information
        sa.Column('account_code', sa.String(50), nullable=True, comment='Optional account code'),
        sa.Column('synonym', sa.String(255), nullable=False, comment='Synonym text (e.g., "AR", "Receivables")'),
        sa.Column('canonical_name', sa.String(255), nullable=False, comment='Canonical account name'),
        
        # Confidence and Source
        sa.Column('confidence', sa.Numeric(5, 2), nullable=False, server_default='100.00', comment='Confidence score 0-100'),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual', comment='manual, learned'),
        
        # Usage Tracking
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', comment='Number of times used'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_account_synonyms_code', 'account_code'),
        sa.Index('idx_account_synonyms_synonym', 'synonym'),
        sa.Index('idx_account_synonyms_canonical', 'canonical_name'),
        sa.UniqueConstraint('account_code', 'synonym', name='uq_account_synonym'),
    )
    
    # 2. Create account_mappings table
    op.create_table(
        'account_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Mapping Definition
        sa.Column('source_account_code', sa.String(50), nullable=False),
        sa.Column('source_account_name', sa.String(255), nullable=True),
        sa.Column('target_account_code', sa.String(50), nullable=False),
        sa.Column('target_account_name', sa.String(255), nullable=True),
        
        # Mapping Type
        sa.Column('mapping_type', sa.String(50), nullable=False, comment='exact, fuzzy, calculated, inferred'),
        sa.Column('source_document_type', sa.String(50), nullable=True),
        sa.Column('target_document_type', sa.String(50), nullable=True),
        
        # Learning from Approvals
        sa.Column('approved_count', sa.Integer(), nullable=False, server_default='0', comment='Number of times this mapping was approved'),
        sa.Column('rejected_count', sa.Integer(), nullable=False, server_default='0', comment='Number of times this mapping was rejected'),
        sa.Column('last_approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_approved_by', sa.Integer(), nullable=True),
        
        # Confidence
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=False, server_default='50.00', comment='Calculated confidence based on approvals'),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['last_approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_account_mappings_source', 'source_account_code', 'source_document_type'),
        sa.Index('idx_account_mappings_target', 'target_account_code', 'target_document_type'),
        sa.Index('idx_account_mappings_confidence', 'confidence_score', 'is_active'),
        sa.UniqueConstraint('source_account_code', 'target_account_code', 'source_document_type', 'target_document_type', name='uq_account_mapping'),
    )
    
    # 3. Create calculated_rules table
    op.create_table(
        'calculated_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Rule Identification
        sa.Column('rule_id', sa.String(100), nullable=False, comment='Unique rule identifier (e.g., "BS_IS_NET_INCOME")'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1', comment='Rule version number'),
        
        # Scope
        sa.Column('property_scope', postgresql.JSONB(), nullable=True, comment='Property IDs or "all"'),
        sa.Column('doc_scope', postgresql.JSONB(), nullable=False, comment='Document types this rule applies to'),
        
        # Rule Definition
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('formula', sa.Text(), nullable=False, comment='Formula text (e.g., "BS.current_period_earnings = IS.net_income")'),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Tolerances
        sa.Column('tolerance_absolute', sa.Numeric(15, 2), nullable=True),
        sa.Column('tolerance_percent', sa.Numeric(10, 4), nullable=True),
        
        # Materiality and Severity
        sa.Column('materiality_threshold', sa.Numeric(15, 2), nullable=True),
        sa.Column('severity', sa.String(50), nullable=False, server_default='medium', comment='critical, high, medium, low'),
        
        # Failure Explanation Template
        sa.Column('failure_explanation_template', sa.Text(), nullable=True, comment='Template with placeholders for failure explanation'),
        
        # Effective Dates
        sa.Column('effective_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('expires_at', sa.Date(), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_calculated_rules_rule_id', 'rule_id', 'version'),
        sa.Index('idx_calculated_rules_active', 'is_active', 'effective_date', 'expires_at'),
        sa.UniqueConstraint('rule_id', 'version', name='uq_calculated_rule_version'),
    )


def downgrade():
    """Drop chart of accounts and calculated rules tables"""
    op.drop_table('calculated_rules')
    op.drop_table('account_mappings')
    op.drop_table('account_synonyms')

