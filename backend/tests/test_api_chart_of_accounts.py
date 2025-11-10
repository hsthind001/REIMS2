"""
Tests for Chart of Accounts API endpoints - Sprint 2.1
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

from app.main import app
from app.db.database import get_db


# Create separate base for testing
TestBase = declarative_base()


class User(TestBase):
    """User model for testing"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ChartOfAccounts(TestBase):
    """Chart of Accounts model for testing - SQLite compatible"""
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(50), unique=True, nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False, index=True)
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    parent_account_code = Column(String(50))
    document_types = Column(Text)  # Store as JSON string for SQLite compatibility
    is_calculated = Column(Boolean, default=False)
    calculation_formula = Column(Text)
    display_order = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @property
    def document_types_list(self):
        """Parse document_types from JSON string"""
        import json
        if self.document_types:
            try:
                return json.loads(self.document_types)
            except:
                return []
        return []


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    TestBase.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Create system user for authentication
    system_user = User(
        username="system",
        email="system@reims.local",
        hashed_password="not_used",
        is_active=True,
        is_superuser=True
    )
    session.add(system_user)
    session.commit()
    
    yield session
    session.close()
    TestBase.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create authenticated test client with database override"""
    from app.api.dependencies import get_current_user
    
    # Get the system user from db_session
    system_user = db_session.query(User).filter(User.username == "system").first()
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_current_user():
        """Override authentication to return system user"""
        return system_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    test_client = TestClient(app)
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_accounts(db_session):
    """Create sample chart of accounts for testing"""
    import json
    
    accounts = [
        ChartOfAccounts(
            account_code="0100-0000",
            account_name="ASSETS",
            account_type="asset",
            category="header",
            is_calculated=True,
            display_order=1,
            document_types=json.dumps(["balance_sheet"])
        ),
        ChartOfAccounts(
            account_code="0122-0000",
            account_name="Cash - Operating",
            account_type="asset",
            category="current_asset",
            subcategory="cash",
            parent_account_code="0100-0000",
            display_order=2,
            document_types=json.dumps(["balance_sheet", "cash_flow"])
        ),
        ChartOfAccounts(
            account_code="0305-0000",
            account_name="A/R Tenants",
            account_type="asset",
            category="current_asset",
            subcategory="accounts_receivable",
            parent_account_code="0100-0000",
            display_order=3,
            document_types=json.dumps(["balance_sheet"])
        ),
        ChartOfAccounts(
            account_code="2000-0000",
            account_name="LIABILITIES",
            account_type="liability",
            category="header",
            is_calculated=True,
            display_order=10,
            document_types=json.dumps(["balance_sheet"])
        ),
        ChartOfAccounts(
            account_code="2612-0000",
            account_name="NorthMarq Capital",
            account_type="liability",
            category="long_term_liability",
            subcategory="mortgage",
            parent_account_code="2000-0000",
            display_order=11,
            document_types=json.dumps(["balance_sheet"])
        ),
        ChartOfAccounts(
            account_code="4010-0000",
            account_name="Base Rentals",
            account_type="income",
            category="rental_income",
            subcategory="base_rent",
            display_order=20,
            document_types=json.dumps(["income_statement"])
        ),
        ChartOfAccounts(
            account_code="5010-0000",
            account_name="Property Tax",
            account_type="expense",
            category="operating_expense",
            subcategory="property_tax",
            display_order=30,
            document_types=json.dumps(["income_statement", "cash_flow"])
        ),
        ChartOfAccounts(
            account_code="9999-0000",
            account_name="Inactive Account",
            account_type="expense",
            category="test",
            is_active=False,
            display_order=99,
            document_types=json.dumps(["test"])
        ),
    ]
    
    for account in accounts:
        db_session.add(account)
    db_session.commit()
    
    return accounts


class TestChartOfAccountsAPI:
    """Test Chart of Accounts API endpoints"""
    
    def test_list_all_accounts(self, client, sample_accounts):
        """Test GET /api/v1/chart-of-accounts/ - list all accounts"""
        response = client.get("/api/v1/chart-of-accounts/")
        
        assert response.status_code == 200
        data = response.json()
        # By default, only active accounts are returned
        assert len(data) == 7  # 8 accounts - 1 inactive
    
    def test_list_all_accounts_including_inactive(self, client, sample_accounts):
        """Test listing including inactive accounts"""
        response = client.get("/api/v1/chart-of-accounts/?is_active=false")
        
        assert response.status_code == 200
        data = response.json()
        inactive_codes = [acc["account_code"] for acc in data if not acc["is_active"]]
        assert "9999-0000" in inactive_codes
    
    def test_filter_by_account_type(self, client, sample_accounts):
        """Test filtering by account type"""
        response = client.get("/api/v1/chart-of-accounts/?account_type=asset")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for account in data:
            assert account["account_type"] == "asset"
    
    def test_filter_by_category(self, client, sample_accounts):
        """Test filtering by category"""
        response = client.get("/api/v1/chart-of-accounts/?category=current_asset")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for account in data:
            assert account["category"] == "current_asset"
    
    def test_filter_by_subcategory(self, client, sample_accounts):
        """Test filtering by subcategory"""
        response = client.get("/api/v1/chart-of-accounts/?subcategory=cash")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for account in data:
            assert account["subcategory"] == "cash"
    
    def test_filter_by_document_type(self, client, sample_accounts):
        """Test filtering by document type"""
        response = client.get("/api/v1/chart-of-accounts/?document_type=cash_flow")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for account in data:
            assert "cash_flow" in account["document_types"]
    
    def test_filter_calculated_fields(self, client, sample_accounts):
        """Test filtering calculated fields"""
        response = client.get("/api/v1/chart-of-accounts/?is_calculated=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for account in data:
            assert account["is_calculated"] is True
    
    def test_search_by_code(self, client, sample_accounts):
        """Test search by account code"""
        response = client.get("/api/v1/chart-of-accounts/?search=0122")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("0122" in acc["account_code"] for acc in data)
    
    def test_search_by_name(self, client, sample_accounts):
        """Test search by account name"""
        response = client.get("/api/v1/chart-of-accounts/?search=Cash")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Cash" in acc["account_name"] for acc in data)
    
    def test_pagination(self, client, sample_accounts):
        """Test pagination"""
        # Get first 3 accounts
        response1 = client.get("/api/v1/chart-of-accounts/?skip=0&limit=3")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1) == 3
        
        # Get next 3 accounts
        response2 = client.get("/api/v1/chart-of-accounts/?skip=3&limit=3")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Ensure no overlap
        codes1 = {acc["account_code"] for acc in data1}
        codes2 = {acc["account_code"] for acc in data2}
        assert codes1.isdisjoint(codes2)
    
    def test_get_account_by_code(self, client, sample_accounts):
        """Test GET /api/v1/chart-of-accounts/{account_code}"""
        response = client.get("/api/v1/chart-of-accounts/0122-0000")
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_code"] == "0122-0000"
        assert data["account_name"] == "Cash - Operating"
    
    def test_get_account_not_found(self, client, sample_accounts):
        """Test getting non-existent account"""
        response = client.get("/api/v1/chart-of-accounts/9999-9999")
        assert response.status_code == 404
    
    def test_get_account_children(self, client, sample_accounts):
        """Test GET /api/v1/chart-of-accounts/{account_code}/children"""
        response = client.get("/api/v1/chart-of-accounts/0100-0000/children")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for account in data:
            assert account["parent_account_code"] == "0100-0000"
    
    def test_get_summary(self, client, sample_accounts):
        """Test GET /api/v1/chart-of-accounts/summary"""
        response = client.get("/api/v1/chart-of-accounts/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_accounts" in data
        assert "active_accounts" in data
        assert "calculated_accounts" in data
        assert "by_type" in data
        
        assert data["total_accounts"] == 8
        assert data["active_accounts"] == 7
        assert data["calculated_accounts"] >= 2
        assert "asset" in data["by_type"]
        assert "liability" in data["by_type"]
        assert "income" in data["by_type"]
        assert "expense" in data["by_type"]
    
    def test_create_account(self, client, sample_accounts):
        """Test POST /api/v1/chart-of-accounts/"""
        new_account = {
            "account_code": "TEST-001",
            "account_name": "Test Account",
            "account_type": "asset",
            "category": "test",
            "is_calculated": False,
            "is_active": True
        }
        
        response = client.post("/api/v1/chart-of-accounts/", json=new_account)
        
        assert response.status_code == 201
        data = response.json()
        assert data["account_code"] == "TEST-001"
        assert data["account_name"] == "Test Account"
    
    def test_create_duplicate_account(self, client, sample_accounts):
        """Test creating account with duplicate code"""
        duplicate_account = {
            "account_code": "0122-0000",  # Existing code
            "account_name": "Duplicate",
            "account_type": "asset"
        }
        
        response = client.post("/api/v1/chart-of-accounts/", json=duplicate_account)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_update_account(self, client, sample_accounts):
        """Test PUT /api/v1/chart-of-accounts/{account_code}"""
        update_data = {
            "account_name": "Updated Cash Account",
            "subcategory": "updated_cash"
        }
        
        response = client.put("/api/v1/chart-of-accounts/0122-0000", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["account_name"] == "Updated Cash Account"
        assert data["subcategory"] == "updated_cash"
    
    def test_update_account_not_found(self, client, sample_accounts):
        """Test updating non-existent account"""
        update_data = {"account_name": "Updated"}
        response = client.put("/api/v1/chart-of-accounts/9999-9999", json=update_data)
        assert response.status_code == 404
    
    def test_delete_account(self, client, sample_accounts):
        """Test DELETE /api/v1/chart-of-accounts/{account_code}"""
        response = client.delete("/api/v1/chart-of-accounts/9999-0000")
        
        assert response.status_code == 204
        
        # Verify account is deleted
        get_response = client.get("/api/v1/chart-of-accounts/9999-0000")
        assert get_response.status_code == 404
    
    def test_delete_account_not_found(self, client, sample_accounts):
        """Test deleting non-existent account"""
        response = client.delete("/api/v1/chart-of-accounts/9999-9999")
        assert response.status_code == 404
    
    def test_combined_filters(self, client, sample_accounts):
        """Test combining multiple filters"""
        response = client.get(
            "/api/v1/chart-of-accounts/?account_type=asset&category=current_asset&is_active=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        for account in data:
            assert account["account_type"] == "asset"
            assert account["category"] == "current_asset"
            assert account["is_active"] is True

