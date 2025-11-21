"""
Natural Language Query Service - RAG-powered conversational interface

Enables users to query financial data using natural language:
- "What was the NOI for Eastern Shore Plaza in Q3 2024?"
- "Show me occupancy trends over the last 2 years"
- "Which properties have the highest operating expense ratio?"
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import json
import hashlib
import re
import os
from typing import Optional

from app.models.nlq_query import NLQQuery
from app.models.property import Property
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_metrics import FinancialMetrics
from app.models.rent_roll_data import RentRollData
from app.models.financial_period import FinancialPeriod
from app.core.config import settings
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.embedding_service import EmbeddingService

# LLM imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class NaturalLanguageQueryService:
    """
    Natural Language Query Service using RAG

    Architecture:
    1. Intent Detection → Understand what user wants
    2. Data Retrieval → Query database for relevant data
    3. Response Generation → LLM generates natural language answer
    4. Citation → Track sources for answer
    """

    # Intent types
    INTENT_METRIC_QUERY = 'metric_query'
    INTENT_COMPARISON = 'comparison'
    INTENT_TREND_ANALYSIS = 'trend_analysis'
    INTENT_AGGREGATION = 'aggregation'
    INTENT_RANKING = 'ranking'

    # Common metrics mapping
    METRIC_MAPPINGS = {
        'noi': {'table': 'income_statement', 'field': 'net_operating_income'},
        'net operating income': {'table': 'income_statement', 'field': 'net_operating_income'},
        'revenue': {'table': 'income_statement', 'field': 'total_revenue'},
        'total revenue': {'table': 'income_statement', 'field': 'total_revenue'},
        'expenses': {'table': 'income_statement', 'field': 'total_expenses'},
        'total expenses': {'table': 'income_statement', 'field': 'total_expenses'},
        'assets': {'table': 'balance_sheet', 'field': 'total_assets'},
        'total assets': {'table': 'balance_sheet', 'field': 'total_assets'},
        'liabilities': {'table': 'balance_sheet', 'field': 'total_liabilities'},
        'equity': {'table': 'balance_sheet', 'field': 'total_equity'},
        'occupancy': {'table': 'metrics', 'field': 'occupancy_rate'},
        'occupancy rate': {'table': 'metrics', 'field': 'occupancy_rate'},
        'cash flow': {'table': 'cash_flow', 'field': 'net_cash_flow'},
    }

    def __init__(self, db: Session):
        self.db = db

        # Initialize LLM client
        self.llm_client = None
        self.llm_type = None

        # Initialize LLM client - check OpenAI first
        if OPENAI_AVAILABLE:
            openai_key = getattr(settings, 'OPENAI_API_KEY', None) or os.environ.get('OPENAI_API_KEY')
            if openai_key:
                try:
                    self.llm_client = OpenAI(api_key=openai_key)
                    self.llm_type = 'openai'
                    logger.info("✅ NLQ Service initialized with OpenAI")
                except Exception as e:
                    logger.warning(f"OpenAI initialization failed: {e}")

        # Fallback to Anthropic if OpenAI not available
        if not self.llm_client and ANTHROPIC_AVAILABLE:
            anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None) or os.environ.get('ANTHROPIC_API_KEY')
            if anthropic_key:
                try:
                    self.llm_client = Anthropic(api_key=anthropic_key)
                    self.llm_type = 'anthropic'
                    logger.info("✅ NLQ Service initialized with Anthropic Claude")
                except Exception as e:
                    logger.warning(f"Anthropic initialization failed: {e}")
        
        if not self.llm_client:
            logger.info("⚠️  No LLM client available - using rule-based fallback")
        
        # Initialize RAG services
        self.embedding_service = EmbeddingService(db)
        self.rag_service = RAGRetrievalService(db, self.embedding_service)

    def query(self, question: str, user_id: int) -> Dict:
        """
        Process natural language query

        Args:
            question: User's natural language question
            user_id: User ID for logging

        Returns:
            dict: Answer with data, citations, and metadata
        """
        start_time = datetime.now()
        logger.info(f"Processing NLQ: '{question}' for user {user_id}")

        try:
            # 1. Check cache
            cached = self._check_cache(question)
            if cached:
                logger.info("Returning cached result")
                return cached

            # 2. If LLM is available, use it directly for better understanding
            if self.llm_client:
                logger.info("Using LLM for query understanding")
                return self._query_with_llm(question, user_id, start_time)
            
            # 3. Fallback to rule-based system if no LLM
            # Detect intent
            intent = self._detect_intent(question)
            logger.info(f"Detected intent: {intent['intent_type']}")

            # Retrieve data
            data_result = self._retrieve_data(intent)
            
            # Handle different return types (structured data vs hybrid)
            if isinstance(data_result, tuple):
                data, sql_query = data_result
                document_chunks = None
            elif isinstance(data_result, dict):
                # Hybrid query result
                data = data_result.get('structured_data', [])
                document_chunks = data_result.get('document_chunks', [])
                sql_query = data_result.get('sql_query')
            else:
                data = []
                sql_query = None
                document_chunks = None
            
            # For DSCR queries, allow empty results (might legitimately have no properties below threshold)
            # Still generate an answer even if no data found
            if not data and not document_chunks and 'dscr' not in question.lower():
                return {
                    "success": False,
                    "error": "No data found for query",
                    "question": question
                }

            # 4. Generate answer
            answer = self._generate_answer(question, data, intent, document_chunks=document_chunks)

            # 5. Extract citations
            citations = self._extract_citations(data, intent)

            # 6. Calculate confidence
            confidence = self._calculate_confidence(data, intent)

            # 7. Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 8. Store query (handle case where user_id might not exist)
            nlq = None
            try:
                # Serialize data (handle Decimal and other non-JSON types)
                serialized_data = self._serialize_data(data)
                if document_chunks:
                    # Also serialize document chunks
                    serialized_data['document_chunks'] = [
                        {
                            'chunk_id': chunk.get('chunk_id'),
                            'document_id': chunk.get('document_id'),
                            'similarity': float(chunk.get('similarity', 0)) if chunk.get('similarity') else None,
                            'property_name': chunk.get('property_name'),
                            'period': chunk.get('period'),
                            'file_name': chunk.get('file_name')
                        }
                        for chunk in document_chunks[:5]  # Limit to top 5
                    ]
                
                nlq = NLQQuery(
                    user_id=user_id,
                    question=question,
                    intent=intent,
                    answer=answer,
                    data_retrieved=serialized_data,
                    citations=citations,
                    confidence_score=confidence,
                    sql_query=sql_query,
                    execution_time_ms=execution_time_ms
                )
                self.db.add(nlq)
                self.db.commit()
                self.db.refresh(nlq)
            except Exception as e:
                # If user doesn't exist or other DB error, log but don't fail
                logger.warning(f"Failed to save NLQ query to database: {e}")
                self.db.rollback()

            result = {
                "success": True,
                "question": question,
                "answer": answer,
                "data": data,
                "document_chunks": document_chunks if document_chunks else [],
                "citations": citations,
                "confidence": confidence,
                "sql_query": sql_query,
                "execution_time_ms": execution_time_ms,
                "query_id": nlq.id if nlq else None
            }

            # Cache result
            self._cache_result(question, result)

            logger.info(f"NLQ processed in {execution_time_ms}ms")
            return result

        except Exception as e:
            logger.error(f"NLQ failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }

    def get_suggestions(self) -> List[str]:
        """Get suggested questions users can ask"""
        return [
            "What was the NOI for each property last quarter?",
            "Show me occupancy trends over the last year",
            "Which property has the highest operating expense ratio?",
            "Compare revenue for all properties in 2024",
            "What are the top 5 expenses for Eastern Shore Plaza?",
            "Show me properties with NOI greater than $1 million",
            "What is the average occupancy rate across all properties?",
            "Which properties had the highest revenue growth?",
            "Show me the cash position for Brookside Mall",
            "What was total revenue across all properties last month?"
        ]

    def get_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's query history"""
        queries = self.db.query(NLQQuery)\
            .filter(NLQQuery.user_id == user_id)\
            .order_by(NLQQuery.created_at.desc())\
            .limit(limit)\
            .all()

        return [q.to_dict() for q in queries]

    # Helper methods
    
    def _query_with_llm(self, question: str, user_id: int, start_time: datetime) -> Dict:
        """
        Use LLM directly to understand query, retrieve data, and generate answer
        
        This is the primary method when LLM is available - it's more flexible
        and can handle any question variation.
        """
        try:
            # Step 1: Use LLM to understand the query and determine what data is needed
            understanding_prompt = f"""You are a financial data analyst assistant. A user asked: "{question}"

Based on this question, determine:
1. What type of data is needed (properties with losses, revenue comparison, DSCR values, rent roll data, lease information, etc.)
2. What database tables/fields to query
3. Whether this needs structured data, document content, or both

IMPORTANT: If the question mentions:
- "rent roll", "lease", "occupied area", "vacant area", "tenancy", "tenant schedule"
- Specific document names or file references
- Data that might be in PDF documents
Then set "needs_document_content": true

Respond in JSON format:
{{
    "query_type": "loss_query|profit_query|dscr_query|revenue_query|trend_query|aggregation_query|document_query|hybrid_query",
    "needs_structured_data": true/false,
    "needs_document_content": true/false,
    "key_entities": {{
        "properties": ["list of property names if mentioned"],
        "metrics": ["list of metrics like 'net_income', 'revenue', 'dscr', 'occupied_area', 'lease_area'"],
        "filters": {{"loss": true/false, "profit": true/false, "threshold": number or null}}
    }},
    "sql_hint": "suggested SQL query approach"
}}"""

            if self.llm_type == 'openai':
                understanding_response = self.llm_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a financial data analyst. Respond only with valid JSON."},
                        {"role": "user", "content": understanding_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
                understanding_text = understanding_response.choices[0].message.content.strip()
            elif self.llm_type == 'anthropic':
                understanding_response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=300,
                    temperature=0.1,
                    messages=[{"role": "user", "content": understanding_prompt}]
                )
                understanding_text = understanding_response.content[0].text.strip()
            else:
                # Fallback to rule-based
                return self._query_fallback(question, user_id, start_time)
            
            # Parse understanding
            import json
            if understanding_text.startswith("```"):
                understanding_text = understanding_text.split("```")[1]
                if understanding_text.startswith("json"):
                    understanding_text = understanding_text[4:]
                understanding_text = understanding_text.strip()
            
            try:
                understanding = json.loads(understanding_text)
            except:
                # If JSON parsing fails, fallback to rule-based
                logger.warning("LLM understanding parse failed, using fallback")
                return self._query_fallback(question, user_id, start_time)
            
            # Step 2: Retrieve data based on LLM understanding
            data = []
            document_chunks = []
            sql_query = None
            
            query_type = understanding.get('query_type', '')
            needs_structured = understanding.get('needs_structured_data', True)
            needs_documents = understanding.get('needs_document_content', False)
            entities = understanding.get('key_entities', {})
            
            # Retrieve structured data if needed
            if needs_structured:
                # Check for rent roll area queries FIRST
                rent_roll_keywords = ['rent roll', 'occupied area', 'vacant area', 'lease area', 'total area']
                if any(keyword in question.lower() for keyword in rent_roll_keywords):
                    data, sql_query = self._query_rent_roll_metrics(entities, question)
                # Use understanding to build query
                elif 'loss' in query_type or (entities.get('filters', {}).get('loss')):
                    data, sql_query = self._query_loss_profit(entities, question)
                elif 'dscr' in query_type:
                    data, sql_query = self._query_dscr(entities, question.lower())
                elif 'revenue' in query_type or 'trend' in query_type:
                    # Create intent dict for existing methods
                    intent = {
                        'intent_type': 'trend_analysis' if 'trend' in query_type else 'metric_query',
                        'entities': entities,
                        'original_question': question
                    }
                    data, sql_query = self._query_trends(intent.get('entities', {}))
                elif 'aggregation' in query_type:
                    intent = {
                        'intent_type': 'aggregation',
                        'entities': {**entities, 'original_question': question},
                        'original_question': question
                    }
                    data, sql_query = self._query_aggregation(intent.get('entities', {}))
                else:
                    # Try general metric query
                    intent = {
                        'intent_type': 'metric_query',
                        'entities': entities,
                        'original_question': question
                    }
                    data, sql_query = self._query_metric(intent.get('entities', {}))
            
            # Retrieve document content if needed
            if needs_documents:
                document_chunks = self._query_document_content(entities, question)
            
            # Step 3: Generate comprehensive answer using LLM with retrieved data
            answer = self._generate_llm_answer_with_context(question, data, document_chunks, understanding)
            
            # Step 4: Extract citations and calculate confidence
            citations = self._extract_citations(data if data else [], {'intent_type': query_type})
            confidence = self._calculate_confidence(data if data else [], {'intent_type': query_type})
            
            # Step 5: Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Step 6: Store query
            nlq = None
            try:
                serialized_data = self._serialize_data(data if data else [])
                if document_chunks:
                    serialized_data['document_chunks'] = [
                        {
                            'chunk_id': chunk.get('chunk_id'),
                            'document_id': chunk.get('document_id'),
                            'similarity': float(chunk.get('similarity', 0)) if chunk.get('similarity') else None,
                            'property_name': chunk.get('property_name'),
                            'period': chunk.get('period'),
                            'file_name': chunk.get('file_name')
                        }
                        for chunk in document_chunks[:5]
                    ]
                
                nlq = NLQQuery(
                    user_id=user_id,
                    question=question,
                    intent={'query_type': query_type, 'understanding': understanding},
                    answer=answer,
                    data_retrieved=serialized_data,
                    citations=citations,
                    confidence_score=confidence,
                    sql_query=sql_query,
                    execution_time_ms=execution_time_ms
                )
                self.db.add(nlq)
                self.db.commit()
                self.db.refresh(nlq)
            except Exception as e:
                logger.warning(f"Failed to save NLQ query: {e}")
                self.db.rollback()
            
            result = {
                "success": True,
                "question": question,
                "answer": answer,
                "data": data if data else [],
                "document_chunks": document_chunks if document_chunks else [],
                "citations": citations,
                "confidence": confidence,
                "sql_query": sql_query,
                "execution_time_ms": execution_time_ms,
                "query_id": nlq.id if nlq else None
            }
            
            self._cache_result(question, result)
            logger.info(f"LLM query processed in {execution_time_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            # Fallback to rule-based system
            return self._query_fallback(question, user_id, start_time)
    
    def _query_fallback(self, question: str, user_id: int, start_time: datetime) -> Dict:
        """Fallback to rule-based query system"""
        # 2. Detect intent
        intent = self._detect_intent(question)
        logger.info(f"Detected intent: {intent['intent_type']}")

        # 3. Retrieve data
        data_result = self._retrieve_data(intent)
        
        # Handle different return types (structured data vs hybrid)
        if isinstance(data_result, tuple):
            data, sql_query = data_result
            document_chunks = None
        elif isinstance(data_result, dict):
            # Hybrid query result
            data = data_result.get('structured_data', [])
            document_chunks = data_result.get('document_chunks', [])
            sql_query = data_result.get('sql_query')
        else:
            data = []
            sql_query = None
            document_chunks = None
        
        # For DSCR queries, allow empty results (might legitimately have no properties below threshold)
        # Still generate an answer even if no data found
        if not data and not document_chunks and 'dscr' not in question.lower():
            return {
                "success": False,
                "error": "No data found for query",
                "question": question
            }

        # 4. Generate answer
        answer = self._generate_answer(question, data, intent, document_chunks=document_chunks)

        # 5. Extract citations
        citations = self._extract_citations(data, intent)

        # 6. Calculate confidence
        confidence = self._calculate_confidence(data, intent)

        # 7. Calculate execution time
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # 8. Store query
        nlq = None
        try:
            serialized_data = self._serialize_data(data)
            if document_chunks:
                serialized_data['document_chunks'] = [
                    {
                        'chunk_id': chunk.get('chunk_id'),
                        'document_id': chunk.get('document_id'),
                        'similarity': float(chunk.get('similarity', 0)) if chunk.get('similarity') else None,
                        'property_name': chunk.get('property_name'),
                        'period': chunk.get('period'),
                        'file_name': chunk.get('file_name')
                    }
                    for chunk in document_chunks[:5]
                ]
            
            nlq = NLQQuery(
                user_id=user_id,
                question=question,
                intent=intent,
                answer=answer,
                data_retrieved=serialized_data,
                citations=citations,
                confidence_score=confidence,
                sql_query=sql_query,
                execution_time_ms=execution_time_ms
            )
            self.db.add(nlq)
            self.db.commit()
            self.db.refresh(nlq)
        except Exception as e:
            logger.warning(f"Failed to save NLQ query: {e}")
            self.db.rollback()

        result = {
            "success": True,
            "question": question,
            "answer": answer,
            "data": data,
            "document_chunks": document_chunks if document_chunks else [],
            "citations": citations,
            "confidence": confidence,
            "sql_query": sql_query,
            "execution_time_ms": execution_time_ms,
            "query_id": nlq.id if nlq else None
        }

        self._cache_result(question, result)
        logger.info(f"NLQ processed in {execution_time_ms}ms")
        return result
    
    def _detect_intent(self, question: str) -> Dict:
        """
        Detect query intent

        Uses LLM if available, otherwise rule-based
        """
        question_lower = question.lower()

        # Rule-based intent detection
        # Check for "which" queries first (usually ranking/comparison)
        if any(word in question_lower for word in ['which', 'what']) and any(word in question_lower for word in ['property', 'properties']):
            # "which property" queries are usually ranking queries
            if any(word in question_lower for word in ['highest', 'lowest', 'top', 'bottom', 'best', 'worst', 'most', 'least']):
                intent_type = self.INTENT_RANKING
            elif any(word in question_lower for word in ['loss', 'losses', 'loses', 'losing', 'negative', 'profit', 'profitable', 'making']):
                # Loss/profit queries will be handled by _query_loss_profit
                intent_type = self.INTENT_RANKING
            else:
                intent_type = self.INTENT_RANKING  # Default "which" queries to ranking
        elif any(word in question_lower for word in ['compare', 'versus', 'vs', 'vs.', 'between']):
            intent_type = self.INTENT_COMPARISON
        elif any(word in question_lower for word in ['trend', 'over time', 'historical', 'change']):
            intent_type = self.INTENT_TREND_ANALYSIS
        elif any(word in question_lower for word in ['total', 'sum', 'average', 'mean', 'all properties']):
            intent_type = self.INTENT_AGGREGATION
        elif any(word in question_lower for word in ['highest', 'lowest', 'top', 'bottom', 'best', 'worst']):
            intent_type = self.INTENT_RANKING
        else:
            intent_type = self.INTENT_METRIC_QUERY

        # Extract entities
        entities = {
            'properties': self._extract_properties(question),
            'metrics': self._extract_metrics(question),
            'time_period': self._extract_time_period(question),
            'original_question': question
        }

        return {
            'intent_type': intent_type,
            'entities': entities,
            'original_question': question,
            'query_type': 'structured_data'
        }

    def _extract_properties(self, question: str) -> List[str]:
        """Extract property names from question"""
        properties = self.db.query(Property.property_name, Property.property_code).all()

        mentioned = []
        question_lower = question.lower()

        for prop_name, prop_code in properties:
            if prop_name.lower() in question_lower or prop_code.lower() in question_lower:
                mentioned.append(prop_name)

        return mentioned

    def _extract_metrics(self, question: str) -> List[str]:
        """Extract metrics from question"""
        metrics = []
        question_lower = question.lower()

        # Check for DSCR specifically
        if 'dscr' in question_lower or 'debt service coverage' in question_lower or 'debt service coverage ratio' in question_lower:
            metrics.append('dscr')
        
        # Check for portfolio value
        if 'portfolio value' in question_lower or 'total portfolio' in question_lower or ('total' in question_lower and 'value' in question_lower):
            metrics.append('portfolio_value')
        
        # Check for loss/profit queries (handle typos and variations)
        loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
        profit_keywords = ['profit', 'profits', 'profitable', 'making money', 'earning']
        
        if any(keyword in question_lower for keyword in loss_keywords):
            metrics.append('loss')
        elif any(keyword in question_lower for keyword in profit_keywords):
            metrics.append('profit')
        
        # Check for net income (often related to loss/profit)
        if 'net income' in question_lower or 'net profit' in question_lower or 'net loss' in question_lower:
            metrics.append('net_income')
        
        for metric_name in self.METRIC_MAPPINGS.keys():
            if metric_name in question_lower:
                metrics.append(metric_name)

        return metrics

    def _extract_time_period(self, question: str) -> Optional[Dict]:
        """Extract time period from question"""
        question_lower = question.lower()

        # Simple patterns
        if 'last quarter' in question_lower or 'q4' in question_lower:
            return {'period': 'last_quarter'}
        elif 'last year' in question_lower or 'last 12 months' in question_lower:
            return {'period': 'last_year'}
        elif 'last month' in question_lower:
            return {'period': 'last_month'}
        elif re.search(r'20\d{2}', question):
            # Extract year
            year_match = re.search(r'20\d{2}', question)
            return {'year': int(year_match.group())}

        return None

    def _retrieve_data(self, intent: Dict) -> tuple:
        """
        Retrieve data from database based on intent

        Returns: (data, sql_query)
        """
        intent_type = intent['intent_type']
        entities = intent['entities']
        question_lower = intent.get('original_question', '').lower()

        # Check for DSCR-specific queries
        if 'dscr' in question_lower or 'debt service coverage' in question_lower:
            return self._query_dscr(entities, question_lower)
        
        # Check for loss/profit queries
        loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
        profit_keywords = ['profit', 'profits', 'profitable', 'making money', 'earning']
        
        if any(keyword in question_lower for keyword in loss_keywords + profit_keywords):
            return self._query_loss_profit(entities, question_lower)
        
        # Check for portfolio value queries (should use aggregation)
        if 'portfolio value' in question_lower or ('total portfolio' in question_lower and 'value' in question_lower):
            intent_type = self.INTENT_AGGREGATION
            # Add portfolio_value to metrics for detection
            if 'portfolio_value' not in entities.get('metrics', []):
                entities['metrics'] = entities.get('metrics', []) + ['portfolio_value']
        
        if intent_type == self.INTENT_METRIC_QUERY:
            return self._query_metric(entities)
        elif intent_type == self.INTENT_COMPARISON:
            return self._query_comparison(entities)
        elif intent_type == self.INTENT_TREND_ANALYSIS:
            return self._query_trends(entities)
        elif intent_type == self.INTENT_AGGREGATION:
            # Ensure original_question is in entities for _query_aggregation
            if 'original_question' not in entities:
                entities['original_question'] = question_lower
            return self._query_aggregation(entities)
        elif intent_type == self.INTENT_RANKING:
            return self._query_ranking(entities)
        else:
            return [], None
    
    def _retrieve_structured_data(self, intent_type: str, entities: Dict, question_lower: str) -> tuple:
        """Retrieve structured data from database (existing logic)"""
        if intent_type == self.INTENT_METRIC_QUERY:
            return self._query_metric(entities)
        elif intent_type == self.INTENT_COMPARISON:
            return self._query_comparison(entities)
        elif intent_type == self.INTENT_TREND_ANALYSIS:
            return self._query_trends(entities)
        elif intent_type == self.INTENT_AGGREGATION:
            # Ensure original_question is in entities for _query_aggregation
            if 'original_question' not in entities:
                entities['original_question'] = question_lower
            return self._query_aggregation(entities)
        elif intent_type == self.INTENT_RANKING:
            return self._query_ranking(entities)
        else:
            return [], None
    
    def _query_document_content(self, entities: Dict, question: str) -> List[Dict]:
        """
        Query document content using RAG
        
        Returns: List of relevant chunks
        """
        # Extract property/period filters from entities
        property_id = None
        period_id = None
        document_type = None
        
        # Try to find property ID from property names
        properties = entities.get('properties', [])
        if properties:
            property_obj = self.db.query(Property).filter(
                Property.property_name.in_(properties)
            ).first()
            if property_obj:
                property_id = property_obj.id
        
        # Extract document type if mentioned
        question_lower = question.lower()
        if 'income statement' in question_lower:
            document_type = 'income_statement'
        elif 'balance sheet' in question_lower:
            document_type = 'balance_sheet'
        elif 'cash flow' in question_lower:
            document_type = 'cash_flow'
        elif 'rent roll' in question_lower:
            document_type = 'rent_roll'
        
        # Retrieve relevant chunks
        chunks = self.rag_service.retrieve_relevant_chunks(
            query=question,
            top_k=5,
            property_id=property_id,
            period_id=period_id,
            document_type=document_type,
            min_similarity=0.3
        )
        
        return chunks
    
    def _retrieve_document_content(self, entities: Dict, question: str) -> List[Dict]:
        """Helper to retrieve document content (used in hybrid queries)"""
        return self._query_document_content(entities, question)
    
    def _generate_answer_from_chunks(self, question: str, chunks: List[Dict], structured_data: List[Dict] = None) -> str:
        """
        Generate answer from document chunks using LLM
        
        Args:
            question: User's question
            chunks: Retrieved document chunks
            structured_data: Optional structured data to combine
        
        Returns:
            Generated answer
        """
        if not self.llm_client:
            # Fallback: return chunk summaries
            answer_parts = [f"Found {len(chunks)} relevant document sections:\n"]
            for idx, chunk in enumerate(chunks[:5], 1):
                answer_parts.append(f"\n{idx}. From {chunk.get('file_name', 'document')} ({chunk.get('property_name', 'N/A')}, {chunk.get('period', 'N/A')}):")
                answer_parts.append(f"   {chunk['chunk_text'][:300]}...")
            return "\n".join(answer_parts)
        
        # Build context from chunks
        context_parts = []
        for chunk in chunks[:5]:  # Limit to top 5 chunks
            context_parts.append(
                f"[Document: {chunk.get('file_name', 'Unknown')}, "
                f"Property: {chunk.get('property_name', 'N/A')}, "
                f"Period: {chunk.get('period', 'N/A')}]\n"
                f"{chunk['chunk_text']}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Add structured data if available
        structured_context = ""
        if structured_data:
            structured_context = f"\n\nStructured Data:\n{json.dumps(structured_data[:3], indent=2)}"
        
        # Generate answer with LLM
        prompt = f"""Based on the following document excerpts and any structured data provided, answer the user's question accurately.

User Question: "{question}"

Document Excerpts:
{context}
{structured_context}

Instructions:
- Answer based on the document content provided
- If the answer isn't in the documents, say so
- Cite specific information from the documents
- Be concise and accurate
- If structured data is provided, you can reference it but prioritize document content

Answer:"""

        try:
            if self.llm_type == 'openai':
                response = self.llm_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a financial data assistant. Answer questions based on provided document excerpts."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            
            elif self.llm_type == 'anthropic':
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"LLM answer generation from chunks failed: {e}")
            # Fallback
            answer_parts = [f"Found {len(chunks)} relevant document sections:\n"]
            for idx, chunk in enumerate(chunks[:3], 1):
                answer_parts.append(f"\n{idx}. {chunk.get('file_name', 'document')}: {chunk['chunk_text'][:200]}...")
            return "\n".join(answer_parts)

    def _query_dscr(self, entities: Dict, question: str) -> tuple:
        """Query DSCR data from database"""
        from app.models.financial_metrics import FinancialMetrics
        from app.models.financial_period import FinancialPeriod
        from app.models.property import Property
        from app.services.dscr_monitoring_service import DSCRMonitoringService
        
        # Extract threshold if mentioned (e.g., "below 1.25")
        threshold = 1.25  # Default threshold
        threshold_match = re.search(r'below\s+([\d.]+)|under\s+([\d.]+)|less than\s+([\d.]+)', question)
        if threshold_match:
            threshold = float(threshold_match.group(1) or threshold_match.group(2) or threshold_match.group(3))
        
        # Get all properties with their latest DSCR
        # Note: Property model may not have 'status' field, so get all properties
        properties = self.db.query(Property).all()
        dscr_service = DSCRMonitoringService(self.db)
        
        results = []
        for prop in properties:
            # Get periods with debt service data (mortgage interest exists)
            # Try to find period with mortgage interest (account 7010-0000)
            from app.models.income_statement_data import IncomeStatementData
            
            periods_with_debt = (
                self.db.query(FinancialPeriod)
                .join(IncomeStatementData, IncomeStatementData.period_id == FinancialPeriod.id)
                .filter(
                    FinancialPeriod.property_id == prop.id,
                    IncomeStatementData.account_code == '7010-0000',
                    IncomeStatementData.period_amount.isnot(None),
                    IncomeStatementData.period_amount != 0
                )
                .order_by(FinancialPeriod.period_end_date.desc())
                .all()
            )
            
            # Use period with debt service data, or fallback to latest period
            target_period = periods_with_debt[0] if periods_with_debt else (
                self.db.query(FinancialPeriod)
                .filter(FinancialPeriod.property_id == prop.id)
                .order_by(FinancialPeriod.period_end_date.desc())
                .first()
            )
            
            if not target_period:
                continue
            
            # Calculate DSCR
            dscr_result = dscr_service.calculate_dscr(prop.id, target_period.id)
            
            if dscr_result.get('success') and dscr_result.get('dscr'):
                dscr_value = float(dscr_result['dscr'])
                noi = float(dscr_result.get('noi', 0))
                debt_service = float(dscr_result.get('total_debt_service', 0))
                
                # Filter based on threshold if mentioned
                if 'below' in question or 'under' in question or 'less than' in question:
                    if dscr_value >= threshold:
                        continue
                elif 'above' in question or 'over' in question or 'greater than' in question:
                    if dscr_value <= threshold:
                        continue
                
                results.append({
                    'property_name': prop.property_name,
                    'property_code': prop.property_code,
                    'dscr': dscr_value,
                    'noi': noi,
                    'debt_service': debt_service,
                    'period_year': target_period.period_year,
                    'period_month': target_period.period_month,
                    'status': dscr_result.get('status', 'unknown'),
                    'gap': max(0, debt_service - noi) if dscr_value < threshold else 0
                })
        
        # Sort by DSCR (lowest first for "below" queries)
        if 'below' in question or 'under' in question:
            results.sort(key=lambda x: x['dscr'])
        else:
            results.sort(key=lambda x: x['dscr'], reverse=True)
        
        sql_query = f"""
        SELECT p.property_name, p.property_code, fm.dscr, fm.net_operating_income as noi, 
               fp.period_year, fp.period_month
        FROM properties p
        JOIN financial_metrics fm ON p.id = fm.property_id
        JOIN financial_periods fp ON fm.period_id = fp.id
        WHERE fm.dscr IS NOT NULL
        ORDER BY fm.dscr ASC
        """
        
        return results, sql_query
    
    def _query_loss_profit(self, entities: Dict, question: str) -> tuple:
        """
        Query for properties with losses or profits
        
        Handles queries like:
        - "which property is making loses for me?"
        - "show me properties with losses"
        - "which properties are profitable?"
        """
        question_lower = question.lower()
        
        # Determine if looking for losses or profits
        loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
        is_loss_query = any(keyword in question_lower for keyword in loss_keywords)
        
        # Query properties with net income data
        sql = """
        SELECT 
            p.property_name,
            p.property_code,
            fm.net_income,
            fm.net_operating_income as noi,
            fm.total_revenue,
            fm.total_expenses,
            fp.period_year,
            fp.period_month,
            CONCAT(fp.period_year, '-', LPAD(fp.period_month::text, 2, '0')) as period
        FROM properties p
        JOIN financial_periods fp ON p.id = fp.property_id
        JOIN financial_metrics fm ON fp.id = fm.period_id
        WHERE fm.net_income IS NOT NULL
        """
        
        # Get latest period for each property
        sql += """
          AND fp.id IN (
              SELECT MAX(fp2.id)
              FROM financial_periods fp2
              JOIN financial_metrics fm2 ON fp2.id = fm2.period_id
              WHERE fp2.property_id = p.id
                AND fm2.net_income IS NOT NULL
          )
        """
        
        # Filter by loss or profit
        if is_loss_query:
            sql += " AND fm.net_income < 0"
        else:
            sql += " AND fm.net_income > 0"
        
        sql += " ORDER BY fm.net_income ASC" if is_loss_query else " ORDER BY fm.net_income DESC"
        
        try:
            result = self.db.execute(text(sql)).fetchall()
            data = [dict(r._mapping) for r in result]
            
            return data, sql
        except Exception as e:
            logger.error(f"Error querying loss/profit: {e}")
            return [], None
    
    def _query_metric(self, entities: Dict) -> tuple:
        """Query for specific metric value"""
        properties = entities.get('properties', [])
        metrics = entities.get('metrics', [])

        if not metrics:
            return [], None

        # Build query
        sql_parts = []
        params = {}

        for metric in metrics:
            mapping = self.METRIC_MAPPINGS.get(metric)
            if not mapping:
                continue

            if mapping['table'] == 'income_statement':
                sql = """
                SELECT p.property_name, fp.period_name, isd.period_amount, isd.account_name
                FROM income_statement_data isd
                JOIN properties p ON isd.property_id = p.id
                JOIN financial_periods fp ON isd.period_id = fp.id
                WHERE isd.account_name LIKE :metric
                """
                if properties:
                    sql += " AND p.property_name IN :properties"
                    params['properties'] = tuple(properties)

                sql += " ORDER BY fp.period_year DESC, fp.period_month DESC LIMIT 10"
                params['metric'] = f'%{mapping["field"]}%'

                result = self.db.execute(text(sql), params).fetchall()
                return [dict(r._mapping) for r in result], sql

        return [], None

    def _query_comparison(self, entities: Dict) -> tuple:
        """Query for comparison between properties"""
        properties = entities.get('properties', [])
        metrics = entities.get('metrics', ['revenue'])  # Default to revenue

        if len(properties) < 2:
            # Get all properties for comparison
            sql = """
            SELECT p.property_name, SUM(isd.period_amount) as total
            FROM income_statement_data isd
            JOIN properties p ON isd.property_id = p.id
            WHERE isd.account_name LIKE '%revenue%'
            GROUP BY p.property_name
            ORDER BY total DESC
            """
        else:
            sql = """
            SELECT p.property_name, SUM(isd.period_amount) as total
            FROM income_statement_data isd
            JOIN properties p ON isd.property_id = p.id
            WHERE isd.account_name LIKE '%revenue%'
            AND p.property_name IN :properties
            GROUP BY p.property_name
            ORDER BY total DESC
            """

        params = {'properties': tuple(properties)} if properties and len(properties) >= 2 else {}
        result = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _query_trends(self, entities: Dict) -> tuple:
        """Query for trends over time"""
        properties = entities.get('properties', [])
        metrics = entities.get('metrics', [])
        
        # Determine what metric to query
        query_metric = 'revenue'  # default
        if 'noi' in [m.lower() for m in metrics] or 'net operating income' in [m.lower() for m in metrics]:
            # Query NOI from financial_metrics table
            sql = """
            SELECT 
                p.property_name, 
                p.property_code,
                fp.period_year as year, 
                fp.period_month as month, 
                CONCAT(fp.period_year, '-', LPAD(fp.period_month::text, 2, '0')) as period_name,
                fm.net_operating_income as value
            FROM financial_metrics fm
            JOIN properties p ON fm.property_id = p.id
            JOIN financial_periods fp ON fm.period_id = fp.id
            WHERE fm.net_operating_income IS NOT NULL
            """
            
            params = {}
            if properties:
                sql += " AND p.property_name IN :properties"
                params['properties'] = tuple(properties)
            
            # Get last 12 months
            sql += " AND fp.period_end_date >= CURRENT_DATE - INTERVAL '12 months'"
            sql += " ORDER BY p.property_name, fp.period_year DESC, fp.period_month DESC LIMIT 24"
            
            result = self.db.execute(text(sql), params).fetchall()
            return [dict(r._mapping) for r in result], sql
        
        # Default: revenue query (existing logic)
        sql = """
        SELECT p.property_name, fp.period_year as year, fp.period_month as month, 
               CONCAT(fp.period_year, '-', LPAD(fp.period_month::text, 2, '0')) as period_name, 
               SUM(isd.period_amount) as value
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        JOIN financial_periods fp ON isd.period_id = fp.id
        WHERE isd.account_code = '4990-0000'  -- Total Revenue account code
        """
        
        params = {}
        if properties:
            sql += " AND p.property_name IN :properties"
            params['properties'] = tuple(properties)
        
        sql += " AND fp.period_end_date >= CURRENT_DATE - INTERVAL '12 months'"
        sql += " GROUP BY p.property_name, fp.period_year, fp.period_month"
        sql += " ORDER BY p.property_name, fp.period_year DESC, fp.period_month DESC LIMIT 24"
        
        result = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _query_aggregation(self, entities: Dict) -> tuple:
        """Query for aggregated data"""
        metrics = entities.get('metrics', [])
        question_lower = entities.get('original_question', '').lower()
        
        # Check if this is a portfolio value query
        if 'portfolio value' in question_lower or 'total portfolio' in question_lower or ('total' in question_lower and 'value' in question_lower and 'portfolio' in question_lower):
            # Query total assets from financial_metrics (portfolio value)
            # Get latest period WITH financial_metrics for each property
            sql = """
            WITH latest_periods AS (
                SELECT p.id as property_id, MAX(fp.id) as period_id
                FROM properties p
                JOIN financial_periods fp ON p.id = fp.property_id
                JOIN financial_metrics fm ON fp.id = fm.period_id
                WHERE fm.total_assets IS NOT NULL
                GROUP BY p.id
            )
            SELECT
                COUNT(DISTINCT p.id) as property_count,
                SUM(fm.total_assets) as total_portfolio_value,
                AVG(fm.total_assets) as avg_property_value,
                SUM(fm.total_equity) as total_equity,
                SUM(fm.total_liabilities) as total_liabilities,
                SUM(fm.net_operating_income) as total_noi,
                MAX(fp.period_end_date) as latest_period_date
            FROM properties p
            JOIN latest_periods lp ON p.id = lp.property_id
            JOIN financial_periods fp ON lp.period_id = fp.id
            JOIN financial_metrics fm ON fp.id = fm.period_id
            WHERE fm.total_assets IS NOT NULL
            """
            
            result = self.db.execute(text(sql)).fetchall()
            return [dict(r._mapping) for r in result], sql
        
        # Default: revenue aggregation
        sql = """
        SELECT
            COUNT(DISTINCT p.id) as property_count,
            SUM(isd.period_amount) as total_revenue,
            AVG(isd.period_amount) as avg_revenue
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        JOIN financial_periods fp ON isd.period_id = fp.id
        WHERE isd.account_code = '4990-0000'
          AND fp.id IN (
              SELECT MAX(fp2.id)
              FROM financial_periods fp2
              WHERE fp2.property_id = p.id
          )
        """

        result = self.db.execute(text(sql)).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _query_ranking(self, entities: Dict) -> tuple:
        """Query for ranking/top items"""
        direction = 'DESC'  # Highest
        if any(word in entities.get('original_question', '').lower() for word in ['lowest', 'bottom', 'worst']):
            direction = 'ASC'

        sql = f"""
        SELECT p.property_name, SUM(isd.period_amount) as total
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        JOIN financial_periods fp ON isd.period_id = fp.id
        WHERE isd.account_code = '4990-0000'
          AND fp.id IN (
              SELECT MAX(fp2.id)
              FROM financial_periods fp2
              WHERE fp2.property_id = p.id
          )
        GROUP BY p.property_name
        ORDER BY total {direction}
        LIMIT 5
        """

        result = self.db.execute(text(sql)).fetchall()
        return [dict(r._mapping) for r in result], sql
    
    def _query_rent_roll_metrics(self, entities: Dict, question: str) -> tuple:
        """
        Query rent roll metrics like occupied area, vacant area, etc.
        
        Returns: (data, sql_query)
        """
        question_lower = question.lower()
        properties = entities.get('properties', [])
        
        # Extract property name from question if not in entities
        property_name = None
        property_code = None
        if 'hammond' in question_lower:
            property_name = 'Hammond Aire Shopping Center'
            property_code = 'HMND001'
        elif 'wendover' in question_lower or 'wend' in question_lower:
            property_name = 'Wendover Commons'
            property_code = 'WEND001'
        elif 'eastern shore' in question_lower or 'esp' in question_lower:
            property_name = 'Eastern Shore Plaza'
            property_code = 'ESP001'
        elif 'spring hill' in question_lower or 'crossing' in question_lower:
            property_name = 'The Crossings of Spring Hill'
            property_code = 'TCSH001'
        
        # Extract period from question
        period_year = None
        period_month = None
        if 'april 2025' in question_lower or '2025-04' in question_lower:
            period_year = 2025
            period_month = 4
        elif '2024' in question_lower:
            period_year = 2024
            # Try to extract month
            if 'december' in question_lower or 'dec' in question_lower:
                period_month = 12
        
        # Build query - use unit_area_sqft (correct column name)
        query = self.db.query(
            Property.property_name,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            RentRollData.unit_area_sqft,
            RentRollData.occupancy_status
        ).join(
            FinancialPeriod, RentRollData.period_id == FinancialPeriod.id
        ).join(
            Property, RentRollData.property_id == Property.id
        )
        
        # Apply filters - try property code first, then name
        if property_code:
            query = query.filter(Property.property_code == property_code)
        elif property_name:
            query = query.filter(Property.property_name == property_name)
        elif properties:
            query = query.filter(Property.property_name.in_(properties))
        
        if period_year:
            query = query.filter(FinancialPeriod.period_year == period_year)
        if period_month:
            query = query.filter(FinancialPeriod.period_month == period_month)
        
        records = query.all()
        
        # Aggregate data
        total_area = 0
        occupied_area = 0
        vacant_area = 0
        occupied_units = 0
        vacant_units = 0
        
        for record in records:
            area = float(record.unit_area_sqft or 0)
            total_area += area
            
            if record.occupancy_status and record.occupancy_status.lower() == 'occupied':
                occupied_area += area
                occupied_units += 1
            elif record.occupancy_status and record.occupancy_status.lower() == 'vacant':
                vacant_area += area
                vacant_units += 1
        
        if total_area > 0:
            occupancy_rate = (occupied_area / total_area) * 100
        else:
            occupancy_rate = 0
        
        # Build result
        if total_area > 0:
            result = [{
                'property_name': records[0].property_name if records else None,
                'property_code': records[0].property_code if records else None,
                'period_year': records[0].period_year if records else None,
                'period_month': records[0].period_month if records else None,
                'total_area': total_area,
                'occupied_area': occupied_area,
                'vacant_area': vacant_area,
                'occupied_units': occupied_units,
                'vacant_units': vacant_units,
                'occupancy_rate': occupancy_rate
            }]
        else:
            result = []
        
        sql_query = f"""
        SELECT 
            p.property_name,
            p.property_code,
            fp.period_year,
            fp.period_month,
            SUM(CASE WHEN rr.occupancy_status = 'occupied' THEN rr.unit_area_sqft ELSE 0 END) as occupied_area,
            SUM(CASE WHEN rr.occupancy_status = 'vacant' THEN rr.unit_area_sqft ELSE 0 END) as vacant_area,
            SUM(rr.unit_area_sqft) as total_area,
            COUNT(CASE WHEN rr.occupancy_status = 'occupied' THEN 1 END) as occupied_units,
            COUNT(CASE WHEN rr.occupancy_status = 'vacant' THEN 1 END) as vacant_units
        FROM rent_roll_data rr
        JOIN properties p ON rr.property_id = p.id
        JOIN financial_periods fp ON rr.period_id = fp.id
        WHERE {'p.property_code = :property_code' if property_code else ('p.property_name = :property_name' if property_name else '1=1')}
        {'AND fp.period_year = :period_year' if period_year else ''}
        {'AND fp.period_month = :period_month' if period_month else ''}
        GROUP BY p.property_name, p.property_code, fp.period_year, fp.period_month
        """
        
        return result, sql_query

    def _generate_answer(self, question: str, data: List[Dict], intent: Dict, document_chunks: List[Dict] = None) -> str:
        """Generate natural language answer from data and/or document chunks"""
        question_lower = question.lower()
        
        # Handle document content queries
        if document_chunks and len(document_chunks) > 0:
            return self._generate_answer_from_chunks(question, document_chunks, data)
        
        # Check if this is a DSCR query - use specialized answer generator
        if 'dscr' in question_lower and data:
            return self._generate_dscr_answer(question, data)
        
        # Check if this is a trend query
        if ('trend' in question_lower or 'over time' in question_lower or 'last 12 months' in question_lower or 'last year' in question_lower) and data:
            return self._generate_trend_answer(question, data, intent)
        
        # Check if this is a loss/profit query
        loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
        profit_keywords = ['profit', 'profits', 'profitable', 'making money', 'earning']
        if any(keyword in question_lower for keyword in loss_keywords + profit_keywords) and data:
            return self._generate_loss_profit_answer(question, data, intent)
        
        # Check if this is a rent roll area query - use specialized answer generator
        rent_roll_area_keywords = ['occupied area', 'vacant area', 'lease area', 'total area', 'rent roll']
        if any(keyword in question_lower for keyword in rent_roll_area_keywords) and data:
            return self._generate_rent_roll_area_answer(question, data, intent)
        
        if not self.llm_client:
            return self._template_answer(question, data, intent)
        
        # Prepare data for LLM
        data_json = json.dumps(data, indent=2, default=str)

        prompt = f"""You are a financial analyst assistant. Answer the user's question using ONLY the data provided.

User Question: {question}

Retrieved Data:
{data_json}

CRITICAL RULES:
1. Use ONLY the data above
2. Be specific with numbers and property names
3. Format currency as $X,XXX.XX
4. Format percentages as XX.X%
5. Keep answer concise (2-3 sentences max)
6. If data is insufficient, state what's missing

Generate a clear, accurate answer:"""

        try:
            if self.llm_type == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview'),
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst. You ONLY use provided data."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=300
                )
                return response.choices[0].message.content

            elif self.llm_type == 'anthropic':
                response = self.llm_client.messages.create(
                    model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                    max_tokens=300,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            return self._template_answer(question, data, intent)
    
    def _generate_llm_answer_with_context(self, question: str, data: List[Dict], document_chunks: List[Dict], understanding: Dict) -> str:
        """
        Generate answer using LLM with full context from structured data and documents
        
        This is the primary answer generation method when LLM is available
        """
        if not self.llm_client:
            return self._template_answer(question, data, {'intent_type': understanding.get('query_type', 'metric_query')})
        
        # Build comprehensive context
        context_parts = []
        
        # Add structured data context
        if data:
            data_summary = []
            for idx, row in enumerate(data[:20], 1):  # Limit to 20 rows
                row_summary = {}
                for key, value in row.items():
                    if value is not None:
                        if hasattr(value, '__float__'):
                            try:
                                row_summary[key] = float(value)
                            except:
                                row_summary[key] = str(value)
                        elif hasattr(value, 'isoformat'):
                            row_summary[key] = value.isoformat()
                        else:
                            row_summary[key] = value
                data_summary.append(row_summary)
            
            context_parts.append("**Structured Financial Data:**")
            context_parts.append(json.dumps(data_summary, indent=2, default=str))
        
        # Add document content context
        if document_chunks:
            doc_context = []
            for chunk in document_chunks[:5]:
                doc_context.append(
                    f"[Document: {chunk.get('file_name', 'Unknown')}, "
                    f"Property: {chunk.get('property_name', 'N/A')}, "
                    f"Period: {chunk.get('period', 'N/A')}, "
                    f"Similarity: {chunk.get('similarity', 0):.2f}]\n"
                    f"{chunk.get('chunk_text', '')[:500]}"
                )
            context_parts.append("\n**Relevant Document Excerpts:**")
            context_parts.append("\n---\n".join(doc_context))
        
        context = "\n\n".join(context_parts) if context_parts else "No specific data found."
        
        # Build comprehensive prompt
        prompt = f"""You are a financial analyst assistant helping users understand their real estate investment portfolio.

**User Question:** "{question}"

**Query Understanding:**
- Query Type: {understanding.get('query_type', 'general')}
- Needs Structured Data: {understanding.get('needs_structured_data', False)}
- Needs Document Content: {understanding.get('needs_document_content', False)}

**Available Data:**
{context}

**Instructions:**
1. Answer the user's question directly and accurately using the provided data
2. If the question asks about losses/profits, focus on net_income values
3. Format currency values clearly (e.g., $1.2M, $500K, $1,234)
4. Include specific property names and codes when relevant
5. If data shows losses, provide actionable insights
6. Be concise but comprehensive
7. If the answer isn't in the data, say so clearly
8. Use the document excerpts to provide additional context if relevant

**Generate a clear, helpful answer:**"""

        try:
            if self.llm_type == 'openai':
                response = self.llm_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst assistant. Answer questions accurately using provided data."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            
            elif self.llm_type == 'anthropic':
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"LLM answer generation with context failed: {e}")
            # Fallback to template answer
            return self._template_answer(question, data, {'intent_type': understanding.get('query_type', 'metric_query')})
        
        return "I apologize, but I encountered an error generating the answer. Please try rephrasing your question."

    def _generate_dscr_answer(self, question: str, data: List[Dict]) -> str:
        """Generate DSCR-specific answer"""
        if not data:
            return "I couldn't find any properties matching your DSCR criteria."
        
        question_lower = question.lower()
        threshold = 1.25
        threshold_match = re.search(r'below\s+([\d.]+)|under\s+([\d.]+)|less than\s+([\d.]+)', question_lower)
        if threshold_match:
            threshold = float(threshold_match.group(1) or threshold_match.group(2) or threshold_match.group(3))
        
        answer_parts = [f"Found {len(data)} property(ies) with DSCR {'below' if 'below' in question_lower else 'above'} {threshold}:\n"]
        
        for idx, prop in enumerate(data[:10], 1):  # Limit to 10 properties
            prop_name = prop.get('property_name', 'Unknown Property')
            dscr = prop.get('dscr', 0)
            noi = prop.get('noi', 0)
            debt_service = prop.get('debt_service', 0)
            gap = prop.get('gap', 0)
            
            # Format NOI and debt service
            noi_formatted = f"${noi/1000:.1f}K" if noi >= 1000 else f"${noi:,.0f}"
            debt_formatted = f"${debt_service/1000:.1f}K" if debt_service >= 1000 else f"${debt_service:,.0f}"
            
            # Calculate percentage below threshold
            pct_below = ((threshold - dscr) / threshold * 100) if dscr < threshold else 0
            
            status_icon = "🔴" if dscr < 1.25 else "🟡" if dscr < 1.5 else "🟢"
            
            answer_parts.append(
                f"{idx}. {status_icon} **{prop_name}** ({prop.get('property_code', 'N/A')}) - DSCR: {dscr:.2f}"
            )
            
            if pct_below > 0:
                answer_parts.append(f"   ({pct_below:.1f}% below threshold)")
            
            answer_parts.append(f"   NOI: {noi_formatted} | Debt Service: {debt_formatted}/year")
            
            if gap > 0:
                gap_formatted = f"${gap/1000:.1f}K" if gap >= 1000 else f"${gap:,.0f}"
                answer_parts.append(f"   Gap: Needs {gap_formatted} additional NOI")
            
            answer_parts.append("")
        
        if len(data) > 10:
            answer_parts.append(f"\n... and {len(data) - 10} more property(ies)")
        
        # Add recommendation if any properties below threshold
        below_threshold = [p for p in data if p.get('dscr', 0) < threshold]
        if below_threshold:
            answer_parts.append(f"\n💡 Recommendation: Review {len(below_threshold)} property(ies) with DSCR below {threshold} for potential refinancing or operational improvements.")
        
        return "\n".join(answer_parts)
    
    def _generate_trend_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Generate answer for trend queries"""
        if not data:
            return "I couldn't find any trend data for your query."
        
        # Group by property
        by_property = {}
        for row in data:
            prop_name = row.get('property_name', 'Unknown')
            if prop_name not in by_property:
                by_property[prop_name] = []
            
            period_name = row.get('period_name')
            if not period_name:
                year = row.get('year', 0)
                month = row.get('month', 0)
                period_name = f"{year}-{str(month).zfill(2)}"
            
            by_property[prop_name].append({
                'period': period_name,
                'value': float(row.get('value', 0))
            })
        
        answer_parts = []
        for prop_name, periods in by_property.items():
            # Sort by period (most recent first)
            periods.sort(key=lambda x: x['period'], reverse=True)
            
            if not periods:
                continue
                
            latest = periods[0]['value']
            oldest = periods[-1]['value'] if len(periods) > 1 else latest
            
            # Format value
            if latest >= 1000000:
                latest_formatted = f"${latest/1000000:.2f}M"
            elif latest >= 1000:
                latest_formatted = f"${latest/1000:.1f}K"
            else:
                latest_formatted = f"${latest:,.0f}"
            
            answer_parts.append(f"**{prop_name}**: Latest value: {latest_formatted}")
            
            if len(periods) > 1:
                change = latest - oldest
                pct_change = (change / oldest * 100) if oldest != 0 else 0
                change_formatted = f"${change/1000:.1f}K" if abs(change) >= 1000 else f"${change:,.0f}"
                
                answer_parts.append(
                    f"  📈 Trend: {change_formatted} ({pct_change:+.1f}%) change over {len(periods)} periods"
                )
                answer_parts.append(f"  Periods: {periods[-1]['period']} to {periods[0]['period']}")
            else:
                answer_parts.append(f"  Period: {periods[0]['period']}")
            
            answer_parts.append("")  # Empty line between properties
        
        return "\n".join(answer_parts)
    
    def _generate_loss_profit_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Generate answer for loss/profit queries"""
        if not data:
            question_lower = question.lower()
            loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
            if any(keyword in question_lower for keyword in loss_keywords):
                return "✅ Good news! I couldn't find any properties with losses. All properties appear to be profitable."
            else:
                return "I couldn't find any profitable properties matching your criteria."
        
        question_lower = question.lower()
        loss_keywords = ['loss', 'losses', 'loses', 'losing', 'negative', 'deficit', 'unprofitable', 'not profitable', 'making loss', 'making loses']
        is_loss_query = any(keyword in question_lower for keyword in loss_keywords)
        
        if is_loss_query:
            answer_parts = [f"Found {len(data)} property(ies) with losses:\n"]
        else:
            answer_parts = [f"Found {len(data)} profitable property(ies):\n"]
        
        for idx, prop in enumerate(data[:10], 1):  # Limit to 10 properties
            prop_name = prop.get('property_name', 'Unknown Property')
            prop_code = prop.get('property_code', 'N/A')
            net_income = float(prop.get('net_income') or 0)
            noi = float(prop.get('noi') or 0)
            revenue = float(prop.get('total_revenue') or 0)
            expenses = float(prop.get('total_expenses') or 0)
            period = prop.get('period', 'N/A')
            
            # Format values
            net_income_formatted = f"-${abs(net_income)/1000:.1f}K" if abs(net_income) >= 1000 else f"-${abs(net_income):,.0f}"
            if net_income > 0:
                net_income_formatted = f"${net_income/1000:.1f}K" if net_income >= 1000 else f"${net_income:,.0f}"
            
            noi_formatted = f"${noi/1000:.1f}K" if noi >= 1000 else f"${noi:,.0f}"
            revenue_formatted = f"${revenue/1000:.1f}K" if revenue >= 1000 else f"${revenue:,.0f}"
            
            status_icon = "🔴" if net_income < 0 else "🟢"
            
            answer_parts.append(
                f"{idx}. {status_icon} **{prop_name}** ({prop_code})"
            )
            answer_parts.append(f"   Net Income: {net_income_formatted}")
            answer_parts.append(f"   NOI: {noi_formatted} | Revenue: {revenue_formatted}")
            answer_parts.append(f"   Period: {period}")
            answer_parts.append("")
        
        if len(data) > 10:
            answer_parts.append(f"\n... and {len(data) - 10} more property(ies)")
        
        # Add recommendation for loss queries
        if is_loss_query and data:
            total_loss = sum(float(p.get('net_income') or 0) for p in data)
            total_loss_formatted = f"${abs(total_loss)/1000:.1f}K" if abs(total_loss) >= 1000 else f"${abs(total_loss):,.0f}"
            answer_parts.append(f"\n💡 Total Loss: {total_loss_formatted} across {len(data)} property(ies)")
            answer_parts.append("   Recommendation: Review these properties for operational improvements or consider refinancing options.")
        
        return "\n".join(answer_parts)
    
    def _generate_rent_roll_area_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Generate answer for rent roll area queries"""
        if not data:
            return "I couldn't find any rent roll area data for your query. Please ensure the rent roll document has been uploaded and processed."
        
        question_lower = question.lower()
        answer_parts = []
        
        for row in data:
            property_name = row.get('property_name', 'Unknown Property')
            property_code = row.get('property_code', 'N/A')
            period_year = row.get('period_year')
            period_month = row.get('period_month')
            occupied_area = float(row.get('occupied_area', 0))
            vacant_area = float(row.get('vacant_area', 0))
            total_area = float(row.get('total_area', 0))
            occupied_units = row.get('occupied_units', 0)
            vacant_units = row.get('vacant_units', 0)
            occupancy_rate = float(row.get('occupancy_rate', 0))
            
            period_str = f"{period_year}-{period_month:02d}" if period_year and period_month else "N/A"
            
            # Format based on what was asked
            if 'occupied area' in question_lower:
                answer_parts.append(f"**{property_name}** ({property_code}) - {period_str}")
                answer_parts.append(f"Total Occupied Area: **{occupied_area:,.2f} sq ft**")
                if total_area > 0:
                    answer_parts.append(f"Total Leasable Area: {total_area:,.2f} sq ft")
                    answer_parts.append(f"Occupancy Rate: {occupancy_rate:.2f}%")
                answer_parts.append(f"Occupied Units: {occupied_units}")
            
            elif 'vacant area' in question_lower:
                answer_parts.append(f"**{property_name}** ({property_code}) - {period_str}")
                answer_parts.append(f"Total Vacant Area: **{vacant_area:,.2f} sq ft**")
                if total_area > 0:
                    answer_parts.append(f"Total Leasable Area: {total_area:,.2f} sq ft")
                    answer_parts.append(f"Vacancy Rate: {100 - occupancy_rate:.2f}%")
                answer_parts.append(f"Vacant Units: {vacant_units}")
            
            elif 'total area' in question_lower:
                answer_parts.append(f"**{property_name}** ({property_code}) - {period_str}")
                answer_parts.append(f"Total Leasable Area: **{total_area:,.2f} sq ft**")
                answer_parts.append(f"  - Occupied: {occupied_area:,.2f} sq ft ({occupancy_rate:.2f}%)")
                answer_parts.append(f"  - Vacant: {vacant_area:,.2f} sq ft ({100 - occupancy_rate:.2f}%)")
            
            else:
                # Default: show all
                answer_parts.append(f"**{property_name}** ({property_code}) - {period_str}")
                answer_parts.append(f"Total Occupied Area: **{occupied_area:,.2f} sq ft**")
                answer_parts.append(f"Total Vacant Area: {vacant_area:,.2f} sq ft")
                answer_parts.append(f"Total Leasable Area: {total_area:,.2f} sq ft")
                answer_parts.append(f"Occupancy Rate: {occupancy_rate:.2f}%")
                answer_parts.append(f"Occupied Units: {occupied_units} | Vacant Units: {vacant_units}")
        
        return "\n".join(answer_parts)
    
    def _template_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Fallback template-based answer"""
        if not data:
            return "I couldn't find any data to answer your question."

        intent_type = intent['intent_type']

        if intent_type == self.INTENT_COMPARISON:
            lines = [f"**{row.get('property_name', 'Unknown')}**: ${row.get('total', 0):,.2f}" for row in data[:5]]
            return "Property comparison:\n" + "\n".join(lines)

        elif intent_type == self.INTENT_AGGREGATION:
            if not data:
                return "I couldn't find any aggregated data for your query."
            
            row = data[0]
            
            # Check if this is a portfolio value query
            question_lower = question.lower()
            if 'portfolio value' in question_lower or 'total portfolio' in question_lower or ('total' in question_lower and 'value' in question_lower):
                total_value = float(row.get('total_portfolio_value') or 0)
                property_count = row.get('property_count') or 0
                avg_value = float(row.get('avg_property_value') or 0)
                total_equity = float(row.get('total_equity') or 0)
                total_liabilities = float(row.get('total_liabilities') or 0)
                
                # Format values
                if total_value >= 1000000:
                    total_formatted = f"${total_value/1000000:.2f}M"
                elif total_value >= 1000:
                    total_formatted = f"${total_value/1000:.1f}K"
                else:
                    total_formatted = f"${total_value:,.0f}"
                
                answer_parts = [f"**Total Portfolio Value**: {total_formatted}"]
                answer_parts.append(f"  Properties: {property_count}")
                
                if avg_value > 0:
                    if avg_value >= 1000000:
                        answer_parts.append(f"  Average Property Value: ${avg_value/1000000:.2f}M")
                    else:
                        answer_parts.append(f"  Average Property Value: ${avg_value/1000:.1f}K")
                
                if total_equity > 0:
                    if total_equity >= 1000000:
                        answer_parts.append(f"  Total Equity: ${total_equity/1000000:.2f}M")
                    else:
                        answer_parts.append(f"  Total Equity: ${total_equity/1000:.1f}K")
                
                if total_liabilities > 0:
                    if total_liabilities >= 1000000:
                        answer_parts.append(f"  Total Liabilities: ${total_liabilities/1000000:.2f}M")
                    else:
                        answer_parts.append(f"  Total Liabilities: ${total_liabilities/1000:.1f}K")
                
                return "\n".join(answer_parts)
            
            # Default: revenue aggregation
            total_revenue = float(row.get('total_revenue') or 0)
            avg_revenue = float(row.get('avg_revenue') or 0)
            property_count = row.get('property_count') or 0
            
            return f"Across {property_count} properties, total revenue is ${total_revenue:,.2f} with an average of ${avg_revenue:,.2f}."

        elif intent_type == self.INTENT_RANKING:
            top = data[0]
            return f"The highest performing property is {top.get('property_name', 'Unknown')} with ${top.get('total', 0):,.2f}."

        else:
            # Generic answer
            if len(data) == 1:
                row = data[0]
                return f"For {row.get('property_name', 'the property')}, the value is ${row.get('period_amount', 0):,.2f} for {row.get('period_name', 'the period')}."
            else:
                return f"Found {len(data)} results for your query."

    def _extract_citations(self, data: List[Dict], intent: Dict) -> List[Dict]:
        """Extract data sources for citations"""
        citations = [
            {"source": "REIMS2 Financial Database", "type": "internal"}
        ]

        # Add specific tables
        tables_used = set()
        if any('property_name' in row for row in data):
            tables_used.add("Properties")
        if any('period_name' in row for row in data):
            tables_used.add("Financial Periods")

        if tables_used:
            citations.append({
                "source": f"Tables: {', '.join(tables_used)}",
                "type": "database"
            })

        return citations

    def _calculate_confidence(self, data: List[Dict], intent: Dict) -> float:
        """Calculate confidence in answer"""
        if not data:
            return 0.0

        # Base confidence
        confidence = 0.7

        # More data = higher confidence
        if len(data) >= 5:
            confidence += 0.2
        elif len(data) >= 2:
            confidence += 0.1

        return min(1.0, confidence)

    def _serialize_data(self, data: List[Dict]) -> Dict:
        """Serialize data for JSON storage (handles Decimal and other non-JSON types)"""
        try:
            # Convert Decimal and other types to JSON-serializable formats
            serialized_rows = []
            for row in data[:50]:  # Limit to 50 rows
                serialized_row = {}
                for key, value in row.items():
                    if hasattr(value, '__float__'):  # Decimal, float
                        try:
                            serialized_row[key] = float(value)
                        except (ValueError, TypeError):
                            serialized_row[key] = str(value)
                    elif hasattr(value, 'isoformat'):  # datetime, date
                        serialized_row[key] = value.isoformat()
                    else:
                        serialized_row[key] = value
                serialized_rows.append(serialized_row)
            
            return {
                "rows": serialized_rows,
                "total_rows": len(data)
            }
        except Exception as e:
            logger.warning(f"Data serialization failed: {e}")
            return {"rows": [], "total_rows": 0}

    def _check_cache(self, question: str) -> Optional[Dict]:
        """Check if similar question was asked recently"""
        # Simple exact match cache (could be enhanced with similarity search)
        question_hash = hashlib.md5(question.lower().encode()).hexdigest()

        # Check last 24 hours
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=24)

        cached = self.db.query(NLQQuery)\
            .filter(NLQQuery.created_at >= cutoff)\
            .filter(NLQQuery.question == question)\
            .first()

        if cached:
            return cached.to_dict()

        return None

    def _cache_result(self, question: str, result: Dict):
        """Cache result (already stored in database via NLQQuery)"""
        pass
