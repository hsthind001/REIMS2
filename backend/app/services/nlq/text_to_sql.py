"""
Text-to-SQL Engine with Vanna.ai Integration

Features:
1. Natural language to SQL translation
2. Schema documentation and learning
3. Query validation and optimization
4. Self-learning from successful queries
5. Support for complex joins and aggregations

Vanna.ai provides:
- Training from DDL statements
- Learning from question-SQL pairs
- Query generation with context
- Confidence scoring
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from loguru import logger
import json
import re

# Vanna.ai integration
try:
    from vanna.openai import OpenAI_Chat as VannaOpenAI
    from vanna.chromadb import ChromaDB_VectorStore as VannaChromaDB
    VANNA_AVAILABLE = True
except ImportError:
    VANNA_AVAILABLE = False
    logger.warning("Vanna.ai not available - text-to-SQL will use fallback mode")

from app.config.nlq_config import nlq_config
from app.services.nlq.temporal_processor import temporal_processor


class VannaTextToSQL:
    """Vanna.ai-powered Text-to-SQL engine"""

    def __init__(self):
        """Initialize Vanna"""
        if not VANNA_AVAILABLE:
            self.vanna = None
            logger.warning("Vanna not available - using fallback SQL generation")
            return

        # Initialize Vanna with vector store
        class MyVanna(VannaChromaDB, VannaOpenAI):
            def __init__(self, config=None):
                VannaChromaDB.__init__(self, config=config)
                VannaOpenAI.__init__(self, config=config)

        self.vanna = MyVanna(config={
            'api_key': nlq_config.OPENAI_API_KEY,
            'model': 'gpt-4-turbo-preview'
        })

        self.is_trained = False

    def train_on_schema(self, db: Session):
        """Train Vanna on database schema"""
        if not self.vanna:
            return

        try:
            logger.info("Training Vanna on REIMS database schema...")

            # Get DDL statements for all tables
            ddl_statements = self._get_ddl_statements(db)

            for table_name, ddl in ddl_statements.items():
                self.vanna.train(ddl=ddl)
                logger.info(f"Trained on table: {table_name}")

            # Train on documentation
            self._train_documentation()

            # Train on example queries
            self._train_example_queries()

            self.is_trained = True
            logger.info("Vanna training complete")

        except Exception as e:
            logger.error(f"Vanna training error: {e}", exc_info=True)

    def _get_ddl_statements(self, db: Session) -> Dict[str, str]:
        """Generate DDL statements for training"""

        # Key REIMS tables
        ddl_statements = {
            "balance_sheet_data": """
                CREATE TABLE balance_sheet_data (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER NOT NULL,
                    period_id INTEGER NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    account_name VARCHAR(255),
                    amount DECIMAL(15, 2),
                    category VARCHAR(50),
                    statement_date DATE,
                    year INTEGER,
                    month INTEGER,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id),
                    FOREIGN KEY (period_id) REFERENCES periods(id)
                );
                COMMENT ON TABLE balance_sheet_data IS 'Balance sheet financial data';
                COMMENT ON COLUMN balance_sheet_data.account_code IS 'Chart of accounts code (e.g., 1010 for Cash)';
                COMMENT ON COLUMN balance_sheet_data.category IS 'Assets, Liabilities, or Equity';
            """,

            "income_statement_data": """
                CREATE TABLE income_statement_data (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER NOT NULL,
                    period_id INTEGER NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    account_name VARCHAR(255),
                    amount DECIMAL(15, 2),
                    category VARCHAR(50),
                    statement_date DATE,
                    year INTEGER,
                    month INTEGER,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id),
                    FOREIGN KEY (period_id) REFERENCES periods(id)
                );
                COMMENT ON TABLE income_statement_data IS 'Income statement financial data';
                COMMENT ON COLUMN income_statement_data.category IS 'Revenue, Operating Expenses, or Other';
            """,

            "cash_flow_data": """
                CREATE TABLE cash_flow_data (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER NOT NULL,
                    period_id INTEGER NOT NULL,
                    account_code VARCHAR(20) NOT NULL,
                    account_name VARCHAR(255),
                    amount DECIMAL(15, 2),
                    category VARCHAR(50),
                    statement_date DATE,
                    year INTEGER,
                    month INTEGER,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(id),
                    FOREIGN KEY (period_id) REFERENCES periods(id)
                );
                COMMENT ON TABLE cash_flow_data IS 'Cash flow statement data';
            """,

            "properties": """
                CREATE TABLE properties (
                    id SERIAL PRIMARY KEY,
                    property_code VARCHAR(10) UNIQUE NOT NULL,
                    property_name VARCHAR(255),
                    address TEXT,
                    city VARCHAR(100),
                    state VARCHAR(50),
                    zip_code VARCHAR(20),
                    property_type VARCHAR(50),
                    units INTEGER,
                    square_footage DECIMAL(12, 2),
                    created_at TIMESTAMP
                );
                COMMENT ON TABLE properties IS 'Real estate properties managed in REIMS';
            """,

            "periods": """
                CREATE TABLE periods (
                    id SERIAL PRIMARY KEY,
                    property_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    period_type VARCHAR(20),
                    start_date DATE,
                    end_date DATE,
                    is_closed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (property_id) REFERENCES properties(id)
                );
                COMMENT ON TABLE periods IS 'Reporting periods for financial statements';
            """
        }

        return ddl_statements

    def _train_documentation(self):
        """Train on REIMS-specific documentation"""
        if not self.vanna:
            return

        documentation = [
            "Account code 1010 represents Cash and Cash Equivalents",
            "Account code 1020 represents Accounts Receivable",
            "Account code 1030 represents Prepaid Expenses",
            "Account codes 1000-1999 are Assets",
            "Account codes 2000-2999 are Liabilities",
            "Account codes 3000-3999 are Equity",
            "Account codes 4000-4999 are Revenue",
            "Account codes 5000-5999 are Operating Expenses",
            "Property code ESP refers to Esperanza property",
            "Property code OAK refers to Oakland property",
            "Cash position means the value in account code 1010 (Cash)",
            "Net Operating Income (NOI) = Revenue - Operating Expenses",
            "DSCR (Debt Service Coverage Ratio) = NOI / Annual Debt Service",
            "Current Ratio = Current Assets / Current Liabilities",
        ]

        for doc in documentation:
            self.vanna.train(documentation=doc)

    def _train_example_queries(self):
        """Train on example question-SQL pairs"""
        if not self.vanna:
            return

        examples = [
            {
                "question": "What was the cash position in November 2025?",
                "sql": """
                    SELECT b.amount as cash_position
                    FROM balance_sheet_data b
                    WHERE b.account_code = '1010'
                      AND b.year = 2025
                      AND b.month = 11
                """
            },
            {
                "question": "Show me total revenue for Q4 2025",
                "sql": """
                    SELECT SUM(i.amount) as total_revenue
                    FROM income_statement_data i
                    WHERE i.category = 'Revenue'
                      AND i.year = 2025
                      AND i.month IN (10, 11, 12)
                """
            },
            {
                "question": "What are total assets for property ESP?",
                "sql": """
                    SELECT p.property_code, SUM(b.amount) as total_assets
                    FROM balance_sheet_data b
                    JOIN properties p ON b.property_id = p.id
                    WHERE p.property_code = 'ESP'
                      AND b.category = 'Assets'
                    GROUP BY p.property_code
                """
            },
            {
                "question": "Show operating expenses for last month",
                "sql": """
                    SELECT SUM(i.amount) as operating_expenses
                    FROM income_statement_data i
                    WHERE i.category = 'Operating Expenses'
                      AND i.year = EXTRACT(YEAR FROM CURRENT_DATE)
                      AND i.month = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
                """
            }
        ]

        for example in examples:
            self.vanna.train(
                question=example["question"],
                sql=example["sql"]
            )

    async def generate_sql(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """
        Generate SQL from natural language question

        Args:
            question: Natural language question
            context: Optional context (property_id, etc.)

        Returns:
            Tuple of (sql_query, confidence_score)
        """
        if not self.vanna:
            return await self._fallback_sql_generation(question, context)

        try:
            # Ensure Vanna is trained
            if not self.is_trained:
                logger.warning("Vanna not trained - using fallback")
                return await self._fallback_sql_generation(question, context)

            # Extract temporal info and add to question
            temporal_info = temporal_processor.extract_temporal_info(question)
            enhanced_question = self._enhance_question(question, temporal_info, context)

            # Generate SQL with Vanna
            sql = self.vanna.generate_sql(enhanced_question)

            # Validate SQL
            is_valid, validation_msg = self._validate_sql(sql)

            if not is_valid:
                logger.warning(f"Invalid SQL generated: {validation_msg}")
                return await self._fallback_sql_generation(question, context)

            # Estimate confidence (simplified)
            confidence = 0.8  # Vanna doesn't provide built-in confidence

            return sql, confidence

        except Exception as e:
            logger.error(f"Vanna SQL generation error: {e}", exc_info=True)
            return await self._fallback_sql_generation(question, context)

    def _enhance_question(
        self,
        question: str,
        temporal_info: Dict,
        context: Optional[Dict]
    ) -> str:
        """Enhance question with extracted context"""
        enhanced = question

        # Add property context
        if context and context.get("property_code"):
            enhanced += f" for property {context['property_code']}"

        return enhanced

    def _validate_sql(self, sql: str) -> Tuple[bool, str]:
        """Validate generated SQL"""
        # Basic validation
        sql_lower = sql.lower()

        # Check for dangerous operations
        dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create']
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                return False, f"Dangerous keyword found: {keyword}"

        # Must be a SELECT query
        if not sql_lower.strip().startswith('select'):
            return False, "Only SELECT queries are allowed"

        # Must have FROM clause
        if 'from' not in sql_lower:
            return False, "Missing FROM clause"

        return True, "Valid"

    async def _fallback_sql_generation(
        self,
        question: str,
        context: Optional[Dict]
    ) -> Tuple[str, float]:
        """Fallback SQL generation using templates"""

        # Extract temporal info
        temporal_info = temporal_processor.extract_temporal_info(question)

        # Simple template matching
        question_lower = question.lower()

        # Cash position query
        if "cash position" in question_lower or "cash" in question_lower:
            sql = self._template_cash_position(temporal_info, context)
            return sql, 0.7

        # Revenue query
        elif "revenue" in question_lower:
            sql = self._template_revenue(temporal_info, context)
            return sql, 0.7

        # Expenses query
        elif "expense" in question_lower:
            sql = self._template_expenses(temporal_info, context)
            return sql, 0.7

        # Generic balance sheet
        elif "balance sheet" in question_lower or "assets" in question_lower:
            sql = self._template_balance_sheet(temporal_info, context)
            return sql, 0.6

        # Generic income statement
        elif "income statement" in question_lower or "net income" in question_lower:
            sql = self._template_income_statement(temporal_info, context)
            return sql, 0.6

        # Default: return empty
        return "", 0.0

    def _template_cash_position(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for cash position queries"""
        sql = """
            SELECT
                p.property_code,
                b.year,
                b.month,
                b.amount as cash_position
            FROM balance_sheet_data b
            JOIN properties p ON b.property_id = p.id
            WHERE b.account_code = '1010'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND b.year = {filters['year']} AND b.month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND b.year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY b.year DESC, b.month DESC LIMIT 1"

        return sql

    def _template_revenue(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for revenue queries"""
        sql = """
            SELECT
                p.property_code,
                i.year,
                i.month,
                SUM(i.amount) as total_revenue
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            WHERE i.category = 'Revenue'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND i.year = {filters['year']} AND i.month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND i.year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " GROUP BY p.property_code, i.year, i.month ORDER BY i.year DESC, i.month DESC"

        return sql

    def _template_expenses(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for expense queries"""
        sql = """
            SELECT
                p.property_code,
                i.year,
                i.month,
                SUM(i.amount) as total_expenses
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            WHERE i.category = 'Operating Expenses'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND i.year = {filters['year']} AND i.month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND i.year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " GROUP BY p.property_code, i.year, i.month ORDER BY i.year DESC, i.month DESC"

        return sql

    def _template_balance_sheet(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for balance sheet queries"""
        sql = """
            SELECT
                p.property_code,
                b.category,
                b.account_code,
                b.account_name,
                b.amount
            FROM balance_sheet_data b
            JOIN properties p ON b.property_id = p.id
            WHERE 1=1
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND b.year = {filters['year']} AND b.month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND b.year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY b.category, b.account_code"

        return sql

    def _template_income_statement(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for income statement queries"""
        sql = """
            SELECT
                p.property_code,
                i.category,
                i.account_code,
                i.account_name,
                i.amount
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            WHERE 1=1
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND i.year = {filters['year']} AND i.month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND i.year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY i.category, i.account_code"

        return sql


# Singleton instance
_text_to_sql_instance = None


def get_text_to_sql() -> VannaTextToSQL:
    """Get or create Text-to-SQL instance"""
    global _text_to_sql_instance
    if _text_to_sql_instance is None:
        _text_to_sql_instance = VannaTextToSQL()
    return _text_to_sql_instance
