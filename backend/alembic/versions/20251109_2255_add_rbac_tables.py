"""add rbac tables

Revision ID: 20251109_2255
Revises: 20251109_2245
Create Date: 2025-11-09 22:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20251109_2255'
down_revision = '20251109_2245'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('resource', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    
    # Create role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    
    # Seed roles
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('Admin', 'Full system access'),
        ('Manager', 'Property and team management'),
        ('Analyst', 'View and analyze financial data'),
        ('Viewer', 'Read-only access to reports')
    """)
    
    # Seed permissions
    op.execute("""
        INSERT INTO permissions (name, resource, action, description) VALUES
        ('view_documents', 'document', 'read', 'View documents'),
        ('upload_documents', 'document', 'create', 'Upload documents'),
        ('delete_documents', 'document', 'delete', 'Delete documents'),
        ('view_financials', 'financial', 'read', 'View financial data'),
        ('edit_financials', 'financial', 'update', 'Edit financial data'),
        ('manage_users', 'user', 'manage', 'Manage user accounts'),
        ('manage_properties', 'property', 'manage', 'Manage properties'),
        ('view_audit_log', 'audit', 'read', 'View audit trail')
    """)


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')

