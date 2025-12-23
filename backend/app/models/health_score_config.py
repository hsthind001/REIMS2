"""
Health Score Configuration Model

Stores persona-specific health score configurations with weights,
trend components, and blocked close rules.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class HealthScoreConfig(Base):
    """Persona-specific health score configuration"""
    
    __tablename__ = "health_score_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Persona
    persona = Column(String(50), nullable=False, unique=True, comment='controller, analyst, investor, auditor')
    
    # Weights (JSONB)
    weights_json = Column(JSONB(), nullable=False, comment='{approval_score: 0.4, confidence_score: 0.3, discrepancy_penalty: 0.3}')
    
    # Trend and Volatility
    trend_weight = Column(Numeric(5, 2), nullable=True, comment='Weight for trend component (0-1)')
    volatility_weight = Column(Numeric(5, 2), nullable=True, comment='Weight for volatility component (0-1)')
    
    # Blocked Close Rules (JSONB)
    blocked_close_rules = Column(JSONB(), nullable=True, comment='[{condition: "covenant_violation", max_score: 60}]')
    
    # Metadata
    description = Column(Text(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('persona', name='uq_health_score_persona'),
    )
    
    def __repr__(self):
        return f"<HealthScoreConfig {self.persona}>"

