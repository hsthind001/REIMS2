"""
Knowledge Graph Population for NLQ System

Populates Neo4j knowledge graph with REIMS entities and relationships:
1. Properties → Periods → Financial Statements
2. Chart of Accounts → Account Codes → Formulas
3. Users → Audit Logs → Changes
4. Validation Rules → Accounts
5. Document → Reconciliation → Statements

Graph Schema:
- Nodes: Property, Period, Account, Formula, User, Document, ValidationRule
- Relationships: HAS_PERIOD, CONTAINS_ACCOUNT, USES_FORMULA, MODIFIED_BY, etc.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from loguru import logger

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("neo4j not available - knowledge graph population disabled")

from app.db.database import SessionLocal
from app.db.models import (
    Property,
    Period,
    User,
    BalanceSheetData,
    IncomeStatementData,
    CashFlowData,
    AuditLog
)
from app.config.nlq_config import nlq_config

console = Console()


class KnowledgeGraphPopulator:
    """Populate Neo4j knowledge graph from REIMS database"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """Initialize Neo4j connection"""
        if not NEO4J_AVAILABLE:
            self.driver = None
            logger.warning("Neo4j not available")
            return

        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        self.stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": 0
        }

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()

    async def populate_all(self, db):
        """Populate entire knowledge graph"""
        if not self.driver:
            console.print("[red]✗ Neo4j driver not available[/red]")
            return

        console.print(Panel.fit(
            "[bold cyan]Knowledge Graph Population[/bold cyan]\n"
            "[dim]Populating Neo4j with REIMS entities and relationships[/dim]",
            border_style="cyan"
        ))

        # Clear existing graph (optional)
        await self._clear_graph()

        # Create constraints and indexes
        await self._create_constraints()

        # Populate nodes and relationships
        tasks = [
            ("Properties", self._populate_properties),
            ("Periods", self._populate_periods),
            ("Accounts", self._populate_accounts),
            ("Formulas", self._populate_formulas),
            ("Users", self._populate_users),
            ("Validation Rules", self._populate_validation_rules),
            ("Relationships", self._create_relationships)
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task("[cyan]Populating graph...", total=len(tasks))

            for task_name, task_func in tasks:
                progress.update(task_id, description=f"[cyan]{task_name}...")
                try:
                    await task_func(db)
                except Exception as e:
                    logger.error(f"Error in {task_name}: {e}", exc_info=True)
                    self.stats["errors"] += 1
                progress.advance(task_id)

        self._print_summary()

    async def _clear_graph(self):
        """Clear existing graph data"""
        console.print("[yellow]Clearing existing graph data...[/yellow]")

        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        console.print("[green]✓ Graph cleared[/green]")

    async def _create_constraints(self):
        """Create uniqueness constraints and indexes"""
        console.print("[cyan]Creating constraints and indexes...[/cyan]")

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.property_code IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (per:Period) REQUIRE per.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_code IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Formula) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:ValidationRule) REQUIRE v.id IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.property_code)",
            "CREATE INDEX IF NOT EXISTS FOR (per:Period) ON (per.year, per.month)",
            "CREATE INDEX IF NOT EXISTS FOR (a:Account) ON (a.category)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Formula) ON (f.category)",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                session.run(constraint)
            for index in indexes:
                session.run(index)

        console.print("[green]✓ Constraints and indexes created[/green]")

    async def _populate_properties(self, db):
        """Populate Property nodes"""
        properties = db.query(Property).all()

        with self.driver.session() as session:
            for prop in properties:
                session.run(
                    """
                    MERGE (p:Property {id: $id})
                    SET p.property_code = $property_code,
                        p.property_name = $property_name,
                        p.address = $address,
                        p.city = $city,
                        p.state = $state,
                        p.property_type = $property_type,
                        p.units = $units,
                        p.square_footage = $square_footage
                    """,
                    id=prop.id,
                    property_code=prop.property_code,
                    property_name=prop.property_name,
                    address=prop.address,
                    city=prop.city,
                    state=prop.state,
                    property_type=prop.property_type,
                    units=prop.units,
                    square_footage=float(prop.square_footage) if prop.square_footage else None
                )
                self.stats["nodes_created"] += 1

    async def _populate_periods(self, db):
        """Populate Period nodes"""
        periods = db.query(Period).all()

        with self.driver.session() as session:
            for period in periods:
                session.run(
                    """
                    MERGE (per:Period {id: $id})
                    SET per.property_id = $property_id,
                        per.year = $year,
                        per.month = $month,
                        per.period_type = $period_type,
                        per.start_date = date($start_date),
                        per.end_date = date($end_date),
                        per.is_closed = $is_closed
                    """,
                    id=period.id,
                    property_id=period.property_id,
                    year=period.year,
                    month=period.month,
                    period_type=period.period_type,
                    start_date=period.start_date.isoformat() if period.start_date else None,
                    end_date=period.end_date.isoformat() if period.end_date else None,
                    is_closed=period.is_closed
                )
                self.stats["nodes_created"] += 1

    async def _populate_accounts(self, db):
        """Populate Account nodes from chart of accounts"""
        # Get unique accounts from financial statements
        accounts = set()

        # Balance Sheet
        bs_accounts = db.query(
            BalanceSheetData.account_code,
            BalanceSheetData.account_name,
            BalanceSheetData.category
        ).distinct().all()
        accounts.update(bs_accounts)

        # Income Statement
        is_accounts = db.query(
            IncomeStatementData.account_code,
            IncomeStatementData.account_name,
            IncomeStatementData.category
        ).distinct().all()
        accounts.update(is_accounts)

        # Cash Flow
        cf_accounts = db.query(
            CashFlowData.account_code,
            CashFlowData.account_name,
            CashFlowData.category
        ).distinct().all()
        accounts.update(cf_accounts)

        with self.driver.session() as session:
            for account_code, account_name, category in accounts:
                if account_code:
                    session.run(
                        """
                        MERGE (a:Account {account_code: $account_code})
                        SET a.account_name = $account_name,
                            a.category = $category
                        """,
                        account_code=account_code,
                        account_name=account_name or "Unknown",
                        category=category or "Unknown"
                    )
                    self.stats["nodes_created"] += 1

    async def _populate_formulas(self, db):
        """Populate Formula nodes"""
        formulas = {
            "current_ratio": {
                "name": "Current Ratio",
                "formula": "Current Assets / Current Liabilities",
                "category": "liquidity",
                "inputs": ["current_assets", "current_liabilities"],
                "output_type": "ratio"
            },
            "dscr": {
                "name": "Debt Service Coverage Ratio",
                "formula": "NOI / Annual Debt Service",
                "category": "mortgage",
                "inputs": ["noi", "annual_debt_service"],
                "output_type": "ratio"
            },
            "noi": {
                "name": "Net Operating Income",
                "formula": "Total Revenue - Operating Expenses",
                "category": "income_statement",
                "inputs": ["total_revenue", "operating_expenses"],
                "output_type": "currency"
            },
            "ltv": {
                "name": "Loan-to-Value Ratio",
                "formula": "Loan Amount / Property Value",
                "category": "leverage",
                "inputs": ["loan_amount", "property_value"],
                "output_type": "percentage"
            },
            "occupancy_rate": {
                "name": "Occupancy Rate",
                "formula": "Occupied Units / Total Units",
                "category": "rent_roll",
                "inputs": ["occupied_units", "total_units"],
                "output_type": "percentage"
            }
        }

        with self.driver.session() as session:
            for key, formula in formulas.items():
                session.run(
                    """
                    MERGE (f:Formula {name: $name})
                    SET f.formula = $formula,
                        f.category = $category,
                        f.inputs = $inputs,
                        f.output_type = $output_type,
                        f.key = $key
                    """,
                    name=formula["name"],
                    formula=formula["formula"],
                    category=formula["category"],
                    inputs=formula["inputs"],
                    output_type=formula["output_type"],
                    key=key
                )
                self.stats["nodes_created"] += 1

    async def _populate_users(self, db):
        """Populate User nodes"""
        users = db.query(User).all()

        with self.driver.session() as session:
            for user in users:
                session.run(
                    """
                    MERGE (u:User {id: $id})
                    SET u.username = $username,
                        u.email = $email,
                        u.full_name = $full_name,
                        u.is_active = $is_active
                    """,
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    is_active=user.is_active
                )
                self.stats["nodes_created"] += 1

    async def _populate_validation_rules(self, db):
        """Populate ValidationRule nodes"""
        # Common validation rules
        validation_rules = [
            {
                "id": "cash_non_negative",
                "name": "Cash Must Be Non-Negative",
                "description": "Cash balance cannot be negative",
                "rule_type": "constraint",
                "applies_to": "1010",  # Cash account
                "severity": "error"
            },
            {
                "id": "balance_sheet_balance",
                "name": "Balance Sheet Must Balance",
                "description": "Assets = Liabilities + Equity",
                "rule_type": "equation",
                "applies_to": "balance_sheet",
                "severity": "error"
            },
            {
                "id": "revenue_positive",
                "name": "Revenue Should Be Positive",
                "description": "Revenue accounts should have positive values",
                "rule_type": "constraint",
                "applies_to": "4000",  # Revenue category
                "severity": "warning"
            }
        ]

        with self.driver.session() as session:
            for rule in validation_rules:
                session.run(
                    """
                    MERGE (v:ValidationRule {id: $id})
                    SET v.name = $name,
                        v.description = $description,
                        v.rule_type = $rule_type,
                        v.applies_to = $applies_to,
                        v.severity = $severity
                    """,
                    **rule
                )
                self.stats["nodes_created"] += 1

    async def _create_relationships(self, db):
        """Create relationships between nodes"""
        with self.driver.session() as session:
            # Property HAS_PERIOD Period
            session.run(
                """
                MATCH (p:Property), (per:Period)
                WHERE p.id = per.property_id
                MERGE (p)-[:HAS_PERIOD]->(per)
                """
            )
            self.stats["relationships_created"] += 1

            # Formula USES_ACCOUNT Account
            # Current Ratio uses current assets/liabilities
            session.run(
                """
                MATCH (f:Formula {key: 'current_ratio'}), (a:Account)
                WHERE a.category IN ['Assets', 'Liabilities']
                MERGE (f)-[:USES_ACCOUNT]->(a)
                """
            )

            # DSCR uses NOI
            session.run(
                """
                MATCH (dscr:Formula {key: 'dscr'}), (noi:Formula {key: 'noi'})
                MERGE (dscr)-[:DEPENDS_ON]->(noi)
                """
            )

            # ValidationRule APPLIES_TO Account
            session.run(
                """
                MATCH (v:ValidationRule), (a:Account)
                WHERE v.applies_to = a.account_code
                MERGE (v)-[:APPLIES_TO]->(a)
                """
            )

            # Audit trail relationships (if audit logs exist)
            audit_logs = db.query(AuditLog).limit(1000).all()
            for log in audit_logs:
                session.run(
                    """
                    MATCH (u:User {id: $user_id}), (p:Property {id: $property_id})
                    MERGE (u)-[r:MODIFIED {
                        timestamp: datetime($timestamp),
                        action: $action,
                        table_name: $table_name
                    }]->(p)
                    """,
                    user_id=log.user_id,
                    property_id=log.property_id,
                    timestamp=log.timestamp.isoformat(),
                    action=log.action,
                    table_name=log.table_name
                )

    def _print_summary(self):
        """Print population summary"""
        console.print("\n" + "="*80)

        table = Table(title="Knowledge Graph Population Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Nodes Created", str(self.stats["nodes_created"]))
        table.add_row("Relationships Created", str(self.stats["relationships_created"]))
        table.add_row("Errors", str(self.stats["errors"]))

        console.print(table)

        if self.stats["errors"] == 0:
            console.print("\n[bold green]✓ Knowledge Graph Population Complete![/bold green]")
        else:
            console.print(f"\n[yellow]⚠ Completed with {self.stats['errors']} errors[/yellow]")


async def main():
    """Run knowledge graph population"""
    # Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    # Initialize database connection
    db = SessionLocal()

    try:
        # Initialize populator
        populator = KnowledgeGraphPopulator(neo4j_uri, neo4j_user, neo4j_password)

        # Populate graph
        await populator.populate_all(db)

        # Close connections
        populator.close()

    except Exception as e:
        logger.error(f"Population error: {e}", exc_info=True)
        console.print(f"[red]✗ Error: {e}[/red]")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
