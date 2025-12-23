"""Add Alert Workflow Enhancements

Revision ID: 20251224_0004
Revises: 20251224_0003
Create Date: 2025-12-24 16:00:00.000000

Creates tables for:
- alert_suppressions: Alert suppression rules with expiry
- alert_snoozes: Alert snoozing until next period
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0004'
down_revision = '20251224_0003'
branch_labels = None
depends_on = None


def upgrade():
    """Create alert workflow enhancement tables"""
    
    # 1. Create alert_suppressions table
    op.create_table(
        'alert_suppressions',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Alert Reference
        sa.Column('alert_id', sa.Integer(), nullable=True, comment='Specific alert ID (nullable for rule-based)'),
        sa.Column('alert_type', sa.String(50), nullable=True, comment='Alert type pattern'),
        
        # Suppression Rule
        sa.Column('rule_id', sa.Integer(), nullable=True, comment='Suppression rule ID'),
        sa.Column('suppression_reason', sa.Text(), nullable=False),
        
        # Expiry
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='When suppression expires'),
        sa.Column('expires_after_periods', sa.Integer(), nullable=True, comment='Expire after N periods'),
        
        # Scope
        sa.Column('property_id', sa.Integer(), nullable=True, comment='NULL = global suppression'),
        sa.Column('account_code', sa.String(50), nullable=True, comment='Account-specific suppression'),
        
        # Metadata
        sa.Column('suppressed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['suppressed_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_alert_suppressions_alert', 'alert_id'),
        sa.Index('idx_alert_suppressions_expires', 'expires_at'),
    )
    
    # 2. Create alert_snoozes table
    op.create_table(
        'alert_snoozes',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Alert Reference
        sa.Column('alert_id', sa.Integer(), nullable=False, comment='Alert ID to snooze'),
        
        # Snooze Details
        sa.Column('until_period_id', sa.Integer(), nullable=True, comment='Snooze until this period'),
        sa.Column('until_date', sa.DateTime(timezone=True), nullable=True, comment='Snooze until this date'),
        sa.Column('snooze_reason', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('snoozed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['until_period_id'], ['financial_periods.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['snoozed_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_alert_snoozes_alert', 'alert_id'),
        sa.Index('idx_alert_snoozes_until', 'until_period_id', 'until_date'),
    )
    
    # 3. Create alert_suppression_rules table
    op.create_table(
        'alert_suppression_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Rule Definition
        sa.Column('rule_name', sa.String(255), nullable=False),
        sa.Column('alert_type_pattern', sa.String(100), nullable=True, comment='Pattern to match alert types'),
        sa.Column('condition_json', postgresql.JSONB(), nullable=True, comment='Conditions for suppression'),
        
        # Expiry
        sa.Column('expires_after_periods', sa.Integer(), nullable=True, comment='Auto-expire after N periods'),
        sa.Column('expires_after_days', sa.Integer(), nullable=True, comment='Auto-expire after N days'),
        
        # Scope
        sa.Column('property_id', sa.Integer(), nullable=True, comment='NULL = global rule'),
        sa.Column('account_code', sa.String(50), nullable=True, comment='Account-specific rule'),
        
        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_alert_suppression_rules_active', 'is_active', 'property_id'),
    )


def downgrade():
    """Drop alert workflow enhancement tables"""
    op.drop_table('alert_suppression_rules')
    op.drop_table('alert_snoozes')
    op.drop_table('alert_suppressions')

