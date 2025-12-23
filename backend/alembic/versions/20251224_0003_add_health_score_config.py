"""Add Health Score Configuration Table

Revision ID: 20251224_0003
Revises: 20251224_0002
Create Date: 2025-12-24 14:00:00.000000

Creates table for:
- health_score_configs: Persona-specific health score configurations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251224_0003'
down_revision = '20251224_0002'
branch_labels = None
depends_on = None


def upgrade():
    """Create health score configuration table"""
    
    op.create_table(
        'health_score_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Persona
        sa.Column('persona', sa.String(50), nullable=False, unique=True, comment='controller, analyst, investor, auditor'),
        
        # Weights (JSONB)
        sa.Column('weights_json', postgresql.JSONB(), nullable=False, comment='{approval_score: 0.4, confidence_score: 0.3, discrepancy_penalty: 0.3}'),
        
        # Trend and Volatility
        sa.Column('trend_weight', sa.Numeric(5, 2), nullable=True, comment='Weight for trend component (0-1)'),
        sa.Column('volatility_weight', sa.Numeric(5, 2), nullable=True, comment='Weight for volatility component (0-1)'),
        
        # Blocked Close Rules (JSONB)
        sa.Column('blocked_close_rules', postgresql.JSONB(), nullable=True, comment='[{condition: "covenant_violation", max_score: 60}]'),
        
        # Metadata
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('persona', name='uq_health_score_persona'),
    )


def downgrade():
    """Drop health score configuration table"""
    op.drop_table('health_score_configs')

