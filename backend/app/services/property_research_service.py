"""
Property Research Service - Orchestrate comprehensive property intelligence

Coordinates M1 Retriever Agent and stores results
"""
from typing import Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
import logging

from app.models.property import Property
from app.models.property_research import PropertyResearch
from app.agents.retriever_agent import RetrieverAgent

logger = logging.getLogger(__name__)


class PropertyResearchService:
    """
    Orchestrate comprehensive property research

    Workflow:
    1. Get property details
    2. Trigger M1 Retriever Agent
    3. Store results in database
    4. Return structured research data
    """

    def __init__(self, db: Session):
        self.db = db
        self.retriever = RetrieverAgent(db)

    async def conduct_research(self, property_id: int, force_refresh: bool = False) -> Dict:
        """
        Conduct comprehensive research for a property

        Args:
            property_id: Property to research
            force_refresh: Force new research even if recent data exists

        Returns:
            dict: Research results
        """
        logger.info(f"Starting property research for property_id={property_id}")

        # 1. Get property
        property = self.db.query(Property).filter(Property.id == property_id).first()
        if not property:
            return {
                "success": False,
                "error": f"Property {property_id} not found"
            }

        # 2. Check if recent research exists (unless force_refresh)
        if not force_refresh:
            recent_research = self._get_recent_research(property_id, days=30)
            if recent_research:
                logger.info(f"Using cached research from {recent_research.research_date}")
                return {
                    "success": True,
                    "data": recent_research.to_dict(),
                    "cached": True
                }

        # 3. Trigger M1 Retriever Agent
        try:
            research_result = await self.retriever.conduct_research(property_id)

            if not research_result.get('success'):
                return research_result

            research_data = research_result['data']

            # 4. Store in database
            property_research = PropertyResearch(
                property_id=property_id,
                research_date=date.today(),
                demographics_data=research_data.get('demographics'),
                employment_data=research_data.get('employment'),
                developments_data=research_data.get('developments'),
                market_data=research_data.get('market_analysis'),
                sources=research_data.get('sources'),
                confidence_score=research_data.get('confidence_score')
            )

            self.db.add(property_research)
            self.db.commit()
            self.db.refresh(property_research)

            logger.info(f"Research stored successfully. ID: {property_research.id}")

            return {
                "success": True,
                "data": property_research.to_dict(),
                "cached": False
            }

        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await self.retriever.close()

    def get_latest_research(self, property_id: int) -> Optional[PropertyResearch]:
        """Get most recent research for a property"""
        return self.db.query(PropertyResearch)\
            .filter(PropertyResearch.property_id == property_id)\
            .order_by(PropertyResearch.research_date.desc())\
            .first()

    def get_demographics(self, property_id: int) -> Optional[Dict]:
        """Get demographics data for property"""
        research = self.get_latest_research(property_id)
        if research and research.demographics_data:
            return research.demographics_data
        return None

    def get_employment_data(self, property_id: int) -> Optional[Dict]:
        """Get employment data for property"""
        research = self.get_latest_research(property_id)
        if research and research.employment_data:
            return research.employment_data
        return None

    def get_nearby_developments(self, property_id: int) -> Optional[list]:
        """Get nearby developments"""
        research = self.get_latest_research(property_id)
        if research and research.developments_data:
            return research.developments_data
        return []

    def get_market_analysis(self, property_id: int) -> Optional[Dict]:
        """Get market analysis"""
        research = self.get_latest_research(property_id)
        if research and research.market_data:
            return research.market_data
        return None

    def get_demographic_trends(self, property_id: int, years: int = 5) -> Dict:
        """
        Analyze demographic trends over time

        Args:
            property_id: Property ID
            years: Number of years to analyze

        Returns:
            dict: Trend analysis
        """
        # Get historical research data
        historical_research = self.db.query(PropertyResearch)\
            .filter(PropertyResearch.property_id == property_id)\
            .order_by(PropertyResearch.research_date.desc())\
            .limit(years * 4)\
            .all()  # Assuming quarterly research

        if not historical_research:
            return {
                "success": False,
                "error": "No historical research data available"
            }

        # Extract trends
        trends = {
            "population_trend": self._calculate_trend(
                [r.demographics_data.get('population') for r in historical_research if r.demographics_data]
            ),
            "income_trend": self._calculate_trend(
                [r.demographics_data.get('median_income') for r in historical_research if r.demographics_data]
            ),
            "data_points": len(historical_research)
        }

        return {
            "success": True,
            "trends": trends
        }

    def get_employment_trends(self, property_id: int, years: int = 5) -> Dict:
        """
        Analyze employment trends over time

        Returns trend analysis of unemployment rate, major employers, etc.
        """
        historical_research = self.db.query(PropertyResearch)\
            .filter(PropertyResearch.property_id == property_id)\
            .order_by(PropertyResearch.research_date.desc())\
            .limit(years * 4)\
            .all()

        if not historical_research:
            return {
                "success": False,
                "error": "No historical research data available"
            }

        # Extract employment trends
        unemployment_rates = [
            r.employment_data.get('unemployment_rate')
            for r in historical_research
            if r.employment_data and r.employment_data.get('unemployment_rate') is not None
        ]

        trends = {
            "unemployment_trend": self._calculate_trend(unemployment_rates),
            "current_rate": unemployment_rates[0] if unemployment_rates else None,
            "data_points": len(unemployment_rates)
        }

        return {
            "success": True,
            "trends": trends
        }

    def assess_development_impact(self, property_id: int) -> Dict:
        """
        Assess impact of nearby developments on property

        Returns:
            dict: Impact assessment with scores
        """
        research = self.get_latest_research(property_id)
        if not research or not research.developments_data:
            return {
                "success": False,
                "error": "No development data available"
            }

        developments = research.developments_data
        if not developments:
            return {
                "success": True,
                "impact_score": 5.0,  # Neutral
                "impact_level": "neutral",
                "developments_count": 0
            }

        # Calculate overall impact score (1-10 scale)
        total_impact = sum(d.get('impact_score', 5.0) for d in developments)
        avg_impact = total_impact / len(developments)

        # Categorize impact
        if avg_impact >= 7.5:
            impact_level = "high_positive"
        elif avg_impact >= 6.0:
            impact_level = "moderate_positive"
        elif avg_impact >= 4.0:
            impact_level = "neutral"
        elif avg_impact >= 2.5:
            impact_level = "moderate_negative"
        else:
            impact_level = "high_negative"

        # Find most impactful development
        most_impactful = max(developments, key=lambda d: d.get('impact_score', 0))

        return {
            "success": True,
            "impact_score": avg_impact,
            "impact_level": impact_level,
            "developments_count": len(developments),
            "most_impactful_development": most_impactful,
            "developments": developments
        }

    def generate_market_health_score(self, property_id: int) -> Dict:
        """
        Generate overall market health score for property area

        Combines demographics, employment, and market data into single score (0-100)
        """
        research = self.get_latest_research(property_id)
        if not research:
            return {
                "success": False,
                "error": "No research data available"
            }

        score = 50.0  # Base score

        # Demographics factor (30 points)
        if research.demographics_data:
            demographics = research.demographics_data

            # Median income score (15 points)
            median_income = demographics.get('median_income', 0)
            if median_income >= 100000:
                score += 15
            elif median_income >= 75000:
                score += 12
            elif median_income >= 50000:
                score += 8
            else:
                score += 5

            # Education level score (15 points)
            education = demographics.get('education_level', {})
            bachelors_rate = education.get('bachelors', 0)
            if bachelors_rate >= 0.5:
                score += 15
            elif bachelors_rate >= 0.3:
                score += 10
            else:
                score += 5

        # Employment factor (30 points)
        if research.employment_data:
            employment = research.employment_data

            # Unemployment rate (inverse scoring - lower is better)
            unemployment_rate = employment.get('unemployment_rate', 0.05)
            if unemployment_rate <= 0.03:
                score += 15
            elif unemployment_rate <= 0.05:
                score += 12
            elif unemployment_rate <= 0.07:
                score += 8
            else:
                score += 5

            # Employment trend (15 points)
            trend = employment.get('trend', 'stable')
            if trend == 'increasing' or trend == 'decreasing':  # decreasing unemployment = positive
                score += 15
            else:
                score += 10

        # Market factor (20 points)
        if research.market_data:
            market = research.market_data

            # Rental rate trend (10 points)
            rental_trend = market.get('rental_rate_trend', 'stable')
            if rental_trend == 'increasing':
                score += 10
            elif rental_trend == 'stable':
                score += 7
            else:
                score += 3

            # Vacancy rate (10 points - lower is better)
            vacancy_rate = market.get('vacancy_rate', 0.1)
            if vacancy_rate <= 0.05:
                score += 10
            elif vacancy_rate <= 0.10:
                score += 7
            else:
                score += 3

        # Cap score at 100
        final_score = min(100, score)

        # Determine health category
        if final_score >= 85:
            health_category = "excellent"
        elif final_score >= 70:
            health_category = "good"
        elif final_score >= 55:
            health_category = "fair"
        else:
            health_category = "poor"

        return {
            "success": True,
            "health_score": final_score,
            "health_category": health_category,
            "confidence": float(research.confidence_score) if research.confidence_score else 0.8
        }

    def _get_recent_research(self, property_id: int, days: int = 30) -> Optional[PropertyResearch]:
        """Get research data if it's recent (within N days)"""
        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=days)

        return self.db.query(PropertyResearch)\
            .filter(
                PropertyResearch.property_id == property_id,
                PropertyResearch.research_date >= cutoff_date
            )\
            .order_by(PropertyResearch.research_date.desc())\
            .first()

    def _calculate_trend(self, values: list) -> str:
        """
        Calculate trend from list of values

        Returns: "increasing", "decreasing", "stable", or "insufficient_data"
        """
        # Filter out None values
        values = [v for v in values if v is not None]

        if len(values) < 2:
            return "insufficient_data"

        # Simple trend: compare first and last
        if values[0] > values[-1] * 1.05:  # 5% threshold
            return "decreasing"
        elif values[0] < values[-1] * 0.95:
            return "increasing"
        else:
            return "stable"
