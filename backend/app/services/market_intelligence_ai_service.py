"""
AI-Enhanced Market Intelligence Service using Open-Source LLMs

Replaces rule-based insights with LLM-generated analysis using:
- Ollama (local inference, 100% free)
- Groq (cloud fallback, very low cost)
- Structured prompts for consistent output

Author: REIMS Development Team
Date: 2025-01-09
"""

import json
import logging
from typing import Dict, Any, Optional
from app.services.local_llm_service import (
    get_local_llm_service,
    LLMTaskType
)
from app.services import market_intelligence_prompts as prompts

logger = logging.getLogger(__name__)


class MarketIntelligenceAIService:
    """
    Enhanced Market Intelligence service using open-source LLMs
    """

    def __init__(self):
        self.llm_service = get_local_llm_service()
        logger.info("Initialized MarketIntelligenceAIService with local LLM")

    async def generate_ai_insights(
        self,
        property_data: Dict[str, Any],
        market_intelligence: Dict[str, Any],
        use_local_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive AI insights using local LLMs

        Args:
            property_data: Property characteristics and metrics
            market_intelligence: Complete market intelligence data
            use_local_llm: If True, use local Ollama; if False, fallback to Groq

        Returns:
            Complete AI insights including SWOT, recommendations, risks
        """
        logger.info(f"Generating AI insights for property {property_data.get('property_code')}")

        try:
            # Prepare market data for prompts
            market_data = {
                "property_code": property_data.get("property_code"),
                **market_intelligence
            }

            # Step 1: Generate SWOT Analysis
            logger.info("Generating SWOT analysis with LLM...")
            swot_analysis = await self._generate_swot_with_llm(market_data)

            # Step 2: Generate Investment Recommendation
            logger.info("Generating investment recommendation...")
            recommendation = await self._generate_recommendation_with_llm(
                market_data,
                swot_analysis
            )

            # Step 3: Generate Risk Assessment
            logger.info("Generating risk assessment...")
            risk_assessment = await self._generate_risk_assessment_with_llm(
                market_data,
                swot_analysis
            )

            # Step 4: Generate Competitive Analysis (if data available)
            competitive_analysis = None
            if market_intelligence.get("competitive_analysis"):
                logger.info("Generating competitive analysis...")
                competitive_analysis = await self._generate_competitive_analysis_with_llm(
                    market_data,
                    property_data
                )

            # Step 5: Generate Market Trends Synthesis
            logger.info("Generating market trends synthesis...")
            market_trends = await self._generate_market_trends_with_llm(market_data)

            # Combine all insights
            ai_insights = {
                "swot_analysis": swot_analysis,
                "investment_recommendation": recommendation.get("recommendation"),
                "confidence": recommendation.get("confidence"),
                "rationale": recommendation.get("rationale"),
                "priority": recommendation.get("priority"),
                "key_risks": recommendation.get("key_risks", []),
                "risk_mitigation_strategies": recommendation.get("risk_mitigation_strategies", []),
                "expected_return_scenarios": recommendation.get("expected_return_scenarios", {}),
                "optimal_holding_period": recommendation.get("optimal_holding_period"),
                "action_items": recommendation.get("action_items", []),
                "risk_assessment": risk_assessment.get("narrative"),
                "overall_risk_score": risk_assessment.get("overall_risk_score"),
                "risk_level": risk_assessment.get("risk_level"),
                "risk_categories": risk_assessment.get("risk_categories", []),
                "opportunities": self._extract_opportunities_from_swot(swot_analysis),
                "market_trend_synthesis": market_trends.get("executive_summary"),
                "demand_drivers": market_trends.get("demand_drivers", []),
                "supply_constraints": market_trends.get("supply_constraints", []),
                "competitive_intelligence": competitive_analysis,
                "generated_by": "local_llm",
                "model_used": "llama3.3:70b-instruct-q4_K_M"
            }

            logger.info("AI insights generation complete")
            return ai_insights

        except Exception as e:
            logger.error(f"Failed to generate AI insights: {e}", exc_info=True)

            # Fallback to simple insights
            return self._generate_fallback_insights(property_data, market_intelligence)

    async def _generate_swot_with_llm(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate SWOT analysis using LLM"""
        try:
            # Generate prompt
            prompt = prompts.generate_swot_prompt(market_data)

            # Call LLM
            swot_json = await self.llm_service.generate_json(
                prompt=prompt,
                task_type=LLMTaskType.ANALYSIS,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=3000
            )

            return swot_json

        except Exception as e:
            logger.error(f"SWOT generation failed: {e}")
            raise

    async def _generate_recommendation_with_llm(
        self,
        market_data: Dict[str, Any],
        swot_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate investment recommendation using LLM"""
        try:
            # Generate prompt
            prompt = prompts.generate_investment_recommendation_prompt(
                market_data,
                swot_analysis
            )

            # Call LLM
            recommendation_json = await self.llm_service.generate_json(
                prompt=prompt,
                task_type=LLMTaskType.NARRATIVE,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=4000
            )

            return recommendation_json

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            raise

    async def _generate_risk_assessment_with_llm(
        self,
        market_data: Dict[str, Any],
        swot_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate risk assessment using LLM"""
        try:
            # Generate prompt
            prompt = prompts.generate_risk_assessment_prompt(
                market_data,
                swot_analysis
            )

            # Call LLM
            risk_json = await self.llm_service.generate_json(
                prompt=prompt,
                task_type=LLMTaskType.ANALYSIS,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2500
            )

            return risk_json

        except Exception as e:
            logger.error(f"Risk assessment generation failed: {e}")
            raise

    async def _generate_competitive_analysis_with_llm(
        self,
        market_data: Dict[str, Any],
        property_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate competitive analysis using LLM"""
        try:
            # Generate prompt
            prompt = prompts.generate_competitive_analysis_prompt(
                market_data,
                property_data
            )

            # Call LLM
            competitive_json = await self.llm_service.generate_json(
                prompt=prompt,
                task_type=LLMTaskType.ANALYSIS,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2500
            )

            return competitive_json

        except Exception as e:
            logger.error(f"Competitive analysis generation failed: {e}")
            return None

    async def _generate_market_trends_with_llm(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate market trends synthesis using LLM"""
        try:
            # Generate prompt
            prompt = prompts.generate_market_trends_prompt(market_data)

            # Call LLM
            trends_json = await self.llm_service.generate_json(
                prompt=prompt,
                task_type=LLMTaskType.ANALYSIS,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2500
            )

            return trends_json

        except Exception as e:
            logger.error(f"Market trends generation failed: {e}")
            raise

    async def generate_swot_streaming(
        self,
        market_data: Dict[str, Any]
    ):
        """
        Generate SWOT analysis with streaming (for real-time UI updates)

        Yields:
            Text chunks as they are generated
        """
        try:
            # Generate prompt
            prompt = prompts.generate_swot_prompt(market_data)

            # Stream response
            async for chunk in self.llm_service.generate_stream(
                prompt=prompt,
                task_type=LLMTaskType.ANALYSIS,
                system_prompt=prompts.SYSTEM_PROMPT,
                temperature=0.3
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Streaming SWOT generation failed: {e}")
            raise

    async def analyze_property_image(
        self,
        image_path: str,
        analysis_type: str = "esg"
    ) -> Dict[str, Any]:
        """
        Analyze property image for ESG factors or condition assessment

        Args:
            image_path: Path to property image
            analysis_type: Type of analysis (esg, condition, amenities)

        Returns:
            Analysis results
        """
        try:
            if analysis_type == "esg":
                prompt = """Analyze this property image for ESG (Environmental, Social, Governance) factors:

**Environmental (0-100):**
- Energy efficiency indicators (solar panels, insulation quality, window types)
- Landscaping sustainability (native plants, water conservation)
- Stormwater management (permeable surfaces, rain gardens)
- Visible climate risks (flooding potential, wildfire proximity)

**Social (0-100):**
- Curb appeal and community integration
- Accessibility features (ramps, wide doorways)
- Safety indicators (lighting, security features)
- Neighborhood character and walkability

**Governance (0-100):**
- Property maintenance quality
- Building code compliance indicators
- Overall property upkeep standards

Provide scores for each dimension and explain your reasoning with specific visual evidence."""

            elif analysis_type == "condition":
                prompt = """Assess the physical condition of this property:

**Exterior Condition:**
- Roof condition
- Siding/facade quality
- Windows and doors
- Landscaping maintenance

**Maintenance Level:**
- Overall upkeep (Excellent/Good/Fair/Poor)
- Deferred maintenance indicators
- Recent improvements visible

**Estimated Condition Score (0-100):**
- Provide a quantitative score
- List specific issues requiring attention
- Estimate repair/improvement costs

Be specific about what you observe in the image."""

            else:
                prompt = f"Analyze this property image for: {analysis_type}"

            # Analyze image
            analysis_text = await self.llm_service.analyze_image(
                image_path=image_path,
                prompt=prompt,
                system_prompt="You are a professional property inspector with expertise in real estate valuation and ESG assessment."
            )

            return {
                "analysis": analysis_text,
                "image_path": image_path,
                "analysis_type": analysis_type
            }

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise

    def _extract_opportunities_from_swot(
        self,
        swot_analysis: Dict[str, Any]
    ) -> list:
        """Extract formatted opportunities from SWOT analysis"""
        opportunities = swot_analysis.get("opportunities", [])

        return [
            {
                "opportunity": opp.get("title"),
                "description": opp.get("description"),
                "impact": opp.get("impact", "Medium")
            }
            for opp in opportunities
        ]

    def _generate_fallback_insights(
        self,
        property_data: Dict[str, Any],
        market_intelligence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate simple rule-based insights as fallback
        (Used when LLM is unavailable)
        """
        logger.warning("Using fallback rule-based insights (LLM unavailable)")

        location = market_intelligence.get("location_intelligence", {})
        esg = market_intelligence.get("esg_assessment", {})
        forecasts = market_intelligence.get("forecasts", {})

        # Simple SWOT
        strengths = []
        if location.get("walk_score", 0) >= 70:
            strengths.append({"title": "High Walkability", "description": "Excellent pedestrian access", "impact": "High"})
        if esg.get("composite_esg_score", 0) >= 75:
            strengths.append({"title": "Strong ESG Profile", "description": "Low environmental and social risk", "impact": "High"})

        weaknesses = []
        if esg.get("composite_esg_score", 0) < 50:
            weaknesses.append({"title": "ESG Concerns", "description": "Below-average ESG performance", "impact": "Medium"})

        opportunities = []
        if forecasts.get("rent_growth_percentage", 0) > 4:
            opportunities.append({"title": "Strong Rent Growth", "description": "Market fundamentals support rent increases", "impact": "High"})

        threats = []
        economic = market_intelligence.get("economic_indicators", {})
        if economic.get("unemployment_rate", 0) > 6:
            threats.append({"title": "Economic Headwinds", "description": "Elevated unemployment may pressure demand", "impact": "Medium"})

        return {
            "swot_analysis": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "opportunities": opportunities,
                "threats": threats
            },
            "investment_recommendation": "REVIEW",
            "confidence": 50,
            "rationale": "Automated analysis. LLM service unavailable for detailed insights.",
            "generated_by": "fallback_rules"
        }


# Singleton instance
_ai_service: Optional[MarketIntelligenceAIService] = None


def get_market_intelligence_ai_service() -> MarketIntelligenceAIService:
    """Get or create AI service singleton"""
    global _ai_service

    if _ai_service is None:
        _ai_service = MarketIntelligenceAIService()

    return _ai_service
