"""
Unit Tests for Coreference Resolver Service

Tests pronoun resolution, implicit reference resolution,
and LLM-based resolution with conversation context.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.coreference_resolver import CoreferenceResolver
from app.config.coreference_config import coreference_config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"resolved_query": "What was NOI for Eastern Shore Plaza in Q4 2024?", "confidence": 0.95, "reasoning": "Resolved Q4 and property from context"}'
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestCoreferenceDetection:
    """Test coreference detection"""
    
    def test_detects_pronouns(self):
        """Test detection of pronouns"""
        resolver = CoreferenceResolver()
        
        assert resolver.has_coreference("What about that property?") is True
        assert resolver.has_coreference("What is this property?") is True
        assert resolver.has_coreference("How about it in Q4?") is True
        assert resolver.has_coreference("What about they?") is True
    
    def test_detects_implicit_phrases(self):
        """Test detection of implicit phrases"""
        resolver = CoreferenceResolver()
        
        assert resolver.has_coreference("And for Q4?") is True
        assert resolver.has_coreference("What about December?") is True
        assert resolver.has_coreference("How about Q3?") is True
        assert resolver.has_coreference("Also for 2024?") is True
    
    def test_detects_temporal_indicators(self):
        """Test detection of temporal indicators"""
        resolver = CoreferenceResolver()
        
        assert resolver.has_coreference("What about last quarter?") is True
        assert resolver.has_coreference("Show me next month") is True
        assert resolver.has_coreference("Previous year data") is True
    
    def test_no_coreference_detected(self):
        """Test that complete queries don't trigger detection"""
        resolver = CoreferenceResolver()
        
        assert resolver.has_coreference("What was NOI for Eastern Shore in Q3 2024?") is False
        assert resolver.has_coreference("Show me revenue for Property X") is False
        assert resolver.has_coreference("Compare DSCR across properties") is False


class TestRuleBasedResolution:
    """Test rule-based resolution"""
    
    def test_resolve_that_property(self):
        """Test resolving 'that property' using context"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore Plaza in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about that property in Q4?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        assert 'Eastern Shore Plaza' in result['resolved_query'] or result['resolved_query'] != "What about that property in Q4?"
        assert result['method'] in ['rules', 'llm']
    
    def test_resolve_implicit_temporal(self):
        """Test resolving implicit temporal references"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="And for Q4?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        # Should include year if not present
        assert result['resolved_query'] != "And for Q4?"
    
    def test_resolve_what_about(self):
        """Test resolving 'what about' queries"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about December?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        assert result['resolved_query'] != "What about December?"


class TestLLMResolution:
    """Test LLM-based resolution"""
    
    @patch('app.services.coreference_resolver.OpenAI')
    @patch('app.core.config.settings')
    def test_llm_resolves_coreference(self, mock_settings, mock_openai_class, mock_openai_client):
        """Test LLM resolution of coreference"""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_openai_class.return_value = mock_openai_client
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"resolved_query": "What was NOI for Eastern Shore Plaza in Q4 2024?", "confidence": 0.95, "reasoning": "Resolved Q4 and property from context"}'
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        resolver = CoreferenceResolver()
        resolver.openai_client = mock_openai_client
        resolver.use_llm = True
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore Plaza in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about Q4?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        assert result['resolved_query'] == "What was NOI for Eastern Shore Plaza in Q4 2024?"
        assert result['method'] == 'llm'
        assert result['confidence'] == 0.95
    
    @patch('app.services.coreference_resolver.OpenAI')
    @patch('app.core.config.settings')
    def test_llm_fallback_to_rules(self, mock_settings, mock_openai_class, mock_openai_client):
        """Test LLM fallback to rules on error"""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_openai_class.return_value = mock_openai_client
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        resolver = CoreferenceResolver()
        resolver.openai_client = mock_openai_client
        resolver.use_llm = True
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about Q4?",
            conversation_history=history,
            context=context
        )
        
        # Should fall back to rules
        assert result['method'] in ['rules', 'llm_fallback']
        assert result['has_coreference'] is True


class TestConversationExamples:
    """Test real conversation examples"""
    
    def test_example_1_property_reference(self):
        """Test: 'What about that property in Q4?'"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about that property in Q4?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        assert 'Eastern Shore' in result['resolved_query'] or 'Eastern Shore Plaza' in result['resolved_query']
        assert 'Q4' in result['resolved_query']
        assert '2024' in result['resolved_query']
    
    def test_example_2_implicit_period(self):
        """Test: 'And for December?'"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="And for December?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        # Should include property and metric from context
        assert result['resolved_query'] != "And for December?"
    
    def test_example_3_pronoun_resolution(self):
        """Test: 'What about it in Q1?'"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about it in Q1?",
            conversation_history=history,
            context=context
        )
        
        assert result['has_coreference'] is True
        assert 'Eastern Shore' in result['resolved_query'] or 'Eastern Shore Plaza' in result['resolved_query']
        assert 'Q1' in result['resolved_query']


class TestPerformance:
    """Test performance requirements"""
    
    def test_resolution_time_target(self):
        """Test that resolution time is <500ms"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        result = resolver.resolve_coreference(
            query="What about Q4?",
            conversation_history=history,
            context=context
        )
        
        # Should complete in <500ms (rule-based should be much faster)
        assert result['resolution_time_ms'] < coreference_config.TARGET_RESOLUTION_TIME_MS


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_query(self):
        """Test handling of empty query"""
        resolver = CoreferenceResolver()
        
        result = resolver.resolve_coreference(
            query="",
            conversation_history=[],
            context=None
        )
        
        assert result['resolved_query'] == ""
        assert result['has_coreference'] is False
    
    def test_no_conversation_history(self):
        """Test resolution without conversation history"""
        resolver = CoreferenceResolver()
        
        result = resolver.resolve_coreference(
            query="What about that property?",
            conversation_history=[],
            context=None
        )
        
        # Should detect coreference but may not resolve well without context
        assert result['has_coreference'] is True
    
    def test_no_context(self):
        """Test resolution without context"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        result = resolver.resolve_coreference(
            query="What about Q4?",
            conversation_history=history,
            context=None
        )
        
        # Should still attempt resolution using history
        assert result['has_coreference'] is True


class TestCaching:
    """Test caching functionality"""
    
    def test_cache_storage(self):
        """Test that resolutions are cached"""
        resolver = CoreferenceResolver()
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3 2024?',
                'answer': 'The NOI was $1.2M'
            }
        ]
        
        context = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'time_periods': [{'year': 2024, 'quarter': 3}]
        }
        
        query = "What about Q4?"
        
        # First call (not cached)
        result1 = resolver.resolve_coreference(query, history, context)
        assert result1.get('cached', False) == False
        
        # Second call (should be cached)
        result2 = resolver.resolve_coreference(query, history, context)
        assert result2.get('cached', False) == True
        assert result2['resolved_query'] == result1['resolved_query']
    
    def test_clear_cache(self):
        """Test cache clearing"""
        resolver = CoreferenceResolver()
        
        # Add some entries
        history = [{'question': 'Q1', 'answer': 'A1'}]
        resolver.resolve_coreference("test query", history, None)
        
        assert len(resolver.resolution_cache) > 0
        
        # Clear cache
        resolver.clear_cache()
        
        assert len(resolver.resolution_cache) == 0


class TestStatus:
    """Test service status"""
    
    def test_get_status(self):
        """Test getting service status"""
        resolver = CoreferenceResolver()
        
        status = resolver.get_status()
        
        assert 'llm_available' in status
        assert 'cache_stats' in status
        assert 'config' in status
    
    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        resolver = CoreferenceResolver()
        
        stats = resolver.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_ttl_minutes' in stats
        assert 'cache_enabled' in stats

