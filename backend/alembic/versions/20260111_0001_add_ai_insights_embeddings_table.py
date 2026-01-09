"""Add AI insights embeddings table with pgvector fallback

Revision ID: 20260111_0001_ai_embeddings
Revises: 20260110_0003_backfill_metrics_and_tenant_risk
Create Date: 2026-01-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
    VECTOR_TYPE = Vector
except Exception:  # pragma: no cover - optional dependency
    VECTOR_TYPE = None

# revision identifiers, used by Alembic.
revision = '20260111_0001_ai_embeddings'
down_revision = '20260110_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    vector_available = False
    if VECTOR_TYPE:
        try:
            # Enable extension if permitted
            bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
            chk = bind.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
            vector_available = bool(chk)
        except Exception:
            vector_available = False

    columns = [
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('property_code', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('dim', sa.Integer(), nullable=False),
        sa.Column('embedding_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    ]

    if vector_available:
        columns.insert(
            4,
            sa.Column('embedding_vector', VECTOR_TYPE(384), nullable=True)
        )

    op.create_table('ai_insights_embeddings', *columns)
    op.create_index('ix_ai_insights_embeddings_property_code', 'ai_insights_embeddings', ['property_code'])

    if vector_available:
        try:
            bind.execute(sa.text("""
                CREATE INDEX IF NOT EXISTS ix_ai_embeddings_vector
                ON ai_insights_embeddings
                USING ivfflat (embedding_vector vector_cosine_ops)
                WITH (lists = 100);
            """))
        except Exception:
            # Optional index creation; skip on environments without ivfflat support
            pass


def downgrade() -> None:
    op.drop_index('ix_ai_insights_embeddings_property_code', table_name='ai_insights_embeddings')
    op.drop_table('ai_insights_embeddings')
