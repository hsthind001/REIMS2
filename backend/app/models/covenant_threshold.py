"""
Covenant threshold model for per-property covenant configuration.

Allows override of global system_config covenant values per property and date range.
"""
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class CovenantThreshold(Base):
    """
    Per-property covenant threshold overrides.

    When present and effective for a given period, these values override
    the global system_config covenant keys (e.g. covenant_dscr_minimum).
    """

    __tablename__ = "covenant_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    covenant_type = Column(String(50), nullable=False, index=True)
    threshold_value = Column(DECIMAL(15, 4), nullable=False)
    comparison_operator = Column(String(10), nullable=False, server_default=">=")
    effective_date = Column(Date, nullable=False, index=True)
    expiration_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    property = relationship("Property", backref="covenant_thresholds")

    def __repr__(self):
        return (
            f"<CovenantThreshold(property_id={self.property_id}, covenant_type='{self.covenant_type}', "
            f"threshold_value={self.threshold_value})>"
        )
