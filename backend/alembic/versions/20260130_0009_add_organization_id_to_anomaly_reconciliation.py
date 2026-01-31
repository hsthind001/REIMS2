"""Add organization_id to anomaly_detections, reconciliation_sessions, reconciliation_differences, reconciliation_resolutions (E2-S3)

Revision ID: 20260130_0009
Revises: 20260130_0008
Create Date: 2026-01-30

Part of tenant isolation - backfill from document_uploads (anomaly) or properties (reconciliation).
"""
from alembic import op
import sqlalchemy as sa


revision = "20260130_0009"
down_revision = "20260130_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # anomaly_detections: via document_id -> document_uploads.organization_id
    op.add_column("anomaly_detections", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_anomaly_detections_organization",
        "anomaly_detections",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        UPDATE anomaly_detections ad
        SET organization_id = du.organization_id
        FROM document_uploads du
        WHERE ad.document_id = du.id AND du.organization_id IS NOT NULL
    """)
    op.create_index("ix_anomaly_detections_organization_id", "anomaly_detections", ["organization_id"], unique=False)

    # reconciliation_sessions: via property_id -> properties.organization_id
    op.add_column("reconciliation_sessions", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reconciliation_sessions_organization",
        "reconciliation_sessions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        UPDATE reconciliation_sessions rs
        SET organization_id = p.organization_id
        FROM properties p
        WHERE rs.property_id = p.id AND p.organization_id IS NOT NULL
    """)
    op.create_index("ix_reconciliation_sessions_organization_id", "reconciliation_sessions", ["organization_id"], unique=False)

    # reconciliation_differences: via session_id -> reconciliation_sessions.organization_id
    op.add_column("reconciliation_differences", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reconciliation_differences_organization",
        "reconciliation_differences",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        UPDATE reconciliation_differences rd
        SET organization_id = rs.organization_id
        FROM reconciliation_sessions rs
        WHERE rd.session_id = rs.id AND rs.organization_id IS NOT NULL
    """)
    op.create_index("ix_reconciliation_differences_organization_id", "reconciliation_differences", ["organization_id"], unique=False)

    # reconciliation_resolutions: via difference_id -> reconciliation_differences.organization_id
    op.add_column("reconciliation_resolutions", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reconciliation_resolutions_organization",
        "reconciliation_resolutions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("""
        UPDATE reconciliation_resolutions rr
        SET organization_id = rd.organization_id
        FROM reconciliation_differences rd
        WHERE rr.difference_id = rd.id AND rd.organization_id IS NOT NULL
    """)
    op.create_index("ix_reconciliation_resolutions_organization_id", "reconciliation_resolutions", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reconciliation_resolutions_organization_id", table_name="reconciliation_resolutions")
    op.drop_constraint("fk_reconciliation_resolutions_organization", "reconciliation_resolutions", type_="foreignkey")
    op.drop_column("reconciliation_resolutions", "organization_id")

    op.drop_index("ix_reconciliation_differences_organization_id", table_name="reconciliation_differences")
    op.drop_constraint("fk_reconciliation_differences_organization", "reconciliation_differences", type_="foreignkey")
    op.drop_column("reconciliation_differences", "organization_id")

    op.drop_index("ix_reconciliation_sessions_organization_id", table_name="reconciliation_sessions")
    op.drop_constraint("fk_reconciliation_sessions_organization", "reconciliation_sessions", type_="foreignkey")
    op.drop_column("reconciliation_sessions", "organization_id")

    op.drop_index("ix_anomaly_detections_organization_id", table_name="anomaly_detections")
    op.drop_constraint("fk_anomaly_detections_organization", "anomaly_detections", type_="foreignkey")
    op.drop_column("anomaly_detections", "organization_id")
