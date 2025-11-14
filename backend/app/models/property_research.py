"""
Property Research Model - Demographics, Employment, Market Intelligence
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class PropertyResearch(Base):
    """
    Property Research - Comprehensive market intelligence

    Stores results from M1 Retriever Agent:
    - Demographics (Census Bureau)
    - Employment data (BLS)
    - Nearby developments
    - Market analysis
    """
    __tablename__ = "property_research"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    research_date = Column(Date, nullable=False, index=True)

    # JSON fields for flexible data storage
    demographics_data = Column(JSONB, nullable=True, comment="Census Bureau demographics data")
    employment_data = Column(JSONB, nullable=True, comment="BLS employment statistics")
    developments_data = Column(JSONB, nullable=True, comment="Nearby development projects")
    market_data = Column(JSONB, nullable=True, comment="Market analysis and trends")
    sources = Column(JSONB, nullable=True, comment="Data sources used")

    # Quality metadata
    confidence_score = Column(Numeric(5, 4), nullable=True, comment="Overall confidence in research data (0-1)")

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    property = relationship("Property", back_populates="research_data")

    def __repr__(self):
        return f"<PropertyResearch(id={self.id}, property_id={self.property_id}, date={self.research_date})>"

    @property
    def population(self):
        """Convenience property to get population from demographics"""
        if self.demographics_data:
            return self.demographics_data.get('population')
        return None

    @property
    def median_income(self):
        """Convenience property to get median income from demographics"""
        if self.demographics_data:
            return self.demographics_data.get('median_income')
        return None

    @property
    def unemployment_rate(self):
        """Convenience property to get unemployment rate from employment data"""
        if self.employment_data:
            return self.employment_data.get('unemployment_rate')
        return None

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'property_id': self.property_id,
            'research_date': self.research_date.isoformat() if self.research_date else None,
            'demographics': self.demographics_data,
            'employment': self.employment_data,
            'developments': self.developments_data,
            'market_analysis': self.market_data,
            'sources': self.sources,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
