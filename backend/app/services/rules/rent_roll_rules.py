from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class RentRollRulesMixin:
    
    def _execute_rent_roll_rules(self):
        """Execute Rent Roll rules"""
        self._rule_rr_1_annual_rent()
        self._rule_rr_2_occupancy()
        self._rule_rr_3_vacancy_calc()
        
    def _get_rr_aggregate(self, func, column_name):
        """Helper to get aggregate from rent_roll_data"""
        query = text(f"""
            SELECT {func}({column_name})
            FROM rent_roll_data
            WHERE property_id = :p_id 
            AND period_id = :period_id
        """)
        result = self.db.execute(query, {
            "p_id": self.property_id, 
            "period_id": self.period_id
        })
        val = result.scalar()
        return float(val) if val is not None else 0.0

    def _rule_rr_1_annual_rent(self):
        """RR-1: Annual Rent = Monthly Rent * 12"""
        annual = self._get_rr_aggregate("SUM", "annual_rent")
        monthly = self._get_rr_aggregate("SUM", "monthly_rent")
        
        expected = monthly * 12
        diff = annual - expected
        
        status = "PASS" if abs(diff) < 100.0 else "WARNING"
        
        self.results.append(ReconciliationResult(
            rule_id="RR-1",
            rule_name="Annual vs Monthly Rent",
            category="Rent Roll",
            status=status,
            source_value=annual,
            target_value=expected,
            difference=diff,
            variance_pct=0.0 if expected == 0 else (abs(diff)/expected)*100,
            details=f"Annual ${annual:,.0f} vs Monthly*12 ${expected:,.0f}",
            severity="medium"
        ))

    def _rule_rr_2_occupancy(self):
        """RR-2: Calculate Occupancy Rate"""
        total_units = self._get_rr_aggregate("COUNT", "id")
        
        occupancy_query = text("""
            SELECT COUNT(*) FROM rent_roll_data 
            WHERE property_id = :p_id AND period_id = :period_id
            AND status = 'Occupied'
        """)
        res = self.db.execute(occupancy_query, {"p_id": self.property_id, "period_id": self.period_id})
        occupied_units = res.scalar() or 0
        
        rate = 0.0
        if total_units > 0:
            rate = occupied_units / total_units
            
        self.results.append(ReconciliationResult(
            rule_id="RR-2",
            rule_name="Occupancy Rate",
            category="Rent Roll",
            status="INFO",
            source_value=rate,
            target_value=0.90, 
            difference=rate - 0.90,
            variance_pct=0,
            details=f"Occupancy is {rate:.1%} ({occupied_units}/{total_units})",
            severity="info"
        ))

    def _rule_rr_3_vacancy_calc(self):
        """RR-3: Vacancy Integrity"""
        pass
