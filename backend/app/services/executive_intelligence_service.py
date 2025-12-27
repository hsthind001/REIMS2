"""
Executive Intelligence Service

Calculates executive-level metrics and investment recommendations from market intelligence data.
Provides actionable insights for C-level decision making.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutiveIntelligenceService:
    """Service for calculating executive-level market intelligence metrics."""

    def calculate_location_score(self, location_intel: Optional[Dict], demographics: Optional[Dict]) -> Optional[float]:
        """
        Calculate location quality score (0-10).

        Factors:
        - Walk/Bike/Transit scores (30%)
        - School ratings (20%)
        - Crime index (20%)
        - Amenities proximity (15%)
        - Demographics (15%)
        """
        if not location_intel or not location_intel.get('data'):
            return None

        try:
            data = location_intel['data']
            score = 0.0

            # Mobility scores (30%) - normalized to 0-3
            walk_score = data.get('walk_score', 0) / 100 * 1.2
            bike_score = data.get('bike_score', 0) / 100 * 0.9
            transit_score = data.get('transit_score', 0) / 100 * 0.9
            score += (walk_score + bike_score + transit_score)

            # School ratings (20%) - normalized to 0-2
            school_rating = data.get('school_rating_avg', 5) / 10 * 2.0
            score += school_rating

            # Crime index (20%) - inverted (lower crime = higher score) to 0-2
            crime_index = data.get('crime_index', 50)
            crime_score = (100 - crime_index) / 100 * 2.0
            score += crime_score

            # Amenities (15%) - normalized to 0-1.5
            amenities = data.get('amenities', {})
            amenity_score = 0
            if amenities.get('grocery_stores_1mi', 0) > 0:
                amenity_score += 0.4
            if amenities.get('restaurants_1mi', 0) > 3:
                amenity_score += 0.3
            if amenities.get('parks_1mi', 0) > 0:
                amenity_score += 0.3
            if amenities.get('schools_2mi', 0) > 0:
                amenity_score += 0.3
            if amenities.get('hospitals_5mi', 0) > 0:
                amenity_score += 0.2
            score += min(amenity_score, 1.5)

            # Demographics quality (15%) - normalized to 0-1.5
            if demographics and demographics.get('data'):
                demo = demographics['data']
                income_score = 0
                edu_score = 0

                median_income = demo.get('median_household_income', 0)
                if median_income > 80000:
                    income_score = 0.8
                elif median_income > 60000:
                    income_score = 0.6
                elif median_income > 40000:
                    income_score = 0.4

                college_pct = demo.get('college_educated_pct', 0)
                if college_pct > 40:
                    edu_score = 0.7
                elif college_pct > 25:
                    edu_score = 0.5
                elif college_pct > 15:
                    edu_score = 0.3

                score += (income_score + edu_score)

            # Cap at 10
            return round(min(score, 10.0), 1)

        except Exception as e:
            logger.error(f"Error calculating location score: {e}")
            return None

    def calculate_market_cap_rate(self, competitive_analysis: Optional[Dict]) -> float:
        """Calculate market average cap rate from competitive analysis or economic data."""
        if not competitive_analysis or not competitive_analysis.get('data'):
            return 0.0

        try:
            data = competitive_analysis['data']
            avg_cap = data.get('market_avg_cap_rate', 0)
            return round(avg_cap, 2) if avg_cap else 0.0
        except Exception as e:
            logger.error(f"Error calculating market cap rate: {e}")
            return 0.0

    def calculate_rent_growth(self, forecasts: Optional[Dict]) -> Optional[float]:
        """Extract rent growth forecast from forecasts data."""
        if not forecasts or not forecasts.get('data'):
            return None

        try:
            data = forecasts['data']
            rent_growth = data.get('rent_growth_3yr_cagr', None)
            return round(rent_growth, 1) if rent_growth else None
        except Exception as e:
            logger.error(f"Error extracting rent growth: {e}")
            return None

    def calculate_risk_score(self,
                            esg_assessment: Optional[Dict],
                            economic_indicators: Optional[Dict],
                            forecasts: Optional[Dict],
                            location_intel: Optional[Dict]) -> int:
        """
        Calculate composite risk score (0-100, higher = more risk).

        Factors:
        - ESG risks (30%)
        - Economic conditions (25%)
        - Market forecast risks (25%)
        - Location/crime (20%)
        """
        try:
            risk = 0

            # ESG Risks (30 points max)
            if esg_assessment and esg_assessment.get('data'):
                esg_data = esg_assessment['data']
                esg_score = esg_data.get('composite_score', {}).get('overall', {}).get('score', 75)
                # Lower ESG score = higher risk (invert)
                esg_risk = (100 - esg_score) / 100 * 30
                risk += esg_risk
            else:
                risk += 15  # Moderate risk if no ESG data

            # Economic Conditions (25 points max)
            if economic_indicators and economic_indicators.get('data'):
                econ_data = economic_indicators['data']

                # Recession probability
                recession_prob = econ_data.get('recession_probability', {}).get('value', 0)
                risk += (recession_prob / 100) * 10

                # Unemployment
                unemployment = econ_data.get('unemployment_rate', {}).get('value', 4)
                if unemployment > 6:
                    risk += 8
                elif unemployment > 5:
                    risk += 5
                elif unemployment > 4:
                    risk += 2

                # Mortgage rates
                mortgage_rate = econ_data.get('mortgage_rate_30y', {}).get('value', 6)
                if mortgage_rate > 7:
                    risk += 7
                elif mortgage_rate > 6:
                    risk += 4
            else:
                risk += 12  # Moderate risk if no economic data

            # Market Forecast Risks (25 points max)
            if forecasts and forecasts.get('data'):
                forecast_data = forecasts['data']

                # Rent growth (negative growth = risk)
                rent_growth = forecast_data.get('rent_growth_3yr_cagr', 3)
                if rent_growth < 0:
                    risk += 15
                elif rent_growth < 2:
                    risk += 10
                elif rent_growth < 3:
                    risk += 5

                # Vacancy risk
                vacancy_forecast = forecast_data.get('vacancy_rate_forecast', 5)
                if vacancy_forecast > 10:
                    risk += 10
                elif vacancy_forecast > 7:
                    risk += 5
            else:
                risk += 12  # Moderate risk if no forecast

            # Location/Crime (20 points max)
            if location_intel and location_intel.get('data'):
                loc_data = location_intel['data']
                crime_index = loc_data.get('crime_index', 50)
                # Higher crime = higher risk
                risk += (crime_index / 100) * 20
            else:
                risk += 10  # Moderate risk if no location data

            return round(min(risk, 100))

        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 50  # Default moderate risk

    def calculate_opportunity_score(self,
                                   location_score: Optional[float],
                                   rent_growth: Optional[float],
                                   demographics: Optional[Dict],
                                   competitive_analysis: Optional[Dict]) -> int:
        """
        Calculate opportunity score (0-100, higher = better opportunity).

        Factors:
        - Rent growth potential (30%)
        - Location quality (25%)
        - Demographic trends (25%)
        - Competitive positioning (20%)
        """
        try:
            score = 0

            # Rent Growth Potential (30 points)
            if rent_growth is not None:
                if rent_growth >= 5:
                    score += 30
                elif rent_growth >= 3:
                    score += 20
                elif rent_growth >= 2:
                    score += 15
                elif rent_growth >= 0:
                    score += 10
            else:
                score += 15  # Moderate if unknown

            # Location Quality (25 points)
            if location_score is not None:
                score += (location_score / 10) * 25
            else:
                score += 12  # Moderate if unknown

            # Demographics (25 points)
            if demographics and demographics.get('data'):
                demo = demographics['data']

                # Income growth indicator
                median_income = demo.get('median_household_income', 0)
                if median_income > 80000:
                    score += 12
                elif median_income > 60000:
                    score += 8
                elif median_income > 40000:
                    score += 5

                # Education (proxy for growth)
                college_pct = demo.get('college_educated_pct', 0)
                if college_pct > 40:
                    score += 10
                elif college_pct > 25:
                    score += 6
                elif college_pct > 15:
                    score += 3

                # Population density (demand indicator)
                population = demo.get('population', 0)
                if population > 5000:
                    score += 3
            else:
                score += 12  # Moderate if unknown

            # Competitive Positioning (20 points)
            if competitive_analysis and competitive_analysis.get('data'):
                comp_data = competitive_analysis['data']

                # New supply vs demand
                absorption = comp_data.get('absorption_rate_units_per_mo', 0)
                new_supply = comp_data.get('new_supply_pipeline_units', 0)

                if absorption > 0 and new_supply / max(absorption, 1) < 12:
                    # Less than 1 year of supply = opportunity
                    score += 15
                elif absorption > 0 and new_supply / max(absorption, 1) < 24:
                    score += 10
                else:
                    score += 5

                # Market cap rate vs trend
                score += 5  # Placeholder
            else:
                score += 10  # Moderate if unknown

            return round(min(score, 100))

        except Exception as e:
            logger.error(f"Error calculating opportunity score: {e}")
            return 50  # Default moderate

    def generate_investment_recommendation(self,
                                         risk_score: int,
                                         opportunity_score: int,
                                         your_cap_rate: float,
                                         market_cap_rate: float) -> Dict[str, Any]:
        """
        Generate executive investment recommendation.

        Returns:
        - action: "BUY", "HOLD", "SELL", "REVIEW"
        - confidence: 0-100
        - rationale: List of key reasons
        - priority: "HIGH", "MEDIUM", "LOW"
        """
        try:
            # Calculate decision matrix score
            # Opportunity - Risk = Net Attractiveness
            net_score = opportunity_score - risk_score

            # Cap rate comparison
            cap_rate_premium = your_cap_rate - market_cap_rate if market_cap_rate > 0 else 0

            # Decision logic
            action = "REVIEW"
            confidence = 50
            rationale = []
            priority = "MEDIUM"

            # Strong Buy Signals
            if net_score >= 30 and opportunity_score >= 70:
                action = "BUY"
                confidence = 85
                priority = "HIGH"
                rationale.append(f"Exceptional opportunity (score: {opportunity_score}/100)")
                rationale.append(f"Risk is manageable ({risk_score}/100)")

            # Moderate Buy Signals
            elif net_score >= 15 and opportunity_score >= 60:
                action = "BUY"
                confidence = 70
                priority = "MEDIUM"
                rationale.append(f"Strong opportunity (score: {opportunity_score}/100)")
                rationale.append(f"Acceptable risk level ({risk_score}/100)")

            # Hold Signals - performing well
            elif net_score >= 0 and cap_rate_premium >= 0:
                action = "HOLD"
                confidence = 75
                priority = "LOW"
                rationale.append(f"Asset performing at/above market (cap rate +{cap_rate_premium:.1f}%)")
                rationale.append(f"Balanced opportunity/risk profile")

            # Hold Signals - neutral
            elif net_score >= -15:
                action = "HOLD"
                confidence = 60
                priority = "MEDIUM"
                rationale.append(f"Market conditions stable")
                rationale.append(f"Monitor for changes in risk/opportunity balance")

            # Sell Signals - high risk
            elif risk_score >= 70:
                action = "SELL"
                confidence = 80
                priority = "HIGH"
                rationale.append(f"High risk exposure ({risk_score}/100)")
                rationale.append(f"Limited upside potential ({opportunity_score}/100)")

            # Sell Signals - underperforming
            elif cap_rate_premium < -1.0 and opportunity_score < 40:
                action = "SELL"
                confidence = 75
                priority = "HIGH"
                rationale.append(f"Underperforming market (cap rate {cap_rate_premium:.1f}%)")
                rationale.append(f"Weak growth prospects")

            # Review Signals
            else:
                action = "REVIEW"
                confidence = 50
                priority = "MEDIUM"
                rationale.append(f"Mixed signals - detailed analysis recommended")
                rationale.append(f"Opportunity: {opportunity_score}/100, Risk: {risk_score}/100")

            # Add cap rate context if available
            if market_cap_rate > 0:
                if cap_rate_premium >= 0.5:
                    rationale.append(f"Outperforming market by {cap_rate_premium:.1f}%")
                elif cap_rate_premium <= -0.5:
                    rationale.append(f"Underperforming market by {abs(cap_rate_premium):.1f}%")

            return {
                "action": action,
                "confidence": confidence,
                "priority": priority,
                "rationale": rationale,
                "metrics": {
                    "net_score": net_score,
                    "opportunity_score": opportunity_score,
                    "risk_score": risk_score,
                    "cap_rate_premium": round(cap_rate_premium, 2)
                }
            }

        except Exception as e:
            logger.error(f"Error generating investment recommendation: {e}")
            return {
                "action": "REVIEW",
                "confidence": 0,
                "priority": "HIGH",
                "rationale": ["Error calculating recommendation - manual review required"],
                "metrics": {}
            }

    def generate_executive_summary(self, market_intelligence: Dict[str, Any], your_cap_rate: float = 0.0) -> Dict[str, Any]:
        """
        Generate complete executive summary with all calculated metrics.

        Args:
            market_intelligence: Complete market intelligence data
            your_cap_rate: Property's actual cap rate

        Returns:
            Executive summary with scores, recommendation, and key insights
        """
        try:
            # Extract data
            demographics = market_intelligence.get('demographics')
            economic_indicators = market_intelligence.get('economic_indicators')
            location_intelligence = market_intelligence.get('location_intelligence')
            esg_assessment = market_intelligence.get('esg_assessment')
            forecasts = market_intelligence.get('forecasts')
            competitive_analysis = market_intelligence.get('competitive_analysis')
            ai_insights = market_intelligence.get('ai_insights')

            # Calculate scores
            location_score = self.calculate_location_score(location_intelligence, demographics)
            market_cap_rate = self.calculate_market_cap_rate(competitive_analysis)
            rent_growth = self.calculate_rent_growth(forecasts)
            risk_score = self.calculate_risk_score(esg_assessment, economic_indicators, forecasts, location_intelligence)
            opportunity_score = self.calculate_opportunity_score(location_score, rent_growth, demographics, competitive_analysis)

            # Generate recommendation
            recommendation = self.generate_investment_recommendation(
                risk_score, opportunity_score, your_cap_rate, market_cap_rate
            )

            # Extract key insights
            key_findings = []
            if ai_insights and ai_insights.get('data'):
                ai_data = ai_insights['data']
                opportunities = ai_data.get('opportunities', [])
                key_findings.extend(opportunities[:2])  # Top 2

            return {
                "location_score": location_score,
                "market_cap_rate": market_cap_rate,
                "rent_growth": rent_growth,
                "risk_score": risk_score,
                "opportunity_score": opportunity_score,
                "investment_recommendation": recommendation,
                "key_findings": key_findings,
                "executive_summary": {
                    "headline": self._generate_headline(recommendation, location_score, rent_growth),
                    "quick_stats": {
                        "location_quality": self._score_to_label(location_score, "location"),
                        "growth_potential": self._score_to_label(rent_growth, "growth"),
                        "risk_level": self._score_to_label(risk_score, "risk"),
                        "opportunity_level": self._score_to_label(opportunity_score, "opportunity")
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {
                "location_score": None,
                "market_cap_rate": 0.0,
                "rent_growth": None,
                "risk_score": 50,
                "opportunity_score": 50,
                "investment_recommendation": {
                    "action": "REVIEW",
                    "confidence": 0,
                    "priority": "HIGH",
                    "rationale": ["Error generating summary - manual review required"],
                    "metrics": {}
                },
                "key_findings": [],
                "executive_summary": {
                    "headline": "Insufficient data for recommendation",
                    "quick_stats": {}
                }
            }

    def _generate_headline(self, recommendation: Dict, location_score: Optional[float], rent_growth: Optional[float]) -> str:
        """Generate executive headline summary."""
        action = recommendation.get('action', 'REVIEW')
        confidence = recommendation.get('confidence', 0)

        if action == "BUY" and confidence >= 80:
            return f"STRONG BUY: Premium location ({location_score}/10) with {rent_growth}% growth potential"
        elif action == "BUY":
            return f"BUY: Attractive opportunity with manageable risk"
        elif action == "HOLD":
            return f"HOLD: Asset performing at market - monitor conditions"
        elif action == "SELL":
            return f"SELL RECOMMENDED: High risk or underperformance detected"
        else:
            return f"REVIEW REQUIRED: Mixed signals - detailed analysis needed"

    def _score_to_label(self, score: Optional[float], metric_type: str) -> str:
        """Convert numeric score to executive label."""
        if score is None:
            return "Unknown"

        if metric_type == "location":
            if score >= 8:
                return "Premium"
            elif score >= 6:
                return "Strong"
            elif score >= 4:
                return "Average"
            else:
                return "Below Average"

        elif metric_type == "growth":
            if score >= 5:
                return "Exceptional"
            elif score >= 3:
                return "Strong"
            elif score >= 2:
                return "Moderate"
            elif score >= 0:
                return "Stable"
            else:
                return "Declining"

        elif metric_type == "risk":
            if score >= 70:
                return "High Risk"
            elif score >= 50:
                return "Moderate Risk"
            elif score >= 30:
                return "Low Risk"
            else:
                return "Minimal Risk"

        elif metric_type == "opportunity":
            if score >= 75:
                return "Exceptional"
            elif score >= 60:
                return "Strong"
            elif score >= 40:
                return "Moderate"
            else:
                return "Limited"

        return "Unknown"
