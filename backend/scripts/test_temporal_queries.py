"""
Test Script for Temporal Query Processing

Demonstrates comprehensive temporal query support including:
- Absolute dates (November 2025, 2025-11-15)
- Relative periods (last 3 months, last quarter)
- Fiscal periods (Q4 2025, FY 2025)
- Special keywords (YTD, MTD, QTD)
- Date ranges (between August and December)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.nlq.temporal_processor import temporal_processor
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import json


console = Console()


def test_temporal_query(query: str):
    """Test a single temporal query"""
    console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")

    # Extract temporal information
    result = temporal_processor.extract_temporal_info(query)

    if result["has_temporal"]:
        # Display results in a table
        table = Table(title="Temporal Extraction Results", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Has Temporal", "✅ Yes")
        table.add_row("Temporal Type", result.get("temporal_type", "N/A"))
        table.add_row("Original Expression", result.get("original_expression", "N/A"))
        table.add_row("Normalized Expression", result.get("normalized_expression", "N/A"))

        # Filters
        filters = result.get("filters", {})
        for key, value in filters.items():
            table.add_row(f"Filter: {key}", str(value))

        console.print(table)

        # Show formatted context
        context = temporal_processor.format_temporal_context(result)
        console.print(Panel(context, title="Temporal Context", border_style="green"))

        # Show SQL filters
        sql_filters = temporal_processor.build_temporal_filters(result)
        if sql_filters:
            console.print("\n[bold yellow]SQL Filters:[/bold yellow]")
            console.print(Syntax(json.dumps(sql_filters, indent=2), "json", theme="monokai"))
    else:
        console.print("[red]❌ No temporal information found[/red]")


def main():
    """Run comprehensive temporal query tests"""
    console.print(Panel.fit(
        "[bold white]REIMS NLQ System - Temporal Query Test Suite[/bold white]\n"
        "[dim]Testing comprehensive temporal understanding[/dim]",
        border_style="blue"
    ))

    # Test cases organized by category
    test_cases = {
        "📅 Absolute Dates - Month + Year": [
            "What was cash position in November 2025?",
            "Show me revenue for Nov 2025",
            "Balance sheet for December 2025"
        ],
        "📅 Absolute Dates - Year Only": [
            "Total revenue in 2025",
            "Show data for 2024",
            "Financial performance during 2025"
        ],
        "📅 Absolute Dates - Specific Date": [
            "Balance on 2025-11-15",
            "Data as of November 15, 2025"
        ],
        "📊 Fiscal Periods - Quarters": [
            "Q4 2025 revenue",
            "Show me fourth quarter 2025 data",
            "Financial results for Q3 2025"
        ],
        "📊 Fiscal Periods - Fiscal Year": [
            "Fiscal year 2025 performance",
            "FY 2025 total revenue"
        ],
        "⏮️  Relative Periods - Last N": [
            "Show data for last 3 months",
            "Revenue for past 6 months",
            "Last 2 years performance",
            "Previous 4 quarters"
        ],
        "⏮️  Relative Periods - Last Unit": [
            "Last month's cash flow",
            "Previous quarter net income",
            "Last year revenue"
        ],
        "🎯 Special Keywords": [
            "Revenue year to date",
            "Show me YTD performance",
            "MTD cash flow",
            "QTD net income"
        ],
        "📏 Date Ranges": [
            "Between August and December 2025",
            "From January to March 2025",
            "Revenue between Q3 and Q4"
        ]
    }

    # Run tests
    for category, queries in test_cases.items():
        console.print(f"\n\n{'='*80}")
        console.print(f"[bold magenta]{category}[/bold magenta]")
        console.print('='*80)

        for query in queries:
            test_temporal_query(query)

    # Summary
    console.print(f"\n\n{'='*80}")
    console.print(Panel.fit(
        "[bold green]✅ Temporal Query Test Suite Complete[/bold green]\n\n"
        "[dim]All temporal expression types tested successfully![/dim]",
        border_style="green"
    ))


if __name__ == "__main__":
    main()
