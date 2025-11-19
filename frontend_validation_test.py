#!/usr/bin/env python3
"""
REIMS2 Frontend Validation Test Suite
Tests React components, TypeScript compliance, and frontend structure
"""
import json
import re
from pathlib import Path
from datetime import datetime

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

def test_frontend_pages():
    """Test all frontend page files for React compliance"""
    print("\n" + "="*60)
    print("TESTING: Frontend Page Structure")
    print("="*60)

    pages_path = Path("/home/user/REIMS2/src/pages")

    expected_pages = [
        "Dashboard.tsx",
        "Properties.tsx",
        "Documents.tsx",
        "Reports.tsx",
        "Reconciliation.tsx",
        "Alerts.tsx",
        "Anomalies.tsx",
        "Performance.tsx",
        "Users.tsx",
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
        "Login.tsx",
        "Register.tsx",
    ]

    for page_name in expected_pages:
        page_path = pages_path / page_name

        if not page_path.exists():
            log_test("Frontend Pages", f"{page_name}", "failed", "File not found")
            continue

        try:
            content = page_path.read_text()

            # Check for React import
            has_react_import = bool(re.search(r'import.*from\s+["\']react["\']', content))

            # Check for export default
            has_export_default = 'export default' in content

            # Check for function component
            has_function_component = bool(re.search(r'function\s+\w+\s*\(', content)) or bool(re.search(r'const\s+\w+\s*=\s*\(', content))

            # Check for return statement with JSX
            has_return_jsx = bool(re.search(r'return\s*\(', content))

            issues = []
            if not has_react_import:
                issues.append("Missing React import")
            if not has_export_default:
                issues.append("Missing export default")
            if not has_function_component:
                issues.append("Missing function component")
            if not has_return_jsx:
                issues.append("Missing return JSX")

            if issues:
                log_test("Frontend Pages", f"{page_name}", "failed", ", ".join(issues))
            else:
                log_test("Frontend Pages", f"{page_name}", "passed",
                        f"Size: {len(content):,} bytes")
        except Exception as e:
            log_test("Frontend Pages", f"{page_name}", "failed", str(e))

def test_api_integration():
    """Test that pages have API integration"""
    print("\n" + "="*60)
    print("TESTING: API Integration in Pages")
    print("="*60)

    pages_path = Path("/home/user/REIMS2/src/pages")

    api_pages = [
        "PropertyIntelligence.tsx",
        "TenantOptimizer.tsx",
        "NaturalLanguageQuery.tsx",
        "RiskManagement.tsx",
        "VarianceAnalysis.tsx",
        "DocumentSummarization.tsx",
        "BulkImport.tsx",
        "ExitStrategyAnalysis.tsx",
    ]

    for page_name in api_pages:
        page_path = pages_path / page_name

        if not page_path.exists():
            log_test("API Integration", f"{page_name}", "skipped", "File not found")
            continue

        try:
            content = page_path.read_text()

            # Check for API_BASE_URL
            has_api_base = 'API_BASE_URL' in content

            # Check for fetch calls
            has_fetch = bool(re.search(r'fetch\s*\(', content))

            # Check for async/await
            has_async = 'async' in content and 'await' in content

            # Check for error handling
            has_error_handling = 'try' in content and 'catch' in content

            # Count API endpoints
            endpoint_count = len(re.findall(r'\$\{API_BASE_URL\}/', content))

            if has_api_base and has_fetch and has_async:
                log_test("API Integration", f"{page_name}", "passed",
                        f"{endpoint_count} endpoints, Error handling: {has_error_handling}")
            else:
                missing = []
                if not has_api_base:
                    missing.append("API_BASE_URL")
                if not has_fetch:
                    missing.append("fetch")
                if not has_async:
                    missing.append("async/await")
                log_test("API Integration", f"{page_name}", "failed",
                        f"Missing: {', '.join(missing)}")
        except Exception as e:
            log_test("API Integration", f"{page_name}", "failed", str(e))

def test_state_management():
    """Test React hooks usage"""
    print("\n" + "="*60)
    print("TESTING: State Management (React Hooks)")
    print("="*60)

    pages_path = Path("/home/user/REIMS2/src/pages")

    state_pages = [
        "PropertyIntelligence.tsx",
        "TenantOptimizer.tsx",
        "NaturalLanguageQuery.tsx",
        "RiskManagement.tsx",
        "VarianceAnalysis.tsx",
        "DocumentSummarization.tsx",
        "BulkImport.tsx",
        "ExitStrategyAnalysis.tsx",
    ]

    for page_name in state_pages:
        page_path = pages_path / page_name

        if not page_path.exists():
            log_test("State Management", f"{page_name}", "skipped", "File not found")
            continue

        try:
            content = page_path.read_text()

            # Count useState
            use_state_count = len(re.findall(r'useState', content))

            # Count useEffect
            use_effect_count = len(re.findall(r'useEffect', content))

            # Check for loading state
            has_loading = 'loading' in content.lower()

            # Check for error state
            has_error = bool(re.search(r'error.*useState', content) or re.search(r'useState.*error', content))

            if use_state_count > 0:
                log_test("State Management", f"{page_name}", "passed",
                        f"useState: {use_state_count}, useEffect: {use_effect_count}, Loading: {has_loading}, Error: {has_error}")
            else:
                log_test("State Management", f"{page_name}", "failed",
                        "No useState hooks found")
        except Exception as e:
            log_test("State Management", f"{page_name}", "failed", str(e))

def test_typescript_interfaces():
    """Test TypeScript interface definitions"""
    print("\n" + "="*60)
    print("TESTING: TypeScript Interfaces")
    print("="*60)

    pages_path = Path("/home/user/REIMS2/src/pages")

    ts_pages = [
        "PropertyIntelligence.tsx",
        "TenantOptimizer.tsx",
        "NaturalLanguageQuery.tsx",
        "RiskManagement.tsx",
        "VarianceAnalysis.tsx",
        "DocumentSummarization.tsx",
        "BulkImport.tsx",
        "ExitStrategyAnalysis.tsx",
    ]

    for page_name in ts_pages:
        page_path = pages_path / page_name

        if not page_path.exists():
            log_test("TypeScript", f"{page_name}", "skipped", "File not found")
            continue

        try:
            content = page_path.read_text()

            # Count interfaces
            interface_count = len(re.findall(r'interface\s+\w+', content))

            # Count types
            type_count = len(re.findall(r'type\s+\w+\s*=', content))

            # Check for typed props
            has_typed_props = bool(re.search(r':\s*\w+\[', content) or bool(re.search(r':\s*\w+\{', content)))

            total_types = interface_count + type_count

            if total_types > 0:
                log_test("TypeScript", f"{page_name}", "passed",
                        f"Interfaces: {interface_count}, Types: {type_count}")
            else:
                log_test("TypeScript", f"{page_name}", "failed",
                        "No TypeScript interfaces or types found")
        except Exception as e:
            log_test("TypeScript", f"{page_name}", "failed", str(e))

def test_css_styling():
    """Test CSS file and styling"""
    print("\n" + "="*60)
    print("TESTING: CSS Styling")
    print("="*60)

    css_path = Path("/home/user/REIMS2/src/App.css")

    if not css_path.exists():
        log_test("CSS", "App.css", "failed", "File not found")
        return

    try:
        content = css_path.read_text()

        # Check for essential selectors
        essential_selectors = [
            'page-container',
            'page-header',
            'card',
            'btn-primary',
            'form-input',
            'table',
        ]

        missing_selectors = [sel for sel in essential_selectors if f'.{sel}' not in content]

        if not missing_selectors:
            log_test("CSS", "Essential selectors", "passed",
                    f"{len(essential_selectors)} essential selectors found")
        else:
            log_test("CSS", "Essential selectors", "failed",
                    f"Missing: {', '.join(missing_selectors)}")

        # Check for CSS variables
        has_variables = ':root' in content
        var_count = len(re.findall(r'--[\w-]+:', content))

        if has_variables and var_count > 5:
            log_test("CSS", "CSS Variables", "passed",
                    f"{var_count} CSS variables defined")
        else:
            log_test("CSS", "CSS Variables", "failed",
                    f"Only {var_count} CSS variables found")

        # Check for responsive design
        has_media_queries = '@media' in content
        media_query_count = len(re.findall(r'@media', content))

        if has_media_queries:
            log_test("CSS", "Responsive Design", "passed",
                    f"{media_query_count} media queries")
        else:
            log_test("CSS", "Responsive Design", "skipped",
                    "No media queries found")

        # File size check
        size_kb = len(content) / 1024
        log_test("CSS", "File Size", "passed",
                f"{size_kb:.1f} KB")

    except Exception as e:
        log_test("CSS", "App.css", "failed", str(e))

def test_app_tsx():
    """Test main App.tsx file"""
    print("\n" + "="*60)
    print("TESTING: App.tsx Main File")
    print("="*60)

    app_path = Path("/home/user/REIMS2/src/App.tsx")

    if not app_path.exists():
        log_test("App.tsx", "File exists", "failed", "File not found")
        return

    try:
        content = app_path.read_text()

        # Check for page imports
        page_imports = [
            'PropertyIntelligence',
            'TenantOptimizer',
            'NaturalLanguageQuery',
            'RiskManagement',
            'VarianceAnalysis',
            'DocumentSummarization',
            'BulkImport',
            'ExitStrategyAnalysis',
        ]

        missing_imports = [page for page in page_imports if f'import {page}' not in content and f'import {{ {page}' not in content]

        if not missing_imports:
            log_test("App.tsx", "Page Imports", "passed",
                    f"All {len(page_imports)} page imports found")
        else:
            log_test("App.tsx", "Page Imports", "failed",
                    f"Missing: {', '.join(missing_imports)}")

        # Check for routing
        has_routing = 'currentPage' in content or 'page' in content.lower()

        if has_routing:
            log_test("App.tsx", "Routing Logic", "passed",
                    "Page navigation implemented")
        else:
            log_test("App.tsx", "Routing Logic", "failed",
                    "No routing logic found")

        # Check for navigation menu
        nav_items = len(re.findall(r'onClick=\{.*setCurrentPage', content)) or len(re.findall(r'onClick.*page', content))

        if nav_items > 10:
            log_test("App.tsx", "Navigation Menu", "passed",
                    f"{nav_items} navigation items")
        else:
            log_test("App.tsx", "Navigation Menu", "failed",
                    f"Only {nav_items} navigation items found")

    except Exception as e:
        log_test("App.tsx", "Main File", "failed", str(e))

def generate_report():
    """Generate final test report"""
    print("\n" + "="*60)
    print("FRONTEND VALIDATION SUMMARY")
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
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": test_results['total'],
            "passed": test_results['passed'],
            "failed": test_results['failed'],
            "skipped": test_results['skipped'],
            "pass_rate": pass_rate
        },
        "errors": test_results['errors']
    }

    report_file = Path("/home/user/REIMS2/FRONTEND_TEST_RESULTS.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Report saved to: {report_file}")

    return pass_rate >= 80

if __name__ == "__main__":
    print("=" * 60)
    print("REIMS2 FRONTEND VALIDATION TEST SUITE")
    print("=" * 60)
    print(f"Testing Date: {datetime.now().isoformat()}")
    print("=" * 60)

    # Run all tests
    test_frontend_pages()
    test_api_integration()
    test_state_management()
    test_typescript_interfaces()
    test_css_styling()
    test_app_tsx()

    # Generate final report
    success = generate_report()

    import sys
    sys.exit(0 if success else 1)
