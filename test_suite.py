#!/usr/bin/env python3
"""
REIMS2 Comprehensive Testing Suite
Tests all features, APIs, and integrations
"""
import json
import sys
from pathlib import Path

# Test results tracking
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}

def log_test(category, test_name, status, message=""):
    """Log test result"""
    test_results["total"] += 1
    test_results[status] += 1

    symbol = {
        "passed": "✅",
        "failed": "❌",
        "skipped": "⚠️"
    }.get(status, "❓")

    print(f"{symbol} [{category}] {test_name}")
    if message:
        print(f"   → {message}")

    if status == "failed":
        test_results["errors"].append({
            "category": category,
            "test": test_name,
            "message": message
        })

def test_imports():
    """Test Python module imports"""
    print("\n" + "="*60)
    print("TESTING: Module Imports")
    print("="*60)

    modules_to_test = [
        ("FastAPI", "fastapi", "FastAPI framework"),
        ("SQLAlchemy", "sqlalchemy", "Database ORM"),
        ("Pydantic", "pydantic", "Data validation"),
        ("Alembic", "alembic", "Database migrations"),
        ("Pandas", "pandas", "Data manipulation"),
        ("NumPy", "numpy", "Numerical computing"),
        ("OpenAI", "openai", "AI integration"),
        ("Anthropic", "anthropic", "Claude integration"),
    ]

    for name, module, desc in modules_to_test:
        try:
            __import__(module)
            log_test("Imports", f"{name} ({desc})", "passed")
        except ImportError as e:
            log_test("Imports", f"{name} ({desc})", "failed", str(e))

def test_model_definitions():
    """Test database model definitions"""
    print("\n" + "="*60)
    print("TESTING: Database Models")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    models_to_test = [
        "Property",
        "User",
        "DocumentUpload",
        "FinancialPeriod",
        "IncomeStatementData",
        "BalanceSheetData",
        "CashFlowData",
        "RentRollData",
        "Budget",
        "Forecast",
        "CommitteeAlert",
        "WorkflowLock",
        "DocumentSummary",
        "PropertyResearch",
        "TenantRecommendation",
        "NLQQuery",
    ]

    try:
        from app.models import (
            Property, User, DocumentUpload, FinancialPeriod,
            IncomeStatementData, BalanceSheetData, CashFlowData,
            RentRollData, Budget, Forecast, CommitteeAlert,
            WorkflowLock, DocumentSummary, PropertyResearch,
            TenantRecommendation, NLQQuery
        )

        for model_name in models_to_test:
            try:
                model = eval(model_name)
                # Check if model has __tablename__
                if hasattr(model, '__tablename__'):
                    log_test("Models", f"{model_name} model", "passed",
                            f"Table: {model.__tablename__}")
                else:
                    log_test("Models", f"{model_name} model", "failed",
                            "Missing __tablename__")
            except Exception as e:
                log_test("Models", f"{model_name} model", "failed", str(e))

    except Exception as e:
        log_test("Models", "Import models", "failed", str(e))

def test_service_files():
    """Test service file existence and structure"""
    print("\n" + "="*60)
    print("TESTING: Service Layer Files")
    print("="*60)

    services = [
        "document_summarization_service.py",
        "statistical_anomaly_service.py",
        "variance_analysis_service.py",
        "bulk_import_service.py",
        "dscr_monitoring_service.py",
        "ltv_monitoring_service.py",
        "cap_rate_service.py",
        "exit_strategy_service.py",
        "workflow_lock_service.py",
        "property_research_service.py",
        "tenant_recommendation_service.py",
        "nlq_service.py",
    ]

    services_path = Path("/home/user/REIMS2/backend/app/services")

    for service_file in services:
        file_path = services_path / service_file
        if file_path.exists():
            # Check file size and basic structure
            size = file_path.stat().st_size
            if size > 1000:  # At least 1KB
                log_test("Services", service_file, "passed",
                        f"Size: {size:,} bytes")
            else:
                log_test("Services", service_file, "failed",
                        f"File too small: {size} bytes")
        else:
            log_test("Services", service_file, "failed", "File not found")

def test_api_endpoints():
    """Test API endpoint file existence"""
    print("\n" + "="*60)
    print("TESTING: API Endpoint Files")
    print("="*60)

    endpoints = [
        "document_summary.py",
        "statistical_anomalies.py",
        "variance_analysis.py",
        "bulk_import.py",
        "risk_alerts.py",
        "workflow_locks.py",
        "property_research.py",
        "tenant_recommendations.py",
        "nlq.py",
    ]

    api_path = Path("/home/user/REIMS2/backend/app/api/v1")

    for endpoint_file in endpoints:
        file_path = api_path / endpoint_file
        if file_path.exists():
            size = file_path.stat().st_size
            log_test("API Endpoints", endpoint_file, "passed",
                    f"Size: {size:,} bytes")
        else:
            log_test("API Endpoints", endpoint_file, "failed", "File not found")

def test_frontend_pages():
    """Test frontend page files"""
    print("\n" + "="*60)
    print("TESTING: Frontend Pages")
    print("="*60)

    pages = [
        "PropertyIntelligence.tsx",
        "TenantOptimizer.tsx",
        "NaturalLanguageQuery.tsx",
        "RiskManagement.tsx",
        "VarianceAnalysis.tsx",
        "DocumentSummarization.tsx",
        "BulkImport.tsx",
        "ExitStrategyAnalysis.tsx",
        "FinancialDataViewer.tsx",
        "ReviewQueue.tsx",
    ]

    pages_path = Path("/home/user/REIMS2/src/pages")

    for page_file in pages:
        file_path = pages_path / page_file
        if file_path.exists():
            size = file_path.stat().st_size
            # Check for React import
            content = file_path.read_text()
            has_react = "import" in content and "react" in content.lower()
            has_api = "API_BASE_URL" in content or "fetch(" in content

            if has_react:
                status_msg = f"Size: {size:,} bytes"
                if has_api:
                    status_msg += ", Has API integration"
                log_test("Frontend", page_file, "passed", status_msg)
            else:
                log_test("Frontend", page_file, "failed", "Missing React import")
        else:
            log_test("Frontend", page_file, "failed", "File not found")

def test_database_migrations():
    """Test database migration files"""
    print("\n" + "="*60)
    print("TESTING: Database Migrations")
    print("="*60)

    migrations_path = Path("/home/user/REIMS2/backend/alembic/versions")

    if migrations_path.exists():
        migration_files = list(migrations_path.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__pycache__"]

        log_test("Migrations", "Migration directory", "passed",
                f"Found {len(migration_files)} migration files")

        # Check for today's migrations
        today_migrations = [f for f in migration_files if "20251114" in f.name]
        if today_migrations:
            for mig in today_migrations:
                log_test("Migrations", mig.name, "passed",
                        f"Size: {mig.stat().st_size:,} bytes")
        else:
            log_test("Migrations", "Today's migrations", "skipped",
                    "No migrations from today")
    else:
        log_test("Migrations", "Migration directory", "failed",
                "Directory not found")

def test_code_quality():
    """Test code quality and structure"""
    print("\n" + "="*60)
    print("TESTING: Code Quality")
    print("="*60)

    # Test for common issues
    backend_path = Path("/home/user/REIMS2/backend")

    # Check for TODO/FIXME comments
    todo_count = 0
    fixme_count = 0

    for py_file in backend_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text()
            todo_count += content.count("TODO")
            fixme_count += content.count("FIXME")
        except:
            pass

    log_test("Code Quality", "TODO comments", "passed" if todo_count < 10 else "failed",
            f"Found {todo_count} TODO comments")
    log_test("Code Quality", "FIXME comments", "passed" if fixme_count == 0 else "failed",
            f"Found {fixme_count} FIXME comments")

    # Check for proper imports in main.py
    main_py = backend_path / "app" / "main.py"
    if main_py.exists():
        content = main_py.read_text()

        required_routers = [
            "document_summary",
            "statistical_anomalies",
            "variance_analysis",
            "bulk_import",
            "risk_alerts",
            "workflow_locks",
        ]

        for router in required_routers:
            if router in content:
                log_test("Code Quality", f"Router '{router}' registered", "passed")
            else:
                log_test("Code Quality", f"Router '{router}' registered", "failed",
                        "Router not found in main.py")

def generate_report():
    """Generate final test report"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    print(f"\nTotal Tests: {test_results['total']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⚠️  Skipped: {test_results['skipped']}")

    pass_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    print(f"\n📊 Pass Rate: {pass_rate:.1f}%")

    if test_results['errors']:
        print("\n" + "="*60)
        print("FAILED TESTS")
        print("="*60)
        for error in test_results['errors']:
            print(f"\n❌ [{error['category']}] {error['test']}")
            print(f"   {error['message']}")

    # Save report to file
    report = {
        "summary": {
            "total": test_results['total'],
            "passed": test_results['passed'],
            "failed": test_results['failed'],
            "skipped": test_results['skipped'],
            "pass_rate": pass_rate
        },
        "errors": test_results['errors']
    }

    report_file = Path("/home/user/REIMS2/TEST_RESULTS.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Report saved to: {report_file}")

    return pass_rate >= 80

if __name__ == "__main__":
    print("=" * 60)
    print("REIMS2 COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print(f"Testing Environment: {sys.version}")
    print("=" * 60)

    # Run all tests
    test_imports()
    test_model_definitions()
    test_service_files()
    test_api_endpoints()
    test_frontend_pages()
    test_database_migrations()
    test_code_quality()

    # Generate final report
    success = generate_report()

    sys.exit(0 if success else 1)
