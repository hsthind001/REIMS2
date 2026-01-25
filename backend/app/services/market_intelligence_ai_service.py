"""
AI-Enhanced Market Intelligence Service using Open-Source LLMs

Replaces rule-based insights with LLM-generated analysis using:
- Ollama (local inference, 100% free)
- Groq (cloud fallback, very low cost)
- Structured prompts for consistent output

Author: REIMS Development Team
Date: 2025-01-09
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
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
        self.llm_timeout_sec = self._get_llm_timeout()
        self.prefer_fast = self._get_prefer_fast()
        logger.info("Initialized MarketIntelligenceAIService with local LLM")

    def _get_llm_timeout(self) -> int:
        raw = os.getenv("AI_INSIGHTS_LLM_TIMEOUT_SEC") or os.getenv("LLM_TIMEOUT_SEC")
        if raw:
            try:
                return max(10, int(raw))
            except ValueError:
                logger.warning(f"Invalid LLM timeout value: {raw}")
        return 90

    def _get_prefer_fast(self) -> bool:
        raw = os.getenv("AI_INSIGHTS_PREFER_FAST", "")
        return raw.strip().lower() in {"1", "true", "yes", "y"}

    def _get_max_tokens(self, default_tokens: int) -> int:
        raw = os.getenv("AI_INSIGHTS_MAX_TOKENS")
        if raw:
            try:
                return max(256, int(raw))
            except ValueError:
                logger.warning(f"Invalid AI insights max token override: {raw}")
        return default_tokens

    async def _safe_generate_json(
        self,
        *,
        label: str,
        prompt: str,
        task_type: LLMTaskType,
        temperature: float,
        max_tokens: int
    ) -> Optional[Dict[str, Any]]:
        """Safely generate JSON from LLM with timeout + error handling."""
        timeout = self.llm_timeout_sec
        try:
            return await asyncio.wait_for(
                self.llm_service.generate_json(
                    prompt=prompt,
                    task_type=task_type,
                    system_prompt=prompts.SYSTEM_PROMPT,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    prefer_fast=self.prefer_fast,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"{label} timed out after {timeout}s")
        except Exception as e:
            logger.error(f"{label} failed: {e}")
        return None

    def _record_llm_usage(self, models_used: set[str], providers_used: set[str]) -> None:
        model = getattr(self.llm_service, "last_model_used", None)
        provider = getattr(self.llm_service, "last_provider", None)
        if model:
            models_used.add(str(model))
        if provider:
            providers_used.add(provider.value if hasattr(provider, "value") else str(provider))

    def _swot_item_to_text(self, item: Any) -> str:
        if isinstance(item, dict):
            title = item.get("title") or item.get("name") or item.get("opportunity") or item.get("category")
            description = item.get("description") or item.get("detail")
            if title and description:
                return f"{title}: {description}"
            return title or description or json.dumps(item)
        return str(item)

    def _extract_data_item(self, item: Any) -> Dict[str, Any]:
        """Extract nested data payloads from tagged market intelligence structures."""
        if item is None:
            return {}
        if isinstance(item, dict) and "data" in item:
            return item.get("data", {}) or {}
        if isinstance(item, dict):
            return item
        return {}

    def _compute_data_coverage(self, market_intelligence: Dict[str, Any]) -> Dict[str, Any]:
        """Compute data coverage for AI insights."""
        categories = [
            "demographics",
            "economic_indicators",
            "location_intelligence",
            "esg_assessment",
            "forecasts",
            "competitive_analysis",
        ]
        present: List[str] = []
        missing: List[str] = []
        for key in categories:
            data = self._extract_data_item(market_intelligence.get(key))
            if data:
                present.append(key)
            else:
                missing.append(key)
        coverage_ratio = round(len(present) / len(categories), 2) if categories else 0.0
        return {
            "coverage_ratio": coverage_ratio,
            "coverage_percent": int(coverage_ratio * 100),
            "present": present,
            "missing": missing,
        }

    def _normalize_swot_analysis(self, swot_analysis: Dict[str, Any]) -> Dict[str, list]:
        normalized = {}
        for key in ("strengths", "weaknesses", "opportunities", "threats"):
            items = swot_analysis.get(key, [])
            normalized[key] = [self._swot_item_to_text(item) for item in items if item]
        return normalized

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
        if not use_local_llm:
            logger.info("use_local_llm disabled; LLM provider config will be honored.")

        try:
            models_used: set[str] = set()
            providers_used: set[str] = set()
            llm_sections_used: set[str] = set()
            fallback_sections_used: set[str] = set()
            coverage = self._compute_data_coverage(market_intelligence)

            # Prepare market data for prompts
            market_data = {
                "property_code": property_data.get("property_code"),
                **market_intelligence
            }

            fallback_insights = self._generate_fallback_insights(property_data, market_intelligence)
            fallback_swot = fallback_insights.get("swot_analysis", {})
            fallback_recommendation = fallback_insights.get("investment_recommendation", {})
            fallback_risk = {
                "narrative": fallback_insights.get("risk_assessment"),
                "overall_risk_score": fallback_insights.get("overall_risk_score"),
                "risk_level": fallback_insights.get("risk_level"),
                "risk_categories": fallback_insights.get("risk_categories", []),
            }
            fallback_trends = {
                "executive_summary": fallback_insights.get("market_trend_synthesis"),
                "demand_drivers": fallback_insights.get("demand_drivers", []),
                "supply_constraints": fallback_insights.get("supply_constraints", []),
            }

            # Step 1: Generate SWOT Analysis
            logger.info("Generating SWOT analysis with LLM...")
            swot_candidate = await self._generate_swot_with_llm(market_data)
            if swot_candidate:
                swot_analysis = self._normalize_swot_analysis(swot_candidate)
                self._record_llm_usage(models_used, providers_used)
                llm_sections_used.add("swot")
            else:
                swot_analysis = fallback_swot
                fallback_sections_used.add("swot")

            # Step 2: Generate Investment Recommendation
            logger.info("Generating investment recommendation...")
            recommendation = await self._generate_recommendation_with_llm(
                market_data,
                swot_analysis
            )
            if recommendation:
                self._record_llm_usage(models_used, providers_used)
                llm_sections_used.add("recommendation")
                recommendation_payload = recommendation
            else:
                fallback_sections_used.add("recommendation")
                recommendation_payload = fallback_recommendation or {}

            # Step 3: Generate Risk Assessment
            logger.info("Generating risk assessment...")
            risk_assessment = await self._generate_risk_assessment_with_llm(
                market_data,
                swot_analysis
            )
            if risk_assessment:
                self._record_llm_usage(models_used, providers_used)
                llm_sections_used.add("risk")
            else:
                fallback_sections_used.add("risk")
                risk_assessment = fallback_risk

            # Step 4: Generate Competitive Analysis (if data available)
            competitive_analysis = None
            if market_intelligence.get("competitive_analysis"):
                logger.info("Generating competitive analysis...")
                competitive_analysis = await self._generate_competitive_analysis_with_llm(
                    market_data,
                    property_data
                )
                if competitive_analysis:
                    self._record_llm_usage(models_used, providers_used)
                    llm_sections_used.add("competitive")
                else:
                    fallback_sections_used.add("competitive")

            # Step 5: Generate Market Trends Synthesis
            logger.info("Generating market trends synthesis...")
            market_trends = await self._generate_market_trends_with_llm(market_data)
            if market_trends:
                self._record_llm_usage(models_used, providers_used)
                llm_sections_used.add("trends")
            else:
                fallback_sections_used.add("trends")
                market_trends = fallback_trends

            # Combine all insights
            rec_action = recommendation_payload.get("recommendation") or "REVIEW"
            key_factors = recommendation_payload.get("key_factors")
            if not key_factors:
                strengths = swot_analysis.get("strengths", [])
                weaknesses = swot_analysis.get("weaknesses", [])
                opportunities = swot_analysis.get("opportunities", [])
                threats = swot_analysis.get("threats", [])
                if rec_action == "BUY":
                    key_factors = (strengths + opportunities)[:4]
                elif rec_action == "SELL":
                    key_factors = (threats + weaknesses)[:4]
                else:
                    key_factors = (strengths + weaknesses)[:4]

            if llm_sections_used and fallback_sections_used:
                generated_by = "hybrid_llm_fallback"
            elif llm_sections_used:
                generated_by = "local_llm"
            else:
                generated_by = "fallback_rules"

            ai_insights = {
                "swot_analysis": swot_analysis,
                "investment_recommendation": {
                    "recommendation": rec_action,
                    "confidence_score": recommendation_payload.get("confidence")
                    or recommendation_payload.get("confidence_score")
                    or 0,
                    "rationale": recommendation_payload.get("rationale") or "",
                    "key_factors": key_factors or [],
                },
                "confidence": recommendation_payload.get("confidence")
                or recommendation_payload.get("confidence_score"),
                "rationale": recommendation_payload.get("rationale"),
                "priority": recommendation_payload.get("priority"),
                "key_risks": recommendation_payload.get("key_risks", []),
                "risk_mitigation_strategies": recommendation_payload.get("risk_mitigation_strategies", []),
                "expected_return_scenarios": recommendation_payload.get("expected_return_scenarios", {}),
                "optimal_holding_period": recommendation_payload.get("optimal_holding_period"),
                "action_items": recommendation_payload.get("action_items", []),
                "risk_assessment": risk_assessment.get("narrative"),
                "overall_risk_score": risk_assessment.get("overall_risk_score"),
                "risk_level": risk_assessment.get("risk_level"),
                "risk_categories": risk_assessment.get("risk_categories", []),
                "opportunities": self._extract_opportunities_from_swot(swot_analysis),
                "market_trend_synthesis": market_trends.get("executive_summary"),
                "demand_drivers": market_trends.get("demand_drivers", []),
                "supply_constraints": market_trends.get("supply_constraints", []),
                "competitive_intelligence": competitive_analysis,
                "generated_by": generated_by,
                "model_used": ", ".join(sorted(models_used)) if llm_sections_used else None,
                "provider_used": ", ".join(sorted(providers_used)) if llm_sections_used else None,
                "data_coverage": coverage,
                "generated_at": datetime.utcnow().isoformat()
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
    ) -> Optional[Dict[str, Any]]:
        """Generate SWOT analysis using LLM"""
        # Generate prompt
        prompt = prompts.generate_swot_prompt(market_data)

        # Call LLM
        return await self._safe_generate_json(
            label="SWOT generation",
            prompt=prompt,
            task_type=LLMTaskType.ANALYSIS,
            temperature=0.3,
            max_tokens=self._get_max_tokens(1800),
        )

    async def _generate_recommendation_with_llm(
        self,
        market_data: Dict[str, Any],
        swot_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate investment recommendation using LLM"""
        # Generate prompt
        prompt = prompts.generate_investment_recommendation_prompt(
            market_data,
            swot_analysis
        )

        # Call LLM
        return await self._safe_generate_json(
            label="Recommendation generation",
            prompt=prompt,
            task_type=LLMTaskType.NARRATIVE,
            temperature=0.4,
            max_tokens=self._get_max_tokens(2000),
        )

    async def _generate_risk_assessment_with_llm(
        self,
        market_data: Dict[str, Any],
        swot_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate risk assessment using LLM"""
        # Generate prompt
        prompt = prompts.generate_risk_assessment_prompt(
            market_data,
            swot_analysis
        )

        # Call LLM
        return await self._safe_generate_json(
            label="Risk assessment generation",
            prompt=prompt,
            task_type=LLMTaskType.ANALYSIS,
            temperature=0.3,
            max_tokens=self._get_max_tokens(1600),
        )

    async def _generate_competitive_analysis_with_llm(
        self,
        market_data: Dict[str, Any],
        property_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate competitive analysis using LLM"""
        # Generate prompt
        prompt = prompts.generate_competitive_analysis_prompt(
            market_data,
            property_data
        )

        # Call LLM
        return await self._safe_generate_json(
            label="Competitive analysis generation",
            prompt=prompt,
            task_type=LLMTaskType.ANALYSIS,
            temperature=0.3,
            max_tokens=self._get_max_tokens(1600),
        )

    async def _generate_market_trends_with_llm(
        self,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate market trends synthesis using LLM"""
        # Generate prompt
        prompt = prompts.generate_market_trends_prompt(market_data)

        # Call LLM
        return await self._safe_generate_json(
            label="Market trends generation",
            prompt=prompt,
            task_type=LLMTaskType.ANALYSIS,
            temperature=0.3,
            max_tokens=self._get_max_tokens(1400),
        )

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

        return [self._swot_item_to_text(opp) for opp in opportunities if opp]

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

        location = self._extract_data_item(market_intelligence.get("location_intelligence"))
        esg = self._extract_data_item(market_intelligence.get("esg_assessment"))
        forecasts = self._extract_data_item(market_intelligence.get("forecasts"))
        economic = self._extract_data_item(market_intelligence.get("economic_indicators"))
        demographics = self._extract_data_item(market_intelligence.get("demographics"))

        # Simple SWOT
        strengths = []
        amenities = location.get("amenities") or {}
        walk_score = location.get("walk_score", 0)
        if isinstance(walk_score, dict):
            walk_score = walk_score.get("value") or 0
        if (walk_score or 0) >= 70:
            strengths.append({"title": "High Walkability", "description": "Excellent pedestrian access", "impact": "High"})
        if (amenities.get("restaurants_1mi") or 0) >= 15:
            strengths.append({"title": "Amenity Density", "description": "Strong nearby amenity mix supports demand", "impact": "Medium"})
        esg_score = esg.get("composite_esg_score", 0)
        if isinstance(esg_score, dict):
            esg_score = esg_score.get("score") or esg_score.get("composite_score") or 0
        if (esg_score or 0) >= 75:
            strengths.append({"title": "Strong ESG Profile", "description": "Low environmental and social risk", "impact": "High"})

        weaknesses = []
        esg_score = esg.get("composite_esg_score", 0)
        if isinstance(esg_score, dict):
            esg_score = esg_score.get("score") or esg_score.get("composite_score") or 0
        if (esg_score or 0) < 50:
            weaknesses.append({"title": "ESG Concerns", "description": "Below-average ESG performance", "impact": "Medium"})
        unemployment_val = economic.get("unemployment_rate")
        if isinstance(unemployment_val, dict):
            unemployment_val = unemployment_val.get("value")
        if (unemployment_val or 0) > 6:
            weaknesses.append({"title": "Economic Softness", "description": "Elevated unemployment may pressure demand", "impact": "Medium"})

        opportunities = []
        rent_growth = forecasts.get("rent_growth_percentage")
        if rent_growth is None and isinstance(forecasts.get("rent_forecast_12mo"), dict):
            rent_growth = forecasts.get("rent_forecast_12mo", {}).get("change_pct")
        if (rent_growth or 0) > 4:
            opportunities.append({"title": "Strong Rent Growth", "description": "Market fundamentals support rent increases", "impact": "High"})
        income_val = demographics.get("median_household_income", 0)
        if isinstance(income_val, dict):
            income_val = income_val.get("value") or 0
        if (income_val or 0) > 75000:
            opportunities.append({"title": "Income Upside", "description": "Higher income base can support premium rents", "impact": "Medium"})

        threats = []
        unemployment_val = economic.get("unemployment_rate")
        if isinstance(unemployment_val, dict):
            unemployment_val = unemployment_val.get("value")
        if (unemployment_val or 0) > 6:
            threats.append({"title": "Economic Headwinds", "description": "Elevated unemployment may pressure demand", "impact": "Medium"})

        swot_analysis = self._normalize_swot_analysis({
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
        })

        opportunities_list = self._extract_opportunities_from_swot(swot_analysis)

        coverage = self._compute_data_coverage(market_intelligence)

        return {
            "swot_analysis": swot_analysis,
            "investment_recommendation": {
                "recommendation": "REVIEW",
                "confidence_score": max(35, coverage.get("coverage_percent", 50)),
                "rationale": "Automated analysis based on available data (LLM unavailable).",
                "key_factors": swot_analysis.get("weaknesses", [])[:2] or swot_analysis.get("strengths", [])[:2] or ["Limited data availability"],
            },
            "risk_assessment": "Risk assessment limited due to incomplete data sources.",
            "opportunities": opportunities_list,
            "market_trend_synthesis": "Market trend synthesis limited to available indicators.",
            "confidence": coverage.get("coverage_percent", 50),
            "rationale": "Automated analysis based on available data (LLM unavailable).",
            "generated_by": "fallback_rules",
            "data_coverage": coverage,
            "generated_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_ai_service: Optional[MarketIntelligenceAIService] = None


def get_market_intelligence_ai_service() -> MarketIntelligenceAIService:
    """Get or create AI service singleton"""
    global _ai_service

    if _ai_service is None:
        _ai_service = MarketIntelligenceAIService()

    return _ai_service
