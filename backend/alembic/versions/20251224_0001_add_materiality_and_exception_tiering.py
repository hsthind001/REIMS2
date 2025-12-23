"""Add Materiality Config and Exception Tiering Tables

Revision ID: 20251224_0001
Revises: 20251223_0001
Create Date: 2025-12-24 10:00:00.000000

Creates tables for:
- materiality_configs: Materiality thresholds per property/statement/account
- account_risk_classes: Risk classification for account codes
- auto_resolution_rules: Rules for auto-resolving tier 0 exceptions
- Extends forensic_matches and forensic_discrepancies with exception_tier
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0001'
down_revision = '20251223_0001'
branch_labels = None
depends_on = None


def upgrade():
    """Create materiality and exception tiering tables"""
    
    # 1. Create account_risk_classes table
    op.create_table(
        'account_risk_classes',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Account Pattern
        sa.Column('account_code_pattern', sa.String(50), nullable=False, comment='e.g., "1*" for assets, "2*" for liabilities'),
        sa.Column('account_name_pattern', sa.String(255), nullable=True, comment='Optional name pattern for matching'),
        
        # Risk Classification
        sa.Column('risk_class', sa.String(50), nullable=False, comment='critical, high, medium, low'),
        sa.Column('default_tolerance_absolute', sa.Numeric(15, 2), nullable=True, comment='Default absolute tolerance'),
        sa.Column('default_tolerance_percent', sa.Numeric(10, 4), nullable=True, comment='Default percentage tolerance'),
        sa.Column('reconciliation_frequency', sa.String(50), nullable=False, server_default='monthly', comment='daily, weekly, monthly, quarterly'),
        
        # Property Type Override (JSONB)
        sa.Column('property_type_override', postgresql.JSONB(), nullable=True, comment='Property-specific overrides'),
        
        # Metadata
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_account_risk_classes_pattern', 'account_code_pattern'),
        sa.Index('idx_account_risk_classes_risk', 'risk_class'),
    )
    
    # 2. Create materiality_configs table
    op.create_table(
        'materiality_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Scope
        sa.Column('property_id', sa.Integer(), nullable=True, comment='NULL = global default'),
        sa.Column('statement_type', sa.String(50), nullable=True, comment='balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement, NULL = all'),
        sa.Column('account_code', sa.String(50), nullable=True, comment='NULL = statement-level default'),
        
        # Thresholds
        sa.Column('absolute_threshold', sa.Numeric(15, 2), nullable=False, comment='Absolute materiality threshold'),
        sa.Column('relative_threshold_percent', sa.Numeric(10, 4), nullable=True, comment='Relative threshold as % of revenue/assets'),
        sa.Column('risk_class', sa.String(50), nullable=False, comment='critical, high, medium, low'),
        
        # Tolerance Configuration
        sa.Column('tolerance_type', sa.String(50), nullable=False, server_default='standard', comment='strict, standard, loose'),
        sa.Column('tolerance_absolute', sa.Numeric(15, 2), nullable=True),
        sa.Column('tolerance_percent', sa.Numeric(10, 4), nullable=True),
        
        # Effective Dates
        sa.Column('effective_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('expires_at', sa.Date(), nullable=True),
        
        # Metadata
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_materiality_configs_property', 'property_id'),
        sa.Index('idx_materiality_configs_scope', 'property_id', 'statement_type', 'account_code'),
        sa.Index('idx_materiality_configs_effective', 'effective_date', 'expires_at'),
    )
    
    # 3. Create auto_resolution_rules table
    op.create_table(
        'auto_resolution_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Rule Definition
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False, comment='rounding, timing, synonym, mapping'),
        
        # Condition (JSONB for flexible pattern matching)
        sa.Column('condition_json', postgresql.JSONB(), nullable=False, comment='Pattern matching conditions'),
        
        # Action
        sa.Column('action_type', sa.String(50), nullable=False, comment='auto_close, suggest_fix, route_to_queue'),
        sa.Column('suggested_mapping', postgresql.JSONB(), nullable=True, comment='Suggested account mapping or adjustment'),
        
        # Confidence Threshold
        sa.Column('confidence_threshold', sa.Numeric(5, 2), nullable=False, comment='Minimum confidence to apply rule (0-100)'),
        
        # Scope
        sa.Column('property_id', sa.Integer(), nullable=True, comment='NULL = global rule'),
        sa.Column('statement_type', sa.String(50), nullable=True, comment='NULL = all statement types'),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='Higher priority rules evaluated first'),
        
        # Metadata
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_auto_resolution_rules_pattern', 'pattern_type', 'is_active'),
        sa.Index('idx_auto_resolution_rules_priority', 'priority', 'is_active'),
    )
    
    # 4. Add exception_tier to forensic_matches
    op.add_column(
        'forensic_matches',
        sa.Column(
            'exception_tier',
            sa.String(50),
            nullable=True,
            comment='tier_0_auto_close, tier_1_auto_suggest, tier_2_route, tier_3_escalate'
        )
    )
    op.create_index('idx_forensic_matches_tier', 'forensic_matches', ['exception_tier', 'status'])
    
    # 5. Add exception_tier and auto_resolution_rule_id to forensic_discrepancies
    op.add_column(
        'forensic_discrepancies',
        sa.Column(
            'exception_tier',
            sa.String(50),
            nullable=True,
            comment='tier_0_auto_close, tier_1_auto_suggest, tier_2_route, tier_3_escalate'
        )
    )
    op.add_column(
        'forensic_discrepancies',
        sa.Column(
            'auto_resolution_rule_id',
            sa.Integer(),
            nullable=True,
            comment='Rule that auto-resolved this discrepancy'
        )
    )
    op.create_foreign_key(
        'fk_discrepancy_auto_rule',
        'forensic_discrepancies',
        'auto_resolution_rules',
        ['auto_resolution_rule_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_forensic_discrepancies_tier', 'forensic_discrepancies', ['exception_tier', 'severity'])


def downgrade():
    """Drop materiality and exception tiering tables"""
    
    # Remove indexes and columns from existing tables
    op.drop_index('idx_forensic_discrepancies_tier', table_name='forensic_discrepancies')
    op.drop_constraint('fk_discrepancy_auto_rule', 'forensic_discrepancies', type_='foreignkey')
    op.drop_column('forensic_discrepancies', 'auto_resolution_rule_id')
    op.drop_column('forensic_discrepancies', 'exception_tier')
    
    op.drop_index('idx_forensic_matches_tier', table_name='forensic_matches')
    op.drop_column('forensic_matches', 'exception_tier')
    
    # Drop new tables
    op.drop_table('auto_resolution_rules')
    op.drop_table('materiality_configs')
    op.drop_table('account_risk_classes')

