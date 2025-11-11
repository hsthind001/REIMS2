"""Seed sample properties

Revision ID: b1f3e8d4c7a2
Revises: a9a5178a1b3f
Create Date: 2025-11-04 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f3e8d4c7a2'
down_revision: Union[str, Sequence[str], None] = 'a9a5178a1b3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed sample properties - idempotent"""
    # Insert sample properties if they don't already exist
    op.execute("""
        INSERT INTO properties (
            property_code, property_name, property_type, 
            address, city, state, zip_code, country,
            total_area_sqft, acquisition_date, ownership_structure,
            status, notes, created_at
        )
        VALUES 
            (
                'ESP001', 
                'Eastern Shore Plaza', 
                'retail',
                '1234 Main Street',
                'Phoenix',
                'AZ',
                '85001',
                'USA',
                125000.50,
                '2020-01-15',
                'LLC',
                'active',
                'Premium shopping center in Phoenix metro area',
                NOW()
            ),
            (
                'HMND001',
                'Hammond Aire Shopping Center',
                'retail',
                '5678 Commerce Drive',
                'Hammond',
                'IN',
                '46320',
                'USA',
                98500.00,
                '2019-06-01',
                'Partnership',
                'active',
                'Regional shopping center in Hammond, Indiana',
                NOW()
            ),
            (
                'TCSH001',
                'The Crossings of Spring Hill',
                'retail',
                '9012 Center Boulevard',
                'Town Center',
                'FL',
                '33411',
                'USA',
                110250.00,
                '2021-03-20',
                'LLC',
                'active',
                'Mixed-use retail center in South Florida',
                NOW()
            ),
            (
                'WEND001',
                'Wendover Commons',
                'retail',
                '3456 Wendover Avenue',
                'Greensboro',
                'NC',
                '27407',
                'USA',
                87600.00,
                '2018-11-10',
                'LLC',
                'active',
                'Community shopping center in Greensboro, NC',
                NOW()
            )
        ON CONFLICT (property_code) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove sample properties"""
    op.execute("""
        DELETE FROM properties 
        WHERE property_code IN ('ESP001', 'HMND001', 'TCSH001', 'WEND001');
    """)

