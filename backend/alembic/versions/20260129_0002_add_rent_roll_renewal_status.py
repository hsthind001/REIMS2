"""add renewal_status to rent_roll_data

Revision ID: 20260129_0002
Revises: 20260129_0001
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa

revision = "20260129_0002"
down_revision = "20260129_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rent_roll_data",
        sa.Column("renewal_status", sa.String(50), nullable=True),
    )
    op.create_index(
        "ix_rent_roll_data_renewal_status",
        "rent_roll_data",
        ["renewal_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rent_roll_data_renewal_status", table_name="rent_roll_data")
    op.drop_column("rent_roll_data", "renewal_status")
