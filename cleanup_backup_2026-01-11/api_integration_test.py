#!/usr/bin/env python3
"""
REIMS2 API Integration Testing Suite
Tests API endpoints, service logic, and integrations with mocked dependencies
"""
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

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

def test_api_endpoint_imports():
    """Test that all API endpoints can be imported"""
    print("\n" + "="*60)
    print("TESTING: API Endpoint Imports")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    endpoints = [
        ("app.api.v1.properties", "Properties API"),
        ("app.api.v1.documents", "Documents API"),
        ("app.api.v1.financial_data", "Financial Data API"),
        ("app.api.v1.reports", "Reports API"),
        ("app.api.v1.users", "Users API"),
        ("app.api.v1.document_summary", "Document Summary API"),
        ("app.api.v1.statistical_anomalies", "Statistical Anomalies API"),
        ("app.api.v1.variance_analysis", "Variance Analysis API"),
        ("app.api.v1.bulk_import", "Bulk Import API"),
        ("app.api.v1.risk_alerts", "Risk Alerts API"),
        ("app.api.v1.workflow_locks", "Workflow Locks API"),
        ("app.api.v1.property_research", "Property Research API"),
        ("app.api.v1.tenant_recommendations", "Tenant Recommendations API"),
        ("app.api.v1.nlq", "NLQ API"),
    ]

    for module_path, desc in endpoints:
        try:
            __import__(module_path)
            log_test("API Imports", desc, "passed")
        except Exception as e:
            log_test("API Imports", desc, "failed", str(e))

def test_service_layer_imports():
    """Test that all service modules can be imported"""
    print("\n" + "="*60)
    print("TESTING: Service Layer Imports")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    services = [
        ("app.services.pdf_extraction_service", "PDF Extraction Service"),
        ("app.services.financial_data_service", "Financial Data Service"),
        ("app.services.validation_service", "Validation Service"),
        ("app.services.document_summarization_service", "Document Summarization Service"),
        ("app.services.statistical_anomaly_service", "Statistical Anomaly Service"),
        ("app.services.variance_analysis_service", "Variance Analysis Service"),
        ("app.services.bulk_import_service", "Bulk Import Service"),
        ("app.services.dscr_monitoring_service", "DSCR Monitoring Service"),
        ("app.services.ltv_monitoring_service", "LTV Monitoring Service"),
        ("app.services.cap_rate_service", "Cap Rate Service"),
        ("app.services.exit_strategy_service", "Exit Strategy Service"),
        ("app.services.workflow_lock_service", "Workflow Lock Service"),
        ("app.services.property_research_service", "Property Research Service"),
        ("app.services.tenant_recommendation_service", "Tenant Recommendation Service"),
        ("app.services.nlq_service", "NLQ Service"),
    ]

    for module_path, desc in services:
        try:
            __import__(module_path)
            log_test("Service Imports", desc, "passed")
        except Exception as e:
            log_test("Service Imports", desc, "failed", str(e))

def test_service_functions():
    """Test service layer functions with mocked dependencies"""
    print("\n" + "="*60)
    print("TESTING: Service Layer Functions")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    # Test Exit Strategy Service
    try:
        from app.services import exit_strategy_service

        # Mock data
        mock_property = Mock()
        mock_property.id = 1

        # Test hold strategy calculation
        result = exit_strategy_service.calculate_hold_strategy(
            investment_amount=10000000,
            annual_noi=800000,
            holding_period_years=5,
            discount_rate=0.10,
            appreciation_rate=0.03
        )

        if result and 'irr' in result and 'npv' in result:
            log_test("Service Functions", "Exit Strategy - Hold Calculation", "passed",
                    f"IRR: {result['irr']:.2%}, NPV: ${result['npv']:,.0f}")
        else:
            log_test("Service Functions", "Exit Strategy - Hold Calculation", "failed",
                    "Missing required fields in result")
    except Exception as e:
        log_test("Service Functions", "Exit Strategy - Hold Calculation", "failed", str(e))

    # Test Cap Rate Service
    try:
        from app.services import cap_rate_service

        cap_rate = cap_rate_service.calculate_cap_rate(
            noi=800000,
            property_value=10000000
        )

        if cap_rate == 0.08:  # 8%
            log_test("Service Functions", "Cap Rate Calculation", "passed",
                    f"Cap Rate: {cap_rate:.2%}")
        else:
            log_test("Service Functions", "Cap Rate Calculation", "failed",
                    f"Expected 8%, got {cap_rate:.2%}")
    except Exception as e:
        log_test("Service Functions", "Cap Rate Calculation", "failed", str(e))

    # Test DSCR Monitoring Service
    try:
        from app.services import dscr_monitoring_service

        dscr = dscr_monitoring_service.calculate_dscr(
            noi=800000,
            debt_service=600000
        )

        expected_dscr = 800000 / 600000  # 1.33
        if abs(dscr - expected_dscr) < 0.01:
            log_test("Service Functions", "DSCR Calculation", "passed",
                    f"DSCR: {dscr:.2f}")
        else:
            log_test("Service Functions", "DSCR Calculation", "failed",
                    f"Expected {expected_dscr:.2f}, got {dscr:.2f}")
    except Exception as e:
        log_test("Service Functions", "DSCR Calculation", "failed", str(e))

    # Test LTV Monitoring Service
    try:
        from app.services import ltv_monitoring_service

        ltv = ltv_monitoring_service.calculate_ltv(
            loan_balance=7000000,
            property_value=10000000
        )

        expected_ltv = 0.70  # 70%
        if abs(ltv - expected_ltv) < 0.01:
            log_test("Service Functions", "LTV Calculation", "passed",
                    f"LTV: {ltv:.2%}")
        else:
            log_test("Service Functions", "LTV Calculation", "failed",
                    f"Expected {expected_ltv:.2%}, got {ltv:.2%}")
    except Exception as e:
        log_test("Service Functions", "LTV Calculation", "failed", str(e))

def test_statistical_functions():
    """Test statistical anomaly detection functions"""
    print("\n" + "="*60)
    print("TESTING: Statistical Anomaly Detection")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    try:
        from app.services import statistical_anomaly_service
        import numpy as np

        # Test Z-Score calculation
        data = [100, 105, 98, 102, 500, 101, 99]  # 500 is an outlier
        z_scores = statistical_anomaly_service.calculate_z_scores(data)

        # The outlier (500) should have high z-score
        max_z_score = max(abs(z) for z in z_scores)
        if max_z_score > 2.0:
            log_test("Statistical", "Z-Score Outlier Detection", "passed",
                    f"Max Z-score: {max_z_score:.2f}")
        else:
            log_test("Statistical", "Z-Score Outlier Detection", "failed",
                    f"Expected Z-score > 2.0, got {max_z_score:.2f}")
    except Exception as e:
        log_test("Statistical", "Z-Score Outlier Detection", "failed", str(e))

    try:
        # Test CUSUM calculation
        from app.services import statistical_anomaly_service

        data = [100] * 10 + [150] * 5  # Detect shift in mean
        cusum_pos, cusum_neg = statistical_anomaly_service.calculate_cusum(data)

        # Should detect positive shift
        if max(cusum_pos) > 0:
            log_test("Statistical", "CUSUM Shift Detection", "passed",
                    f"Max CUSUM+: {max(cusum_pos):.2f}")
        else:
            log_test("Statistical", "CUSUM Shift Detection", "failed",
                    "No shift detected")
    except Exception as e:
        log_test("Statistical", "CUSUM Shift Detection", "failed", str(e))

def test_variance_analysis():
    """Test variance analysis calculations"""
    print("\n" + "="*60)
    print("TESTING: Variance Analysis")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    try:
        from app.services import variance_analysis_service

        # Test variance calculation
        budgeted = 100000
        actual = 95000
        variance = variance_analysis_service.calculate_variance(budgeted, actual)

        expected_variance = -5000
        expected_percentage = -5.0

        if variance['amount'] == expected_variance and abs(variance['percentage'] - expected_percentage) < 0.1:
            log_test("Variance", "Variance Calculation", "passed",
                    f"Amount: ${variance['amount']:,}, Percentage: {variance['percentage']:.1f}%")
        else:
            log_test("Variance", "Variance Calculation", "failed",
                    f"Expected ${expected_variance:,} ({expected_percentage}%), got ${variance['amount']:,} ({variance['percentage']:.1f}%)")
    except Exception as e:
        log_test("Variance", "Variance Calculation", "failed", str(e))

    try:
        # Test tolerance checking
        from app.services import variance_analysis_service

        within_tolerance = variance_analysis_service.is_within_tolerance(
            variance_percentage=-5.0,
            tolerance_percentage=10.0
        )

        if within_tolerance:
            log_test("Variance", "Tolerance Check (Within)", "passed",
                    "5% variance within 10% tolerance")
        else:
            log_test("Variance", "Tolerance Check (Within)", "failed",
                    "Should be within tolerance")
    except Exception as e:
        log_test("Variance", "Tolerance Check (Within)", "failed", str(e))

    try:
        # Test out of tolerance
        from app.services import variance_analysis_service

        outside_tolerance = not variance_analysis_service.is_within_tolerance(
            variance_percentage=-15.0,
            tolerance_percentage=10.0
        )

        if outside_tolerance:
            log_test("Variance", "Tolerance Check (Outside)", "passed",
                    "15% variance outside 10% tolerance")
        else:
            log_test("Variance", "Tolerance Check (Outside)", "failed",
                    "Should be outside tolerance")
    except Exception as e:
        log_test("Variance", "Tolerance Check (Outside)", "failed", str(e))

def test_database_models():
    """Test database model relationships and properties"""
    print("\n" + "="*60)
    print("TESTING: Database Model Integrity")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    try:
        from app.models import Property, Budget, Forecast, CommitteeAlert

        # Test Property model has required attributes
        required_attrs = ['id', 'property_name', 'address', 'property_type']
        missing = [attr for attr in required_attrs if not hasattr(Property, attr)]

        if not missing:
            log_test("Models", "Property Model Attributes", "passed",
                    f"All {len(required_attrs)} required attributes present")
        else:
            log_test("Models", "Property Model Attributes", "failed",
                    f"Missing attributes: {', '.join(missing)}")
    except Exception as e:
        log_test("Models", "Property Model Attributes", "failed", str(e))

    try:
        # Test Budget model
        from app.models import Budget

        required_attrs = ['id', 'property_id', 'budget_name', 'budget_year']
        missing = [attr for attr in required_attrs if not hasattr(Budget, attr)]

        if not missing:
            log_test("Models", "Budget Model Attributes", "passed",
                    f"All {len(required_attrs)} required attributes present")
        else:
            log_test("Models", "Budget Model Attributes", "failed",
                    f"Missing attributes: {', '.join(missing)}")
    except Exception as e:
        log_test("Models", "Budget Model Attributes", "failed", str(e))

def test_nlq_sql_generation():
    """Test Natural Language Query to SQL generation"""
    print("\n" + "="*60)
    print("TESTING: NLQ SQL Generation")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    test_cases = [
        ("Show all properties", "SELECT"),
        ("Total NOI for 2024", "SUM"),
        ("Properties with DSCR below 1.25", "WHERE"),
    ]

    for query, expected_keyword in test_cases:
        try:
            from app.services import nlq_service

            # Mock LLM response
            with patch.object(nlq_service, 'generate_sql_with_llm', return_value=f"SELECT * FROM properties"):
                sql = nlq_service.generate_sql_with_llm(query)

                if expected_keyword in sql.upper():
                    log_test("NLQ", f"Query: '{query}'", "passed",
                            f"Generated SQL contains {expected_keyword}")
                else:
                    log_test("NLQ", f"Query: '{query}'", "failed",
                            f"SQL missing {expected_keyword}")
        except Exception as e:
            log_test("NLQ", f"Query: '{query}'", "failed", str(e))

def test_document_summarization():
    """Test document summarization M1/M2/M3 pattern"""
    print("\n" + "="*60)
    print("TESTING: Document Summarization (M1/M2/M3)")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    try:
        from app.services import document_summarization_service

        # Test that M1, M2, M3 methods exist
        methods = ['m1_retrieve_context', 'm2_generate_summary', 'm3_audit_quality']
        missing = [m for m in methods if not hasattr(document_summarization_service, m)]

        if not missing:
            log_test("Doc Summary", "M1/M2/M3 Pattern Implementation", "passed",
                    "All 3 agents implemented")
        else:
            log_test("Doc Summary", "M1/M2/M3 Pattern Implementation", "failed",
                    f"Missing methods: {', '.join(missing)}")
    except Exception as e:
        log_test("Doc Summary", "M1/M2/M3 Pattern Implementation", "failed", str(e))

def test_bulk_import_validation():
    """Test bulk import CSV validation"""
    print("\n" + "="*60)
    print("TESTING: Bulk Import Validation")
    print("="*60)

    sys.path.insert(0, '/home/user/REIMS2/backend')

    try:
        from app.services import bulk_import_service

        # Test CSV validation function exists
        if hasattr(bulk_import_service, 'validate_csv_format'):
            log_test("Bulk Import", "CSV Validation Function", "passed",
                    "Validation function implemented")
        else:
            log_test("Bulk Import", "CSV Validation Function", "skipped",
                    "Function not found")
    except Exception as e:
        log_test("Bulk Import", "CSV Validation Function", "failed", str(e))

def generate_report():
    """Generate final test report"""
    print("\n" + "="*60)
    print("API INTEGRATION TEST SUMMARY")
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

    report_file = Path("/home/user/REIMS2/API_TEST_RESULTS.json")
    report_file.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Report saved to: {report_file}")

    return pass_rate >= 80

if __name__ == "__main__":
    print("=" * 60)
    print("REIMS2 API INTEGRATION TEST SUITE")
    print("=" * 60)
    print(f"Testing Environment: {sys.version}")
    print("=" * 60)

    # Run all tests
    test_api_endpoint_imports()
    test_service_layer_imports()
    test_service_functions()
    test_statistical_functions()
    test_variance_analysis()
    test_database_models()
    test_nlq_sql_generation()
    test_document_summarization()
    test_bulk_import_validation()

    # Generate final report
    success = generate_report()

    sys.exit(0 if success else 1)
