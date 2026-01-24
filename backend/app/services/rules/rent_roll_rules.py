from sqlalchemy import text
from app.services.reconciliation_types import ReconciliationResult

class RentRollRulesMixin:
    
    def _execute_rent_roll_rules(self):
        """Execute Rent Roll rules"""
        self._rule_rr_1_annual_rent()
        self._rule_rr_2_occupancy()
        self._rule_rr_3_vacancy_calc()
        
        # Financial Calcs
        self._rule_rr_4_monthly_rent_psf()
        self._rule_rr_5_annual_rent_psf()
        
        # Tenant Specific
        self._rule_rr_6_petsmart_rent_increase()
        self._rule_rr_7_spirit_halloween_seasonal()
        
        # Aggregate Changes
        self._rule_rr_8_total_monthly_rent_check()
        self._rule_rr_9_vacant_units_tracking()
        
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
        """RR-3: Vacancy Integrity (Vacant Area match)"""
        # Rule says Total = Occupied + Vacant. We confirmed Occupied in RR-2.
        # Now verify if we have vacant units rows or if it's derived.
        # Usually RR has rows for "Vacant" status.
        
        total_area = self._get_rr_aggregate("SUM", "area")
        
        q_occ = text("SELECT SUM(area) FROM rent_roll_data WHERE property_id=:p AND period_id=:id AND status='Occupied'")
        occ_area = self.db.execute(q_occ, {"p": self.property_id, "id": self.period_id}).scalar() or 0
        
        q_vac = text("SELECT SUM(area) FROM rent_roll_data WHERE property_id=:p AND period_id=:id AND status='Vacant'")
        vac_area = self.db.execute(q_vac, {"p": self.property_id, "id": self.period_id}).scalar() or 0
        
        calc_total = occ_area + vac_area
        diff = total_area - calc_total
        
        self.results.append(ReconciliationResult(
            rule_id="RR-3",
            rule_name="Vacancy Area Check",
            category="Rent Roll",
            status="PASS" if abs(diff) < 1.0 else "WARNING",
            source_value=calc_total,
            target_value=total_area,
            difference=diff,
            variance_pct=0,
            details=f"Occ({occ_area:,.0f}) + Vac({vac_area:,.0f}) = Tot({total_area:,.0f})",
            severity="medium",
            formula="Occupied + Vacant = Total Area"
        ))

    def _rule_rr_4_monthly_rent_psf(self):
        """RR-4: Monthly Rent PSF Calculation"""
        # Check average or specific tenant integrity?
        # We can calculate aggregate $/SF
        total_area = self._get_rr_aggregate("SUM", "area")
        total_rent = self._get_rr_aggregate("SUM", "monthly_rent")
        
        psf = total_rent / total_area if total_area else 0
        
        self.results.append(ReconciliationResult(
            rule_id="RR-4",
            rule_name="Monthly Rent PSF",
            category="Rent Roll",
            status="INFO",
            source_value=psf,
            target_value=0.85, # From analysis ~0.85
            difference=psf - 0.85,
            variance_pct=0,
            details=f"Avg Rent PSF: ${psf:.2f}",
            severity="low",
            formula="Total Rent / Total Area"
        ))

    def _rule_rr_5_annual_rent_psf(self):
        """RR-5: Annual Rent PSF Calculation"""
        total_area = self._get_rr_aggregate("SUM", "area")
        total_annual = self._get_rr_aggregate("SUM", "annual_rent")
        
        psf = total_annual / total_area if total_area else 0
        
        self.results.append(ReconciliationResult(
            rule_id="RR-5",
            rule_name="Annual Rent PSF",
            category="Rent Roll",
            status="INFO",
            source_value=psf,
            target_value=10.20,
            difference=psf - 10.20,
            variance_pct=0,
            details=f"Avg Annual PSF: ${psf:.2f}",
            severity="low",
            formula="Total Annual / Total Area"
        ))

    def _rule_rr_6_petsmart_rent_increase(self):
        """RR-6: Petsmart Rent Increase Tracking"""
        # Specific check for Petsmart rent
        q = text("SELECT monthly_rent FROM rent_roll_data WHERE property_id=:p AND period_id=:id AND tenant_name ILIKE '%Petsmart%' LIMIT 1")
        val = self.db.execute(q, {"p": self.property_id, "id": self.period_id}).scalar()
        val = float(val) if val else 0
        
        # Expected is either 22,179.40 (Aug-Sep) or 23,016.35 (Oct-Dec)
        # We accept either as valid, but note it
        match = False
        if abs(val - 22179.40) < 1.0 or abs(val - 23016.35) < 1.0:
            match = True
            
        self.results.append(ReconciliationResult(
            rule_id="RR-6",
            rule_name="Petsmart Rent Check",
            category="Rent Roll",
            status="PASS" if match else "WARNING",
            source_value=val,
            target_value=23016.35, 
            difference=0,
            variance_pct=0,
            details=f"Petsmart Rent: ${val:,.2f}",
            severity="medium",
            formula="Specific Tenant Check"
        ))

    def _rule_rr_7_spirit_halloween_seasonal(self):
        """RR-7: Spirit Halloween Seasonal Logic"""
        # Check Unit 600 or 'Spirit'
        q = text("SELECT status, monthly_rent FROM rent_roll_data WHERE property_id=:p AND period_id=:id AND (tenant_name ILIKE '%Spirit%' OR unit_id='600') LIMIT 1")
        row = self.db.execute(q, {"p": self.property_id, "id": self.period_id}).mappings().first()
        
        details = "Unit 600 check"
        if row:
            if row['monthly_rent'] == 0:
                status = "PASS"
                details = f"Unit 600 Rent $0 (Correct seasonal/vacant)"
            else:
                status = "INFO"
                details = f"Unit 600 Rent ${row['monthly_rent']}"
        else:
            status = "SKIP"
            
        self.results.append(ReconciliationResult(
            rule_id="RR-7",
            rule_name="Spirit Halloween/Unit 600",
            category="Rent Roll",
            status=status,
            source_value=0,
            target_value=0,
            difference=0,
            variance_pct=0,
            details=details,
            severity="low",
            formula="Seasonal Check"
        ))

    def _rule_rr_8_total_monthly_rent_check(self):
        """RR-8: Total Monthly Rent Logic"""
        total = self._get_rr_aggregate("SUM", "monthly_rent")
        # Should be > 229k
        self.results.append(ReconciliationResult(
            rule_id="RR-8",
            rule_name="Total Monthly Rent",
            category="Rent Roll",
            status="PASS" if total > 220000 else "WARNING",
            source_value=total,
            target_value=230000,
            difference=0,
            variance_pct=0,
            details=f"Total: ${total:,.2f}",
            severity="high",
            formula="Range > 220k"
        ))

    def _rule_rr_9_vacant_units_tracking(self):
        """RR-9: Vacancy Tracking"""
        q = text("SELECT COUNT(*) FROM rent_roll_data WHERE property_id=:p AND period_id=:id AND status='Vacant'")
        count = self.db.execute(q, {"p": self.property_id, "id": self.period_id}).scalar() or 0
        
        # Expect 2 or 3
        status = "PASS" if count in [2,3] else "INFO"
        self.results.append(ReconciliationResult(
            rule_id="RR-9",
            rule_name="Vacant Unit Count",
            category="Rent Roll",
            status=status,
            source_value=count,
            target_value=2,
            difference=0,
            variance_pct=0,
            details=f"Vacant Units: {count}",
            severity="medium",
            formula="Count [2,3]"
        ))
