"""
Natural Language Query Model - Query log and cache
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base


class NLQQuery(Base):
    """
    Natural Language Queries - Query log and results

    Stores all NLQ queries with answers, data, and citations
    """
    __tablename__ = "nlq_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False, comment="User's natural language question")
    intent = Column(JSONB, nullable=True, comment="Detected intent and entities")
    answer = Column(Text, nullable=True, comment="Generated answer")
    data_retrieved = Column(JSONB, nullable=True, comment="Data retrieved from database")
    citations = Column(JSONB, nullable=True, comment="Citations/sources for answer")
    confidence_score = Column(Numeric(5, 4), nullable=True, comment="Confidence in answer (0-1)")
    sql_query = Column(Text, nullable=True, comment="SQL query executed (for transparency)")
    execution_time_ms = Column(Integer, nullable=True, comment="Query execution time in milliseconds")
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<NLQQuery(id={self.id}, user_id={self.user_id}, question='{self.question[:50]}...')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question': self.question,
            'intent': self.intent,
            'answer': self.answer,
            'data_retrieved': self.data_retrieved,
            'citations': self.citations,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'sql_query': self.sql_query,
            'execution_time_ms': self.execution_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @property
    def was_successful(self):
        """Check if query was successful"""
        return self.answer is not None and self.confidence_score and self.confidence_score > 0.7

    def get_similar_queries(self, db, limit=5):
        """
        Find similar past queries (for caching/suggestions)

        Uses simple keyword matching - could be enhanced with embeddings
        """
        keywords = self.question.lower().split()
        # This is simplified - real implementation would use vector similarity
        return []
