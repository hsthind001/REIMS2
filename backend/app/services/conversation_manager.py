"""
Conversation Manager Service

Manages conversation history and context extraction for NLQ queries.
Enables follow-up questions without repeating context.
"""
import logging
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.nlq_query import NLQQuery
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)

# Try to import CoreferenceResolver
try:
    from app.services.coreference_resolver import CoreferenceResolver
    COREFERENCE_AVAILABLE = True
except ImportError:
    COREFERENCE_AVAILABLE = False
    logger.warning("CoreferenceResolver not available. Coreference resolution will be disabled.")


class ConversationManager:
    """
    Manages conversation history and context for NLQ queries
    
    Tracks conversation history, extracts context (properties, metrics, periods),
    and handles context expiration.
    """
    
    def __init__(self, db: Session, user_id: Optional[int] = None):
        """
        Initialize conversation manager
        
        Args:
            db: Database session
            user_id: User ID for conversation tracking (optional)
        """
        self.db = db
        self.user_id = user_id
        self.max_history_length = 5  # Last 5 Q&A pairs
        self.context_expiry_minutes = 30  # 30 minutes of inactivity
        
        # Initialize coreference resolver if available
        self.coreference_resolver = None
        if COREFERENCE_AVAILABLE:
            try:
                self.coreference_resolver = CoreferenceResolver()
                logger.info("ConversationManager initialized with CoreferenceResolver support")
            except Exception as e:
                logger.warning(f"Failed to initialize CoreferenceResolver: {e}. Coreference resolution will be disabled.")
    
    def get_or_create_conversation_id(
        self,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Get existing conversation ID or create new one
        
        Args:
            conversation_id: Existing conversation ID (optional)
        
        Returns:
            Conversation ID string
        """
        if conversation_id:
            # Validate conversation exists and is not expired
            if self._is_conversation_valid(conversation_id):
                return conversation_id
            else:
                logger.info(f"Conversation {conversation_id} expired or invalid. Creating new conversation.")
        
        # Create new conversation ID
        return str(uuid.uuid4())
    
    def save_query(
        self,
        query: str,
        answer: str,
        conversation_id: str,
        turn_number: int,
        entities: Optional[Dict[str, Any]] = None
    ) -> NLQQuery:
        """
        Save query and answer to conversation history
        
        Args:
            query: User query text
            answer: System answer text
            conversation_id: Conversation ID
            turn_number: Turn number in conversation (1-indexed)
            entities: Extracted entities (properties, metrics, periods)
        
        Returns:
            Saved NLQQuery object
        """
        try:
            nlq_query = NLQQuery(
                question=query,
                answer=answer,
                conversation_id=conversation_id,
                turn_number=turn_number,
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )
            
            # Store entities in metadata if available
            if entities:
                if not nlq_query.metadata:
                    nlq_query.metadata = {}
                nlq_query.metadata['entities'] = entities
            
            self.db.add(nlq_query)
            self.db.commit()
            self.db.refresh(nlq_query)
            
            logger.debug(f"Saved query to conversation {conversation_id}, turn {turn_number}")
            
            return nlq_query
            
        except Exception as e:
            logger.error(f"Failed to save query to conversation: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def resolve_query_with_context(
        self,
        query: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Resolve coreferences in query using conversation context
        
        Args:
            query: User query (may contain coreferences)
            conversation_id: Conversation ID
        
        Returns:
            Dict with resolved_query, original_query, and resolution metadata
        """
        if not self.coreference_resolver:
            # No resolver available, return original query
            return {
                'original_query': query,
                'resolved_query': query,
                'has_coreference': False,
                'method': 'no_resolver'
            }
        
        # Get conversation history
        history_data = self.get_conversation_history(conversation_id)
        history = history_data.get('history', [])
        context = history_data.get('context', {})
        
        # Resolve coreferences
        resolution_result = self.coreference_resolver.resolve_coreference(
            query=query,
            conversation_history=history,
            context=context
        )
        
        return resolution_result
    
    def get_conversation_history(
        self,
        conversation_id: str,
        max_turns: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get conversation history with context
        
        Args:
            conversation_id: Conversation ID
            max_turns: Maximum number of turns to return (default: max_history_length)
        
        Returns:
            Dict with conversation history and extracted context
        """
        if max_turns is None:
            max_turns = self.max_history_length
        
        try:
            # Get recent queries for this conversation
            queries = self.db.query(NLQQuery).filter(
                NLQQuery.conversation_id == conversation_id
            ).order_by(desc(NLQQuery.turn_number)).limit(max_turns).all()
            
            # Reverse to chronological order
            queries = list(reversed(queries))
            
            if not queries:
                return {
                    'conversation_id': conversation_id,
                    'history': [],
                    'context': {},
                    'last_query_time': None,
                    'turn_count': 0
                }
            
            # Build history
            history = []
            for q in queries:
                history.append({
                    'question': q.question,
                    'answer': q.answer,
                    'entities': q.metadata.get('entities', {}) if q.metadata else {},
                    'timestamp': q.created_at.isoformat() if q.created_at else None,
                    'turn_number': q.turn_number
                })
            
            # Extract accumulated context
            context = self._extract_context(history)
            
            # Get last query time
            last_query = queries[-1]
            last_query_time = last_query.created_at if last_query.created_at else None
            
            return {
                'conversation_id': conversation_id,
                'history': history,
                'context': context,
                'last_query_time': last_query_time.isoformat() if last_query_time else None,
                'turn_count': len(queries)
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}", exc_info=True)
            return {
                'conversation_id': conversation_id,
                'history': [],
                'context': {},
                'last_query_time': None,
                'turn_count': 0,
                'error': str(e)
            }
    
    def _extract_context(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract accumulated context from conversation history
        
        Args:
            history: List of Q&A pairs with entities
        
        Returns:
            Dict with accumulated context (properties, metrics, periods)
        """
        context = {
            'properties': [],
            'metrics': [],
            'time_periods': []
        }
        
        # Extract from most recent to oldest (keep most recent values)
        seen_properties = set()
        seen_metrics = set()
        seen_periods = set()
        
        # Process in reverse order to prioritize recent context
        for entry in reversed(history):
            entities = entry.get('entities', {})
            
            # Extract properties
            properties = entities.get('properties', [])
            for prop in properties:
                prop_id = prop.get('property_id') if isinstance(prop, dict) else prop
                if prop_id and prop_id not in seen_properties:
                    if isinstance(prop, dict):
                        context['properties'].append(prop)
                    else:
                        # Look up property details
                        property_obj = self.db.query(Property).filter(Property.id == prop_id).first()
                        if property_obj:
                            context['properties'].append({
                                'property_id': property_obj.id,
                                'property_name': property_obj.property_name,
                                'property_code': property_obj.property_code
                            })
                    seen_properties.add(prop_id)
            
            # Extract metrics
            metrics = entities.get('metrics', [])
            for metric in metrics:
                if metric not in seen_metrics:
                    context['metrics'].append(metric)
                    seen_metrics.add(metric)
            
            # Extract time periods
            periods = entities.get('periods', [])
            for period in periods:
                period_key = self._get_period_key(period)
                if period_key and period_key not in seen_periods:
                    context['time_periods'].append(period)
                    seen_periods.add(period_key)
        
        return context
    
    def _get_period_key(self, period: Dict[str, Any]) -> Optional[str]:
        """Generate unique key for period"""
        if isinstance(period, dict):
            year = period.get('year')
            quarter = period.get('quarter')
            month = period.get('month')
            if year:
                if quarter:
                    return f"{year}-Q{quarter}"
                elif month:
                    return f"{year}-{month:02d}"
                else:
                    return str(year)
        return None
    
    def _is_conversation_valid(self, conversation_id: str) -> bool:
        """
        Check if conversation is still valid (not expired)
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            True if conversation is valid, False if expired
        """
        try:
            # Get most recent query for this conversation
            last_query = self.db.query(NLQQuery).filter(
                NLQQuery.conversation_id == conversation_id
            ).order_by(desc(NLQQuery.created_at)).first()
            
            if not last_query or not last_query.created_at:
                return False
            
            # Check if expired
            age = datetime.utcnow() - last_query.created_at
            return age < timedelta(minutes=self.context_expiry_minutes)
            
        except Exception as e:
            logger.error(f"Error checking conversation validity: {e}", exc_info=True)
            return False
    
    def get_next_turn_number(self, conversation_id: str) -> int:
        """
        Get next turn number for conversation
        
        Args:
            conversation_id: Conversation ID
        
        Returns:
            Next turn number (1-indexed)
        """
        try:
            max_turn = self.db.query(NLQQuery).filter(
                NLQQuery.conversation_id == conversation_id
            ).with_entities(NLQQuery.turn_number).order_by(desc(NLQQuery.turn_number)).first()
            
            if max_turn and max_turn.turn_number:
                return max_turn.turn_number + 1
            
            return 1
            
        except Exception as e:
            logger.error(f"Error getting next turn number: {e}", exc_info=True)
            return 1
    
    def get_user_conversations(
        self,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations for a user
        
        Args:
            user_id: User ID (default: self.user_id)
            limit: Maximum number of conversations to return
        
        Returns:
            List of conversation summaries
        """
        if user_id is None:
            user_id = self.user_id
        
        if not user_id:
            return []
        
        try:
            # Get distinct conversations for user
            conversations = self.db.query(
                NLQQuery.conversation_id,
                NLQQuery.created_at
            ).filter(
                NLQQuery.user_id == user_id
            ).distinct().order_by(desc(NLQQuery.created_at)).limit(limit).all()
            
            result = []
            for conv_id, created_at in conversations:
                # Get summary
                history = self.get_conversation_history(conv_id, max_turns=1)
                result.append({
                    'conversation_id': conv_id,
                    'last_query': history['history'][0]['question'] if history['history'] else None,
                    'last_query_time': history['last_query_time'],
                    'turn_count': history['turn_count']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}", exc_info=True)
            return []
    
    def clear_expired_conversations(self) -> int:
        """
        Clear expired conversations (older than expiry time)
        
        Returns:
            Number of conversations cleared
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.context_expiry_minutes)
            
            # Get expired conversation IDs
            expired_conversations = self.db.query(NLQQuery.conversation_id).filter(
                NLQQuery.created_at < cutoff_time
            ).distinct().all()
            
            expired_count = len(expired_conversations)
            
            # Optionally delete expired queries (or just mark as expired)
            # For now, we'll just return the count
            # Actual deletion can be done via cleanup job
            
            logger.info(f"Found {expired_count} expired conversations")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error clearing expired conversations: {e}", exc_info=True)
            return 0

