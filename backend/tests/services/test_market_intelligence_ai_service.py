import json

from app.services.market_intelligence_ai_service import MarketIntelligenceAIService


def test_normalize_swot_analysis_coerces_items_to_strings():
    service = MarketIntelligenceAIService()
    swot = {
        "strengths": [{"title": "Transit Access", "description": "Strong commuter network"}],
        "weaknesses": ["High vacancy"],
        "opportunities": [{"opportunity": "Rent upside", "description": "Below-market rents"}],
        "threats": [{"category": "Supply", "detail": "New deliveries incoming"}],
    }

    normalized = service._normalize_swot_analysis(swot)

    assert normalized["strengths"] == ["Transit Access: Strong commuter network"]
    assert normalized["weaknesses"] == ["High vacancy"]
    assert normalized["opportunities"] == ["Rent upside: Below-market rents"]
    assert normalized["threats"] == ["Supply: New deliveries incoming"]


def test_extract_opportunities_from_swot_returns_strings():
    service = MarketIntelligenceAIService()
    swot = {"opportunities": [{"title": "Amenity upgrade", "description": "Modernize common areas"}]}

    opportunities = service._extract_opportunities_from_swot(swot)

    assert opportunities == ["Amenity upgrade: Modernize common areas"]


def test_generate_fallback_insights_structure():
    service = MarketIntelligenceAIService()
    market_intelligence = {
        "location_intelligence": {"walk_score": 80},
        "esg_assessment": {"composite_esg_score": 45},
        "forecasts": {"rent_growth_percentage": 3},
        "economic_indicators": {"unemployment_rate": 7},
    }

    insights = service._generate_fallback_insights({}, market_intelligence)

    assert isinstance(insights["swot_analysis"]["weaknesses"], list)
    assert all(isinstance(item, str) for item in insights["swot_analysis"]["weaknesses"])
    assert "investment_recommendation" in insights
    assert isinstance(insights["investment_recommendation"], dict)
    assert isinstance(insights["risk_assessment"], str)
    assert isinstance(insights["opportunities"], list)
    assert isinstance(insights["market_trend_synthesis"], str)
    assert insights["generated_by"] == "fallback_rules"
