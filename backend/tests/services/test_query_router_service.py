"""
Unit Tests for Query Router Service

Tests query complexity classification, routing decisions,
and performance requirements.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.query_router_service import QueryRouterService, QueryComplexity
from app.config.query_router_config import query_router_config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"complexity": "simple", "confidence": 0.95, "reasoning": "Direct question"}'
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestSimpleQueries:
    """Test simple query classification"""
    
    def test_simple_what_is_query(self):
        """Test simple 'what is' query"""
        service = QueryRouterService()
        
        result = service.route_query("What is NOI for Property X?", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.SIMPLE.value
        assert result['route'] == query_router_config.SIMPLE_ROUTE
        assert result['confidence'] >= query_router_config.SIMPLE_CONFIDENCE_THRESHOLD
    
    def test_simple_show_me_query(self):
        """Test simple 'show me' query"""
        service = QueryRouterService()
        
        result = service.route_query("Show me revenue in Q3", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.SIMPLE.value
        assert result['route'] == query_router_config.SIMPLE_ROUTE
    
    def test_simple_get_query(self):
        """Test simple 'get' query"""
        service = QueryRouterService()
        
        result = service.route_query("Get DSCR for Property 1", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.SIMPLE.value
        assert result['route'] == query_router_config.SIMPLE_ROUTE
    
    def test_simple_tell_me_query(self):
        """Test simple 'tell me' query"""
        service = QueryRouterService()
        
        result = service.route_query("Tell me the occupancy rate", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.SIMPLE.value
        assert result['route'] == query_router_config.SIMPLE_ROUTE


class TestMediumQueries:
    """Test medium query classification"""
    
    def test_medium_compare_query(self):
        """Test medium 'compare' query"""
        service = QueryRouterService()
        
        result = service.route_query("Compare revenue across properties", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.MEDIUM.value
        assert result['route'] == query_router_config.MEDIUM_ROUTE
        assert result['confidence'] >= query_router_config.MEDIUM_CONFIDENCE_THRESHOLD
    
    def test_medium_trend_query(self):
        """Test medium 'trend' query"""
        service = QueryRouterService()
        
        result = service.route_query("Show trends for all properties", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.MEDIUM.value
        assert result['route'] == query_router_config.MEDIUM_ROUTE
    
    def test_medium_all_properties_query(self):
        """Test medium 'all properties' query"""
        service = QueryRouterService()
        
        result = service.route_query("Show NOI for all properties", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.MEDIUM.value
        assert result['route'] == query_router_config.MEDIUM_ROUTE
    
    def test_medium_between_query(self):
        """Test medium 'between' query"""
        service = QueryRouterService()
        
        result = service.route_query("Compare DSCR between Q2 and Q3", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.MEDIUM.value
        assert result['route'] == query_router_config.MEDIUM_ROUTE


class TestComplexQueries:
    """Test complex query classification"""
    
    def test_complex_why_query(self):
        """Test complex 'why' query"""
        service = QueryRouterService()
        
        result = service.route_query("Why did NOI decrease for Property X?", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['route'] == query_router_config.COMPLEX_ROUTE
        assert result['confidence'] >= query_router_config.COMPLEX_CONFIDENCE_THRESHOLD
    
    def test_complex_how_query(self):
        """Test complex 'how' query"""
        service = QueryRouterService()
        
        result = service.route_query("How did vacancy affect revenue?", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['route'] == query_router_config.COMPLEX_ROUTE
    
    def test_complex_explain_query(self):
        """Test complex 'explain' query"""
        service = QueryRouterService()
        
        result = service.route_query("Explain why DSCR dropped", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['route'] == query_router_config.COMPLEX_ROUTE
    
    def test_complex_analyze_query(self):
        """Test complex 'analyze' query"""
        service = QueryRouterService()
        
        result = service.route_query("Analyze the impact of rent increases on NOI", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['route'] == query_router_config.COMPLEX_ROUTE
    
    def test_complex_predict_query(self):
        """Test complex 'predict' query"""
        service = QueryRouterService()
        
        result = service.route_query("Predict NOI for next quarter", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['route'] == query_router_config.COMPLEX_ROUTE


class TestLLMClassification:
    """Test LLM-based classification"""
    
    @patch('app.services.query_router_service.OpenAI')
    @patch('app.core.config.settings')
    def test_llm_classifies_simple(self, mock_settings, mock_openai_class, mock_openai_client):
        """Test LLM classification for simple query"""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_openai_class.return_value = mock_openai_client
        
        # Mock simple classification
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"complexity": "simple", "confidence": 0.95, "reasoning": "Direct question"}'
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        service = QueryRouterService()
        service.openai_client = mock_openai_client
        service.use_llm = True
        
        result = service.route_query("What is NOI?", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.SIMPLE.value
        assert result['method'] == 'llm'
        assert result['confidence'] == 0.95
    
    @patch('app.services.query_router_service.OpenAI')
    @patch('app.core.config.settings')
    def test_llm_classifies_complex(self, mock_settings, mock_openai_class, mock_openai_client):
        """Test LLM classification for complex query"""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_openai_class.return_value = mock_openai_client
        
        # Mock complex classification
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"complexity": "complex", "confidence": 0.92, "reasoning": "Why question requires reasoning"}'
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        service = QueryRouterService()
        service.openai_client = mock_openai_client
        service.use_llm = True
        
        result = service.route_query("Why did revenue decrease?", use_cache=False)
        
        assert result['complexity'] == QueryComplexity.COMPLEX.value
        assert result['method'] == 'llm'
        assert result['confidence'] == 0.92
    
    @patch('app.services.query_router_service.OpenAI')
    @patch('app.core.config.settings')
    def test_llm_fallback_to_rules(self, mock_settings, mock_openai_class, mock_openai_client):
        """Test LLM fallback to rules on error"""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_openai_class.return_value = mock_openai_client
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        service = QueryRouterService()
        service.openai_client = mock_openai_client
        service.use_llm = True
        
        result = service.route_query("What is NOI?", use_cache=False)
        
        # Should fall back to rules
        assert result['method'] in ['rules_simple', 'rules_default']
        assert 'complexity' in result


class TestRouting:
    """Test routing logic"""
    
    def test_simple_route_mapping(self):
        """Test that simple queries route to direct SQL"""
        service = QueryRouterService()
        
        result = service.route_query("What is NOI?", use_cache=False)
        
        assert result['route'] == query_router_config.SIMPLE_ROUTE
    
    def test_medium_route_mapping(self):
        """Test that medium queries route to hybrid RAG + SQL"""
        service = QueryRouterService()
        
        result = service.route_query("Compare revenue across properties", use_cache=False)
        
        assert result['route'] == query_router_config.MEDIUM_ROUTE
    
    def test_complex_route_mapping(self):
        """Test that complex queries route to multi-step reasoning"""
        service = QueryRouterService()
        
        result = service.route_query("Why did NOI decrease?", use_cache=False)
        
        assert result['route'] == query_router_config.COMPLEX_ROUTE


class TestCaching:
    """Test caching functionality"""
    
    def test_cache_storage(self):
        """Test that routing decisions are cached"""
        service = QueryRouterService()
        
        query = "What is NOI?"
        
        # First call (not cached)
        result1 = service.route_query(query, use_cache=True)
        assert result1['cached'] == False
        
        # Second call (should be cached)
        result2 = service.route_query(query, use_cache=True)
        assert result2['cached'] == True
        assert result2['complexity'] == result1['complexity']
        assert result2['route'] == result1['route']
    
    def test_clear_cache(self):
        """Test cache clearing"""
        service = QueryRouterService()
        
        # Add some entries
        service.route_query("query 1", use_cache=True)
        service.route_query("query 2", use_cache=True)
        
        assert len(service.routing_cache) > 0
        
        # Clear cache
        service.clear_cache()
        
        assert len(service.routing_cache) == 0


class TestPerformance:
    """Test performance requirements"""
    
    def test_decision_time_target(self):
        """Test that decision time is <100ms"""
        service = QueryRouterService()
        
        result = service.route_query("What is NOI?", use_cache=False)
        
        # Should complete in <100ms
        assert result['decision_time_ms'] < query_router_config.TARGET_DECISION_TIME_MS
    
    def test_cached_decision_fast(self):
        """Test that cached decisions are very fast"""
        service = QueryRouterService()
        
        query = "What is NOI?"
        
        # First call
        service.route_query(query, use_cache=True)
        
        # Second call (cached)
        result = service.route_query(query, use_cache=True)
        
        # Cached should be very fast (<10ms)
        assert result['decision_time_ms'] < 10


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_query(self):
        """Test handling of empty query"""
        service = QueryRouterService()
        
        result = service.route_query("", use_cache=False)
        
        assert result['route'] == query_router_config.DEFAULT_ROUTE
        assert 'error' in result
    
    def test_unknown_query_defaults_to_medium(self):
        """Test that unknown queries default to medium"""
        service = QueryRouterService()
        
        # Query that doesn't match any patterns
        result = service.route_query("Random text query", use_cache=False)
        
        # Should default to medium
        assert result['complexity'] == QueryComplexity.MEDIUM.value
        assert result['route'] == query_router_config.MEDIUM_ROUTE


class TestStatus:
    """Test service status"""
    
    def test_get_status(self):
        """Test getting service status"""
        service = QueryRouterService()
        
        status = service.get_status()
        
        assert 'llm_available' in status
        assert 'cache_stats' in status
        assert 'routing_stats' in status
        assert 'config' in status
    
    def test_get_routing_stats(self):
        """Test getting routing statistics"""
        service = QueryRouterService()
        
        # Add some routing decisions
        service.route_query("What is NOI?", use_cache=True)
        service.route_query("Compare revenue", use_cache=True)
        service.route_query("Why did it decrease?", use_cache=True)
        
        stats = service.get_routing_stats()
        
        assert 'total_cached_queries' in stats
        assert 'complexity_distribution' in stats
        assert 'route_distribution' in stats


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_confidence_in_range(self):
        """Test that confidence scores are in 0-1 range"""
        service = QueryRouterService()
        
        queries = [
            "What is NOI?",
            "Compare revenue across properties",
            "Why did NOI decrease?"
        ]
        
        for query in queries:
            result = service.route_query(query, use_cache=False)
            assert 0.0 <= result['confidence'] <= 1.0
    
    def test_high_confidence_for_clear_queries(self):
        """Test that clear queries get high confidence"""
        service = QueryRouterService()
        
        # Very clear simple query
        result = service.route_query("What is NOI for Property X?", use_cache=False)
        
        # Should have high confidence
        assert result['confidence'] >= 0.7

