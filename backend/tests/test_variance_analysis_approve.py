"""
Tests for variance-analysis approve endpoints (Phase 2 runbook).

Ensures PUT /api/v1/variance-analysis/budgets/{id}/approve and
PUT /api/v1/variance-analysis/forecasts/{id}/approve work so AUDIT-51,
AUDIT-52, and TREND-3 can use approved budget/forecast data.
"""
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

# Skip entire module if app cannot be imported (e.g. missing slowapi in env)
pytest.importorskip("slowapi", reason="slowapi not installed; skip variance approve API tests")
from app.main import app  # noqa: E402
from app.db.database import get_db  # noqa: E402
from app.models.property import Property  # noqa: E402
from app.models.financial_period import FinancialPeriod  # noqa: E402
from app.models.budget import Budget, BudgetStatus  # noqa: E402
from app.models.forecast import Forecast  # noqa: E402


@pytest.fixture
def client_with_budget(db_session):
    """Test client with one DRAFT budget for property/period."""
    prop = Property(
        property_code="TEST-VA",
        property_name="Test Property",
        status="active",
    )
    db_session.add(prop)
    db_session.flush()
    period = FinancialPeriod(
        property_id=prop.id,
        period_year=2025,
        period_month=1,
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 1, 31),
    )
    db_session.add(period)
    db_session.flush()
    budget = Budget(
        property_id=prop.id,
        financial_period_id=period.id,
        budget_name="2025 Jan Budget",
        budget_year=2025,
        budget_period_type="monthly",
        status=BudgetStatus.DRAFT,
        account_code="4100",
        account_name="Rental Income",
        budgeted_amount=Decimal("100000.00"),
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_forecast(db_session):
    """Test client with one DRAFT forecast for property/period."""
    prop = Property(
        property_code="TEST-VA-F",
        property_name="Test Property Forecast",
        status="active",
    )
    db_session.add(prop)
    db_session.flush()
    period = FinancialPeriod(
        property_id=prop.id,
        period_year=2025,
        period_month=1,
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 1, 31),
    )
    db_session.add(period)
    db_session.flush()
    forecast = Forecast(
        property_id=prop.id,
        financial_period_id=period.id,
        forecast_name="2025 Jan Forecast",
        forecast_year=2025,
        forecast_period_type="monthly",
        forecast_type="original",
        status=BudgetStatus.DRAFT,
        account_code="4100",
        account_name="Rental Income",
        forecasted_amount=Decimal("105000.00"),
    )
    db_session.add(forecast)
    db_session.commit()
    db_session.refresh(forecast)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_budget_and_forecast(db_session):
    """Test client with one property, one period, one DRAFT budget, one DRAFT forecast (for data-status, list, PATCH)."""
    prop = Property(
        property_code="TEST-VA-DS",
        property_name="Test Data Status",
        status="active",
    )
    db_session.add(prop)
    db_session.flush()
    period = FinancialPeriod(
        property_id=prop.id,
        period_year=2025,
        period_month=1,
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 1, 31),
    )
    db_session.add(period)
    db_session.flush()
    budget = Budget(
        property_id=prop.id,
        financial_period_id=period.id,
        budget_name="2025 Jan",
        budget_year=2025,
        budget_period_type="monthly",
        status=BudgetStatus.DRAFT,
        account_code="4100",
        account_name="Rental Income",
        budgeted_amount=Decimal("100000.00"),
    )
    db_session.add(budget)
    forecast = Forecast(
        property_id=prop.id,
        financial_period_id=period.id,
        forecast_name="2025 Jan",
        forecast_year=2025,
        forecast_period_type="monthly",
        forecast_type="original",
        status=BudgetStatus.DRAFT,
        account_code="4100",
        account_name="Rental Income",
        forecasted_amount=Decimal("105000.00"),
    )
    db_session.add(forecast)
    db_session.commit()
    db_session.refresh(budget)
    db_session.refresh(forecast)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, prop.id, period.id, budget.id, forecast.id
    app.dependency_overrides.clear()


class TestApproveBudget:
    """Test PUT /api/v1/variance-analysis/budgets/{budget_id}/approve."""

    def test_approve_budget_success(self, client_with_budget):
        response = client_with_budget.put("/api/v1/variance-analysis/budgets/1/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["budget_id"] == 1
        assert data["status"] == "APPROVED"
        assert "approved_at" in data

    def test_approve_budget_with_approved_by(self, client_with_budget):
        response = client_with_budget.put(
            "/api/v1/variance-analysis/budgets/1/approve?approved_by=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APPROVED"

    def test_approve_budget_not_found(self, client_with_budget):
        response = client_with_budget.put("/api/v1/variance-analysis/budgets/999/approve")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestApproveForecast:
    """Test PUT /api/v1/variance-analysis/forecasts/{forecast_id}/approve."""

    def test_approve_forecast_success(self, client_with_forecast):
        response = client_with_forecast.put("/api/v1/variance-analysis/forecasts/1/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["forecast_id"] == 1
        assert data["status"] == "APPROVED"

    def test_approve_forecast_not_found(self, client_with_forecast):
        response = client_with_forecast.put("/api/v1/variance-analysis/forecasts/999/approve")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDataStatus:
    """Test GET /api/v1/variance-analysis/properties/{id}/periods/{id}/data-status."""

    def test_data_status_success(self, client_with_budget_and_forecast):
        client, prop_id, period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/{prop_id}/periods/{period_id}/data-status"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == prop_id
        assert data["period_id"] == period_id
        assert data["has_metrics"] is False
        assert data["approved_budget_count"] == 0
        assert data["draft_budget_count"] == 1
        assert data["approved_forecast_count"] == 0
        assert data["draft_forecast_count"] == 1

    def test_data_status_not_found_property(self, client_with_budget_and_forecast):
        client, _prop_id, period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/99999/periods/{period_id}/data-status"
        )
        assert response.status_code == 404

    def test_data_status_not_found_period(self, client_with_budget_and_forecast):
        client, prop_id, _period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/{prop_id}/periods/99999/data-status"
        )
        assert response.status_code == 404


class TestListBudgetsForecasts:
    """Test GET list budgets and list forecasts for property/period."""

    def test_list_budgets_success(self, client_with_budget_and_forecast):
        client, prop_id, period_id, budget_id, _fid = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/{prop_id}/periods/{period_id}/budgets"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == budget_id
        assert data[0]["account_code"] == "4100"
        assert data[0]["budgeted_amount"] == 100000.0
        assert data[0]["status"] == "DRAFT"

    def test_list_forecasts_success(self, client_with_budget_and_forecast):
        client, prop_id, period_id, _bid, forecast_id = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/{prop_id}/periods/{period_id}/forecasts"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == forecast_id
        assert data[0]["account_code"] == "4100"
        assert data[0]["forecasted_amount"] == 105000.0
        assert data[0]["status"] == "DRAFT"

    def test_list_budgets_not_found_property(self, client_with_budget_and_forecast):
        client, _prop_id, period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.get(
            f"/api/v1/variance-analysis/properties/99999/periods/{period_id}/budgets"
        )
        assert response.status_code == 404


class TestPatchBudgetForecast:
    """Test PATCH /api/v1/variance-analysis/budgets/{id} and /forecasts/{id}."""

    def test_patch_budget_amount_success(self, client_with_budget_and_forecast):
        client, _prop_id, _period_id, budget_id, _fid = client_with_budget_and_forecast
        response = client.patch(
            f"/api/v1/variance-analysis/budgets/{budget_id}",
            json={"budgeted_amount": 120000.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == budget_id
        assert data["budgeted_amount"] == 120000.0
        assert data["status"] == "DRAFT"

    def test_patch_forecast_amount_success(self, client_with_budget_and_forecast):
        client, _prop_id, _period_id, _bid, forecast_id = client_with_budget_and_forecast
        response = client.patch(
            f"/api/v1/variance-analysis/forecasts/{forecast_id}",
            json={"forecasted_amount": 110000.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == forecast_id
        assert data["forecasted_amount"] == 110000.0
        assert data["status"] == "DRAFT"

    def test_patch_budget_not_found(self, client_with_budget_and_forecast):
        client, _prop_id, _period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.patch(
            "/api/v1/variance-analysis/budgets/99999",
            json={"budgeted_amount": 100.0},
        )
        assert response.status_code == 404

    def test_patch_forecast_not_found(self, client_with_budget_and_forecast):
        client, _prop_id, _period_id, _bid, _fid = client_with_budget_and_forecast
        response = client.patch(
            "/api/v1/variance-analysis/forecasts/99999",
            json={"forecasted_amount": 100.0},
        )
        assert response.status_code == 404
