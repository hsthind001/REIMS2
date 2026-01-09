"""Seed comprehensive validation rules from SQL scripts"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260110_0002'
down_revision = '20260110_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        from app.db.seeds.full_validation_rules_seed import seed_full_validation_rules
        from app.db.database import SessionLocal
    except Exception:
        return

    session = SessionLocal(bind=bind)
    try:
        seed_full_validation_rules()
    finally:
        session.close()


def downgrade() -> None:
    # Leave seeded rules in place
    pass
