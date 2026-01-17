from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declared_attr

class TenantMixin:
    """
    Mixin to add organization context to models.
    Provides standard organization_id column and relationship.
    """
    
    @declared_attr
    def organization_id(cls):
        # Nullable=True for now to allow migration of existing data, 
        # but intention is for it to be required for new records.
        return Column(Integer, ForeignKey('organizations.id'), nullable=True, index=True)

    @declared_attr
    def organization(cls):
        return relationship("Organization")

    @classmethod
    def filter_by_org(cls, query, organization_id: int):
        """Helper to filter query by organization_id"""
        return query.filter(cls.organization_id == organization_id)
