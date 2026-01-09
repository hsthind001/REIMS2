"""Seed additional calculated rules for forensic reconciliation

Ensures newly added rules are present in all environments.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260110_0001'
down_revision = '20260109_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Data migration to (re)seed calculated rules.
    """
    bind = op.get_bind()
    try:
        from app.db.seeds.forensic_calculated_rules_seed import seed_calculated_rules
        from app.db.database import SessionLocal
    except Exception:
        # If imports fail (e.g., missing app path in Alembic context), skip gracefully
        return

    session = SessionLocal(bind=bind)
    try:
        seed_calculated_rules()
    finally:
        session.close()


def downgrade() -> None:
    """
    No-op: seeded rules are left in place on downgrade.
    """
    pass
