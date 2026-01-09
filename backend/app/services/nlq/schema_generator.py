"""
Database Schema Generator for NLQ System

Extracts complete REIMS database schema for Text-to-SQL training.
Includes all tables, columns, relationships, and documentation.
"""
from typing import Dict, List, Tuple
from sqlalchemy import inspect, MetaData
from sqlalchemy.orm import Session
from loguru import logger

# Import all models to ensure they're registered
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.rent_roll_data import RentRollData
from app.models.audit_trail import AuditTrail
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.user import User
from app.models.document_upload import DocumentUpload
from app.models.validation_result import ValidationResult
from app.models.reconciliation_difference import ReconciliationDifference
from app.models.reconciliation_session import ReconciliationSession
from app.models.alert_rule import AlertRule
from app.models.alert_history import AlertHistory
from app.models.workflow_lock import WorkflowLock
from app.models.notification import Notification
from app.models.budget import Budget
from app.models.data_quality import DataQuality
from app.models.market_intelligence import MarketIntelligence
from app.models.anomaly_detection import AnomalyDetection
from app.models.nlq_query import NLQQuery


class SchemaGenerator:
    """Generate comprehensive database schema documentation"""

    def __init__(self):
        self.metadata = MetaData()
        self.table_descriptions = self._get_table_descriptions()
        self.column_descriptions = self._get_column_descriptions()

    def _get_table_descriptions(self) -> Dict[str, str]:
        """Comprehensive table descriptions"""
        return {
            # Core entities
            "properties": "Real estate properties managed in REIMS (apartments, offices, retail)",
            "financial_periods": "Reporting periods for financial statements (monthly, quarterly, annual)",
            "users": "System users with roles and permissions",

            # Financial statements
            "balance_sheet_data": "Balance sheet line items (Assets, Liabilities, Equity)",
            "income_statement_data": "Income statement line items (Revenue, Expenses, Net Income)",
            "cash_flow_data": "Cash flow statement line items (Operating, Investing, Financing)",
            "mortgage_statement_data": "Mortgage loan data (principal, interest, DSCR, LTV)",
            "rent_roll_data": "Tenant rent roll information (leases, occupancy, rent)",

            # Chart of accounts
            "chart_of_accounts": "Standard account codes and names for financial reporting",
            "account_mappings": "Mapping of property-specific accounts to standard COA",
            "account_synonyms": "Alternative names for accounts",
            "account_semantic_mappings": "AI-learned semantic account mappings",

            # Audit and compliance
            "audit_trails": "Complete audit log of all data changes",
            "validation_results": "Data validation check results",
            "data_quality_scores": "Data quality metrics and scores",

            # Reconciliation
            "reconciliation_sessions": "Reconciliation workflow sessions",
            "reconciliation_differences": "Discrepancies found during reconciliation",
            "reconciliation_resolutions": "Resolution actions for discrepancies",
            "cash_account_reconciliations": "Cash account reconciliation records",
            "forensic_reconciliation_sessions": "Forensic-level reconciliation sessions",
            "forensic_matches": "Matched items in forensic reconciliation",
            "forensic_discrepancies": "Unmatched items in forensic reconciliation",

            # Alerts and monitoring
            "alert_rules": "Configurable alert rules (thresholds, conditions)",
            "alert_history": "Alert trigger history",
            "alert_suppressions": "Temporary alert suppression rules",
            "committee_alerts": "High-priority alerts for investment committee",
            "notifications": "User notifications and messages",

            # Document management
            "document_uploads": "Uploaded financial documents (PDFs, Excel)",
            "document_versions": "Document version history",
            "document_summaries": "AI-generated document summaries",
            "document_chunks": "Document text chunks for RAG/vector search",

            # Anomaly detection
            "anomaly_detections": "Detected financial anomalies",
            "anomaly_thresholds": "Anomaly detection thresholds",
            "anomaly_feedback": "User feedback on anomaly detections",
            "anomaly_explanations": "AI-generated anomaly explanations",

            # Workflow management
            "workflow_locks": "Period locking for workflow control",
            "review_approval_chains": "Multi-level approval workflows",
            "scheduled_tasks": "Automated task scheduling",

            # Budgeting and forecasting
            "budgets": "Budget data by period and account",
            "forecasts": "Financial forecasts",
            "forecast_models": "Forecast model configurations",

            # Market intelligence
            "market_intelligence": "External market data (demographics, economics)",
            "market_data_lineage": "Market data source tracking",
            "property_research": "Property research notes and analysis",

            # Financial metrics
            "financial_metrics": "Calculated financial KPIs (NOI, DSCR, ROI)",
            "cross_property_benchmarks": "Performance benchmarks across properties",
            "tenant_performance_history": "Tenant payment and performance tracking",

            # AI/ML models
            "extraction_learning_patterns": "Learned patterns for data extraction",
            "learned_match_patterns": "Learned patterns for account matching",
            "model_performance_metrics": "ML model performance tracking",
            "hallucination_reviews": "AI hallucination detection and review",

            # NLQ system
            "nlq_queries": "Natural language query history and results",

            # Configuration
            "validation_rules": "Configurable validation rules",
            "data_quality_rules": "Data quality check rules",
            "calculated_rules": "Formula-based calculation rules",
            "materiality_configs": "Materiality threshold configurations",
        }

    def _get_column_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Column-level descriptions for key tables"""
        return {
            "balance_sheet_data": {
                "account_code": "Chart of accounts code (e.g., 1010 for Cash)",
                "account_name": "Human-readable account name",
                "amount": "Account balance amount in dollars",
                "category": "Assets, Liabilities, or Equity",
                "statement_date": "Date of the balance sheet",
                "year": "Fiscal year",
                "month": "Fiscal month (1-12)",
            },
            "income_statement_data": {
                "account_code": "Chart of accounts code (e.g., 4000 for Rental Revenue)",
                "amount": "Account amount for the period",
                "category": "Revenue, Operating Expenses, or Other",
            },
            "properties": {
                "property_code": "Unique property identifier (e.g., ESP001, OAK001)",
                "property_name": "Property name",
                "property_type": "Multifamily, Office, Retail, Industrial, etc.",
                "status": "active, sold, or under_contract",
            },
            "financial_periods": {
                "period_year": "Year of the period",
                "period_month": "Month of the period (1-12)",
                "is_closed": "Whether the period is locked/closed",
                "fiscal_quarter": "Fiscal quarter (1-4)",
            },
            "audit_trails": {
                "table_name": "Name of the table that was modified",
                "record_id": "ID of the record that was changed",
                "field_name": "Name of the field that was modified",
                "old_value": "Previous value before change",
                "new_value": "New value after change",
                "change_type": "CREATE, UPDATE, or DELETE",
                "changed_by_user_id": "User who made the change",
            }
        }

    def generate_ddl_for_table(self, table_name: str, db: Session) -> str:
        """Generate DDL statement for a specific table"""
        try:
            inspector = inspect(db.bind)

            if table_name not in inspector.get_table_names():
                return ""

            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            fk_constraints = inspector.get_foreign_keys(table_name)

            # Build CREATE TABLE statement
            ddl = f"CREATE TABLE {table_name} (\n"

            # Add columns
            column_defs = []
            for col in columns:
                col_def = f"    {col['name']} {col['type']}"
                if not col['nullable']:
                    col_def += " NOT NULL"
                if col.get('default'):
                    col_def += f" DEFAULT {col['default']}"
                column_defs.append(col_def)

            ddl += ",\n".join(column_defs)

            # Add primary key
            if pk_constraint and pk_constraint.get('constrained_columns'):
                pk_cols = ", ".join(pk_constraint['constrained_columns'])
                ddl += f",\n    PRIMARY KEY ({pk_cols})"

            # Add foreign keys
            for fk in fk_constraints:
                local_cols = ", ".join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_cols = ", ".join(fk['referred_columns'])
                ddl += f",\n    FOREIGN KEY ({local_cols}) REFERENCES {ref_table}({ref_cols})"

            ddl += "\n);"

            # Add table comment
            if table_name in self.table_descriptions:
                ddl += f"\nCOMMENT ON TABLE {table_name} IS '{self.table_descriptions[table_name]}';"

            # Add column comments
            if table_name in self.column_descriptions:
                for col_name, col_desc in self.column_descriptions[table_name].items():
                    ddl += f"\nCOMMENT ON COLUMN {table_name}.{col_name} IS '{col_desc}';"

            return ddl

        except Exception as e:
            logger.error(f"Error generating DDL for {table_name}: {e}")
            return ""

    def generate_all_ddl(self, db: Session) -> Dict[str, str]:
        """Generate DDL statements for all tables"""
        inspector = inspect(db.bind)
        all_tables = inspector.get_table_names()

        ddl_statements = {}

        logger.info(f"Generating DDL for {len(all_tables)} tables...")

        for table_name in sorted(all_tables):
            ddl = self.generate_ddl_for_table(table_name, db)
            if ddl:
                ddl_statements[table_name] = ddl
                logger.info(f"✓ Generated DDL for {table_name}")

        logger.info(f"Generated DDL for {len(ddl_statements)} tables")
        return ddl_statements

    def generate_documentation(self) -> List[str]:
        """Generate REIMS-specific documentation for training"""
        return [
            # Account codes
            "Account code 1010 represents Cash and Cash Equivalents",
            "Account code 1020 represents Accounts Receivable",
            "Account code 1030 represents Prepaid Expenses",
            "Account codes 1000-1999 are Assets",
            "Account codes 2000-2999 are Liabilities",
            "Account codes 3000-3999 are Equity",
            "Account codes 4000-4999 are Revenue",
            "Account codes 5000-5999 are Operating Expenses",
            "Account codes 6000-6999 are Other Income/Expenses",

            # Financial concepts
            "Cash position means the value in account code 1010",
            "Net Operating Income (NOI) = Total Revenue - Operating Expenses",
            "EBITDA = Net Income + Interest + Taxes + Depreciation + Amortization",
            "DSCR (Debt Service Coverage Ratio) = NOI / Annual Debt Service",
            "LTV (Loan to Value) = Loan Amount / Property Value",
            "Current Ratio = Current Assets / Current Liabilities",
            "Operating Margin = NOI / Total Revenue",
            "Occupancy Rate = Occupied Units / Total Units",
            "Rent per Square Foot = Total Rent / Total Square Footage",

            # Property types
            "Property types include: Multifamily, Office, Retail, Industrial, Mixed-Use",
            "Multifamily properties are residential apartment buildings",
            "Office properties include commercial office spaces",
            "Retail properties include shopping centers and standalone retail",

            # Periods
            "Q1 refers to months 1-3 (January-March)",
            "Q2 refers to months 4-6 (April-June)",
            "Q3 refers to months 7-9 (July-September)",
            "Q4 refers to months 10-12 (October-December)",
            "YTD means Year to Date",
            "MTD means Month to Date",
            "QTD means Quarter to Date",

            # Audit trail
            "Who changed a value can be found in audit_trails table",
            "Change history is tracked in audit_trails table with old_value and new_value",
            "audit_trails.change_type can be CREATE, UPDATE, or DELETE",

            # Data quality
            "Data quality scores are in data_quality_scores table",
            "Validation errors are in validation_results table",
            "Anomalies are detected and stored in anomaly_detections table",

            # Reconciliation
            "Reconciliation differences are in reconciliation_differences table",
            "Unreconciled items have status = 'unresolved'",
            "Reconciliation sessions track the reconciliation process",

            # Common queries
            "Total assets = SUM of balance_sheet_data where category = 'Assets'",
            "Total liabilities = SUM of balance_sheet_data where category = 'Liabilities'",
            "Total revenue = SUM of income_statement_data where category = 'Revenue'",
            "Total expenses = SUM of income_statement_data where category = 'Operating Expenses'",
            "Net income = Total Revenue - Total Expenses",
        ]

    def get_table_relationships(self) -> Dict[str, List[Tuple[str, str]]]:
        """Document key table relationships"""
        return {
            "properties": [
                ("financial_periods", "property_id -> properties.id"),
                ("balance_sheet_data", "property_id -> properties.id"),
                ("income_statement_data", "property_id -> properties.id"),
            ],
            "financial_periods": [
                ("balance_sheet_data", "period_id -> financial_periods.id"),
                ("income_statement_data", "period_id -> financial_periods.id"),
            ],
            "users": [
                ("audit_trails", "changed_by_user_id -> users.id"),
                ("document_uploads", "uploaded_by_user_id -> users.id"),
            ],
        }


# Singleton instance
_schema_generator = None


def get_schema_generator() -> SchemaGenerator:
    """Get or create schema generator instance"""
    global _schema_generator
    if _schema_generator is None:
        _schema_generator = SchemaGenerator()
    return _schema_generator
