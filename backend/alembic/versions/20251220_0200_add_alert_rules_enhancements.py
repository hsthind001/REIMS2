"""Add Alert Rules Enhancements

Revision ID: 20251220_0200_add_alert_rules_enhancements
Revises: 20251219_1901_add_mortgage_statement_tables
Create Date: 2025-12-20 02:00:00.000000

Enhances alert_rules table with:
- rule_expression (JSONB) - Flexible rule definition
- severity_mapping (JSONB) - Dynamic severity assignment
- cooldown_period (Integer) - Minutes between alerts
- rule_dependencies (JSONB) - Related rules
- property_specific (Boolean) - Property-level vs global
- rule_template_id (Integer) - Link to template
- execution_count (Integer) - Performance tracking
- last_triggered_at (DateTime) - Cooldown tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251220_0200_add_alert_rules_enhancements'
down_revision = '20251219_1901_add_mortgage_statement_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add enhancements to alert_rules table"""
    
    # Add new columns to alert_rules table
    op.add_column('alert_rules', sa.Column('rule_expression', postgresql.JSONB, nullable=True))
    op.add_column('alert_rules', sa.Column('severity_mapping', postgresql.JSONB, nullable=True))
    op.add_column('alert_rules', sa.Column('cooldown_period', sa.Integer(), nullable=True, server_default='60'))
    op.add_column('alert_rules', sa.Column('rule_dependencies', postgresql.JSONB, nullable=True))
    op.add_column('alert_rules', sa.Column('property_specific', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('alert_rules', sa.Column('rule_template_id', sa.Integer(), nullable=True))
    op.add_column('alert_rules', sa.Column('execution_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('alert_rules', sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alert_rules', sa.Column('property_id', sa.Integer(), nullable=True))
    
    # Add indexes for performance
    op.create_index('ix_alert_rules_property_id', 'alert_rules', ['property_id'])
    op.create_index('ix_alert_rules_template_id', 'alert_rules', ['rule_template_id'])
    op.create_index('ix_alert_rules_last_triggered', 'alert_rules', ['last_triggered_at'])
    
    # Add foreign key for property_id if properties table exists
    try:
        op.create_foreign_key(
            'fk_alert_rules_property',
            'alert_rules', 'properties',
            ['property_id'], ['id'],
            ondelete='CASCADE'
        )
    except Exception:
        # Property table might not exist yet, skip foreign key
        pass


def downgrade():
    """Remove enhancements from alert_rules table"""
    
    # Drop foreign key
    try:
        op.drop_constraint('fk_alert_rules_property', 'alert_rules', type_='foreignkey')
    except Exception:
        pass
    
    # Drop indexes
    op.drop_index('ix_alert_rules_last_triggered', table_name='alert_rules')
    op.drop_index('ix_alert_rules_template_id', table_name='alert_rules')
    op.drop_index('ix_alert_rules_property_id', table_name='alert_rules')
    
    # Drop columns
    op.drop_column('alert_rules', 'property_id')
    op.drop_column('alert_rules', 'last_triggered_at')
    op.drop_column('alert_rules', 'execution_count')
    op.drop_column('alert_rules', 'rule_template_id')
    op.drop_column('alert_rules', 'property_specific')
    op.drop_column('alert_rules', 'rule_dependencies')
    op.drop_column('alert_rules', 'cooldown_period')
    op.drop_column('alert_rules', 'severity_mapping')
    op.drop_column('alert_rules', 'rule_expression')

