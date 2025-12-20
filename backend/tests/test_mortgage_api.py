"""
Integration tests for Mortgage API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date

from app.main import app
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.mortgage_statement_data import MortgageStatementData


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_property(db: Session):
    """Create test property"""
    property = Property(
        property_code="TEST001",
        property_name="Test Property",
        status="active"
    )
    db.add(property)
    db.commit()
    db.refresh(property)
    return property


@pytest.fixture
def test_period(db: Session, test_property):
    """Create test financial period"""
    period = FinancialPeriod(
        property_id=test_property.id,
        period_year=2024,
        period_month=12,
        period_start_date=date(2024, 12, 1),
        period_end_date=date(2024, 12, 31)
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@pytest.fixture
def test_mortgage(db: Session, test_property, test_period):
    """Create test mortgage statement"""
    mortgage = MortgageStatementData(
        property_id=test_property.id,
        period_id=test_period.id,
        loan_number="123456789",
        statement_date=date(2024, 12, 31),
        principal_balance=Decimal("10000000"),
        interest_rate=Decimal("5.25"),
        monthly_debt_service=Decimal("90000"),
        annual_debt_service=Decimal("1080000"),
        total_payment_due=Decimal("98000"),
        maturity_date=date(2030, 12, 31)
    )
    db.add(mortgage)
    db.commit()
    db.refresh(mortgage)
    return mortgage


class TestMortgageAPI:
    """Test mortgage API endpoints"""
    
    def test_get_mortgages_by_property_period(
        self,
        client: TestClient,
        test_property,
        test_period,
        test_mortgage,
        db: Session
    ):
        """Test GET mortgages by property/period endpoint"""
        response = client.get(
            f"/api/v1/mortgage/properties/{test_property.id}/periods/{test_period.id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["loan_number"] == "123456789"
    
    def test_get_mortgage_detail(
        self,
        client: TestClient,
        test_mortgage,
        db: Session
    ):
        """Test GET mortgage detail endpoint"""
        response = client.get(f"/api/v1/mortgage/{test_mortgage.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["loan_number"] == "123456789"
        assert data["principal_balance"] == 10000000.0
        assert "payment_history" in data
    
    def test_get_mortgage_not_found(self, client: TestClient):
        """Test GET mortgage detail with non-existent ID"""
        response = client.get("/api/v1/mortgage/99999")
        
        assert response.status_code == 404
    
    def test_get_dscr_history(
        self,
        client: TestClient,
        test_property,
        db: Session
    ):
        """Test GET DSCR history endpoint"""
        response = client.get(
            f"/api/v1/mortgage/properties/{test_property.id}/dscr-history?limit=12"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "property_id" in data
        assert "property_code" in data
        assert "history" in data
    
    def test_get_ltv_history(
        self,
        client: TestClient,
        test_property,
        db: Session
    ):
        """Test GET LTV history endpoint"""
        response = client.get(
            f"/api/v1/mortgage/properties/{test_property.id}/ltv-history?limit=12"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "property_id" in data
        assert "property_code" in data
        assert "history" in data
    
    def test_get_debt_summary(
        self,
        client: TestClient,
        test_property,
        test_period,
        test_mortgage,
        db: Session
    ):
        """Test GET debt summary endpoint"""
        response = client.get(
            f"/api/v1/mortgage/properties/{test_property.id}/periods/{test_period.id}/debt-summary"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_mortgage_debt" in data
        assert "total_annual_debt_service" in data
        assert "dscr" in data
        assert "mortgage_count" in data
    
    def test_get_covenant_monitoring(
        self,
        client: TestClient,
        test_property,
        db: Session
    ):
        """Test GET covenant monitoring endpoint"""
        response = client.get("/api/v1/mortgage/covenant-monitoring")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_maturity_calendar(
        self,
        client: TestClient,
        test_mortgage,
        db: Session
    ):
        """Test GET maturity calendar endpoint"""
        response = client.get("/api/v1/mortgage/maturity-calendar?months_ahead=24")
        
        assert response.status_code == 200
        data = response.json()
        assert "upcoming_maturities" in data
        assert "total_upcoming" in data
        assert isinstance(data["upcoming_maturities"], list)


