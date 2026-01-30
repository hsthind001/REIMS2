"""
Covenant compliance history model.

Stores per-period covenant check results (COVENANT-1..6) for dashboard and audit trail.
Populated when reconciliation rules run (AnalyticsRulesMixin covenant rules).
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class CovenantComplianceHistory(Base):
    """
    Per-period covenant compliance record.

    One row per (property, period, covenant_type) per run.
    covenant_type: DSCR, LTV, MIN_LIQUIDITY, OCCUPANCY, TENANT_CONCENTRATION, REPORTING.
    rule_id: COVENANT-1 .. COVENANT-6.
    """

    __tablename__ = "covenant_compliance_history"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    covenant_type = Column(String(50), nullable=False, index=True)
    rule_id = Column(String(20), nullable=False)
    calculated_value = Column(Numeric(15, 4), nullable=True)
    threshold_value = Column(Numeric(15, 4), nullable=True)
    is_compliant = Column(Boolean, nullable=False)
    variance = Column(Numeric(15, 4), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", backref="covenant_compliance_history")
    period = relationship("FinancialPeriod", backref="covenant_compliance_history")

    def __repr__(self):
        return (
            f"<CovenantComplianceHistory(property_id={self.property_id}, period_id={self.period_id}, "
            f"covenant_type='{self.covenant_type}', is_compliant={self.is_compliant})>"
        )
