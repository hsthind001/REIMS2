"""
Market Intelligence Model

Stores comprehensive market intelligence data for properties including:
- Demographics
- Economic indicators
- Location intelligence
- ESG risk assessment
- Predictive forecasts
- Competitive analysis
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime


class MarketIntelligence(Base):
    """
    Market intelligence data for properties.

    This table stores comprehensive market analysis data including demographics,
    economic indicators, location scores, ESG risk, and predictive forecasts.

    All data is stored in JSONB fields for flexibility with source/vintage tagging.
    """

    __tablename__ = "market_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Demographics (from Census API)
    demographics = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "population": 45000,
                "median_household_income": 75000,
                "median_home_value": 450000,
                "median_gross_rent": 1800,
                "unemployment_rate": 4.2,
                "median_age": 34.5,
                "college_educated_pct": 45.2,
                "housing_units": {...},
                "geography": {"state_fips": "06", "county_fips": "001", "tract": "401100"}
            },
            "lineage": {
                "source": "census_acs5",
                "vintage": "2021",
                "confidence": 95.0,
                "fetched_at": "2025-12-25T10:00:00",
                "metadata": {...}
            }
        }
        """
    )

    # Economic Indicators (from FRED API)
    economic_indicators = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "gdp_growth": {"value": 2.5, "date": "2024-Q3"},
                "unemployment_rate": {"value": 3.8, "date": "2024-11"},
                "inflation_rate": {"value": 3.2, "date": "2024-11"},
                "fed_funds_rate": {"value": 5.25, "date": "2024-11"},
                "mortgage_rate_30y": {"value": 6.8, "date": "2024-11"},
                "recession_probability": {"value": 15.0, "date": "2024-11"},
                "msa_unemployment": {"value": 3.5, "date": "2024-10"},
                "msa_gdp": {"value": 450000, "date": "2024-Q2"}
            },
            "lineage": {...}
        }
        """
    )

    # Location Intelligence (walkability, transit, amenities)
    location_intelligence = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "walk_score": 85,
                "transit_score": 72,
                "bike_score": 68,
                "amenities": {
                    "grocery_stores_1mi": 5,
                    "restaurants_1mi": 45,
                    "schools_2mi": 12,
                    "hospitals_5mi": 3,
                    "parks_1mi": 8
                },
                "transit_access": {
                    "bus_stops_0_5mi": 8,
                    "subway_stations_1mi": 2,
                    "commute_time_downtown_min": 25
                },
                "crime_index": 45.2,
                "school_rating_avg": 7.8
            },
            "lineage": {...}
        }
        """
    )

    # ESG Risk Assessment
    esg_assessment = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "environmental": {
                    "flood_risk_score": 25.0,
                    "flood_zone": "X",
                    "wildfire_risk_score": 10.0,
                    "earthquake_risk_score": 35.0,
                    "climate_risk_composite": 23.3,
                    "energy_efficiency_rating": "B",
                    "emissions_intensity_kg_co2_sqft": 12.5
                },
                "social": {
                    "crime_score": 45.2,
                    "school_quality_score": 7.8,
                    "income_inequality_gini": 0.42,
                    "diversity_index": 0.68,
                    "community_health_score": 75.0
                },
                "governance": {
                    "zoning_compliance_score": 95.0,
                    "permit_history_score": 88.0,
                    "tax_delinquency_risk": "Low",
                    "legal_issues_count": 0,
                    "regulatory_risk_score": 15.0
                },
                "composite_esg_score": 72.5,
                "esg_grade": "B+"
            },
            "lineage": {...}
        }
        """
    )

    # Predictive Forecasts
    forecasts = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "rent_forecast_12mo": {
                    "predicted_rent": 2450,
                    "change_pct": 3.5,
                    "confidence_interval_95": [2380, 2520],
                    "model": "prophet",
                    "r_squared": 0.87
                },
                "occupancy_forecast_12mo": {
                    "predicted_occupancy": 94.5,
                    "change_pct": 1.2,
                    "confidence_interval_95": [92.0, 96.5],
                    "model": "xgboost",
                    "accuracy": 0.91
                },
                "cap_rate_forecast_12mo": {
                    "predicted_cap_rate": 5.8,
                    "change_bps": 25,
                    "confidence_interval_95": [5.5, 6.1],
                    "model": "arima",
                    "mae": 0.15
                },
                "value_forecast_12mo": {
                    "predicted_value": 5450000,
                    "change_pct": 4.2,
                    "confidence_interval_95": [5300000, 5600000],
                    "model": "ensemble",
                    "accuracy": 0.89
                }
            },
            "lineage": {...}
        }
        """
    )

    # Competitive Analysis
    competitive_analysis = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "submarket_position": {
                    "rent_percentile": 65,
                    "occupancy_percentile": 72,
                    "quality_percentile": 58,
                    "value_percentile": 68
                },
                "market_share_pct": 2.3,
                "competitive_threats": [
                    {
                        "property_name": "Nearby Competitor",
                        "distance_mi": 0.8,
                        "threat_score": 75.0,
                        "advantages": ["newer", "more amenities"],
                        "disadvantages": ["higher rent", "smaller units"]
                    }
                ],
                "submarket_trends": {
                    "rent_growth_3yr_cagr": 4.2,
                    "occupancy_trend": "stable",
                    "new_supply_pipeline_units": 450,
                    "absorption_rate_units_per_month": 35
                }
            },
            "lineage": {...}
        }
        """
    )

    # Comparable Properties Analysis
    comparables = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "comparables": [
                    {
                        "property_name": "Comparable 1",
                        "distance_mi": 1.2,
                        "similarity_score": 88.5,
                        "rent_psf": 2.45,
                        "occupancy_rate": 95.0,
                        "cap_rate": 5.5,
                        "year_built": 2015,
                        "units": 120,
                        "adjustments": {
                            "age_adjustment_pct": -5,
                            "location_adjustment_pct": 3,
                            "amenities_adjustment_pct": 2,
                            "size_adjustment_pct": 0
                        },
                        "adjusted_rent_psf": 2.45
                    }
                ],
                "market_rent_estimate": {
                    "mean_rent_psf": 2.42,
                    "median_rent_psf": 2.45,
                    "std_dev": 0.18,
                    "confidence": 85.0,
                    "sample_size": 8
                }
            },
            "lineage": {...}
        }
        """
    )

    # AI Insights (structured format)
    ai_insights = Column(
        JSONB,
        nullable=True,
        comment="""
        {
            "data": {
                "strengths": [
                    {"insight": "Strong demographics", "confidence": 90.0, "impact": "high"},
                    {"insight": "Excellent transit access", "confidence": 95.0, "impact": "high"}
                ],
                "weaknesses": [
                    {"insight": "High flood risk", "confidence": 85.0, "impact": "medium"},
                    {"insight": "Below-market occupancy", "confidence": 92.0, "impact": "high"}
                ],
                "opportunities": [
                    {"insight": "Rent growth potential", "confidence": 78.0, "impact": "high"},
                    {"insight": "ESG improvement opportunities", "confidence": 70.0, "impact": "medium"}
                ],
                "threats": [
                    {"insight": "New supply pipeline", "confidence": 88.0, "impact": "high"},
                    {"insight": "Rising interest rates", "confidence": 95.0, "impact": "high"}
                ],
                "overall_score": 72.5,
                "investment_grade": "B+",
                "confidence": 85.0
            },
            "lineage": {...}
        }
        """
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True, comment="Last time data was refreshed from external sources")

    # Refresh metadata
    refresh_status = Column(String(50), nullable=True, comment="'success', 'partial', 'failure'")
    refresh_error = Column(Text, nullable=True, comment="Error message from last refresh attempt")

    # Relationships
    property_obj = relationship("Property", back_populates="market_intelligence")

    def __repr__(self):
        return f"<MarketIntelligence(id={self.id}, property_id={self.property_id}, updated_at={self.updated_at})>"

    # Indexes
    __table_args__ = (
        Index('idx_market_intelligence_property', 'property_id'),
        Index('idx_market_intelligence_updated', 'updated_at'),
        Index('idx_market_intelligence_last_refreshed', 'last_refreshed_at'),
        {'comment': 'Comprehensive market intelligence data for properties'}
    )
