"""Add anomaly resolution fields

Revision ID: 20260107_0001
Revises: 20260102_0001
Create Date: 2026-01-07 00:00:00.000000

Adds:
- resolution_type enum + column
- root_cause column
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260107_0001'
down_revision = '20260102_0001'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('anomaly_detections')]

    resolution_type_enum = postgresql.ENUM(
        'data_entry', 'extraction', 'mapping', 'business_change', 'covenant_issue',
        name='resolutiontype',
        create_type=True
    )
    resolution_type_enum.create(op.get_bind(), checkfirst=True)

    if 'resolution_type' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('resolution_type', resolution_type_enum, nullable=True))

    if 'root_cause' not in existing_columns:
        op.add_column('anomaly_detections', sa.Column('root_cause', sa.Text(), nullable=True))


def downgrade():
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('anomaly_detections')]

    if 'root_cause' in existing_columns:
        op.drop_column('anomaly_detections', 'root_cause')

    if 'resolution_type' in existing_columns:
        op.drop_column('anomaly_detections', 'resolution_type')

    op.execute("DROP TYPE IF EXISTS resolutiontype")
