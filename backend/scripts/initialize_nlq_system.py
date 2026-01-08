"""
Complete NLQ System Initialization Script

Performs end-to-end setup:
1. Verify dependencies and Docker containers
2. Initialize vector store (Qdrant)
3. Initialize knowledge graph (Neo4j)
4. Train Text-to-SQL engine
5. Ingest reconciliation documents
6. Populate knowledge graph
7. Run system tests
8. Generate setup report

Usage:
    python initialize_nlq_system.py [--skip-docker] [--skip-tests]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from loguru import logger
import subprocess

from app.db.database import SessionLocal
from app.config.nlq_config import nlq_config

console = Console()


class NLQSystemInitializer:
    """Complete NLQ system initialization"""

    def __init__(self, skip_docker: bool = False, skip_tests: bool = False):
        """Initialize"""
        self.skip_docker = skip_docker
        self.skip_tests = skip_tests

        self.status = {
            "dependencies": "pending",
            "docker": "pending",
            "vector_store": "pending",
            "knowledge_graph": "pending",
            "text_to_sql": "pending",
            "document_ingestion": "pending",
            "graph_population": "pending",
            "tests": "pending"
        }

        self.errors = []

    async def initialize_all(self):
        """Run complete initialization"""
        console.print(Panel.fit(
            "[bold cyan]REIMS NLQ System Initialization[/bold cyan]\n"
            "[dim]Setting up best-in-class natural language query system[/dim]",
            border_style="cyan",
            title="NLQ Setup"
        ))

        # Show welcome message
        self._show_welcome()

        # Run initialization steps
        steps = [
            ("Checking Dependencies", self._check_dependencies),
            ("Starting Docker Containers", self._start_docker_containers),
            ("Initializing Vector Store", self._initialize_vector_store),
            ("Initializing Knowledge Graph", self._initialize_knowledge_graph),
            ("Training Text-to-SQL", self._train_text_to_sql),
            ("Ingesting Documents", self._ingest_documents),
            ("Populating Knowledge Graph", self._populate_knowledge_graph),
            ("Running Tests", self._run_tests)
        ]

        for step_name, step_func in steps:
            if step_name == "Starting Docker Containers" and self.skip_docker:
                console.print(f"[yellow]⊘ Skipping: {step_name}[/yellow]")
                self.status["docker"] = "skipped"
                continue

            if step_name == "Running Tests" and self.skip_tests:
                console.print(f"[yellow]⊘ Skipping: {step_name}[/yellow]")
                self.status["tests"] = "skipped"
                continue

            console.print(f"\n[bold cyan]→ {step_name}...[/bold cyan]")

            try:
                await step_func()
                console.print(f"[green]✓ {step_name} completed[/green]")
            except Exception as e:
                console.print(f"[red]✗ {step_name} failed: {e}[/red]")
                self.errors.append(f"{step_name}: {str(e)}")
                logger.error(f"{step_name} error: {e}", exc_info=True)

        # Generate report
        self._generate_report()

    def _show_welcome(self):
        """Show welcome message with system info"""
        info = Table.grid(padding=(0, 2))
        info.add_column(style="cyan", justify="right")
        info.add_column()

        info.add_row("🎯 Primary LLM:", nlq_config.PRIMARY_LLM_PROVIDER.upper())
        info.add_row("🔍 Vector Store:", "Qdrant")
        info.add_row("🕸️ Knowledge Graph:", "Neo4j")
        info.add_row("⏱️ Temporal Support:", "✓ Enabled" if nlq_config.ENABLE_TEMPORAL_UNDERSTANDING else "✗ Disabled")
        info.add_row("🤖 Multi-Agent:", "✓ Enabled" if nlq_config.ENABLE_MULTI_AGENT else "✗ Disabled")
        info.add_row("🔎 Hybrid Search:", "✓ Enabled" if nlq_config.ENABLE_HYBRID_SEARCH else "✗ Disabled")

        console.print(Panel(info, title="[bold]System Configuration[/bold]", border_style="blue"))

    async def _check_dependencies(self):
        """Check Python dependencies"""
        self.status["dependencies"] = "checking"

        required_packages = [
            "qdrant-client",
            "neo4j",
            "langchain",
            "langgraph",
            "vanna",
            "dateparser",
            "pypdf"
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            self.status["dependencies"] = "failed"
            raise Exception(f"Missing packages: {', '.join(missing)}")

        self.status["dependencies"] = "success"

    async def _start_docker_containers(self):
        """Start required Docker containers"""
        self.status["docker"] = "starting"

        containers = [
            {
                "name": "qdrant",
                "image": "qdrant/qdrant:latest",
                "ports": "6333:6333",
                "command": [
                    "docker", "run", "-d",
                    "--name", "qdrant",
                    "-p", "6333:6333",
                    "qdrant/qdrant:latest"
                ]
            },
            {
                "name": "neo4j",
                "image": "neo4j:latest",
                "ports": "7474:7474,7687:7687",
                "env": ["NEO4J_AUTH=neo4j/password"],
                "command": [
                    "docker", "run", "-d",
                    "--name", "neo4j",
                    "-p", "7474:7474",
                    "-p", "7687:7687",
                    "-e", "NEO4J_AUTH=neo4j/password",
                    "neo4j:latest"
                ]
            }
        ]

        for container in containers:
            # Check if already running
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container['name']}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )

            if container['name'] in result.stdout:
                console.print(f"  [yellow]Container '{container['name']}' already running[/yellow]")
                continue

            # Start container
            console.print(f"  Starting {container['name']}...")
            subprocess.run(container["command"], check=True, capture_output=True)

            # Wait for container to be ready
            await asyncio.sleep(3)

        self.status["docker"] = "success"

    async def _initialize_vector_store(self):
        """Initialize Qdrant vector store"""
        self.status["vector_store"] = "initializing"

        try:
            from app.services.nlq.vector_store_manager import vector_store_manager
            from qdrant_client.models import Distance, VectorParams

            # Create collections
            collections = [
                ("reims_nlq_documents", 1024),  # BGE embeddings
                ("reims_reconciliation_docs", 1024)
            ]

            for collection_name, vector_size in collections:
                try:
                    vector_store_manager.client.get_collection(collection_name)
                    console.print(f"  [yellow]Collection '{collection_name}' already exists[/yellow]")
                except:
                    vector_store_manager.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE
                        )
                    )
                    console.print(f"  [green]✓ Created collection '{collection_name}'[/green]")

            self.status["vector_store"] = "success"

        except Exception as e:
            self.status["vector_store"] = "failed"
            raise

    async def _initialize_knowledge_graph(self):
        """Initialize Neo4j knowledge graph"""
        self.status["knowledge_graph"] = "initializing"

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )

            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1")
                result.single()

            driver.close()

            console.print("  [green]✓ Neo4j connection successful[/green]")
            self.status["knowledge_graph"] = "success"

        except Exception as e:
            self.status["knowledge_graph"] = "failed"
            raise Exception(f"Neo4j connection failed: {e}")

    async def _train_text_to_sql(self):
        """Train Vanna Text-to-SQL engine"""
        self.status["text_to_sql"] = "training"

        try:
            from app.services.nlq.text_to_sql import get_text_to_sql

            db = SessionLocal()
            try:
                text_to_sql = get_text_to_sql()
                if text_to_sql.vanna:
                    text_to_sql.train_on_schema(db)
                    console.print("  [green]✓ Vanna training complete[/green]")
                else:
                    console.print("  [yellow]⚠ Vanna not available - using fallback[/yellow]")

                self.status["text_to_sql"] = "success"
            finally:
                db.close()

        except Exception as e:
            self.status["text_to_sql"] = "partial"
            console.print(f"  [yellow]⚠ Text-to-SQL training partial: {e}[/yellow]")

    async def _ingest_documents(self):
        """Ingest reconciliation documents"""
        self.status["document_ingestion"] = "ingesting"

        try:
            # Check if documents directory exists
            docs_dir = Path("/home/hsthind/Downloads/Reconcile - Aduit - Rules")

            if not docs_dir.exists():
                console.print(f"  [yellow]⚠ Documents directory not found: {docs_dir}[/yellow]")
                self.status["document_ingestion"] = "skipped"
                return

            # Run ingestion script
            console.print("  [cyan]Running document ingestion...[/cyan]")
            result = subprocess.run(
                ["python", "backend/scripts/ingest_reconciliation_docs.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                console.print("  [green]✓ Document ingestion complete[/green]")
                self.status["document_ingestion"] = "success"
            else:
                raise Exception(f"Ingestion script failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.status["document_ingestion"] = "timeout"
            console.print("  [yellow]⚠ Document ingestion timed out[/yellow]")
        except Exception as e:
            self.status["document_ingestion"] = "failed"
            raise

    async def _populate_knowledge_graph(self):
        """Populate Neo4j knowledge graph"""
        self.status["graph_population"] = "populating"

        try:
            console.print("  [cyan]Running knowledge graph population...[/cyan]")

            # Run population script
            result = subprocess.run(
                ["python", "backend/scripts/populate_knowledge_graph.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                console.print("  [green]✓ Knowledge graph populated[/green]")
                self.status["graph_population"] = "success"
            else:
                raise Exception(f"Population script failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.status["graph_population"] = "timeout"
            console.print("  [yellow]⚠ Graph population timed out[/yellow]")
        except Exception as e:
            self.status["graph_population"] = "failed"
            raise

    async def _run_tests(self):
        """Run NLQ system tests"""
        self.status["tests"] = "running"

        try:
            console.print("  [cyan]Running NLQ tests...[/cyan]")

            # Run test script
            result = subprocess.run(
                ["python", "backend/scripts/test_nlq_complete.py"],
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )

            if result.returncode == 0:
                console.print("  [green]✓ All tests passed[/green]")
                self.status["tests"] = "success"
            else:
                console.print("  [yellow]⚠ Some tests failed[/yellow]")
                self.status["tests"] = "partial"

        except subprocess.TimeoutExpired:
            self.status["tests"] = "timeout"
            console.print("  [yellow]⚠ Tests timed out[/yellow]")
        except Exception as e:
            self.status["tests"] = "failed"
            console.print(f"  [yellow]⚠ Tests error: {e}[/yellow]")

    def _generate_report(self):
        """Generate final setup report"""
        console.print("\n" + "="*80)

        # Status table
        status_table = Table(title="🎯 Initialization Status", show_header=True)
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="white")

        status_icons = {
            "success": "[green]✓ Success[/green]",
            "failed": "[red]✗ Failed[/red]",
            "partial": "[yellow]⚠ Partial[/yellow]",
            "skipped": "[dim]⊘ Skipped[/dim]",
            "timeout": "[yellow]⏱ Timeout[/yellow]",
            "pending": "[dim]○ Pending[/dim]"
        }

        for component, status in self.status.items():
            status_table.add_row(
                component.replace("_", " ").title(),
                status_icons.get(status, status)
            )

        console.print(status_table)

        # Errors
        if self.errors:
            console.print("\n[bold red]Errors Encountered:[/bold red]")
            for i, error in enumerate(self.errors, 1):
                console.print(f"  {i}. {error}")

        # Success summary
        success_count = sum(1 for s in self.status.values() if s == "success")
        total_count = len([s for s in self.status.values() if s not in ["pending", "skipped"]])

        console.print(f"\n[bold]Summary:[/bold] {success_count}/{total_count} components initialized successfully")

        # Next steps
        if success_count == total_count:
            console.print(Panel.fit(
                "[bold green]✓ NLQ System Ready![/bold green]\n\n"
                "[bold]Next Steps:[/bold]\n"
                "1. Start the FastAPI server: uvicorn app.main:app --reload\n"
                "2. Test the API: POST /api/v1/nlq/query\n"
                "3. View API docs: http://localhost:8000/docs\n"
                "4. Check health: GET /api/v1/nlq/health",
                border_style="green",
                title="Success"
            ))
        else:
            console.print(Panel.fit(
                "[yellow]⚠ Partial Setup Complete[/yellow]\n\n"
                "[bold]Review errors above and:[/bold]\n"
                "1. Check Docker containers: docker ps\n"
                "2. Check logs: tail -f logs/nlq.log\n"
                "3. Retry failed steps manually\n"
                "4. Contact support if issues persist",
                border_style="yellow",
                title="Attention Required"
            ))


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Initialize REIMS NLQ System")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker container setup")
    parser.add_argument("--skip-tests", action="store_true", help="Skip system tests")

    args = parser.parse_args()

    # Initialize system
    initializer = NLQSystemInitializer(
        skip_docker=args.skip_docker,
        skip_tests=args.skip_tests
    )

    await initializer.initialize_all()


if __name__ == "__main__":
    asyncio.run(main())
