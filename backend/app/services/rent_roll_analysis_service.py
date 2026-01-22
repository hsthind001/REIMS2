from typing import Dict, List, Optional, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.rent_roll_data import RentRollData

class RentRollAnalysisService:
    """
    Implements forensic analysis rules for Rent Roll validation.
    Phase 1 of the forensic audit framework.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_rent_roll_integrity(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run fundamental rent roll rules (RR-1 to RR-5).
        """
        results = {}

        # Get all rent roll entries for period
        query = text("""
            SELECT * FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        result = await self.db.execute(
            query, 
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        entries = result.fetchall()

        # RR-1: Total Property Composition
        # Total Area = Occupied Area + Vacant Area
        total_area = sum(float(e.unit_area_sqft or 0) for e in entries)
        occupied_entries = [e for e in entries if e.occupancy_status == 'occupied']
        vacant_entries = [e for e in entries if e.occupancy_status == 'vacant']
        
        occupied_area = sum(float(e.unit_area_sqft or 0) for e in occupied_entries)
        vacant_area = sum(float(e.unit_area_sqft or 0) for e in vacant_entries)
        
        # Check if areas sum up (allowing small float tolerance)
        area_match = abs(total_area - (occupied_area + vacant_area)) < 1.0
        
        results['RR-1'] = {
            'rule_code': 'RR-1',
            'description': 'Total Property Composition',
            'passed': area_match,
            'details': {
                'total_area': total_area,
                'occupied_area': occupied_area,
                'vacant_area': vacant_area,
                'calculated_total': occupied_area + vacant_area
            }
        }

        # RR-2: Occupancy Rate Calculation
        # Occupancy Rate = (Occupied Area / Total Area) * 100
        calculated_occupancy = (occupied_area / total_area * 100) if total_area > 0 else 0
        
        results['RR-2'] = {
            'rule_code': 'RR-2',
            'description': 'Occupancy Rate Calculation',
            'passed': True, # This is a calculation, not a pass/fail unless compared to benchmark
            'value': round(calculated_occupancy, 2),
            'details': f"Occupancy: {calculated_occupancy:.2f}%"
        }

        # RR-3: Annual Rent Calculation
        # Annual Rent = Monthly Rent * 12
        rent_discrepancies = []
        for entry in occupied_entries:
            monthly = float(entry.monthly_rent or 0)
            annual = float(entry.annual_rent or 0)
            expected = monthly * 12
            
            if abs(annual - expected) > 1.0: # $1 tolerance
                rent_discrepancies.append({
                    'tenant': entry.tenant_name,
                    'monthly': monthly,
                    'annual': annual,
                    'expected': expected
                })
        
        results['RR-3'] = {
            'rule_code': 'RR-3',
            'description': 'Annual Rent Verification',
            'passed': len(rent_discrepancies) == 0,
            'failed_items': len(rent_discrepancies),
            'details': rent_discrepancies[:5] # Show top 5
        }

        # RR-4: Monthly Rent Per SF
        # Monthly Rent Per SF = Monthly Rent / Area
        sf_discrepancies = []
        for entry in occupied_entries:
            monthly = float(entry.monthly_rent or 0)
            area = float(entry.unit_area_sqft or 0)
            reported_psf = float(entry.monthly_rent_per_sqft or 0)
            
            if area > 0:
                calc_psf = monthly / area
                if abs(reported_psf - calc_psf) > 0.01:
                    sf_discrepancies.append({
                        'tenant': entry.tenant_name,
                        'calculated': calc_psf,
                        'reported': reported_psf
                    })

        results['RR-4'] = {
            'rule_code': 'RR-4',
            'description': 'Monthly Rent Per SF Verification',
            'passed': len(sf_discrepancies) == 0,
            'details': sf_discrepancies[:5]
        }
        
        return results

    async def analyze_tenant_risk(
        self,
        property_id: UUID, 
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run tenant risk analysis rules (RR-BS-4, RR-ALL-5).
        """
        results = {}
        
        query = text("""
            SELECT * FROM rent_roll_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND occupancy_status = 'occupied'
        """)
        
        result = await self.db.execute(
            query, 
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        entries = result.fetchall()
        
        # RR-BS-4: Tenant Concentration Risk
        # Identify top 5 tenants by annual rent
        sorted_tenants = sorted(entries, key=lambda x: float(x.annual_rent or 0), reverse=True)
        total_annual_rent = sum(float(e.annual_rent or 0) for e in entries)
        
        top_5 = sorted_tenants[:5]
        top_5_rent = sum(float(e.annual_rent or 0) for e in top_5)
        concentration_ratio = (top_5_rent / total_annual_rent) if total_annual_rent > 0 else 0
        
        results['RR-BS-4'] = {
            'rule_code': 'RR-BS-4',
            'description': 'Tenant Concentration Risk',
            'passed': concentration_ratio < 0.60, # Fail if top 5 > 60%
            'concentration_pct': round(concentration_ratio * 100, 2),
            'top_5_tenants': [
                {'name': t.tenant_name, 'rent': float(t.annual_rent or 0)} 
                for t in top_5
            ]
        }
        
        return results
