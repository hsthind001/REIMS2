"""Add anomaly thresholds table for value setup

Revision ID: 20251125_thresholds
Revises: 20251124_concordance
Create Date: 2025-11-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251125_thresholds'
down_revision = '20251124_concordance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create anomaly_thresholds table
    op.create_table(
        'anomaly_thresholds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_code', sa.String(length=50), nullable=False, unique=True),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('threshold_value', sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on account_code for fast lookups
    op.create_index('ix_anomaly_thresholds_account_code', 'anomaly_thresholds', ['account_code'], unique=True)
    op.create_index('ix_anomaly_thresholds_is_active', 'anomaly_thresholds', ['is_active'])
    
    # Create system_config table for global default threshold
    op.create_table(
        'system_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False, unique=True),
        sa.Column('config_value', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_system_config_key', 'system_config', ['config_key'], unique=True)
    
    # Insert default threshold config
    op.execute("""
        INSERT INTO system_config (config_key, config_value, description)
        VALUES ('anomaly_threshold_default', '1000.00', 'Default absolute value threshold for anomaly detection')
    """)


def downgrade() -> None:
    op.drop_index('ix_system_config_key', table_name='system_config')
    op.drop_table('system_config')
    op.drop_index('ix_anomaly_thresholds_is_active', table_name='anomaly_thresholds')
    op.drop_index('ix_anomaly_thresholds_account_code', table_name='anomaly_thresholds')
    op.drop_table('anomaly_thresholds')

