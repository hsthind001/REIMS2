"""seed calculated rules for forensic reconciliation"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260109_0002'
down_revision = '20260108_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Data migration to ensure calculated rules are present.
    """
    bind = op.get_bind()
    # Import inside to avoid Alembic import issues
    try:
        from app.db.seeds.forensic_calculated_rules_seed import seed_calculated_rules
        from app.db.database import SessionLocal
    except Exception:
        # If imports fail, skip rather than blocking schema migrations
        return

    session = SessionLocal(bind=bind)
    try:
        seed_calculated_rules()
    finally:
        session.close()


def downgrade() -> None:
    """
    No-op: we do not delete seeded rules on downgrade.
    """
    pass
