"""Extend Alert Schema

Revision ID: 20251222_0001
Revises: 20251222_0000
Create Date: 2025-12-22 00:01:00.000000

Extends committee_alerts table with new fields for world-class alert management:
- business_impact_score: Combined impact metric
- sla_due_at: SLA deadline timestamp
- mtta: Mean time to acknowledge (minutes)
- mttr: Mean time to resolve (minutes)
- incident_group_id: Group related alerts into incidents
- alert_fatigue_score: Fatigue risk indicator
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20251222_0001'
down_revision = '20251222_0000'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to committee_alerts table"""
    
    # Check if columns already exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('committee_alerts')]
    
    # Add new columns (only if they don't exist)
    if 'business_impact_score' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('business_impact_score', sa.Numeric(10, 4), nullable=True))
    
    if 'sla_due_at' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'mtta' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('mtta', sa.Integer(), nullable=True))  # Mean time to acknowledge in minutes
    
    if 'mttr' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('mttr', sa.Integer(), nullable=True))  # Mean time to resolve in minutes
    
    if 'incident_group_id' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('incident_group_id', UUID(as_uuid=True), nullable=True))
    
    if 'alert_fatigue_score' not in existing_columns:
        op.add_column('committee_alerts', sa.Column('alert_fatigue_score', sa.Numeric(5, 2), nullable=True))
    
    # Create indexes for performance optimization
    try:
        op.create_index('ix_committee_alerts_business_impact_score', 'committee_alerts', ['business_impact_score'])
    except Exception:
        pass  # Index might already exist
    
    try:
        op.create_index('ix_committee_alerts_sla_due_at', 'committee_alerts', ['sla_due_at'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_committee_alerts_incident_group_id', 'committee_alerts', ['incident_group_id'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_committee_alerts_fatigue_score', 'committee_alerts', ['alert_fatigue_score'])
    except Exception:
        pass
    
    # Composite index for SLA tracking queries
    try:
        op.create_index('ix_committee_alerts_sla_status', 'committee_alerts', ['sla_due_at', 'status'])
    except Exception:
        pass


def downgrade():
    """Remove new fields from committee_alerts table"""
    
    # Drop indexes
    try:
        op.drop_index('ix_committee_alerts_sla_status', table_name='committee_alerts')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_committee_alerts_fatigue_score', table_name='committee_alerts')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_committee_alerts_incident_group_id', table_name='committee_alerts')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_committee_alerts_sla_due_at', table_name='committee_alerts')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_committee_alerts_business_impact_score', table_name='committee_alerts')
    except Exception:
        pass
    
    # Drop columns
    op.drop_column('committee_alerts', 'alert_fatigue_score')
    op.drop_column('committee_alerts', 'incident_group_id')
    op.drop_column('committee_alerts', 'mttr')
    op.drop_column('committee_alerts', 'mtta')
    op.drop_column('committee_alerts', 'sla_due_at')
    op.drop_column('committee_alerts', 'business_impact_score')

