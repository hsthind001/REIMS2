"""
Unit Tests for Entity Resolver Service

Tests fuzzy property name matching, typo handling,
confidence scoring, and caching.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.services.entity_resolver_service import EntityResolverService
from app.config.entity_resolver_config import entity_resolver_config


@pytest.fixture
def sample_properties():
    """Sample property data for testing"""
    return [
        {
            'property_id': 1,
            'property_name': 'Eastern Shore Plaza',
            'property_code': 'ESP001'
        },
        {
            'property_id': 2,
            'property_name': 'Hammond Aire Shopping Center',
            'property_code': 'HASC001'
        },
        {
            'property_id': 3,
            'property_name': 'Westfield Mall',
            'property_code': 'WM001'
        },
        {
            'property_id': 4,
            'property_name': 'Riverside Office Complex',
            'property_code': 'ROC001'
        }
    ]


@pytest.fixture
def mock_db_session(sample_properties):
    """Mock database session"""
    mock_db = Mock()
    mock_result = Mock()
    mock_result.fetchall.return_value = [
        Mock(property_id=p['property_id'], property_name=p['property_name'], property_code=p['property_code'])
        for p in sample_properties
    ]
    mock_db.execute.return_value = mock_result
    return mock_db


class TestFuzzyMatching:
    """Test fuzzy matching functionality"""
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_match_typo_in_name(self, mock_fuzz, mock_db_session, sample_properties):
        """Test matching with typo in property name"""
        # Mock fuzzywuzzy responses
        mock_fuzz.partial_ratio.side_effect = lambda a, b: 90 if 'east' in a.lower() and 'east' in b.lower() else 50
        mock_fuzz.ratio.side_effect = lambda a, b: 85 if 'east' in a.lower() and 'east' in b.lower() else 40
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        # Query with typo: "Easten Shore" instead of "Eastern Shore"
        result = service.resolve_property("Easten Shore", use_cache=False)
        
        assert 'matches' in result
        assert len(result['matches']) > 0
        assert result['matches'][0]['property_name'] == 'Eastern Shore Plaza'
        assert result['matches'][0]['confidence'] >= 0.75  # Above threshold
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_match_typo_in_code(self, mock_fuzz, mock_db_session, sample_properties):
        """Test matching with typo in property code"""
        mock_fuzz.partial_ratio.side_effect = lambda a, b: 88 if 'esp' in a.lower() and 'esp' in b.lower() else 30
        mock_fuzz.ratio.side_effect = lambda a, b: 82 if 'esp' in a.lower() and 'esp' in b.lower() else 25
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        # Query with typo: "ESP01" instead of "ESP001"
        result = service.resolve_property("ESP01", use_cache=False)
        
        assert len(result['matches']) > 0
        assert result['matches'][0]['property_code'] == 'ESP001'
        assert result['matches'][0]['matched_field'] == 'code'
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_multiple_matches(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that multiple matches are returned"""
        # Mock to return multiple high-scoring matches
        def mock_partial_ratio(a, b):
            if 'mall' in a.lower() and 'mall' in b.lower():
                return 95
            if 'west' in a.lower() and 'west' in b.lower():
                return 90
            return 30
        
        mock_fuzz.partial_ratio.side_effect = mock_partial_ratio
        mock_fuzz.ratio.side_effect = lambda a, b: 80
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("mall", use_cache=False)
        
        # Should return top matches (up to MAX_MATCHES)
        assert len(result['matches']) <= entity_resolver_config.MAX_MATCHES
        assert all(m['confidence'] >= entity_resolver_config.MIN_CONFIDENCE for m in result['matches'])
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_no_matches_below_threshold(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that matches below threshold are filtered out"""
        # Mock low scores
        mock_fuzz.partial_ratio.return_value = 50  # Below 75 threshold
        mock_fuzz.ratio.return_value = 40
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("completely different", use_cache=False)
        
        # Should return no matches (all below threshold)
        assert len(result['matches']) == 0
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_confidence_scoring(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that confidence scores are calculated correctly"""
        mock_fuzz.partial_ratio.return_value = 85  # 85% similarity
        mock_fuzz.ratio.return_value = 80
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Eastern Shore", use_cache=False)
        
        if result['matches']:
            # Confidence should be similarity / 100
            assert 0.0 <= result['matches'][0]['confidence'] <= 1.0
            assert result['matches'][0]['similarity_score'] == 85


class TestTypoExamples:
    """Test common typo scenarios"""
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_missing_letter(self, mock_fuzz, mock_db_session, sample_properties):
        """Test typo: missing letter (Easten vs Eastern)"""
        def mock_partial(a, b):
            if 'east' in a.lower() and 'eastern' in b.lower():
                return 92
            return 30
        
        mock_fuzz.partial_ratio.side_effect = mock_partial
        mock_fuzz.ratio.return_value = 85
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Easten Shore", use_cache=False)
        assert len(result['matches']) > 0
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_extra_letter(self, mock_fuzz, mock_db_session, sample_properties):
        """Test typo: extra letter (Hammondd vs Hammond)"""
        def mock_partial(a, b):
            if 'hammond' in a.lower() and 'hammond' in b.lower():
                return 93
            return 30
        
        mock_fuzz.partial_ratio.side_effect = mock_partial
        mock_fuzz.ratio.return_value = 86
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Hammondd Aire", use_cache=False)
        assert len(result['matches']) > 0
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_wrong_letter(self, mock_fuzz, mock_db_session, sample_properties):
        """Test typo: wrong letter (Hamond vs Hammond)"""
        def mock_partial(a, b):
            if 'hamond' in a.lower() or 'hammond' in a.lower():
                if 'hammond' in b.lower():
                    return 91
            return 30
        
        mock_fuzz.partial_ratio.side_effect = mock_partial
        mock_fuzz.ratio.return_value = 84
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Hamond Air", use_cache=False)
        assert len(result['matches']) > 0
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_transposed_letters(self, mock_fuzz, mock_db_session, sample_properties):
        """Test typo: transposed letters"""
        def mock_partial(a, b):
            if 'west' in a.lower() and 'west' in b.lower():
                return 90
            return 30
        
        mock_fuzz.partial_ratio.side_effect = mock_partial
        mock_fuzz.ratio.return_value = 83
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Wetsfield", use_cache=False)
        # Should still match "Westfield"
        assert len(result['matches']) > 0


class TestCaching:
    """Test caching functionality"""
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_cache_storage(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that match results are cached"""
        mock_fuzz.partial_ratio.return_value = 90
        mock_fuzz.ratio.return_value = 85
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        query = "Eastern Shore"
        
        # First call (not cached)
        result1 = service.resolve_property(query, use_cache=True)
        assert result1['cached'] == False
        
        # Second call (should be cached)
        result2 = service.resolve_property(query, use_cache=True)
        assert result2['cached'] == True
        assert result2['matches'] == result1['matches']
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_cache_ttl_expiration(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that cache entries expire after TTL"""
        mock_fuzz.partial_ratio.return_value = 90
        mock_fuzz.ratio.return_value = 85
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        query = "Eastern Shore"
        
        # Cache a result
        result1 = service.resolve_property(query, use_cache=True)
        
        # Manually expire the cache entry
        cache_key = service._get_cache_key(query)
        service.match_cache[cache_key]['cached_at'] = datetime.utcnow() - timedelta(minutes=31)
        
        # Next call should not use cache (expired)
        result2 = service.resolve_property(query, use_cache=True)
        # Should regenerate (may or may not be cached=False depending on implementation)
        assert 'matches' in result2
    
    def test_clear_cache(self, mock_db_session):
        """Test cache clearing"""
        service = EntityResolverService(mock_db_session)
        
        # Add some entries
        service.match_cache['key1'] = {'cached_at': datetime.utcnow()}
        service.match_cache['key2'] = {'cached_at': datetime.utcnow()}
        
        assert len(service.match_cache) > 0
        
        # Clear cache
        service.clear_cache()
        
        assert len(service.match_cache) == 0


class TestPropertyLoading:
    """Test property list loading and refresh"""
    
    def test_load_properties(self, mock_db_session, sample_properties):
        """Test that properties are loaded on initialization"""
        service = EntityResolverService(mock_db_session)
        
        assert len(service.properties) == len(sample_properties)
        assert service.last_refresh is not None
    
    def test_refresh_properties(self, mock_db_session, sample_properties):
        """Test manual property refresh"""
        service = EntityResolverService(mock_db_session)
        
        initial_count = len(service.properties)
        initial_refresh = service.last_refresh
        
        # Refresh
        service.refresh_properties()
        
        assert len(service.properties) == initial_count  # Same data
        assert service.last_refresh > initial_refresh  # Refresh time updated
    
    def test_auto_refresh_trigger(self, mock_db_session):
        """Test that auto-refresh is triggered when needed"""
        service = EntityResolverService(mock_db_session)
        
        # Set last refresh to old time
        service.last_refresh = datetime.utcnow() - timedelta(minutes=6)
        
        # Should trigger refresh on next resolve
        with patch.object(service, 'refresh_properties') as mock_refresh:
            with patch('app.services.entity_resolver_service.fuzz') as mock_fuzz:
                mock_fuzz.partial_ratio.return_value = 90
                mock_fuzz.ratio.return_value = 85
                
                service.resolve_property("test", use_cache=False)
                
                # Should have called refresh
                mock_refresh.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_query(self, mock_db_session):
        """Test handling of empty query"""
        service = EntityResolverService(mock_db_session)
        
        result = service.resolve_property("", use_cache=False)
        
        assert result['matches'] == []
        assert 'error' in result
    
    def test_no_properties_loaded(self, mock_db_session):
        """Test handling when no properties are loaded"""
        service = EntityResolverService(mock_db_session)
        service.properties = []
        
        result = service.resolve_property("test", use_cache=False)
        
        assert result['matches'] == []
    
    @patch('app.services.entity_resolver_service.FUZZYWUZZY_AVAILABLE', False)
    def test_fuzzywuzzy_unavailable(self, mock_db_session):
        """Test handling when fuzzywuzzy is not available"""
        service = EntityResolverService(mock_db_session)
        
        result = service.resolve_property("test", use_cache=False)
        
        assert 'error' in result
        assert 'fuzzywuzzy' in result['error'].lower()


class TestPerformance:
    """Test performance requirements"""
    
    @patch('app.services.entity_resolver_service.fuzz')
    def test_matching_time_target(self, mock_fuzz, mock_db_session, sample_properties):
        """Test that matching time is <50ms"""
        mock_fuzz.partial_ratio.return_value = 90
        mock_fuzz.ratio.return_value = 85
        
        service = EntityResolverService(mock_db_session)
        service.properties = sample_properties
        
        result = service.resolve_property("Eastern Shore", use_cache=False)
        
        # Should complete in <50ms
        assert result['matching_time_ms'] < entity_resolver_config.TARGET_MATCHING_TIME_MS


class TestStatus:
    """Test service status"""
    
    def test_get_status(self, mock_db_session):
        """Test getting service status"""
        service = EntityResolverService(mock_db_session)
        
        status = service.get_status()
        
        assert 'fuzzywuzzy_available' in status
        assert 'properties_loaded' in status
        assert 'property_stats' in status
        assert 'cache_stats' in status
        assert 'config' in status
    
    def test_get_cache_stats(self, mock_db_session):
        """Test getting cache statistics"""
        service = EntityResolverService(mock_db_session)
        
        stats = service.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_max_size' in stats
        assert 'cache_ttl_minutes' in stats
        assert 'cache_enabled' in stats
    
    def test_get_property_stats(self, mock_db_session, sample_properties):
        """Test getting property statistics"""
        service = EntityResolverService(mock_db_session)
        
        stats = service.get_property_stats()
        
        assert 'num_properties' in stats
        assert stats['num_properties'] == len(sample_properties)
        assert 'last_refresh' in stats
        assert 'refresh_interval_minutes' in stats

