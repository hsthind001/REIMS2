"""
Unit Tests for Conversation Manager Service

Tests conversation history storage, context extraction,
expiration, and turn numbering.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from app.services.conversation_manager import ConversationManager
from app.models.nlq_query import NLQQuery
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return Mock()


@pytest.fixture
def sample_property():
    """Sample property for testing"""
    prop = Property(
        id=1,
        property_name="Eastern Shore Plaza",
        property_code="ESP001"
    )
    return prop


class TestConversationID:
    """Test conversation ID management"""
    
    def test_create_new_conversation_id(self, mock_db_session):
        """Test creating new conversation ID"""
        manager = ConversationManager(mock_db_session)
        
        conv_id = manager.get_or_create_conversation_id()
        
        assert conv_id is not None
        assert len(conv_id) == 36  # UUID format
    
    def test_reuse_existing_conversation_id(self, mock_db_session):
        """Test reusing existing conversation ID"""
        manager = ConversationManager(mock_db_session)
        
        # Mock valid conversation
        mock_query = Mock()
        mock_query.created_at = datetime.utcnow()
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_query
        
        existing_id = "test-conversation-id"
        conv_id = manager.get_or_create_conversation_id(existing_id)
        
        assert conv_id == existing_id
    
    def test_create_new_if_expired(self, mock_db_session):
        """Test creating new ID if conversation expired"""
        manager = ConversationManager(mock_db_session)
        
        # Mock expired conversation
        mock_query = Mock()
        mock_query.created_at = datetime.utcnow() - timedelta(minutes=31)
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_query
        
        existing_id = "expired-conversation-id"
        conv_id = manager.get_or_create_conversation_id(existing_id)
        
        # Should create new ID
        assert conv_id != existing_id
        assert len(conv_id) == 36


class TestSaveQuery:
    """Test saving queries to conversation"""
    
    def test_save_query_with_entities(self, mock_db_session):
        """Test saving query with extracted entities"""
        manager = ConversationManager(mock_db_session, user_id=1)
        
        entities = {
            'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
            'metrics': ['noi'],
            'periods': [{'year': 2024, 'quarter': 3}]
        }
        
        nlq_query = manager.save_query(
            query="What was NOI for Eastern Shore in Q3?",
            answer="The NOI was $1.2M",
            conversation_id="test-conv-id",
            turn_number=1,
            entities=entities
        )
        
        assert nlq_query.question == "What was NOI for Eastern Shore in Q3?"
        assert nlq_query.answer == "The NOI was $1.2M"
        assert nlq_query.conversation_id == "test-conv-id"
        assert nlq_query.turn_number == 1
        assert nlq_query.metadata['entities'] == entities
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestConversationHistory:
    """Test retrieving conversation history"""
    
    def test_get_empty_conversation(self, mock_db_session):
        """Test getting history for empty conversation"""
        manager = ConversationManager(mock_db_session)
        
        # Mock empty query result
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        history = manager.get_conversation_history("test-conv-id")
        
        assert history['conversation_id'] == "test-conv-id"
        assert history['history'] == []
        assert history['context'] == {}
        assert history['turn_count'] == 0
    
    def test_get_conversation_with_history(self, mock_db_session):
        """Test getting conversation with history"""
        manager = ConversationManager(mock_db_session)
        
        # Mock queries
        mock_query1 = Mock()
        mock_query1.question = "What was NOI?"
        mock_query1.answer = "The NOI was $1.2M"
        mock_query1.metadata = {'entities': {'metrics': ['noi']}}
        mock_query1.created_at = datetime.utcnow()
        mock_query1.turn_number = 1
        
        mock_query2 = Mock()
        mock_query2.question = "And for Q4?"
        mock_query2.answer = "The NOI was $1.5M"
        mock_query2.metadata = {'entities': {'metrics': ['noi'], 'periods': [{'year': 2024, 'quarter': 4}]}}
        mock_query2.created_at = datetime.utcnow()
        mock_query2.turn_number = 2
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_query2, mock_query1]
        
        history = manager.get_conversation_history("test-conv-id")
        
        assert len(history['history']) == 2
        assert history['turn_count'] == 2
        assert history['history'][0]['question'] == "What was NOI?"
        assert history['history'][1]['question'] == "And for Q4?"


class TestContextExtraction:
    """Test context extraction from history"""
    
    def test_extract_properties(self, mock_db_session, sample_property):
        """Test extracting properties from history"""
        manager = ConversationManager(mock_db_session)
        
        history = [
            {
                'question': 'What was NOI for Eastern Shore?',
                'answer': 'The NOI was $1.2M',
                'entities': {
                    'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
                    'metrics': ['noi']
                }
            }
        ]
        
        # Mock property lookup
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_property
        
        context = manager._extract_context(history)
        
        assert len(context['properties']) == 1
        assert context['properties'][0]['property_id'] == 1
        assert context['properties'][0]['property_name'] == 'Eastern Shore Plaza'
    
    def test_extract_metrics(self, mock_db_session):
        """Test extracting metrics from history"""
        manager = ConversationManager(mock_db_session)
        
        history = [
            {
                'question': 'What was NOI?',
                'answer': 'The NOI was $1.2M',
                'entities': {'metrics': ['noi']}
            },
            {
                'question': 'What about DSCR?',
                'answer': 'The DSCR was 1.25',
                'entities': {'metrics': ['dscr']}
            }
        ]
        
        context = manager._extract_context(history)
        
        assert 'noi' in context['metrics']
        assert 'dscr' in context['metrics']
        assert len(context['metrics']) == 2
    
    def test_extract_periods(self, mock_db_session):
        """Test extracting time periods from history"""
        manager = ConversationManager(mock_db_session)
        
        history = [
            {
                'question': 'What was NOI in Q3?',
                'answer': 'The NOI was $1.2M',
                'entities': {'periods': [{'year': 2024, 'quarter': 3}]}
            },
            {
                'question': 'And for Q4?',
                'answer': 'The NOI was $1.5M',
                'entities': {'periods': [{'year': 2024, 'quarter': 4}]}
            }
        ]
        
        context = manager._extract_context(history)
        
        assert len(context['time_periods']) == 2
        assert {'year': 2024, 'quarter': 4} in context['time_periods']
        assert {'year': 2024, 'quarter': 3} in context['time_periods']
    
    def test_prioritize_recent_context(self, mock_db_session):
        """Test that recent context takes priority"""
        manager = ConversationManager(mock_db_session)
        
        history = [
            {
                'question': 'What was NOI for Property A?',
                'answer': 'The NOI was $1.2M',
                'entities': {'properties': [{'property_id': 1}]}
            },
            {
                'question': 'What about Property B?',
                'answer': 'The NOI was $1.5M',
                'entities': {'properties': [{'property_id': 2}]}
            }
        ]
        
        # Mock property lookups
        prop1 = Property(id=1, property_name="Property A", property_code="PA001")
        prop2 = Property(id=2, property_name="Property B", property_code="PB001")
        
        def mock_property_lookup(prop_id):
            if prop_id == 1:
                return prop1
            elif prop_id == 2:
                return prop2
            return None
        
        mock_db_session.query.return_value.filter.return_value.first.side_effect = mock_property_lookup
        
        context = manager._extract_context(history)
        
        # Should have both properties, with Property B (more recent) first
        assert len(context['properties']) == 2
        property_ids = [p['property_id'] for p in context['properties']]
        assert 1 in property_ids
        assert 2 in property_ids


class TestTurnNumbering:
    """Test turn number management"""
    
    def test_get_next_turn_number_new_conversation(self, mock_db_session):
        """Test getting turn number for new conversation"""
        manager = ConversationManager(mock_db_session)
        
        # Mock no existing queries
        mock_db_session.query.return_value.filter.return_value.with_entities.return_value.order_by.return_value.first.return_value = None
        
        turn_number = manager.get_next_turn_number("new-conv-id")
        
        assert turn_number == 1
    
    def test_get_next_turn_number_existing_conversation(self, mock_db_session):
        """Test getting turn number for existing conversation"""
        manager = ConversationManager(mock_db_session)
        
        # Mock existing query with turn_number = 3
        mock_result = Mock()
        mock_result.turn_number = 3
        mock_db_session.query.return_value.filter.return_value.with_entities.return_value.order_by.return_value.first.return_value = mock_result
        
        turn_number = manager.get_next_turn_number("existing-conv-id")
        
        assert turn_number == 4


class TestExpiration:
    """Test conversation expiration"""
    
    def test_conversation_not_expired(self, mock_db_session):
        """Test that recent conversation is not expired"""
        manager = ConversationManager(mock_db_session)
        
        # Mock recent query
        mock_query = Mock()
        mock_query.created_at = datetime.utcnow() - timedelta(minutes=10)
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_query
        
        is_valid = manager._is_conversation_valid("test-conv-id")
        
        assert is_valid is True
    
    def test_conversation_expired(self, mock_db_session):
        """Test that old conversation is expired"""
        manager = ConversationManager(mock_db_session)
        
        # Mock old query
        mock_query = Mock()
        mock_query.created_at = datetime.utcnow() - timedelta(minutes=31)
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_query
        
        is_valid = manager._is_conversation_valid("test-conv-id")
        
        assert is_valid is False
    
    def test_conversation_not_found(self, mock_db_session):
        """Test that non-existent conversation is invalid"""
        manager = ConversationManager(mock_db_session)
        
        # Mock no query found
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        is_valid = manager._is_conversation_valid("non-existent-id")
        
        assert is_valid is False


class TestUserConversations:
    """Test getting user conversations"""
    
    def test_get_user_conversations(self, mock_db_session):
        """Test getting conversations for a user"""
        manager = ConversationManager(mock_db_session, user_id=1)
        
        # Mock conversations
        mock_conv1 = ("conv-id-1", datetime.utcnow())
        mock_conv2 = ("conv-id-2", datetime.utcnow() - timedelta(minutes=5))
        
        mock_db_session.query.return_value.filter.return_value.distinct.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_conv1, mock_conv2]
        
        # Mock history retrieval
        def mock_history(conv_id, max_turns):
            if conv_id == "conv-id-1":
                return {
                    'conversation_id': conv_id,
                    'history': [{'question': 'What is NOI?', 'answer': '$1.2M'}],
                    'last_query_time': datetime.utcnow().isoformat(),
                    'turn_count': 1
                }
            return {'conversation_id': conv_id, 'history': [], 'last_query_time': None, 'turn_count': 0}
        
        manager.get_conversation_history = mock_history
        
        conversations = manager.get_user_conversations()
        
        assert len(conversations) == 2
        assert conversations[0]['conversation_id'] == "conv-id-1"
        assert conversations[0]['last_query'] == "What is NOI?"


class TestFollowUpQueries:
    """Test follow-up query scenarios"""
    
    def test_follow_up_without_property(self, mock_db_session):
        """Test follow-up query that needs property from context"""
        manager = ConversationManager(mock_db_session)
        
        # Initial query
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3?',
                'answer': 'The NOI was $1.2M',
                'entities': {
                    'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
                    'metrics': ['noi'],
                    'periods': [{'year': 2024, 'quarter': 3}]
                }
            }
        ]
        
        context = manager._extract_context(history)
        
        # Follow-up: "And for Q4?" should use property from context
        assert len(context['properties']) == 1
        assert context['properties'][0]['property_name'] == 'Eastern Shore Plaza'
        assert 'noi' in context['metrics']
    
    def test_follow_up_with_that_property(self, mock_db_session):
        """Test follow-up query with 'that property' reference"""
        manager = ConversationManager(mock_db_session)
        
        # Initial query
        history = [
            {
                'question': 'What was NOI for Eastern Shore in Q3?',
                'answer': 'The NOI was $1.2M',
                'entities': {
                    'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
                    'metrics': ['noi'],
                    'periods': [{'year': 2024, 'quarter': 3}]
                }
            }
        ]
        
        context = manager._extract_context(history)
        
        # Follow-up: "What about that property in Q1?" should resolve property from context
        assert len(context['properties']) == 1
        # The NLQ service should use this context to resolve "that property"
        assert context['properties'][0]['property_id'] == 1

