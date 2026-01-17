"""Add Organization and OrganizationMember models for SaaS

Revision ID: 20260117_0001_saas_models
Revises: 20260116_0001_perf_indexes
Create Date: 2026-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260117_0001_saas_models'
down_revision = '20260116_0001_perf_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create Organization table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('subscription_status', sa.String(), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # 2. Create OrganizationMember table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=True, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_members_id'), 'organization_members', ['id'], unique=False)

    # 3. Add organization_id to Properties table
    op.add_column('properties', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_property_organization', 'properties', 'organizations', ['organization_id'], ['id'])


def downgrade() -> None:
    # 1. Remove foreign key and column from Properties
    op.drop_constraint('fk_property_organization', 'properties', type_='foreignkey')
    op.drop_column('properties', 'organization_id')

    # 2. Drop OrganizationMember table
    op.drop_index(op.f('ix_organization_members_id'), table_name='organization_members')
    op.drop_table('organization_members')

    # 3. Drop Organization table
    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
