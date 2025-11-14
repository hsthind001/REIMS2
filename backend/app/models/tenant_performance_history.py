"""
Tenant Performance History Model - ML training data
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base


class TenantPerformanceHistory(Base):
    """
    Tenant Performance History - Historical tenant data for ML

    Used to train tenant recommendation model
    """
    __tablename__ = "tenant_performance_history"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_name = Column(String(200), nullable=False)
    tenant_category = Column(String(100), nullable=True, index=True, comment="Category: retail, restaurant, service, etc.")

    # Lease details
    lease_start_date = Column(Date, nullable=True)
    lease_end_date = Column(Date, nullable=True)
    monthly_rent = Column(Numeric(12, 2), nullable=True)
    space_sqft = Column(Integer, nullable=True)

    # Performance metrics
    performance_score = Column(Numeric(5, 2), nullable=True, comment="Performance score 1-10")
    renewals_count = Column(Integer, default=0, comment="Number of lease renewals")
    still_operating = Column(Boolean, default=True, comment="Whether tenant is still operating")

    # Context at time of lease
    demographics_at_lease = Column(JSONB, nullable=True, comment="Demographics data when lease started")
    tenant_mix_at_lease = Column(JSONB, nullable=True, comment="Other tenants in property at lease start")

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    property_obj = relationship("Property", back_populates="tenant_history")

    def __repr__(self):
        return f"<TenantPerformanceHistory(id={self.id}, tenant='{self.tenant_name}', score={self.performance_score})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'property_id': self.property_id,
            'tenant_name': self.tenant_name,
            'tenant_category': self.tenant_category,
            'lease_start_date': self.lease_start_date.isoformat() if self.lease_start_date else None,
            'lease_end_date': self.lease_end_date.isoformat() if self.lease_end_date else None,
            'monthly_rent': float(self.monthly_rent) if self.monthly_rent else None,
            'space_sqft': self.space_sqft,
            'performance_score': float(self.performance_score) if self.performance_score else None,
            'renewals_count': self.renewals_count,
            'still_operating': self.still_operating,
            'demographics_at_lease': self.demographics_at_lease,
            'tenant_mix_at_lease': self.tenant_mix_at_lease,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @property
    def lease_duration_months(self):
        """Calculate lease duration in months"""
        if self.lease_start_date and self.lease_end_date:
            delta = self.lease_end_date - self.lease_start_date
            return delta.days // 30
        return None

    @property
    def rent_per_sqft(self):
        """Calculate rent per square foot"""
        if self.monthly_rent and self.space_sqft and self.space_sqft > 0:
            return float(self.monthly_rent) / self.space_sqft
        return None

    @property
    def is_successful(self):
        """Determine if tenant was successful (simple heuristic)"""
        if self.performance_score and self.performance_score >= 7.0:
            return True
        if self.renewals_count >= 1:
            return True
        return False
