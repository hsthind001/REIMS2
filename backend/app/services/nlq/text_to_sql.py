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
from app.services.nlq.schema_generator import get_schema_generator


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
        """
        Generate DDL statements for training using comprehensive schema generator.

        This now extracts ALL tables from the database dynamically rather than
        hardcoding a small subset. Includes 90+ tables covering all REIMS modules.
        """
        try:
            schema_gen = get_schema_generator()
            ddl_statements = schema_gen.generate_all_ddl(db)
            logger.info(f"Generated {len(ddl_statements)} DDL statements for training")
            return ddl_statements
        except Exception as e:
            logger.error(f"Error generating DDL statements: {e}", exc_info=True)
            # Fallback to essential tables if schema generation fails
            return self._get_fallback_ddl_statements()

    def _get_fallback_ddl_statements(self) -> Dict[str, str]:
        """
        Fallback DDL statements for essential tables if dynamic generation fails
        """
        return {
            "properties": "CREATE TABLE properties (id SERIAL PRIMARY KEY, property_code VARCHAR(10) UNIQUE NOT NULL, property_name VARCHAR(255), property_type VARCHAR(50), status VARCHAR(20));",
            "financial_periods": "CREATE TABLE financial_periods (id SERIAL PRIMARY KEY, property_id INTEGER, period_year INTEGER, period_month INTEGER, is_closed BOOLEAN);",
            "balance_sheet_data": "CREATE TABLE balance_sheet_data (id SERIAL PRIMARY KEY, property_id INTEGER, period_id INTEGER, account_code VARCHAR(20), account_name VARCHAR(255), amount DECIMAL(15,2), category VARCHAR(50));",
            "income_statement_data": "CREATE TABLE income_statement_data (id SERIAL PRIMARY KEY, property_id INTEGER, period_id INTEGER, account_code VARCHAR(20), account_name VARCHAR(255), amount DECIMAL(15,2), category VARCHAR(50));",
        }

    def _train_documentation(self):
        """
        Train on REIMS-specific documentation using comprehensive schema generator.

        Now includes documentation for ALL REIMS concepts, not just basic ones.
        """
        if not self.vanna:
            return

        try:
            schema_gen = get_schema_generator()
            documentation = schema_gen.generate_documentation()

            logger.info(f"Training on {len(documentation)} documentation items...")

            for doc in documentation:
                self.vanna.train(documentation=doc)

            logger.info("Documentation training complete")

        except Exception as e:
            logger.error(f"Error training documentation: {e}", exc_info=True)

    def _train_example_queries(self):
        """
        Train on example question-SQL pairs covering all major table types.

        Expanded to include examples for:
        - Financial statements (balance sheet, income statement, cash flow)
        - Mortgage data
        - Rent roll
        - Audit trails
        - Reconciliation
        - Data quality
        - Anomalies
        - Alerts
        - Market intelligence
        """
        if not self.vanna:
            return

        examples = [
            # Basic financial queries
            {
                "question": "What was the cash position in November 2025?",
                "sql": "SELECT b.amount as cash_position FROM balance_sheet_data b JOIN financial_periods fp ON b.period_id = fp.id WHERE b.account_code = '1010' AND fp.period_year = 2025 AND fp.period_month = 11"
            },
            {
                "question": "Show me total revenue for Q4 2025",
                "sql": "SELECT SUM(i.amount) as total_revenue FROM income_statement_data i JOIN financial_periods fp ON i.period_id = fp.id WHERE i.account_category = 'Revenue' AND fp.period_year = 2025 AND fp.period_month IN (10, 11, 12)"
            },
            {
                "question": "What are total assets for property ESP?",
                "sql": "SELECT p.property_code, SUM(b.amount) as total_assets FROM balance_sheet_data b JOIN properties p ON b.property_id = p.id WHERE p.property_code = 'ESP' AND b.account_category = 'ASSETS' GROUP BY p.property_code"
            },

            # Audit trail queries
            {
                "question": "Who changed the cash position in November 2025?",
                "sql": "SELECT a.changed_by_user_id, u.username, a.field_name, a.old_value, a.new_value, a.changed_at FROM audit_trails a JOIN users u ON a.changed_by_user_id = u.id WHERE a.table_name = 'balance_sheet_data' AND a.field_name = 'amount' AND EXTRACT(YEAR FROM a.changed_at) = 2025 AND EXTRACT(MONTH FROM a.changed_at) = 11"
            },
            {
                "question": "Show all changes made by user John Doe",
                "sql": "SELECT a.table_name, a.record_id, a.field_name, a.old_value, a.new_value, a.changed_at FROM audit_trails a JOIN users u ON a.changed_by_user_id = u.id WHERE u.username = 'John Doe' ORDER BY a.changed_at DESC"
            },

            # Rent roll queries
            {
                "question": "Show me the rent roll for property ESP",
                "sql": "SELECT r.tenant_name, r.unit_number, r.monthly_rent, r.lease_start_date, r.lease_end_date, r.occupancy_status FROM rent_roll_data r JOIN properties p ON r.property_id = p.id WHERE p.property_code = 'ESP'"
            },
            {
                "question": "What is the occupancy rate for all properties?",
                "sql": "SELECT p.property_code, p.property_name, COUNT(CASE WHEN r.occupancy_status = 'Occupied' THEN 1 END) * 100.0 / COUNT(*) as occupancy_rate FROM rent_roll_data r JOIN properties p ON r.property_id = p.id GROUP BY p.property_code, p.property_name"
            },

            # Mortgage queries
            {
                "question": "What is the current DSCR for property ESP?",
                "sql": "SELECT p.property_code, m.dscr_value, m.statement_date FROM mortgage_statement_data m JOIN properties p ON m.property_id = p.id WHERE p.property_code = 'ESP' ORDER BY m.statement_date DESC LIMIT 1"
            },
            {
                "question": "Show mortgage payment history for the last 6 months",
                "sql": "SELECT m.payment_date, m.principal_amount, m.interest_amount, m.total_payment FROM mortgage_payment_history m WHERE m.payment_date >= CURRENT_DATE - INTERVAL '6 months' ORDER BY m.payment_date DESC"
            },

            # Reconciliation queries
            {
                "question": "Show me unreconciled items",
                "sql": "SELECT r.account_code, r.account_name, r.amount, r.difference_amount, r.status FROM reconciliation_differences r WHERE r.status = 'unresolved' ORDER BY ABS(r.difference_amount) DESC"
            },
            {
                "question": "What reconciliation sessions are open?",
                "sql": "SELECT rs.session_name, rs.created_at, rs.status, p.property_code FROM reconciliation_sessions rs LEFT JOIN properties p ON rs.property_id = p.id WHERE rs.status = 'in_progress'"
            },

            # Data quality queries
            {
                "question": "Show me data quality issues",
                "sql": "SELECT dq.table_name, dq.field_name, dq.issue_type, dq.severity, COUNT(*) as issue_count FROM data_quality_scores dq WHERE dq.severity IN ('high', 'critical') GROUP BY dq.table_name, dq.field_name, dq.issue_type, dq.severity ORDER BY issue_count DESC"
            },
            {
                "question": "What validation errors were found?",
                "sql": "SELECT v.validation_rule_name, v.table_name, v.field_name, v.error_message, v.record_id FROM validation_results v WHERE v.is_valid = false ORDER BY v.created_at DESC"
            },

            # Anomaly queries
            {
                "question": "Show me detected anomalies",
                "sql": "SELECT a.anomaly_type, a.account_code, a.account_name, a.expected_value, a.actual_value, a.severity, a.detected_at FROM anomaly_detections a WHERE a.status = 'unresolved' ORDER BY a.severity DESC, a.detected_at DESC"
            },

            # Alert queries
            {
                "question": "Show active alerts",
                "sql": "SELECT ah.alert_type, ah.severity, ah.message, ah.triggered_at, p.property_code FROM alert_history ah LEFT JOIN properties p ON ah.property_id = p.id WHERE ah.status = 'active' ORDER BY ah.severity DESC, ah.triggered_at DESC"
            },

            # Market intelligence queries
            {
                "question": "Show market intelligence for property ESP",
                "sql": "SELECT m.data_type, m.metric_name, m.metric_value, m.data_date FROM market_intelligence m JOIN properties p ON m.property_id = p.id WHERE p.property_code = 'ESP' ORDER BY m.data_date DESC"
            },
        ]

        logger.info(f"Training on {len(examples)} example queries...")

        for example in examples:
            self.vanna.train(
                question=example["question"],
                sql=example["sql"]
            )

        logger.info("Example query training complete")

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
                fp.period_year as year,
                fp.period_month as month,
                b.amount as cash_position
            FROM balance_sheet_data b
            JOIN properties p ON b.property_id = p.id
            JOIN financial_periods fp ON b.period_id = fp.id
            WHERE b.account_code = '1010'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND fp.period_year = {filters['year']} AND fp.period_month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND fp.period_year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY fp.period_year DESC, fp.period_month DESC LIMIT 1"

        return sql

    def _template_revenue(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for revenue queries"""
        sql = """
            SELECT
                p.property_code,
                fp.period_year as year,
                fp.period_month as month,
                SUM(i.amount) as total_revenue
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            JOIN financial_periods fp ON i.period_id = fp.id
            WHERE i.account_category = 'Revenue'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND fp.period_year = {filters['year']} AND fp.period_month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND fp.period_year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " GROUP BY p.property_code, fp.period_year, fp.period_month ORDER BY fp.period_year DESC, fp.period_month DESC"

        return sql

    def _template_expenses(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for expense queries"""
        sql = """
            SELECT
                p.property_code,
                fp.period_year as year,
                fp.period_month as month,
                SUM(i.amount) as total_expenses
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            JOIN financial_periods fp ON i.period_id = fp.id
            WHERE i.account_category = 'Operating Expenses'
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND fp.period_year = {filters['year']} AND fp.period_month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND fp.period_year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " GROUP BY p.property_code, fp.period_year, fp.period_month ORDER BY fp.period_year DESC, fp.period_month DESC"

        return sql

    def _template_balance_sheet(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for balance sheet queries"""
        sql = """
            SELECT
                p.property_code,
                b.account_category as category,
                b.account_code,
                b.account_name,
                b.amount
            FROM balance_sheet_data b
            JOIN properties p ON b.property_id = p.id
            JOIN financial_periods fp ON b.period_id = fp.id
            WHERE 1=1
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND fp.period_year = {filters['year']} AND fp.period_month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND fp.period_year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY b.account_category, b.account_code"

        return sql

    def _template_income_statement(self, temporal_info: Dict, context: Optional[Dict]) -> str:
        """Template for income statement queries"""
        sql = """
            SELECT
                p.property_code,
                i.account_category as category,
                i.account_code,
                i.account_name,
                i.amount
            FROM income_statement_data i
            JOIN properties p ON i.property_id = p.id
            JOIN financial_periods fp ON i.period_id = fp.id
            WHERE 1=1
        """

        # Add temporal filters
        if temporal_info.get("has_temporal"):
            filters = temporal_info.get("filters", {})
            if "year" in filters and "month" in filters:
                sql += f" AND fp.period_year = {filters['year']} AND fp.period_month = {filters['month']}"
            elif "year" in filters:
                sql += f" AND fp.period_year = {filters['year']}"

        # Add property filter
        if context and context.get("property_code"):
            sql += f" AND p.property_code = '{context['property_code']}'"

        sql += " ORDER BY i.account_category, i.account_code"

        return sql


# Singleton instance
_text_to_sql_instance = None


def get_text_to_sql() -> VannaTextToSQL:
    """Get or create Text-to-SQL instance"""
    global _text_to_sql_instance
    if _text_to_sql_instance is None:
        _text_to_sql_instance = VannaTextToSQL()
    return _text_to_sql_instance
