"""Backfill financial metrics and tenant risk analysis"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260110_0003'
down_revision = '20260110_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        from app.db.seeds.backfill_metrics_and_tenant_risk import backfill_all_metrics_and_tenant_risk
        from app.db.database import SessionLocal
    except Exception:
        return

    session = SessionLocal(bind=bind)
    try:
        backfill_all_metrics_and_tenant_risk()
    finally:
        session.close()


def downgrade() -> None:
    # No data rollback
    pass
