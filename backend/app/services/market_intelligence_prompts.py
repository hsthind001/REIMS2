"""
Prompt Engineering for Market Intelligence AI Insights
Uses structured prompts for consistent, high-quality output

Author: REIMS Development Team
Date: 2025-01-09
"""

from typing import Dict, Any, Optional


def _extract_data(market_data_item: Any) -> Dict:
    """
    Extract nested 'data' field from market intelligence items.
    Handles the structure: {data: {...}, lineage: {...}}

    Args:
        market_data_item: Market intelligence data item (may be dict with 'data' field or direct dict)

    Returns:
        Extracted data dictionary
    """
    if market_data_item is None:
        return {}
    if isinstance(market_data_item, dict):
        # If it has a 'data' key, extract it
        if 'data' in market_data_item:
            return market_data_item.get('data', {}) or {}
        # Otherwise return the dict itself
        return market_data_item
    return {}


def _safe_get(data: Dict, key: str, default=0, value_type=float):
    """
    Safely extract a primitive value from a dict, ensuring it's the correct type.
    Handles nested dicts and ensures f-string compatibility.

    Args:
        data: Dictionary to extract from
        key: Key to extract
        default: Default value if key not found or wrong type
        value_type: Expected type (float, int, str)

    Returns:
        Primitive value safe for f-string formatting
    """
    try:
        value = data.get(key, default)
        # If value is a dict, return default (can't format dict in f-string)
        if isinstance(value, dict):
            return default
        # If value is None, return default
        if value is None:
            return default
        # Try to convert to expected type
        if value_type == str:
            return str(value) if value else default
        elif value_type == float:
            return float(value) if value not in [None, '', {}] else default
        elif value_type == int:
            return int(value) if value not in [None, '', {}] else default
        return value
    except (ValueError, TypeError, AttributeError):
        return default


SYSTEM_PROMPT = """You are a senior real estate investment analyst with 20+ years of experience in commercial and multifamily real estate. You specialize in:

- Market intelligence and competitive analysis
- Financial modeling and underwriting
- Risk assessment and mitigation strategies
- Investment thesis development
- ESG (Environmental, Social, Governance) analysis

Your analysis should be:
- Data-driven and quantitative when possible
- Professional and institutional-grade
- Specific with dollar amounts, percentages, and metrics
- Actionable with clear recommendations
- Grounded in real estate market fundamentals

Always cite specific metrics from the provided data to support your conclusions."""


def generate_swot_prompt(market_data: Dict[str, Any]) -> str:
    """
    Generate prompt for SWOT analysis

    Args:
        market_data: Complete market intelligence data

    Returns:
        Formatted prompt string
    """
    property_code = market_data.get("property_code", "Unknown")

    # Extract key metrics - handle nested 'data' structure
    location = _extract_data(market_data.get("location_intelligence"))
    demographics = _extract_data(market_data.get("demographics"))
    economic = _extract_data(market_data.get("economic_indicators"))
    esg = _extract_data(market_data.get("esg_assessment"))
    forecasts = _extract_data(market_data.get("forecasts"))
    competitive = _extract_data(market_data.get("competitive_analysis"))

    walk_score = _safe_get(location, "walk_score", 0, float)
    transit_score = _safe_get(location, "transit_score", 0, float)
    bike_score = _safe_get(location, "bike_score", 0, float)

    median_income = _safe_get(demographics, "median_household_income", 0, int)
    population = _safe_get(demographics, "total_population", 0, int)
    college_educated = _safe_get(demographics, "college_educated_percentage", 0, float)

    gdp_growth = _safe_get(economic, "gdp_growth", 0, float)
    unemployment = _safe_get(economic, "unemployment_rate", 0, float)
    inflation = _safe_get(economic, "inflation_rate", 0, float)
    fed_funds_rate = _safe_get(economic, "federal_funds_rate", 0, float)

    # Handle ESG - check for nested structure first
    esg_composite_score = esg.get("composite_score", {})
    if isinstance(esg_composite_score, dict) and "overall" in esg_composite_score:
        esg_composite = _safe_get(esg_composite_score.get("overall", {}), "score", 0, float)
        esg_grade = _safe_get(esg_composite_score.get("overall", {}), "grade", "N/A", str)
    else:
        esg_composite = _safe_get(esg, "composite_esg_score", 0, float)
        esg_grade = _safe_get(esg, "esg_grade", "N/A", str)

    environmental_score = _safe_get(esg, "environmental_score", 0, float)
    social_score = _safe_get(esg, "social_score", 0, float)
    governance_score = _safe_get(esg, "governance_score", 0, float)

    rent_growth_forecast = _safe_get(forecasts, "rent_growth_percentage", 0, float)
    occupancy_forecast = _safe_get(forecasts, "occupancy_percentage", 0, float)
    cap_rate_forecast = _safe_get(forecasts, "cap_rate", 0, float)

    submarket = _safe_get(competitive, "submarket", "Unknown", str)
    market_position = _safe_get(competitive, "market_position", "Unknown", str)

    # Extract all remaining values safely
    nearby_restaurants = _safe_get(location, "nearby_restaurants", 0, int)
    nearby_grocery = _safe_get(location, "nearby_grocery", 0, int)
    nearby_schools = _safe_get(location, "nearby_schools", 0, int)
    total_housing_units = _safe_get(demographics, "total_housing_units", 0, int)
    mortgage_rate_30yr = _safe_get(economic, "mortgage_rate_30yr", 0, float)
    comparable_properties_count = _safe_get(competitive, "comparable_properties_count", 0, int)

    prompt = f"""Analyze the following market intelligence data for property {property_code} and generate a comprehensive SWOT analysis.

**PROPERTY OVERVIEW:**
- Property Code: {property_code}
- Submarket: {submarket}
- Market Position: {market_position}

**LOCATION INTELLIGENCE:**
- Walk Score: {walk_score}/100
- Transit Score: {transit_score}/100
- Bike Score: {bike_score}/100
- Nearby Amenities: {nearby_restaurants} restaurants, {nearby_grocery} grocery stores, {nearby_schools} schools

**DEMOGRAPHICS:**
- Total Population: {population:,}
- Median Household Income: ${median_income:,}
- College Educated: {college_educated:.1f}%
- Housing Units: {total_housing_units:,}

**ECONOMIC INDICATORS:**
- GDP Growth: {gdp_growth:.2f}%
- Unemployment Rate: {unemployment:.2f}%
- Inflation Rate (CPI): {inflation:.2f}%
- Federal Funds Rate: {fed_funds_rate:.2f}%
- 30-Year Mortgage Rate: {mortgage_rate_30yr:.2f}%

**ESG ASSESSMENT:**
- Composite ESG Score: {esg_composite}/100 (Grade: {esg_grade})
- Environmental Score: {environmental_score}/100
- Social Score: {social_score}/100
- Governance Score: {governance_score}/100

**FORECASTS (12-Month):**
- Projected Rent Growth: {rent_growth_forecast:.2f}%
- Projected Occupancy: {occupancy_forecast:.1f}%
- Projected Cap Rate: {cap_rate_forecast:.2f}%

**COMPETITIVE ANALYSIS:**
- Submarket: {submarket}
- Market Position: {market_position}
- Competitive Properties: {comparable_properties_count}

---

Generate a detailed SWOT analysis in the following JSON format:

{{
  "strengths": [
    {{
      "title": "Brief strength title",
      "description": "Detailed explanation with specific metrics",
      "impact": "High/Medium/Low"
    }}
  ],
  "weaknesses": [
    {{
      "title": "Brief weakness title",
      "description": "Detailed explanation with specific metrics",
      "impact": "High/Medium/Low"
    }}
  ],
  "opportunities": [
    {{
      "title": "Brief opportunity title",
      "description": "Detailed explanation with market timing and potential",
      "impact": "High/Medium/Low"
    }}
  ],
  "threats": [
    {{
      "title": "Brief threat title",
      "description": "Detailed explanation with risk quantification",
      "impact": "High/Medium/Low"
    }}
  ]
}}

**REQUIREMENTS:**
1. Identify 4-6 items per category (Strengths, Weaknesses, Opportunities, Threats)
2. Each item must reference specific metrics from the data above
3. Prioritize items by impact (include at least 2 High impact items per category)
4. For Opportunities, suggest specific actions or strategies
5. For Threats, quantify the risk level and potential financial impact
6. Use professional real estate terminology
7. Be specific - avoid generic statements

Respond ONLY with the JSON object. No markdown formatting, no explanations."""

    return prompt


def generate_investment_recommendation_prompt(
    market_data: Dict[str, Any],
    swot_analysis: Dict[str, Any]
) -> str:
    """
    Generate prompt for investment recommendation narrative

    Args:
        market_data: Complete market intelligence data
        swot_analysis: Previously generated SWOT analysis

    Returns:
        Formatted prompt string
    """
    property_code = market_data.get("property_code", "Unknown")

    # Calculate key metrics
    strengths_count = len(swot_analysis.get("strengths", []))
    weaknesses_count = len(swot_analysis.get("weaknesses", []))
    opportunities_count = len(swot_analysis.get("opportunities", []))
    threats_count = len(swot_analysis.get("threats", []))

    forecasts = _extract_data(market_data.get("forecasts"))
    esg = _extract_data(market_data.get("esg_assessment"))
    location = _extract_data(market_data.get("location_intelligence"))

    # Extract values safely
    rent_growth = _safe_get(forecasts, "rent_growth_percentage", 0, float)
    cap_rate = _safe_get(forecasts, "cap_rate", 0, float)
    esg_score = _safe_get(esg, "composite_esg_score", 0, float)
    location_score = _safe_get(location, "walk_score", 0, float)

    prompt = f"""Based on the comprehensive market intelligence for property {property_code}, generate a detailed investment recommendation.

**SWOT SUMMARY:**
- Strengths: {strengths_count} identified
- Weaknesses: {weaknesses_count} identified
- Opportunities: {opportunities_count} identified
- Threats: {threats_count} identified

**SWOT ANALYSIS:**
Strengths: {', '.join([s if isinstance(s, str) else s.get('title', str(s)) for s in swot_analysis.get('strengths', [])])}
Weaknesses: {', '.join([w if isinstance(w, str) else w.get('title', str(w)) for w in swot_analysis.get('weaknesses', [])])}
Opportunities: {', '.join([o if isinstance(o, str) else o.get('title', str(o)) for o in swot_analysis.get('opportunities', [])])}
Threats: {', '.join([t if isinstance(t, str) else t.get('title', str(t)) for t in swot_analysis.get('threats', [])])}

**KEY METRICS:**
- Projected Rent Growth: {rent_growth:.2f}%
- Projected Cap Rate: {cap_rate:.2f}%
- ESG Score: {esg_score}/100
- Location Score: {location_score}/100

---

Generate an investment recommendation in the following JSON format:

{{
  "recommendation": "BUY|HOLD|SELL|REVIEW",
  "confidence": 85,
  "rationale": "3-4 paragraph investment thesis explaining the recommendation. Include:\n- Summary of key findings from SWOT\n- Financial justification with specific metrics\n- Risk assessment and mitigation strategies\n- Expected return scenarios (base case, bull case, bear case)\n- Recommended holding period",
  "priority": "High|Medium|Low",
  "key_risks": [
    "Specific risk 1 with quantification",
    "Specific risk 2 with quantification",
    "Specific risk 3 with quantification"
  ],
  "risk_mitigation_strategies": [
    "Actionable mitigation strategy 1",
    "Actionable mitigation strategy 2",
    "Actionable mitigation strategy 3"
  ],
  "expected_return_scenarios": {{
    "base_case": {{
      "description": "Most likely scenario",
      "irr": 12.5,
      "cash_on_cash": 8.2,
      "holding_period_years": 5
    }},
    "bull_case": {{
      "description": "Optimistic scenario if opportunities realized",
      "irr": 18.3,
      "cash_on_cash": 11.5,
      "holding_period_years": 5
    }},
    "bear_case": {{
      "description": "Downside scenario if risks materialize",
      "irr": 6.8,
      "cash_on_cash": 4.5,
      "holding_period_years": 5
    }}
  }},
  "optimal_holding_period": 5,
  "action_items": [
    "Immediate action item 1",
    "Near-term action item 2",
    "Strategic action item 3"
  ]
}}

**REQUIREMENTS:**
1. Recommendation must be one of: BUY, HOLD, SELL, or REVIEW
2. Confidence should be 0-100 (consider data quality and market volatility)
3. Rationale should be 3-4 paragraphs, institutional-grade writing
4. Expected returns should be realistic based on market data
5. Include specific dollar amounts or percentages where possible
6. Action items should be concrete and time-bound
7. Risk assessment must reference specific SWOT threats

**DECISION CRITERIA:**
- BUY: Strong fundamentals, 3+ high-impact opportunities, IRR > 12%
- HOLD: Balanced position, stable fundamentals, minor headwinds
- SELL: Significant threats, deteriorating fundamentals, IRR < 8%
- REVIEW: Insufficient data or major uncertainties requiring further analysis

Respond ONLY with the JSON object. No markdown formatting."""

    return prompt


def generate_risk_assessment_prompt(
    market_data: Dict[str, Any],
    swot_analysis: Dict[str, Any]
) -> str:
    """
    Generate prompt for detailed risk assessment

    Args:
        market_data: Complete market intelligence data
        swot_analysis: Previously generated SWOT analysis

    Returns:
        Formatted prompt string
    """
    property_code = market_data.get("property_code", "Unknown")
    esg = _extract_data(market_data.get("esg_assessment"))
    economic = _extract_data(market_data.get("economic_indicators"))
    forecasts = _extract_data(market_data.get("forecasts"))

    threats = swot_analysis.get("threats", [])
    threats_text = '\n'.join([f"- {t}" for t in threats]) if threats else "- No major threats identified"

    # Extract values safely
    env_score = _safe_get(esg, "environmental_score", 0, float)
    social_score = _safe_get(esg, "social_score", 0, float)
    gov_score = _safe_get(esg, "governance_score", 0, float)
    esg_grade = _safe_get(esg, "esg_grade", "N/A", str)
    unemployment = _safe_get(economic, "unemployment_rate", 0, float)
    inflation = _safe_get(economic, "inflation_rate", 0, float)
    recession_prob = _safe_get(economic, "recession_probability", 0, float)
    rent_growth = _safe_get(forecasts, "rent_growth_percentage", 0, float)
    occupancy = _safe_get(forecasts, "occupancy_percentage", 0, float)

    prompt = f"""Analyze the risk profile for property {property_code} based on the market intelligence and SWOT analysis.

**IDENTIFIED THREATS:**
{threats_text}

**ESG RISK FACTORS:**
- Environmental Score: {env_score}/100
- Social Score: {social_score}/100
- Governance Score: {gov_score}/100
- Overall ESG Grade: {esg_grade}

**ECONOMIC RISK INDICATORS:**
- Unemployment Rate: {unemployment:.2f}%
- Inflation Rate: {inflation:.2f}%
- Recession Probability: {recession_prob:.2f}%

**FORECAST RISKS:**
- Projected Rent Growth: {rent_growth:.2f}%
- Projected Occupancy: {occupancy:.1f}%

---

Generate a comprehensive risk assessment in the following JSON format:

{{
  "overall_risk_score": 65,
  "risk_level": "High|Medium|Low",
  "narrative": "3-paragraph risk assessment covering:\n- Overall risk profile and key concerns\n- Quantification of potential financial impact\n- Comparison to market benchmarks",
  "risk_categories": [
    {{
      "category": "Environmental Risk",
      "score": 45,
      "factors": ["Factor 1", "Factor 2"],
      "impact": "Potential financial impact description"
    }},
    {{
      "category": "Market Risk",
      "score": 70,
      "factors": ["Factor 1", "Factor 2"],
      "impact": "Potential financial impact description"
    }},
    {{
      "category": "Financial Risk",
      "score": 60,
      "factors": ["Factor 1", "Factor 2"],
      "impact": "Potential financial impact description"
    }}
  ],
  "mitigation_plan": [
    {{
      "risk": "Specific risk",
      "strategy": "Detailed mitigation strategy",
      "cost_estimate": 50000,
      "timeline": "Implementation timeline"
    }}
  ]
}}

**REQUIREMENTS:**
1. Overall risk score: 0-100 (0 = no risk, 100 = extreme risk)
2. Risk level: High (>70), Medium (40-70), Low (<40)
3. Identify 4-6 risk categories
4. Quantify financial impact in dollars where possible
5. Provide actionable mitigation strategies
6. Include cost estimates for risk mitigation

Respond ONLY with the JSON object."""

    return prompt


def generate_competitive_analysis_prompt(
    market_data: Dict[str, Any],
    property_metrics: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate prompt for competitive intelligence analysis

    Args:
        market_data: Complete market intelligence data
        property_metrics: Optional property-specific metrics (rent, occupancy, etc.)

    Returns:
        Formatted prompt string
    """
    property_code = market_data.get("property_code", "Unknown")
    competitive = _extract_data(market_data.get("competitive_analysis"))
    location = _extract_data(market_data.get("location_intelligence"))

    # Property metrics (if available)
    current_rent = property_metrics.get("current_rent_psf", 0) if property_metrics else 0
    current_occupancy = property_metrics.get("current_occupancy", 0) if property_metrics else 0

    # Extract competitive/location values safely
    walk_score = _safe_get(location, "walk_score", 0, float)
    nearby_rest = _safe_get(location, "nearby_restaurants", 0, int)
    nearby_grocery = _safe_get(location, "nearby_grocery", 0, int)
    submarket = _safe_get(competitive, "submarket", "Unknown", str)
    market_pos = _safe_get(competitive, "market_position", "Unknown", str)
    comp_count = _safe_get(competitive, "comparable_properties_count", 0, int)
    submarket_rent = _safe_get(competitive, "submarket_avg_rent_psf", 0, float)
    submarket_occ = _safe_get(competitive, "submarket_avg_occupancy", 0, float)

    prompt = f"""Analyze the competitive positioning for property {property_code} in the {submarket} submarket.

**YOUR PROPERTY:**
- Property Code: {property_code}
- Current Rent: ${current_rent:.2f}/SF/month
- Current Occupancy: {current_occupancy:.1f}%
- Walk Score: {walk_score}/100
- Amenities: {nearby_rest} restaurants, {nearby_grocery} grocery stores

**MARKET CONTEXT:**
- Submarket: {submarket}
- Market Position: {market_pos}
- Comparable Properties: {comp_count}
- Submarket Average Rent: ${submarket_rent:.2f}/SF/month
- Submarket Average Occupancy: {submarket_occ:.1f}%

---

Generate a competitive intelligence analysis in the following JSON format:

{{
  "positioning_summary": "2-3 sentence summary of competitive position (premium/mid-tier/value)",
  "differentiation_factors": [
    {{
      "factor": "Differentiation factor name",
      "description": "How this differentiates from competitors",
      "competitive_advantage": true
    }}
  ],
  "competitive_threats": [
    {{
      "competitor": "Competitor name or type",
      "threat_level": "High|Medium|Low",
      "description": "Specific threat description",
      "market_share_risk": "Estimated market share at risk"
    }}
  ],
  "pricing_power_analysis": {{
    "current_position": "Above/At/Below market average",
    "pricing_flexibility": "High|Medium|Low",
    "rent_growth_potential": 4.5,
    "rationale": "Explanation of pricing power"
  }},
  "strategic_recommendations": [
    {{
      "strategy": "Strategy name",
      "description": "Detailed implementation plan",
      "expected_impact": "Quantified expected impact",
      "investment_required": 100000,
      "timeline": "Implementation timeline"
    }}
  ]
}}

**REQUIREMENTS:**
1. Assess positioning relative to submarket average
2. Identify 3-5 differentiation factors
3. List 2-4 competitive threats with quantified risk
4. Provide pricing power analysis with specific percentages
5. Suggest 3-5 strategic recommendations with ROI estimates

Respond ONLY with the JSON object."""

    return prompt


def generate_market_trends_prompt(
    market_data: Dict[str, Any],
    historical_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate prompt for market trend synthesis

    Args:
        market_data: Complete market intelligence data
        historical_data: Optional historical market data

    Returns:
        Formatted prompt string
    """
    property_code = market_data.get("property_code", "Unknown")
    economic = _extract_data(market_data.get("economic_indicators"))
    demographics = _extract_data(market_data.get("demographics"))
    forecasts = _extract_data(market_data.get("forecasts"))

    gdp_growth = _safe_get(economic, 'gdp_growth', 0, float)
    unemployment_rate = _safe_get(economic, 'unemployment_rate', 0, float)
    inflation_rate = _safe_get(economic, 'inflation_rate', 0, float)
    federal_funds_rate = _safe_get(economic, 'federal_funds_rate', 0, float)
    recession_probability = _safe_get(economic, 'recession_probability', 0, float)

    total_population = _safe_get(demographics, 'total_population', 0, int)
    median_income = _safe_get(demographics, 'median_household_income', 0, int)
    college_educated = _safe_get(demographics, 'college_educated_percentage', 0, float)

    rent_growth = _safe_get(forecasts, 'rent_growth_percentage', 0, float)
    occupancy = _safe_get(forecasts, 'occupancy_percentage', 0, float)
    cap_rate = _safe_get(forecasts, 'cap_rate', 0, float)

    prompt = f"""Synthesize market trends for property {property_code} based on current and historical data.

**CURRENT ECONOMIC CONDITIONS:**
- GDP Growth: {gdp_growth:.2f}%
- Unemployment: {unemployment_rate:.2f}%
- Inflation: {inflation_rate:.2f}%
- Federal Funds Rate: {federal_funds_rate:.2f}%
- Recession Probability: {recession_probability:.2f}%

**DEMOGRAPHIC TRENDS:**
- Population: {total_population:,}
- Median Income: ${median_income:,}
- College Educated: {college_educated:.1f}%

**FORECASTS:**
- Projected Rent Growth: {rent_growth:.2f}%
- Projected Occupancy: {occupancy:.1f}%
- Projected Cap Rate: {cap_rate:.2f}%

---

Generate a market trends synthesis in the following JSON format:

{{
  "executive_summary": "2-3 paragraph synthesis of key market trends",
  "macro_trends": [
    {{
      "trend": "Trend name",
      "direction": "Improving|Stable|Deteriorating",
      "impact_on_property": "Specific impact description",
      "confidence": 85
    }}
  ],
  "local_market_dynamics": [
    {{
      "dynamic": "Local market factor",
      "description": "Detailed explanation",
      "opportunity_or_threat": "Opportunity|Threat"
    }}
  ],
  "demand_drivers": [
    "Demand driver 1",
    "Demand driver 2",
    "Demand driver 3"
  ],
  "supply_constraints": [
    "Supply constraint 1",
    "Supply constraint 2"
  ],
  "outlook": {{
    "timeframe": "12-month",
    "sentiment": "Bullish|Neutral|Bearish",
    "key_catalysts": ["Catalyst 1", "Catalyst 2"],
    "key_risks": ["Risk 1", "Risk 2"]
  }}
}}

**REQUIREMENTS:**
1. Synthesize macro trends with local market context
2. Identify 4-6 macro trends
3. Highlight 3-5 local market dynamics
4. List demand drivers and supply constraints
5. Provide 12-month outlook with sentiment

Respond ONLY with the JSON object."""

    return prompt
