"""Extend Anomaly Detection Schema

Revision ID: 20251222_0000
Revises: 20251221_0000
Create Date: 2025-12-22 00:00:00.000000

Extends anomaly_detections table with new fields for world-class anomaly detection:
- anomaly_score (0-100): Unified risk score
- impact_amount: Absolute $ variance/exposure
- direction (enum: up/down): Change direction
- root_cause_candidates (JSONB): Top suspected drivers
- baseline_type (enum: mean, seasonal, forecast, peer-group): Baseline method used
- correlation_id (UUID): Group related anomalies into incidents
- suppressed_until (timestamp): Suppression management
- anomaly_category (enum): Taxonomy classification
- pattern_type (enum): Pattern classification
- Context flags: is_one_off, is_recurrent, cross_property_pattern
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20251222_0000'
down_revision = '20251221_0000'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to anomaly_detections table"""
    
    # Check if columns already exist
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('anomaly_detections')]
    
    # Create enum types
    baseline_type_enum = postgresql.ENUM(
        'mean', 'seasonal', 'forecast', 'peer-group',
        name='baselinetype',
        create_type=True
    )
    baseline_type_enum.create(op.get_bind(), checkfirst=True)
    
    direction_enum = postgresql.ENUM(
        'up', 'down',
        name='anomalydirection',
        create_type=True
    )
    direction_enum.create(op.get_bind(), checkfirst=True)
    
    anomaly_category_enum = postgresql.ENUM(
        'data-quality', 'accounting', 'performance', 'covenant', 'extraction',
        name='anomalycategory',
        create_type=True
    )
    anomaly_category_enum.create(op.get_bind(), checkfirst=True)
    
    pattern_type_enum = postgresql.ENUM(
        'point', 'trend', 'seasonality', 'structure',
        name='patterntype',
        create_type=True
    )
    pattern_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add new columns (only if they don't exist)
    if 'anomaly_score' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('anomaly_score', sa.Numeric(5, 2), nullable=True))
    
    if 'impact_amount' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('impact_amount', sa.Numeric(15, 2), nullable=True))
    
    if 'direction' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('direction', direction_enum, nullable=True))
    
    if 'root_cause_candidates' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('root_cause_candidates', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    if 'baseline_type' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('baseline_type', baseline_type_enum, nullable=True))
    
    if 'correlation_id' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('correlation_id', UUID(as_uuid=True), nullable=True))
    
    if 'suppressed_until' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('suppressed_until', sa.DateTime(timezone=True), nullable=True))
    
    # suppression_reason already exists from previous migration, skip if exists
    if 'suppression_reason' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('suppression_reason', sa.Text(), nullable=True))
    
    if 'anomaly_category' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('anomaly_category', anomaly_category_enum, nullable=True))
    
    if 'pattern_type' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('pattern_type', pattern_type_enum, nullable=True))
    
    if 'is_one_off' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('is_one_off', sa.Boolean(), nullable=True, default=False))
    
    if 'is_recurrent' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('is_recurrent', sa.Boolean(), nullable=True, default=False))
    
    if 'cross_property_pattern' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('cross_property_pattern', sa.Boolean(), nullable=True, default=False))
    
    # Create indexes for performance optimization
    try:
        op.create_index('ix_anomaly_score', 'anomaly_detections', ['anomaly_score'])
    except Exception:
        pass  # Index might already exist
    
    try:
        op.create_index('ix_anomaly_correlation_id', 'anomaly_detections', ['correlation_id'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_anomaly_category', 'anomaly_detections', ['anomaly_category'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_anomaly_baseline_type', 'anomaly_detections', ['baseline_type'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_anomaly_pattern_type', 'anomaly_detections', ['pattern_type'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_anomaly_suppressed_until', 'anomaly_detections', ['suppressed_until'])
    except Exception:
        pass
    
    # Composite index for common queries
    try:
        op.create_index('ix_anomaly_category_severity', 'anomaly_detections', ['anomaly_category', 'severity'])
    except Exception:
        pass


def downgrade():
    """Remove new fields from anomaly_detections table"""
    
    # Drop indexes
    try:
        op.drop_index('ix_anomaly_category_severity', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_suppressed_until', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_pattern_type', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_baseline_type', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_category', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_correlation_id', table_name='anomaly_detections')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_anomaly_score', table_name='anomaly_detections')
    except Exception:
        pass
    
    # Drop columns
    op.drop_column('anomaly_detections', 'cross_property_pattern')
    op.drop_column('anomaly_detections', 'is_recurrent')
    op.drop_column('anomaly_detections', 'is_one_off')
    op.drop_column('anomaly_detections', 'pattern_type')
    op.drop_column('anomaly_detections', 'anomaly_category')
    # Note: suppression_reason might have been added in previous migration, handle carefully
    op.drop_column('anomaly_detections', 'suppressed_until')
    op.drop_column('anomaly_detections', 'correlation_id')
    op.drop_column('anomaly_detections', 'baseline_type')
    op.drop_column('anomaly_detections', 'root_cause_candidates')
    op.drop_column('anomaly_detections', 'direction')
    op.drop_column('anomaly_detections', 'impact_amount')
    op.drop_column('anomaly_detections', 'anomaly_score')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS patterntype')
    op.execute('DROP TYPE IF EXISTS anomalycategory')
    op.execute('DROP TYPE IF EXISTS anomalydirection')
    op.execute('DROP TYPE IF EXISTS baselinetype')

