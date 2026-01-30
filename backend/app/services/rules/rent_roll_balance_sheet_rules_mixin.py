from sqlalchemy import text

from app.services.reconciliation_types import ReconciliationResult
from app.services.rules.covenant_resolver import get_numeric_config_sync


class RentRollBalanceSheetRulesMixin:
    """
    Rent roll to balance sheet forensic rules.
    Source: rent_roll_balance_sheet_forensic_rules.md
    """

    def _execute_rent_roll_balance_sheet_rules(self):
        self._rule_rrbs_1_security_deposits_floor()
        self._rule_rrbs_2_ar_reasonableness()
        self._rule_rrbs_3_prepaid_rent()
        self._rule_rrbs_4_lease_roster_completeness()

    def _add_result(self, **kwargs):
        self.results.append(ReconciliationResult(**kwargs))

    def _rule_rrbs_1_security_deposits_floor(self):
        rr_deposits = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(security_deposit), 0)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        bs_deposits = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (
                    account_name ILIKE '%deposit%' OR account_name ILIKE '%security deposit%'
                  )
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        diff = float(bs_deposits) - float(rr_deposits)
        tolerance = get_numeric_config_sync(self.db, "rrbs_1_tolerance_usd", 1.0)
        status = "PASS" if diff >= -abs(tolerance) else "FAIL"
        self._add_result(
            rule_id="RRBS-1",
            rule_name="Security Deposits Liability Floor",
            category="Rent Roll/BS",
            status=status,
            source_value=float(bs_deposits),
            target_value=float(rr_deposits),
            difference=float(diff),
            variance_pct=0.0,
            details=f"BS deposits ${bs_deposits:,.2f} vs RR deposits ${rr_deposits:,.2f} (tolerance ${tolerance:,.2f})",
            severity="high" if status == "FAIL" else "info",
            formula="BS deposit liability >= rent roll deposits",
        )

    def _rule_rrbs_2_ar_reasonableness(self):
        """FA-RR-2: A/R reasonableness with AR_Months bands (Excellent/Good/Acceptable/Concerning/Critical)."""
        ar = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%a/r%' AND account_name ILIKE '%tenant%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        rr_monthly = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(monthly_rent), 0)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        ar_f = float(ar)
        rr_monthly_f = float(rr_monthly)
        # AR_Months = BS.AR_Tenants / Monthly_Scheduled_Rent (spec)
        ar_months = (ar_f / rr_monthly_f) if rr_monthly_f > 0 else 0.0
        # Bands: <0.5 Excellent, 0.5-1.0 Good, 1.0-2.0 Acceptable, 2.0-3.0 Concerning, 3.0+ Critical
        if ar_months < 0.5:
            band = "Excellent"
        elif ar_months < 1.0:
            band = "Good"
        elif ar_months < 2.0:
            band = "Acceptable"
        elif ar_months < 3.0:
            band = "Concerning"
        else:
            band = "Critical"
        threshold_months = 2.0
        allowed = rr_monthly_f * threshold_months
        status = "PASS" if ar_f <= allowed else "FAIL"
        details = (
            f"A/R ${ar_f:,.2f} vs {threshold_months} months rent ${allowed:,.2f}; "
            f"AR_Months={ar_months:.2f} (band: {band})"
        )
        self._add_result(
            rule_id="RRBS-2",
            rule_name="Tenant A/R Reasonableness",
            category="Rent Roll/BS",
            status=status,
            source_value=float(ar_f),
            target_value=float(allowed),
            difference=float(ar_f - allowed),
            variance_pct=0.0,
            details=details,
            severity="medium" if status == "FAIL" else "info",
            formula="A/R <= 2 months scheduled rent; AR_Months = A/R / Monthly_Scheduled_Rent",
            intermediate_calculations={
                "ar_months": ar_months,
                "band": band,
                "monthly_scheduled_rent": rr_monthly_f,
            },
        )

    def _rule_rrbs_3_prepaid_rent(self):
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not prior_id:
            self._add_result(
                rule_id="RRBS-3",
                rule_name="Prepaid Rent / Rent Received in Advance",
                category="Rent Roll/BS",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable",
                severity="medium",
                formula="Large increases require explanation",
            )
            return
        curr = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (account_name ILIKE '%rent received%' OR account_name ILIKE '%prepaid rent%')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (account_name ILIKE '%rent received%' OR account_name ILIKE '%prepaid rent%')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        delta = float(curr) - float(prior)
        # Spec: flag changes > $20,000; configurable via system_config
        threshold = 20000.0
        if hasattr(self, "_get_config_threshold"):
            threshold = float(self._get_config_threshold("forensic_prepaid_rent_material_threshold", 20000.0))
        status = "PASS" if abs(delta) <= threshold else "FAIL"
        self._add_result(
            rule_id="RRBS-3",
            rule_name="Prepaid Rent / Rent Received in Advance",
            category="Rent Roll/BS",
            status=status,
            source_value=float(delta),
            target_value=0.0,
            difference=float(delta),
            variance_pct=0.0,
            details=f"Change in prepaid rent ${delta:,.2f} (material threshold ${threshold:,.0f})",
            severity="medium" if status == "FAIL" else "info",
            formula="Large increases require explanation (threshold config: forensic_prepaid_rent_material_threshold)",
        )

    def _rule_rrbs_4_lease_roster_completeness(self):
        occupied = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND occupancy_status ILIKE 'occupied'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        duplicate_units = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT unit_number, COUNT(*) AS cnt
                    FROM rent_roll_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND (is_gross_rent_row IS NOT TRUE)
                    GROUP BY unit_number
                    HAVING COUNT(*) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        duplicate_codes = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT tenant_code, COUNT(*) AS cnt
                    FROM rent_roll_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND tenant_code IS NOT NULL
                      AND tenant_code <> ''
                      AND (is_gross_rent_row IS NOT TRUE)
                    GROUP BY tenant_code
                    HAVING COUNT(*) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        missing_codes = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                  AND (tenant_code IS NULL OR tenant_code = '')
                  AND (is_gross_rent_row IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        duplicate_tenants = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT tenant_name, COUNT(*) AS cnt
                    FROM rent_roll_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                      AND (is_gross_rent_row IS NOT TRUE)
                    GROUP BY tenant_name
                    HAVING COUNT(*) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        base_rent = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%base rent%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        status = "PASS" if (occupied == 0 or base_rent != 0) and duplicate_units == 0 and missing_codes == 0 else "FAIL"
        self._add_result(
            rule_id="RRBS-4",
            rule_name="Lease Roster Completeness",
            category="Rent Roll/BS",
            status=status,
            source_value=float(base_rent),
            target_value=1.0,
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Occupied tenants {occupied}, Base rent ${base_rent:,.2f}, "
                f"Duplicate units {duplicate_units}, duplicate tenant names {duplicate_tenants}, "
                f"Duplicate tenant codes {duplicate_codes}, missing tenant codes {missing_codes}"
            ),
            severity="high" if status == "FAIL" else "info",
            formula="Occupied leases should map to revenue streams",
        )
