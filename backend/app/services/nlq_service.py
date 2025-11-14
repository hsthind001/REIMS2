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

from app.models.nlq_query import NLQQuery
from app.models.property import Property
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_metrics import FinancialMetrics
from app.core.config import settings

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

        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                self.llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.llm_type = 'openai'
                logger.info("NLQ Service initialized with OpenAI")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")

        if not self.llm_client and ANTHROPIC_AVAILABLE and hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            try:
                self.llm_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.llm_type = 'anthropic'
                logger.info("NLQ Service initialized with Anthropic Claude")
            except Exception as e:
                logger.warning(f"Anthropic initialization failed: {e}")

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

            # 2. Detect intent
            intent = self._detect_intent(question)
            logger.info(f"Detected intent: {intent['intent_type']}")

            # 3. Retrieve data
            data, sql_query = self._retrieve_data(intent)
            if not data:
                return {
                    "success": False,
                    "error": "No data found for query",
                    "question": question
                }

            # 4. Generate answer
            answer = self._generate_answer(question, data, intent)

            # 5. Extract citations
            citations = self._extract_citations(data, intent)

            # 6. Calculate confidence
            confidence = self._calculate_confidence(data, intent)

            # 7. Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 8. Store query
            nlq = NLQQuery(
                user_id=user_id,
                question=question,
                intent=intent,
                answer=answer,
                data_retrieved=self._serialize_data(data),
                citations=citations,
                confidence_score=confidence,
                sql_query=sql_query,
                execution_time_ms=execution_time_ms
            )
            self.db.add(nlq)
            self.db.commit()
            self.db.refresh(nlq)

            result = {
                "success": True,
                "question": question,
                "answer": answer,
                "data": data,
                "citations": citations,
                "confidence": confidence,
                "sql_query": sql_query,
                "execution_time_ms": execution_time_ms,
                "query_id": nlq.id
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

    def _detect_intent(self, question: str) -> Dict:
        """
        Detect query intent

        Uses LLM if available, otherwise rule-based
        """
        question_lower = question.lower()

        # Rule-based intent detection
        if any(word in question_lower for word in ['compare', 'versus', 'vs', 'vs.', 'between']):
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
            'time_period': self._extract_time_period(question)
        }

        return {
            'intent_type': intent_type,
            'entities': entities,
            'original_question': question
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

        if intent_type == self.INTENT_METRIC_QUERY:
            return self._query_metric(entities)
        elif intent_type == self.INTENT_COMPARISON:
            return self._query_comparison(entities)
        elif intent_type == self.INTENT_TREND_ANALYSIS:
            return self._query_trends(entities)
        elif intent_type == self.INTENT_AGGREGATION:
            return self._query_aggregation(entities)
        elif intent_type == self.INTENT_RANKING:
            return self._query_ranking(entities)
        else:
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
                SELECT p.property_name, fp.period_name, isd.amount_period, isd.account_name
                FROM income_statement_data isd
                JOIN properties p ON isd.property_id = p.id
                JOIN financial_periods fp ON isd.period_id = fp.id
                WHERE isd.account_name LIKE :metric
                """
                if properties:
                    sql += " AND p.property_name IN :properties"
                    params['properties'] = tuple(properties)

                sql += " ORDER BY fp.year DESC, fp.month DESC LIMIT 10"
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
            SELECT p.property_name, SUM(isd.amount_period) as total
            FROM income_statement_data isd
            JOIN properties p ON isd.property_id = p.id
            WHERE isd.account_name LIKE '%revenue%'
            GROUP BY p.property_name
            ORDER BY total DESC
            """
        else:
            sql = """
            SELECT p.property_name, SUM(isd.amount_period) as total
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

        sql = """
        SELECT p.property_name, fp.year, fp.month, fp.period_name, SUM(isd.amount_period) as value
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        JOIN financial_periods fp ON isd.period_id = fp.id
        WHERE isd.account_name LIKE '%revenue%'
        """

        params = {}
        if properties:
            sql += " AND p.property_name IN :properties"
            params['properties'] = tuple(properties)

        sql += " GROUP BY p.property_name, fp.year, fp.month, fp.period_name"
        sql += " ORDER BY fp.year DESC, fp.month DESC LIMIT 24"

        result = self.db.execute(text(sql), params).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _query_aggregation(self, entities: Dict) -> tuple:
        """Query for aggregated data"""
        sql = """
        SELECT
            COUNT(DISTINCT p.id) as property_count,
            SUM(isd.amount_period) as total_revenue,
            AVG(isd.amount_period) as avg_revenue
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        WHERE isd.account_name LIKE '%revenue%'
        """

        result = self.db.execute(text(sql)).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _query_ranking(self, entities: Dict) -> tuple:
        """Query for ranking/top items"""
        direction = 'DESC'  # Highest
        if any(word in entities.get('original_question', '').lower() for word in ['lowest', 'bottom', 'worst']):
            direction = 'ASC'

        sql = f"""
        SELECT p.property_name, SUM(isd.amount_period) as total
        FROM income_statement_data isd
        JOIN properties p ON isd.property_id = p.id
        WHERE isd.account_name LIKE '%revenue%'
        GROUP BY p.property_name
        ORDER BY total {direction}
        LIMIT 5
        """

        result = self.db.execute(text(sql)).fetchall()
        return [dict(r._mapping) for r in result], sql

    def _generate_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Generate natural language answer from data"""
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

    def _template_answer(self, question: str, data: List[Dict], intent: Dict) -> str:
        """Fallback template-based answer"""
        if not data:
            return "I couldn't find any data to answer your question."

        intent_type = intent['intent_type']

        if intent_type == self.INTENT_COMPARISON:
            lines = [f"**{row.get('property_name', 'Unknown')}**: ${row.get('total', 0):,.2f}" for row in data[:5]]
            return "Property comparison:\n" + "\n".join(lines)

        elif intent_type == self.INTENT_AGGREGATION:
            row = data[0]
            return f"Across {row.get('property_count', 0)} properties, total revenue is ${row.get('total_revenue', 0):,.2f} with an average of ${row.get('avg_revenue', 0):,.2f}."

        elif intent_type == self.INTENT_RANKING:
            top = data[0]
            return f"The highest performing property is {top.get('property_name', 'Unknown')} with ${top.get('total', 0):,.2f}."

        else:
            # Generic answer
            if len(data) == 1:
                row = data[0]
                return f"For {row.get('property_name', 'the property')}, the value is ${row.get('amount_period', 0):,.2f} for {row.get('period_name', 'the period')}."
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
        """Serialize data for JSON storage"""
        return {
            "rows": data[:50],  # Limit to 50 rows
            "total_rows": len(data)
        }

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
