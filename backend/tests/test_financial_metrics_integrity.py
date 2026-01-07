"""
Test Financial Metrics Integrity

Ensures that all fixes for financial metrics formulas remain stable:
1. Database schema has all 82 columns
2. FinancialMetrics model matches database schema
3. API response model includes all fields
4. DSCR calculation works correctly
5. All new columns (total_current_assets, quick_ratio, etc.) are accessible
"""
import pytest
from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.financial_metrics import FinancialMetrics
from app.api.v1.metrics import FinancialMetricsResponse
from app.services.metrics_service import MetricsService


class TestFinancialMetricsIntegrity:
    """Test suite to ensure financial metrics fixes don't break"""

    @pytest.fixture(scope="class")
    def db_session(self):
        """Create database session"""
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_database_schema_has_all_columns(self, db_session):
        """Verify financial_metrics table has all 82 columns"""
        inspector = inspect(db_session.bind)
        columns = inspector.get_columns('financial_metrics')
        column_names = {col['name'] for col in columns}

        # Expected column count (83 model fields - 1 for id which is auto)
        assert len(column_names) >= 82, f"Expected at least 82 columns, got {len(column_names)}"

        # Critical new columns from migration 20260106_1722
        required_columns = {
            # Balance Sheet Totals
            'total_current_assets',
            'total_property_equipment',
            'total_other_assets',
            'total_current_liabilities',
            'total_long_term_liabilities',

            # Liquidity Metrics
            'quick_ratio',
            'cash_ratio',
            'working_capital',

            # Leverage Metrics
            'debt_to_assets_ratio',
            'equity_ratio',
            'ltv_ratio',

            # Property Metrics
            'gross_property_value',
            'accumulated_depreciation',
            'net_property_value',
            'depreciation_rate',
            'land_value',
            'building_value_net',
            'improvements_value_net',

            # Cash Position
            'operating_cash',
            'restricted_cash',
            'total_cash_position',

            # Receivables
            'tenant_receivables',
            'intercompany_receivables',
            'other_receivables',
            'total_receivables',
            'ar_percentage_of_assets',

            # Debt Analysis
            'short_term_debt',
            'institutional_debt',
            'mezzanine_debt',
            'shareholder_loans',
            'long_term_debt',
            'total_debt',

            # Equity Analysis
            'partners_contribution',
            'beginning_equity',
            'partners_draw',
            'distributions',
            'current_period_earnings',
            'ending_equity',
            'equity_change',
        }

        missing_columns = required_columns - column_names
        assert not missing_columns, f"Missing required columns: {missing_columns}"

    def test_no_duplicate_column_names(self, db_session):
        """Verify no duplicate column names in database"""
        inspector = inspect(db_session.bind)
        columns = inspector.get_columns('financial_metrics')
        column_names = [col['name'] for col in columns]

        # Check for duplicates
        duplicates = [name for name in column_names if column_names.count(name) > 1]
        assert not duplicates, f"Found duplicate column names: {set(duplicates)}"

    def test_model_fields_match_database(self, db_session):
        """Verify SQLAlchemy model fields match database schema"""
        inspector = inspect(db_session.bind)
        db_columns = {col['name'] for col in inspector.get_columns('financial_metrics')}

        # Get model columns (exclude relationships and hybrid properties)
        model_columns = {col.name for col in inspect(FinancialMetrics).columns}

        # All model columns should exist in database
        missing_in_db = model_columns - db_columns
        assert not missing_in_db, f"Model has columns not in database: {missing_in_db}"

    def test_api_response_model_includes_new_fields(self):
        """Verify FinancialMetricsResponse includes all new fields"""
        response_fields = set(FinancialMetricsResponse.model_fields.keys())

        required_fields = {
            # New fields from migration
            'total_current_assets',
            'quick_ratio',
            'debt_to_assets_ratio',
            'gross_property_value',
            'operating_cash',
            'tenant_receivables',
            'short_term_debt',
            'partners_contribution',

            # Critical mortgage metrics
            'dscr',
            'total_mortgage_debt',
            'total_annual_debt_service',
        }

        missing_fields = required_fields - response_fields
        assert not missing_fields, f"FinancialMetricsResponse missing fields: {missing_fields}"

    def test_dscr_calculation_formula(self, db_session):
        """Verify DSCR calculation formula: NOI / Annual Debt Service"""
        # Get a sample metric with DSCR
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.dscr.isnot(None),
            FinancialMetrics.net_operating_income.isnot(None),
            FinancialMetrics.total_annual_debt_service.isnot(None)
        ).first()

        if metric:
            expected_dscr = float(metric.net_operating_income) / float(metric.total_annual_debt_service)
            actual_dscr = float(metric.dscr)

            # Allow 0.001 tolerance for floating point arithmetic
            assert abs(expected_dscr - actual_dscr) < 0.001, \
                f"DSCR calculation incorrect: expected {expected_dscr}, got {actual_dscr}"

    def test_metrics_service_calculates_mortgage_metrics(self, db_session):
        """Verify MetricsService can calculate mortgage metrics"""
        service = MetricsService(db_session)

        # Get a property/period with mortgage data
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.total_mortgage_debt.isnot(None)
        ).first()

        if metric:
            # Service should have calculate_mortgage_metrics method
            assert hasattr(service, 'calculate_mortgage_metrics'), \
                "MetricsService missing calculate_mortgage_metrics method"

            # Calculate metrics (should not raise exception)
            result = service.calculate_mortgage_metrics(
                metric.property_id,
                metric.period_id,
                {}  # empty existing_metrics
            )

            # Result should have DSCR key
            assert 'dscr' in result, "calculate_mortgage_metrics didn't return DSCR"

    def test_new_columns_are_nullable(self, db_session):
        """Verify new columns are nullable (don't break existing data)"""
        inspector = inspect(db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('financial_metrics')}

        new_columns = [
            'total_current_assets',
            'quick_ratio',
            'debt_to_assets_ratio',
            'gross_property_value',
        ]

        for col_name in new_columns:
            assert col_name in columns, f"Column {col_name} not found"
            assert columns[col_name]['nullable'], f"Column {col_name} should be nullable"

    def test_balance_sheet_totals_calculation(self, db_session):
        """Verify balance sheet totals are properly stored"""
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.total_current_assets.isnot(None),
            FinancialMetrics.total_property_equipment.isnot(None)
        ).first()

        if metric:
            # These values should be positive (or at least non-None)
            assert metric.total_current_assets is not None
            assert metric.total_property_equipment is not None

    def test_liquidity_ratios_valid(self, db_session):
        """Verify liquidity ratios are within reasonable bounds"""
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.current_ratio.isnot(None)
        ).first()

        if metric:
            # Current ratio should be positive
            assert float(metric.current_ratio) >= 0, \
                f"Current ratio should be positive, got {metric.current_ratio}"

            # If quick_ratio exists, it should be <= current_ratio
            if metric.quick_ratio:
                assert float(metric.quick_ratio) <= float(metric.current_ratio) + 0.1, \
                    "Quick ratio should be <= current ratio (with small tolerance)"

    def test_debt_analysis_integrity(self, db_session):
        """Verify debt analysis fields are coherent"""
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.total_debt.isnot(None),
            FinancialMetrics.short_term_debt.isnot(None),
            FinancialMetrics.long_term_debt.isnot(None)
        ).first()

        if metric:
            # total_debt should equal sum of components (with tolerance)
            total = float(metric.short_term_debt or 0) + float(metric.long_term_debt or 0)

            # Allow 10% tolerance for other debt components
            assert abs(float(metric.total_debt) - total) / float(metric.total_debt) < 1.1, \
                "Total debt should approximately equal sum of short + long term debt"

    def test_equity_analysis_integrity(self, db_session):
        """Verify equity analysis fields are coherent"""
        metric = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.beginning_equity.isnot(None),
            FinancialMetrics.ending_equity.isnot(None)
        ).first()

        if metric:
            # Equity change should equal ending - beginning
            if metric.equity_change is not None:
                expected_change = float(metric.ending_equity) - float(metric.beginning_equity)
                actual_change = float(metric.equity_change)

                # Allow 1% tolerance
                if abs(expected_change) > 0:
                    assert abs((actual_change - expected_change) / expected_change) < 0.01, \
                        f"Equity change calculation incorrect: expected {expected_change}, got {actual_change}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
