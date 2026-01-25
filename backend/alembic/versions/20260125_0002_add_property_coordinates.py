"""Add property latitude/longitude columns

Revision ID: 20260125_0002_prop_coords
Revises: 20260125_0001_prop_org_uq
Create Date: 2026-01-25 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260125_0002_prop_coords"
down_revision = "20260125_0001_prop_org_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True)
    )
    op.add_column(
        "properties",
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("properties", "longitude")
    op.drop_column("properties", "latitude")
