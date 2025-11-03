"""
Tests for Property and FinancialPeriod models
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.property import Property
from app.models.financial_period import FinancialPeriod


@pytest.fixture
def sample_property(db_session):
    """Create a sample property for testing"""
    property_obj = Property(
        property_code="TEST001",
        property_name="Test Property",
        property_type="Retail",
        address="123 Main St",
        city="Test City",
        state="CA",
        zip_code="90001",
        country="USA",
        total_area_sqft=Decimal("5000.00"),
        acquisition_date=date(2023, 1, 1),
        status="active"
    )
    db_session.add(property_obj)
    db_session.commit()
    db_session.refresh(property_obj)
    return property_obj


class TestPropertyModel:
    """Test Property model"""
    
    def test_create_property(self, db_session):
        """Test creating a property"""
        property_obj = Property(
            property_code="ESP001",
            property_name="Esplanade Shopping Center",
            property_type="Retail",
            address="1234 Main Street",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            total_area_sqft=Decimal("125000.50"),
            status="active"
        )
        
        db_session.add(property_obj)
        db_session.commit()
        db_session.refresh(property_obj)
        
        assert property_obj.id is not None
        assert property_obj.property_code == "ESP001"
        assert property_obj.property_name == "Esplanade Shopping Center"
        assert property_obj.status == "active"
        assert property_obj.created_at is not None
    
    def test_unique_property_code(self, db_session, sample_property):
        """Test that property_code must be unique"""
        duplicate_property = Property(
            property_code="TEST001",  # Same as sample_property
            property_name="Duplicate Property",
            status="active"
        )
        
        db_session.add(duplicate_property)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_property_repr(self, sample_property):
        """Test Property __repr__ method"""
        repr_str = repr(sample_property)
        assert "TEST001" in repr_str
        assert "Test Property" in repr_str
    
    def test_validate_status(self, db_session):
        """Test status validation"""
        property_obj = Property(
            property_code="VALID001",
            property_name="Valid Property",
            status="active"
        )
        
        # Valid status should not raise
        property_obj.validate_status()
        
        # Invalid status should raise
        property_obj.status = "invalid_status"
        with pytest.raises(ValueError):
            property_obj.validate_status()
    
    def test_property_status_check_constraint(self, db_session):
        """Test database CHECK constraint on status"""
        property_obj = Property(
            property_code="BAD001",
            property_name="Bad Status Property",
            status="invalid_status"  # Invalid status
        )
        
        db_session.add(property_obj)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestFinancialPeriodModel:
    """Test FinancialPeriod model"""
    
    def test_create_financial_period(self, db_session, sample_property):
        """Test creating a financial period"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31),
            fiscal_year=2024,
            fiscal_quarter=1
        )
        
        db_session.add(period)
        db_session.commit()
        db_session.refresh(period)
        
        assert period.id is not None
        assert period.property_id == sample_property.id
        assert period.period_year == 2024
        assert period.period_month == 1
        assert period.is_closed is False
    
    def test_unique_property_period(self, db_session, sample_property):
        """Test unique constraint on (property_id, period_year, period_month)"""
        period1 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        db_session.add(period1)
        db_session.commit()
        
        # Try to create duplicate period
        period2 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,  # Same as period1
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        db_session.add(period2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_period_month_check_constraint(self, db_session, sample_property):
        """Test CHECK constraint on period_month (1-12)"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=13,  # Invalid month
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        
        db_session.add(period)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_fiscal_quarter_check_constraint(self, db_session, sample_property):
        """Test CHECK constraint on fiscal_quarter (1-4 or NULL)"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31),
            fiscal_quarter=5  # Invalid quarter
        )
        
        db_session.add(period)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_cascade_delete(self, db_session, sample_property):
        """Test cascade delete: deleting property deletes its periods"""
        # Create periods for the property
        period1 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        period2 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=2,
            period_start_date=date(2024, 2, 1),
            period_end_date=date(2024, 2, 29)
        )
        
        db_session.add_all([period1, period2])
        db_session.commit()
        
        period1_id = period1.id
        period2_id = period2.id
        
        # Delete property
        db_session.delete(sample_property)
        db_session.commit()
        
        # Verify periods are deleted
        assert db_session.query(FinancialPeriod).filter_by(id=period1_id).first() is None
        assert db_session.query(FinancialPeriod).filter_by(id=period2_id).first() is None
    
    def test_relationship_property_to_periods(self, db_session, sample_property):
        """Test relationship from Property to FinancialPeriod"""
        # Create periods
        period1 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        period2 = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=2,
            period_start_date=date(2024, 2, 1),
            period_end_date=date(2024, 2, 29)
        )
        
        db_session.add_all([period1, period2])
        db_session.commit()
        
        # Access periods through property relationship
        db_session.refresh(sample_property)
        assert len(sample_property.financial_periods) == 2
        assert period1 in sample_property.financial_periods
        assert period2 in sample_property.financial_periods
    
    def test_relationship_period_to_property(self, db_session, sample_property):
        """Test relationship from FinancialPeriod to Property"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        
        db_session.add(period)
        db_session.commit()
        db_session.refresh(period)
        
        # Access property through period relationship
        assert period.property is not None
        assert period.property.id == sample_property.id
        assert period.property.property_code == "TEST001"
    
    def test_get_period_range(self, db_session, sample_property):
        """Test get_period_range() helper method"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        
        start, end = period.get_period_range()
        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)
    
    def test_is_current_period(self, db_session, sample_property):
        """Test is_current_period() helper method"""
        today = date.today()
        
        # Current period
        current_period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=today.year,
            period_month=today.month,
            period_start_date=date(today.year, today.month, 1),
            period_end_date=today
        )
        
        assert current_period.is_current_period() is True
        
        # Past period
        past_period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2020,
            period_month=1,
            period_start_date=date(2020, 1, 1),
            period_end_date=date(2020, 1, 31)
        )
        
        assert past_period.is_current_period() is False
    
    def test_period_repr(self, db_session, sample_property):
        """Test FinancialPeriod __repr__ method"""
        period = FinancialPeriod(
            property_id=sample_property.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        
        repr_str = repr(period)
        assert str(sample_property.id) in repr_str
        assert "2024-01" in repr_str

