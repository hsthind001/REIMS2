"""
AI Insights Embedding model.

Stores lightweight centroid embeddings for Market Intelligence AI insights.
Uses pgvector when available; falls back to JSONB storage otherwise.
"""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
    VECTOR_TYPE = Vector
except Exception:  # pragma: no cover - optional dependency
    Vector = None  # type: ignore
    VECTOR_TYPE = None

from app.db.database import Base


class AIInsightsEmbedding(Base):
    __tablename__ = "ai_insights_embeddings"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    property_code = sa.Column(sa.String(50), nullable=False, index=True)
    model = sa.Column(sa.String(100), nullable=False)
    dim = sa.Column(sa.Integer, nullable=False)
    # Persist JSON always; add vector column when supported
    embedding_json = sa.Column(JSONB, nullable=False)
    if VECTOR_TYPE:
        embedding_vector = sa.Column(VECTOR_TYPE(384), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<AIInsightsEmbedding property_code={self.property_code} model={self.model} dim={self.dim}>"
