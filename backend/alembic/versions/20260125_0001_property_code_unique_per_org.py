"""Enforce property_code uniqueness per organization

Revision ID: 20260125_0001_property_code_org_unique
Revises: 20260117_0001_saas_models
Create Date: 2026-01-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260125_0001_property_code_org_unique"
down_revision = "20260117_0001_saas_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Ensure every property is associated with an organization before adding the constraint.
    null_orgs = bind.execute(
        sa.text("SELECT COUNT(*) FROM properties WHERE organization_id IS NULL")
    ).scalar()
    if null_orgs:
        raise RuntimeError(
            "Cannot add org-scoped uniqueness: properties with NULL organization_id exist."
        )

    # Drop global unique index on property_code (if present).
    op.execute("DROP INDEX IF EXISTS ix_properties_property_code")

    # Enforce uniqueness per organization.
    op.create_unique_constraint(
        "uq_properties_org_property_code",
        "properties",
        ["organization_id", "property_code"],
    )


def downgrade() -> None:
    # Remove org-scoped uniqueness and restore global uniqueness on property_code.
    op.drop_constraint("uq_properties_org_property_code", "properties", type_="unique")
    op.create_index(
        "ix_properties_property_code",
        "properties",
        ["property_code"],
        unique=True,
    )
