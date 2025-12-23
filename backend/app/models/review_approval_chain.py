"""
Review Approval Chain Model

Tracks approval chains for dual approval (4-eyes) mechanism.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class ApprovalStatus(str, enum.Enum):
    """Approval status enum."""
    PENDING = "pending"
    FIRST_APPROVED = "first_approved"
    SECOND_APPROVED = "second_approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewApprovalChain(Base):
    """Tracks approval chain for review items requiring dual approval."""
    
    __tablename__ = "review_approval_chains"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to review item
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    
    # Approval status
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True)
    
    # First approval
    first_approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    first_approved_at = Column(DateTime(timezone=True), nullable=True)
    first_approval_notes = Column(Text, nullable=True)
    
    # Second approval (required for high-risk items)
    second_approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    second_approved_at = Column(DateTime(timezone=True), nullable=True)
    second_approval_notes = Column(Text, nullable=True)
    
    # Rejection
    rejected_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    first_approver = relationship("User", foreign_keys=[first_approver_id])
    second_approver = relationship("User", foreign_keys=[second_approver_id])
    rejector = relationship("User", foreign_keys=[rejected_by])
