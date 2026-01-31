"""Add Postgres RLS policies for defense-in-depth (E2-S3)

Revision ID: 20260130_0002
Revises: 20260130_0001
Create Date: 2026-01-30

Enables Row Level Security on tenant tables. Application must set
app.current_organization_id per request for policies to take effect.
When not set, policies allow all (backward compat during rollout).
"""
from alembic import op


revision = "20260130_0002"
down_revision = "20260130_0001"
branch_labels = None
depends_on = None


def _rls_policy_sql(table: str, org_col: str = "organization_id") -> str:
    """Policy: allow when app.current_organization_id not set (rollout) or matches org."""
    return f"""
        USING (
            current_setting('app.current_organization_id', true) IS NULL
            OR {org_col} = NULLIF(current_setting('app.current_organization_id', true), '')::int
        )
    """


def upgrade() -> None:
    # Properties - has organization_id
    op.execute("ALTER TABLE properties ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY properties_org_isolation ON properties
        FOR ALL
        {_rls_policy_sql('properties')}
    """)

    # Financial periods - has organization_id
    op.execute("ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY financial_periods_org_isolation ON financial_periods
        FOR ALL
        {_rls_policy_sql('financial_periods')}
    """)

    # Document uploads - has organization_id
    op.execute("ALTER TABLE document_uploads ENABLE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY document_uploads_org_isolation ON document_uploads
        FOR ALL
        {_rls_policy_sql('document_uploads')}
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS document_uploads_org_isolation ON document_uploads")
    op.execute("ALTER TABLE document_uploads DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS financial_periods_org_isolation ON financial_periods")
    op.execute("ALTER TABLE financial_periods DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS properties_org_isolation ON properties")
    op.execute("ALTER TABLE properties DISABLE ROW LEVEL SECURITY")
