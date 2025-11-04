from sqlalchemy import Column, Integer, String, DECIMAL, Date, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RentRollData(Base):
    """Tenant lease information from rent roll"""
    
    __tablename__ = "rent_roll_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    
    # Tenant Information
    unit_number = Column(String(50), nullable=False)  # "B-101", "C-110"
    tenant_name = Column(String(255), nullable=False, index=True)
    tenant_code = Column(String(50))  # Internal tenant ID
    
    # Lease Information
    lease_type = Column(String(50))  # "Retail NNN", "Office Gross"
    lease_start_date = Column(Date)
    lease_end_date = Column(Date, index=True)
    lease_term_months = Column(Integer)
    remaining_lease_years = Column(DECIMAL(5, 2))
    
    # Space Information
    unit_area_sqft = Column(DECIMAL(10, 2))
    
    # Financial Information
    monthly_rent = Column(DECIMAL(12, 2))
    monthly_rent_per_sqft = Column(DECIMAL(10, 4))
    annual_rent = Column(DECIMAL(12, 2))
    annual_rent_per_sqft = Column(DECIMAL(10, 4))
    gross_rent = Column(DECIMAL(12, 2))  # Including CAM, tax, insurance
    
    # Deposits
    security_deposit = Column(DECIMAL(12, 2))
    loc_amount = Column(DECIMAL(12, 2))  # Letter of Credit
    
    # Reimbursements
    annual_cam_reimbursement = Column(DECIMAL(12, 2))
    annual_tax_reimbursement = Column(DECIMAL(12, 2))
    annual_insurance_reimbursement = Column(DECIMAL(12, 2))
    
    # Template v2.0 fields
    tenancy_years = Column(DECIMAL(5, 2))  # Years from lease start to report date
    annual_recoveries_per_sf = Column(DECIMAL(10, 4))  # CAM + tax + insurance per SF
    annual_misc_per_sf = Column(DECIMAL(10, 4))  # Misc charges per SF
    is_gross_rent_row = Column(Boolean, default=False, index=True)  # Flag for gross rent calculation rows
    parent_row_id = Column(Integer, ForeignKey('rent_roll_data.id', ondelete='CASCADE'))  # Link gross rent to parent
    notes = Column(Text)  # Extraction notes, validation flags, special conditions
    
    # Status
    occupancy_status = Column(String(50), default='occupied', index=True)  # occupied, vacant, notice
    lease_status = Column(String(50), default='active')  # active, expired, terminated
    
    # Extraction metadata
    extraction_confidence = Column(DECIMAL(5, 2))
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'unit_number', name='uq_rr_property_period_unit'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="rent_roll_data")
    period = relationship("FinancialPeriod", back_populates="rent_roll_data")
    upload = relationship("DocumentUpload", back_populates="rent_roll_data")
    
    # Self-referencing relationship for gross rent rows
    parent = relationship("RentRollData", remote_side=[id], backref="gross_rent_rows")

