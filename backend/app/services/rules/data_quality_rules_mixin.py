import calendar
from datetime import date, timedelta
from sqlalchemy import text

from app.services.reconciliation_types import ReconciliationResult


class DataQualityRulesMixin:
    """
    Data quality and integrity rules.
    Source: DATA_QUALITY_INTEGRITY_RULES.md
    """

    def _execute_data_quality_rules(self):
        self._rule_dq_1_document_inventory()
        self._rule_dq_2_required_fields()
        self._rule_dq_3_temporal_continuity()
        self._rule_dq_4_math_balance_sheet()
        self._rule_dq_5_math_income_statement()
        self._rule_dq_6_math_cash_flow()
        self._rule_dq_7_math_rent_roll()
        self._rule_dq_8_math_mortgage()
        self._rule_dq_9_account_name_consistency()
        self._rule_dq_10_value_range_consistency()
        self._rule_dq_11_format_consistency()
        self._rule_dq_12_period_label_consistency()
        self._rule_dq_13_cross_period_integrity()
        self._rule_dq_14_reference_data_integrity()
        self._rule_dq_15_referential_integrity()
        self._rule_dq_16_timeliness()
        self._rule_dq_17_currency()
        self._rule_dq_18_precision()
        self._rule_dq_19_rounding()
        self._rule_dq_20_sign_convention()
        self._rule_dq_21_unusual_values()
        self._rule_dq_22_authenticity()
        self._rule_dq_23_version_control()
        self._rule_dq_24_extraction_accuracy()
        self._rule_dq_25_calculation_accuracy()
        self._rule_dq_26_scorecard()
        self._rule_dq_27_trend_analysis()
        self._rule_dq_28_data_ownership()
        self._rule_dq_29_access_controls()
        self._rule_dq_30_retention_policy()
        self._rule_dq_31_error_classification()
        self._rule_dq_32_error_correction_process()
        self._rule_dq_33_preventive_controls()

    def _add_result(self, **kwargs):
        self.results.append(ReconciliationResult(**kwargs))

    def _safe_count(self, query: str, params: dict | None = None) -> int:
        try:
            return int(self.db.execute(text(query), params or {}).scalar() or 0)
        except Exception:
            return 0

    def _get_period_year_month(self):
        row = self.db.execute(
            text(
                """
                SELECT period_year, period_month
                FROM financial_periods
                WHERE id = :period_id
                """
            ),
            {"period_id": int(self.period_id)},
        ).fetchone()
        if not row:
            return None, None
        return int(row[0]), int(row[1])

    def _get_period_end_date(self):
        year, month = self._get_period_year_month()
        if not year or not month:
            return None
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)

    def _rule_dq_1_document_inventory(self):
        year, _ = self._get_period_year_month()
        if not year:
            self._add_result(
                rule_id="DQ-1",
                rule_name="Required Document Inventory",
                category="Data Quality",
                status="INFO",
                source_value=0,
                target_value=12,
                difference=0.0,
                variance_pct=0.0,
                details="Unable to determine current period year",
                severity="critical",
                formula="12 monthly documents required",
            )
            return
        rows = self.db.execute(
            text(
                """
                SELECT fp.id, pdc.has_balance_sheet, pdc.has_income_statement,
                       pdc.has_cash_flow, pdc.has_rent_roll, pdc.has_mortgage_statement
                FROM financial_periods fp
                LEFT JOIN period_document_completeness pdc
                  ON pdc.period_id = fp.id AND pdc.property_id = fp.property_id
                WHERE fp.property_id = :property_id
                  AND fp.period_year = :year
                """
            ),
            {"property_id": int(self.property_id), "year": int(year)},
        ).fetchall()
        expected = 12
        if not rows:
            self._add_result(
                rule_id="DQ-1",
                rule_name="Required Document Inventory",
                category="Data Quality",
                status="FAIL",
                source_value=0,
                target_value=expected,
                difference=float(-expected),
                variance_pct=0.0,
                details=f"No document completeness data for {year}",
                severity="critical",
                formula="12 monthly documents required",
            )
            return
        complete_counts = {
            "balance_sheet": 0,
            "income_statement": 0,
            "cash_flow": 0,
            "rent_roll": 0,
            "mortgage_statement": 0,
        }
        for _, bs, is_, cf, rr, ms in rows:
            complete_counts["balance_sheet"] += 1 if bs else 0
            complete_counts["income_statement"] += 1 if is_ else 0
            complete_counts["cash_flow"] += 1 if cf else 0
            complete_counts["rent_roll"] += 1 if rr else 0
            complete_counts["mortgage_statement"] += 1 if ms else 0
        missing = {k: expected - v for k, v in complete_counts.items() if v < expected}
        status = "PASS" if not missing else "FAIL"
        details = (
            "All required documents present" if not missing else f"Missing counts by type: {missing}"
        )
        self._add_result(
            rule_id="DQ-1",
            rule_name="Required Document Inventory",
            category="Data Quality",
            status=status,
            source_value=float(min(complete_counts.values())),
            target_value=float(expected),
            difference=float(min(complete_counts.values()) - expected),
            variance_pct=0.0,
            details=details,
            severity="critical" if status == "FAIL" else "info",
            formula="12 monthly documents per type required",
        )

    def _rule_dq_2_required_fields(self):
        checks = []
        checks.append(
            (
                "balance_sheet",
                self.db.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM balance_sheet_data
                        WHERE property_id = :property_id
                          AND period_id = :period_id
                          AND (account_name IS NULL OR account_code IS NULL OR amount IS NULL)
                        """
                    ),
                    {"property_id": int(self.property_id), "period_id": int(self.period_id)},
                ).scalar(),
            )
        )
        checks.append(
            (
                "income_statement",
                self.db.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM income_statement_data
                        WHERE property_id = :property_id
                          AND period_id = :period_id
                          AND (account_name IS NULL OR account_code IS NULL OR period_amount IS NULL)
                        """
                    ),
                    {"property_id": int(self.property_id), "period_id": int(self.period_id)},
                ).scalar(),
            )
        )
        checks.append(
            (
                "cash_flow",
                self.db.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM cash_flow_data
                        WHERE property_id = :property_id
                          AND period_id = :period_id
                          AND (account_name IS NULL OR account_code IS NULL OR period_amount IS NULL)
                        """
                    ),
                    {"property_id": int(self.property_id), "period_id": int(self.period_id)},
                ).scalar(),
            )
        )
        checks.append(
            (
                "rent_roll",
                self.db.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM rent_roll_data
                        WHERE property_id = :property_id
                          AND period_id = :period_id
                          AND (tenant_name IS NULL OR unit_number IS NULL OR monthly_rent IS NULL)
                        """
                    ),
                    {"property_id": int(self.property_id), "period_id": int(self.period_id)},
                ).scalar(),
            )
        )
        checks.append(
            (
                "mortgage_statement",
                self.db.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM mortgage_statement_data
                        WHERE property_id = :property_id
                          AND period_id = :period_id
                          AND (principal_balance IS NULL OR statement_date IS NULL)
                        """
                    ),
                    {"property_id": int(self.property_id), "period_id": int(self.period_id)},
                ).scalar(),
            )
        )
        missing = {name: int(count or 0) for name, count in checks if int(count or 0) > 0}
        status = "PASS" if not missing else "FAIL"
        self._add_result(
            rule_id="DQ-2",
            rule_name="Data Element Completeness",
            category="Data Quality",
            status=status,
            source_value=float(sum(missing.values())),
            target_value=0.0,
            difference=float(sum(missing.values())),
            variance_pct=0.0,
            details="All required fields populated" if not missing else f"Missing fields: {missing}",
            severity="high" if status == "FAIL" else "info",
            formula="Required fields must be populated",
        )

    def _rule_dq_3_temporal_continuity(self):
        year, _ = self._get_period_year_month()
        if not year:
            self._add_result(
                rule_id="DQ-3",
                rule_name="Temporal Continuity",
                category="Data Quality",
                status="INFO",
                source_value=0,
                target_value=12,
                difference=0.0,
                variance_pct=0.0,
                details="Unable to determine current year",
                severity="high",
                formula="No month gaps in sequence",
            )
            return
        months = [
            row[0]
            for row in self.db.execute(
                text(
                    """
                    SELECT DISTINCT period_month
                    FROM financial_periods
                    WHERE property_id = :property_id AND period_year = :year
                    ORDER BY period_month
                    """
                ),
                {"property_id": int(self.property_id), "year": int(year)},
            ).fetchall()
        ]
        missing = [m for m in range(1, 13) if m not in months]
        status = "PASS" if not missing else "FAIL"
        self._add_result(
            rule_id="DQ-3",
            rule_name="Temporal Continuity",
            category="Data Quality",
            status=status,
            source_value=float(len(months)),
            target_value=12.0,
            difference=float(len(months) - 12),
            variance_pct=0.0,
            details="No missing months" if not missing else f"Missing months: {missing}",
            severity="high" if status == "FAIL" else "info",
            formula="Complete month sequence Jan-Dec",
        )

    def _rule_dq_4_math_balance_sheet(self):
        total_current_assets = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total current assets%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_property_equipment = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (account_name ILIKE '%total property%' OR account_name ILIKE '%property & equipment%')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_other_assets = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total other assets%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_current_liabilities = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total current liabilities%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_assets = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total assets%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_liabilities = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total liabilities%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_equity = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (account_name ILIKE '%total capital%' OR account_name ILIKE '%total equity%')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        component_assets = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_category ILIKE '%assets%'
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        component_liabilities = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_category ILIKE '%liabil%'
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        lhs = float(total_assets)
        rhs = float(total_liabilities) + float(total_equity)
        diff = lhs - rhs
        status = "PASS" if abs(diff) <= 0.01 else "FAIL"
        self._add_result(
            rule_id="DQ-4",
            rule_name="Math Accuracy - Balance Sheet",
            category="Data Quality",
            status=status,
            source_value=float(lhs),
            target_value=float(rhs),
            difference=float(diff),
            variance_pct=0.0,
            details=f"Total Assets ${lhs:,.2f} vs Liabilities+Equity ${rhs:,.2f}",
            severity="critical" if status == "FAIL" else "info",
            formula="Total Assets = Total Liabilities + Total Capital",
        )
        component_details = (
            f"Total current assets ${total_current_assets:,.2f}, "
            f"Total property & equipment ${total_property_equipment:,.2f}, "
            f"Total other assets ${total_other_assets:,.2f}, "
            f"Component assets sum ${component_assets:,.2f}; "
            f"Total current liabilities ${total_current_liabilities:,.2f}, "
            f"Component liabilities sum ${component_liabilities:,.2f}"
        )
        self._add_result(
            rule_id="DQ-4-COMP",
            rule_name="Math Accuracy - Balance Sheet Components",
            category="Data Quality",
            status="INFO",
            source_value=float(component_assets),
            target_value=float(lhs),
            difference=float(component_assets - lhs),
            variance_pct=0.0,
            details=component_details,
            severity="info",
            formula="Component totals should reconcile to totals",
        )

    def _rule_dq_5_math_income_statement(self):
        total_income = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_expenses = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total expense%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        noi = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net operating income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        total_additional = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total additional%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        net_income = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        expected_noi = float(total_income) - float(total_expenses)
        diff = float(noi) - expected_noi
        status = "PASS" if abs(diff) <= 0.1 else "FAIL"
        self._add_result(
            rule_id="DQ-5",
            rule_name="Math Accuracy - Income Statement",
            category="Data Quality",
            status=status,
            source_value=float(noi),
            target_value=float(expected_noi),
            difference=float(diff),
            variance_pct=0.0,
            details=f"NOI ${noi:,.2f} vs Income-Expenses ${expected_noi:,.2f}",
            severity="critical" if status == "FAIL" else "info",
            formula="NOI = Total Income - Total Expenses",
        )
        total_expenses_expected = float(total_expenses) + float(total_additional)
        self._add_result(
            rule_id="DQ-5-EXP",
            rule_name="Math Accuracy - Total Expenses",
            category="Data Quality",
            status="INFO",
            source_value=float(total_expenses_expected),
            target_value=float(total_expenses_expected),
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Total operating expenses ${total_expenses:,.2f} + "
                f"additional expenses ${total_additional:,.2f} = ${total_expenses_expected:,.2f}"
            ),
            severity="info",
            formula="Total Expenses = Operating + Additional",
        )
        if net_income != 0:
            interest_dep = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(period_amount), 0)
                    FROM income_statement_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND (account_name ILIKE '%interest%' OR account_name ILIKE '%depreciation%' OR account_name ILIKE '%amort%')
                    """
                ),
                {"property_id": int(self.property_id), "period_id": int(self.period_id)},
            ).scalar() or 0.0
            expected_net_income = float(noi) - float(interest_dep)
            net_diff = float(net_income) - float(expected_net_income)
            self._add_result(
                rule_id="DQ-5-NI",
                rule_name="Math Accuracy - Net Income",
                category="Data Quality",
                status="PASS" if abs(net_diff) <= 0.1 else "FAIL",
                source_value=float(net_income),
                target_value=float(expected_net_income),
                difference=float(net_diff),
                variance_pct=0.0,
                details=f"Net income ${net_income:,.2f} vs expected ${expected_net_income:,.2f}",
                severity="critical" if abs(net_diff) > 0.1 else "info",
                formula="Net Income = NOI - Interest - Depreciation - Amortization",
            )

    def _rule_dq_6_math_cash_flow(self):
        total_adjustments = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total adjustments%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        cash_flow = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net cash%' AND (is_total IS TRUE OR is_subtotal IS TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        begin_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM cash_account_reconciliation
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%beginning%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        end_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM cash_account_reconciliation
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%ending%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        expected_end = float(begin_cash) + float(cash_flow)
        diff = float(end_cash) - expected_end
        status = "PASS" if abs(diff) <= 1.0 else "FAIL"
        self._add_result(
            rule_id="DQ-6",
            rule_name="Math Accuracy - Cash Flow",
            category="Data Quality",
            status=status,
            source_value=float(end_cash),
            target_value=float(expected_end),
            difference=float(diff),
            variance_pct=0.0,
            details=f"Ending cash ${end_cash:,.2f} vs begin+flow ${expected_end:,.2f}",
            severity="high" if status == "FAIL" else "info",
            formula="Ending Cash = Beginning Cash + Cash Flow",
        )
        net_income_cf = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        cf_expected = float(net_income_cf) + float(total_adjustments)
        cf_diff = float(cash_flow) - cf_expected
        self._add_result(
            rule_id="DQ-6-CF",
            rule_name="Math Accuracy - Cash Flow Calculation",
            category="Data Quality",
            status="PASS" if abs(cf_diff) <= 1.0 else "FAIL",
            source_value=float(cash_flow),
            target_value=float(cf_expected),
            difference=float(cf_diff),
            variance_pct=0.0,
            details=f"Cash flow ${cash_flow:,.2f} vs Net Income + Adjustments ${cf_expected:,.2f}",
            severity="high" if abs(cf_diff) > 1.0 else "info",
            formula="Cash Flow = Net Income + Total Adjustments",
        )
        self._add_result(
            rule_id="DQ-6-ADJ",
            rule_name="Math Accuracy - Total Adjustments",
            category="Data Quality",
            status="INFO",
            source_value=float(total_adjustments),
            target_value=float(total_adjustments),
            difference=0.0,
            variance_pct=0.0,
            details=f"Total adjustments reported ${total_adjustments:,.2f}",
            severity="info",
            formula="Sum of CF adjustment line items",
        )

    def _rule_dq_7_math_rent_roll(self):
        rows = self.db.execute(
            text(
                """
                SELECT monthly_rent, annual_rent, unit_area_sqft, monthly_rent_per_sqft, annual_rent_per_sqft
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (is_gross_rent_row IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="DQ-7",
                rule_name="Math Accuracy - Rent Roll",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No rent roll rows found",
                severity="high",
                formula="Validate rent roll calculations",
            )
            return
        errors = 0
        for monthly, annual, sqft, mpsf, apsf in rows:
            if monthly is not None and annual is not None:
                if abs(float(annual) - float(monthly) * 12) > 0.1:
                    errors += 1
            if monthly is not None and sqft:
                calc = float(monthly) / float(sqft) if float(sqft) else 0.0
                if mpsf is not None and abs(float(mpsf) - calc) > 0.01:
                    errors += 1
            if annual is not None and sqft:
                calc = float(annual) / float(sqft) if float(sqft) else 0.0
                if apsf is not None and abs(float(apsf) - calc) > 0.1:
                    errors += 1
        status = "PASS" if errors == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-7",
            rule_name="Math Accuracy - Rent Roll",
            category="Data Quality",
            status=status,
            source_value=float(errors),
            target_value=0.0,
            difference=float(errors),
            variance_pct=0.0,
            details=f"{errors} rent roll calculation mismatches",
            severity="high" if status == "FAIL" else "info",
            formula="Validate rent roll calculations",
        )
        summary = self.db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(unit_area_sqft), 0) AS total_sqft,
                    COALESCE(SUM(CASE WHEN occupancy_status ILIKE 'vacant' THEN 0 ELSE unit_area_sqft END), 0) AS occupied_sqft
                FROM rent_roll_data
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()
        if summary:
            total_sqft = float(summary[0] or 0.0)
            occupied_sqft = float(summary[1] or 0.0)
            occupancy = (occupied_sqft / total_sqft * 100.0) if total_sqft else 0.0
            self._add_result(
                rule_id="DQ-7-OCC",
                rule_name="Math Accuracy - Occupancy %",
                category="Data Quality",
                status="PASS" if 0 <= occupancy <= 100 else "FAIL",
                source_value=float(occupancy),
                target_value=100.0,
                difference=float(occupancy - 100.0),
                variance_pct=0.0,
                details=f"Occupancy {occupancy:.2f}% (Occupied {occupied_sqft:,.0f} / Total {total_sqft:,.0f})",
                severity="high" if occupancy < 0 or occupancy > 100 else "info",
                formula="Occupancy % = Occupied SF / Total SF",
            )

    def _rule_dq_8_math_mortgage(self):
        rows = self.db.execute(
            text(
                """
                SELECT principal_due, interest_due, tax_escrow_due, insurance_escrow_due,
                       reserve_due, total_payment_due
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="DQ-8",
                rule_name="Math Accuracy - Mortgage Statement",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No mortgage statement data found",
                severity="high",
                formula="Validate mortgage statement calculations",
            )
            return
        errors = 0
        for principal, interest, tax, insurance, reserve, total in rows:
            expected = sum(float(x or 0.0) for x in [principal, interest, tax, insurance, reserve])
            if total is not None and abs(float(total) - expected) > 0.01:
                errors += 1
            if principal is not None and interest is not None and total is not None:
                pi = float(principal or 0.0) + float(interest or 0.0)
                if abs(float(total) - pi) > 200000:
                    errors += 1
        status = "PASS" if errors == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-8",
            rule_name="Math Accuracy - Mortgage Statement",
            category="Data Quality",
            status=status,
            source_value=float(errors),
            target_value=0.0,
            difference=float(errors),
            variance_pct=0.0,
            details=f"{errors} mortgage total payment mismatches",
            severity="high" if status == "FAIL" else "info",
            formula="Total Payment = Principal + Interest + Escrows",
        )

    def _rule_dq_9_account_name_consistency(self):
        inconsistent_bs = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT account_code, COUNT(DISTINCT account_name) AS name_count
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                    GROUP BY account_code
                    HAVING COUNT(DISTINCT account_name) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id)},
        ).scalar() or 0
        inconsistent_is = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT account_code, COUNT(DISTINCT account_name) AS name_count
                    FROM income_statement_data
                    WHERE property_id = :property_id
                    GROUP BY account_code
                    HAVING COUNT(DISTINCT account_name) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id)},
        ).scalar() or 0
        inconsistent_cf = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT account_code, COUNT(DISTINCT account_name) AS name_count
                    FROM cash_flow_data
                    WHERE property_id = :property_id
                    GROUP BY account_code
                    HAVING COUNT(DISTINCT account_name) > 1
                ) sub
                """
            ),
            {"property_id": int(self.property_id)},
        ).scalar() or 0
        total_inconsistent = int(inconsistent_bs) + int(inconsistent_is) + int(inconsistent_cf)
        status = "PASS" if total_inconsistent == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-9",
            rule_name="Account Name Consistency",
            category="Data Quality",
            status=status,
            source_value=float(total_inconsistent),
            target_value=0.0,
            difference=float(total_inconsistent),
            variance_pct=0.0,
            details=(
                f"BS {inconsistent_bs}, IS {inconsistent_is}, CF {inconsistent_cf} account codes with name variants"
            ),
            severity="medium" if status == "FAIL" else "info",
            formula="Account names consistent across periods",
        )

    def _rule_dq_10_value_range_consistency(self):
        negative_cash = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%cash%'
                  AND amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        negative_revenue = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%revenue%'
                  AND period_amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        interest_rate_out = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (interest_rate < 0 OR interest_rate > 20)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        rent_roll_negative = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (unit_area_sqft < 0 OR monthly_rent < 0)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        negative_equity = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_category ILIKE '%capital%'
                  AND amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        negative_debt = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%loan%'
                  AND amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        positive_depr = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%accumulated depreciation%'
                  AND amount > 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        issues = (
            int(negative_cash)
            + int(positive_depr)
            + int(negative_revenue)
            + int(interest_rate_out)
            + int(rent_roll_negative)
            + int(negative_equity)
            + int(negative_debt)
        )
        status = "PASS" if issues == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-10",
            rule_name="Value Range Consistency",
            category="Data Quality",
            status=status,
            source_value=float(issues),
            target_value=0.0,
            difference=float(issues),
            variance_pct=0.0,
            details=(
                f"Range issues: negative cash {negative_cash}, positive depreciation {positive_depr}, "
                f"negative revenue {negative_revenue}, rate out-of-range {interest_rate_out}, "
                f"rent roll negatives {rent_roll_negative}, negative equity {negative_equity}, "
                f"negative loan balances {negative_debt}"
            ),
            severity="medium" if status == "FAIL" else "info",
            formula="Values within expected ranges",
        )

    def _rule_dq_11_format_consistency(self):
        self._add_result(
            rule_id="DQ-11",
            rule_name="Format Consistency",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Format consistency checks require raw document parsing metadata",
            severity="low",
            formula="Currency/date formatting consistency",
        )

    def _rule_dq_12_period_label_consistency(self):
        self._add_result(
            rule_id="DQ-12",
            rule_name="Period Label Consistency",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Period label checks require header metadata",
            severity="medium",
            formula="Consistent period labels across documents",
        )

    def _rule_dq_13_cross_period_integrity(self):
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not prior_id:
            self._add_result(
                rule_id="DQ-13",
                rule_name="Cross-Period Integrity",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable",
                severity="high",
                formula="Ending balance aligns with next beginning balance",
            )
            return
        cash_curr = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%cash%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        cash_prior = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :prior_id
                  AND account_name ILIKE '%cash%'
                """
            ),
            {"property_id": int(self.property_id), "prior_id": int(prior_id)},
        ).scalar() or 0.0
        diff = float(cash_curr) - float(cash_prior)
        status = "PASS" if abs(diff) <= 1.0 else "FAIL"
        self._add_result(
            rule_id="DQ-13",
            rule_name="Cross-Period Integrity",
            category="Data Quality",
            status=status,
            source_value=float(cash_curr),
            target_value=float(cash_prior),
            difference=float(diff),
            variance_pct=0.0,
            details=f"Cash change from prior period ${diff:,.2f}",
            severity="high" if status == "FAIL" else "info",
            formula="Ending balance matches next period starting balance",
        )
        # Balance sheet account continuity (appearance/disappearance)
        missing_prior = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT curr.account_code
                    FROM balance_sheet_data curr
                    LEFT JOIN balance_sheet_data prior
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND prior.period_id = :prior_id
                    WHERE curr.property_id = :property_id
                      AND curr.period_id = :period_id
                      AND prior.account_code IS NULL
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).scalar() or 0
        missing_current = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT prior.account_code
                    FROM balance_sheet_data prior
                    LEFT JOIN balance_sheet_data curr
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND curr.period_id = :period_id
                    WHERE prior.property_id = :property_id
                      AND prior.period_id = :prior_id
                      AND curr.account_code IS NULL
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).scalar() or 0
        total_missing = int(missing_prior) + int(missing_current)
        self._add_result(
            rule_id="DQ-13-BS",
            rule_name="Cross-Period Integrity - BS Account Continuity",
            category="Data Quality",
            status="PASS" if total_missing == 0 else "FAIL",
            source_value=float(total_missing),
            target_value=0.0,
            difference=float(total_missing),
            variance_pct=0.0,
            details=f"Accounts missing prior {missing_prior}, missing current {missing_current}",
            severity="high" if total_missing else "info",
            formula="Accounts should persist across adjacent periods",
        )
        # Balance sheet delta reasonability by category
        delta_rows = self.db.execute(
            text(
                """
                SELECT curr.account_code, curr.account_name, curr.account_category,
                       curr.amount, prior.amount
                FROM balance_sheet_data curr
                JOIN balance_sheet_data prior
                  ON curr.account_code = prior.account_code
                 AND curr.property_id = prior.property_id
                 AND prior.period_id = :prior_id
                WHERE curr.property_id = :property_id
                  AND curr.period_id = :period_id
                  AND (curr.is_total IS NOT TRUE)
                  AND (curr.is_subtotal IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).fetchall()
        large_moves = 0
        for _, _, category, curr_amt, prior_amt in delta_rows:
            if prior_amt in (None, 0):
                continue
            delta_pct = abs((float(curr_amt) - float(prior_amt)) / float(prior_amt))
            threshold = 0.50 if category and "ASSET" in str(category).upper() else 0.60
            if delta_pct > threshold:
                large_moves += 1
        self._add_result(
            rule_id="DQ-13-BS-DELTA",
            rule_name="Cross-Period Integrity - BS Delta Reasonability",
            category="Data Quality",
            status="PASS" if large_moves == 0 else "FAIL",
            source_value=float(large_moves),
            target_value=0.0,
            difference=float(large_moves),
            variance_pct=0.0,
            details=f"Large balance sheet moves: {large_moves}",
            severity="medium" if large_moves else "info",
            formula="Large MoM changes flagged by category threshold",
        )
        # Category-level continuity check
        category_rows = self.db.execute(
            text(
                """
                SELECT curr.account_category,
                       SUM(curr.amount) AS curr_total,
                       SUM(prior.amount) AS prior_total
                FROM balance_sheet_data curr
                JOIN balance_sheet_data prior
                  ON curr.account_code = prior.account_code
                 AND curr.property_id = prior.property_id
                 AND prior.period_id = :prior_id
                WHERE curr.property_id = :property_id
                  AND curr.period_id = :period_id
                  AND (curr.is_total IS NOT TRUE)
                  AND (curr.is_subtotal IS NOT TRUE)
                GROUP BY curr.account_category
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).fetchall()
        category_flags = []
        for category, curr_total, prior_total in category_rows:
            if prior_total in (None, 0):
                continue
            delta_pct = abs((float(curr_total) - float(prior_total)) / float(prior_total))
            threshold = 0.40
            if category and "ASSET" in str(category).upper():
                threshold = 0.35
            if category and "LIABIL" in str(category).upper():
                threshold = 0.45
            if category and "CAPITAL" in str(category).upper():
                threshold = 0.50
            if delta_pct > threshold:
                category_flags.append(f"{category} {delta_pct:.1%}")
        self._add_result(
            rule_id="DQ-13-BS-CAT",
            rule_name="Cross-Period Integrity - Category Continuity",
            category="Data Quality",
            status="PASS" if not category_flags else "FAIL",
            source_value=float(len(category_flags)),
            target_value=0.0,
            difference=float(len(category_flags)),
            variance_pct=0.0,
            details="; ".join(category_flags) if category_flags else "Category totals within thresholds",
            severity="medium" if category_flags else "info",
            formula="Category totals should not swing excessively",
        )
        # Key account continuity checks
        key_patterns = [
            ("%cash%", 0.30),
            ("%a/r%tenant%", 0.40),
            ("%escrow%", 0.50),
            ("%prepaid%", 0.50),
        ]
        key_flags = []
        for pattern, threshold in key_patterns:
            row = self.db.execute(
                text(
                    """
                    SELECT curr.amount, prior.amount
                    FROM balance_sheet_data curr
                    JOIN balance_sheet_data prior
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND prior.period_id = :prior_id
                    WHERE curr.property_id = :property_id
                      AND curr.period_id = :period_id
                      AND curr.account_name ILIKE :pattern
                    LIMIT 1
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "prior_id": int(prior_id),
                    "pattern": pattern,
                },
            ).fetchone()
            if not row or row[1] in (None, 0):
                continue
            delta_pct = abs((float(row[0]) - float(row[1])) / float(row[1]))
            if delta_pct > threshold:
                key_flags.append(f"{pattern} {delta_pct:.1%}")
        self._add_result(
            rule_id="DQ-13-BS-KEY",
            rule_name="Cross-Period Integrity - Key Account Continuity",
            category="Data Quality",
            status="PASS" if not key_flags else "FAIL",
            source_value=float(len(key_flags)),
            target_value=0.0,
            difference=float(len(key_flags)),
            variance_pct=0.0,
            details="; ".join(key_flags) if key_flags else "Key accounts within thresholds",
            severity="medium" if key_flags else "info",
            formula="Key accounts should not swing excessively",
        )
        ytd_decreases = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT curr.account_code, curr.ytd_amount, prior.ytd_amount AS prior_ytd
                    FROM income_statement_data curr
                    JOIN income_statement_data prior
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND prior.period_id = :prior_id
                    WHERE curr.property_id = :property_id
                      AND curr.period_id = :period_id
                      AND curr.ytd_amount < prior.ytd_amount
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).scalar() or 0
        ytd_decreases_cf = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT curr.account_code, curr.ytd_amount, prior.ytd_amount AS prior_ytd
                    FROM cash_flow_data curr
                    JOIN cash_flow_data prior
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND prior.period_id = :prior_id
                    WHERE curr.property_id = :property_id
                      AND curr.period_id = :period_id
                      AND curr.ytd_amount < prior.ytd_amount
                ) sub
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "prior_id": int(prior_id)},
        ).scalar() or 0
        total_decreases = int(ytd_decreases) + int(ytd_decreases_cf)
        self._add_result(
            rule_id="DQ-13-YTD",
            rule_name="Cross-Period Integrity - YTD Monotonicity",
            category="Data Quality",
            status="PASS" if total_decreases == 0 else "FAIL",
            source_value=float(total_decreases),
            target_value=0.0,
            difference=float(total_decreases),
            variance_pct=0.0,
            details=f"YTD decreases: IS {ytd_decreases}, CF {ytd_decreases_cf}",
            severity="high" if total_decreases else "info",
            formula="YTD values should not decrease",
        )

    def _rule_dq_14_reference_data_integrity(self):
        rows = self.db.execute(
            text(
                """
                SELECT period_id, amount
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND account_name ILIKE '%land%'
                ORDER BY period_id
                """
            ),
            {"property_id": int(self.property_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="DQ-14",
                rule_name="Reference Data Integrity",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No reference account data found",
                severity="high",
                formula="Constant reference data should not change",
            )
            return
        values = [float(r[1] or 0.0) for r in rows]
        min_val, max_val = min(values), max(values)
        status = "PASS" if abs(max_val - min_val) <= 0.01 else "FAIL"
        self._add_result(
            rule_id="DQ-14",
            rule_name="Reference Data Integrity",
            category="Data Quality",
            status=status,
            source_value=float(max_val),
            target_value=float(min_val),
            difference=float(max_val - min_val),
            variance_pct=0.0,
            details=f"Land value range ${min_val:,.2f} - ${max_val:,.2f}",
            severity="high" if status == "FAIL" else "info",
            formula="Reference data should be constant",
        )
        # Additional reference constants (best-effort)
        constant_patterns = [
            "%LAND%",
            "%BUILDING%",
            "%LOAN COST%",
            "%PARTNERS CONTRIBUTION%",
            "%BEGINNING EQUITY%",
        ]
        constant_results = []
        for pattern in constant_patterns:
            data = self.db.execute(
                text(
                    """
                    SELECT MIN(amount), MAX(amount)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {"property_id": int(self.property_id), "pattern": pattern},
            ).fetchone()
            if not data or data[0] is None or data[1] is None:
                continue
            min_val, max_val = float(data[0]), float(data[1])
            constant_results.append((pattern.strip("%"), min_val, max_val, max_val - min_val))
        # Mortgage constants (interest rate, total payment)
        mortgage_data = self.db.execute(
            text(
                """
                SELECT MIN(interest_rate), MAX(interest_rate), MIN(total_payment_due), MAX(total_payment_due)
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                """
            ),
            {"property_id": int(self.property_id)},
        ).fetchone()
        if mortgage_data and any(mortgage_data):
            ir_min, ir_max, pay_min, pay_max = mortgage_data
            if ir_min is not None and ir_max is not None:
                constant_results.append(("Interest Rate", float(ir_min), float(ir_max), float(ir_max) - float(ir_min)))
            if pay_min is not None and pay_max is not None:
                constant_results.append(("Total Payment Due", float(pay_min), float(pay_max), float(pay_max) - float(pay_min)))

        if constant_results:
            breaches = [item for item in constant_results if abs(item[3]) > 0.01]
            details = "; ".join(
                f"{name}: ${min_val:,.2f} - ${max_val:,.2f}"
                if "Rate" not in name
                else f"{name}: {min_val:.4f} - {max_val:.4f}"
                for name, min_val, max_val, _ in constant_results
            )
            self._add_result(
                rule_id="DQ-14-REF",
                rule_name="Reference Data Integrity - Constants",
                category="Data Quality",
                status="FAIL" if breaches else "PASS",
                source_value=float(len(breaches)),
                target_value=0.0,
                difference=float(len(breaches)),
                variance_pct=0.0,
                details=details,
                severity="high" if breaches else "info",
                formula="Reference constants should not vary across periods",
            )

    def _rule_dq_15_referential_integrity(self):
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
        missing_codes = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND occupancy_status ILIKE 'occupied'
                  AND (tenant_code IS NULL OR tenant_code = '')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        zero_rent = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND occupancy_status ILIKE 'occupied'
                  AND COALESCE(monthly_rent, 0) = 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        rr_monthly = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(monthly_rent), 0)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                  AND (is_gross_rent_row IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        rr_vs_is_ok = True
        rr_vs_is_diff_pct = 0.0
        if rr_monthly and base_rent:
            rr_vs_is_diff_pct = abs(float(base_rent) - float(rr_monthly)) / float(rr_monthly)
            rr_vs_is_ok = rr_vs_is_diff_pct <= 0.20
        status = "PASS" if (occupied == 0 or base_rent != 0) and missing_codes == 0 and zero_rent == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-15",
            rule_name="Referential Integrity Between Documents",
            category="Data Quality",
            status=status,
            source_value=float(base_rent),
            target_value=1.0,
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Occupied tenants: {occupied}, Base rent ${base_rent:,.2f}, "
                f"Missing tenant codes: {missing_codes}, Zero-rent occupied: {zero_rent}"
            ),
            severity="medium" if status == "FAIL" else "info",
            formula="Rent roll tenants should appear in IS revenue",
        )
        if rr_monthly and base_rent:
            self._add_result(
                rule_id="DQ-15-RR",
                rule_name="Referential Integrity - RR vs Base Rent",
                category="Data Quality",
                status="PASS" if rr_vs_is_ok else "FAIL",
                source_value=float(base_rent),
                target_value=float(rr_monthly),
                difference=float(base_rent - rr_monthly),
                variance_pct=float(rr_vs_is_diff_pct),
                details=(
                    f"Base rent ${base_rent:,.2f} vs RR monthly ${rr_monthly:,.2f} "
                    f"(diff {rr_vs_is_diff_pct:.1%})"
                ),
                severity="medium" if not rr_vs_is_ok else "info",
                formula="Base rent should align with occupied rent roll totals",
            )

    def _rule_dq_16_timeliness(self):
        period_end = self._get_period_end_date()
        if not period_end:
            self._add_result(
                rule_id="DQ-16",
                rule_name="Statement Production Timeline",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Unable to determine period end date",
                severity="medium",
                formula="Statements delivered within 15 days",
            )
            return
        deadline = period_end + timedelta(days=15)
        late_docs = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM document_uploads
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND upload_date > :deadline
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(self.period_id),
                "deadline": deadline,
            },
        ).scalar()
        # If upload_date is missing, this will still return 0.
        self._add_result(
            rule_id="DQ-16",
            rule_name="Statement Production Timeline",
            category="Data Quality",
            status="INFO",
            source_value=float(late_docs or 0),
            target_value=0.0,
            difference=float(late_docs or 0),
            variance_pct=0.0,
            details="Timeliness requires upload_date vs period-end comparison",
            severity="medium",
            formula="Statements delivered within expected days",
        )

    def _rule_dq_17_currency(self):
        self._add_result(
            rule_id="DQ-17",
            rule_name="Data Currency",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Currency checks require ingestion timestamps per document",
            severity="medium",
            formula="Data should be current and up-to-date",
        )

    def _rule_dq_18_precision(self):
        excessive_precision = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND amount::text LIKE '%.%'
                  AND LENGTH(split_part(amount::text, '.', 2)) > 2
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        excessive_is = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND period_amount::text LIKE '%.%'
                  AND LENGTH(split_part(period_amount::text, '.', 2)) > 2
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        excessive_cf = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND period_amount::text LIKE '%.%'
                  AND LENGTH(split_part(period_amount::text, '.', 2)) > 2
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        excessive_rr = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (
                    (monthly_rent::text LIKE '%.%' AND LENGTH(split_part(monthly_rent::text, '.', 2)) > 2) OR
                    (annual_rent::text LIKE '%.%' AND LENGTH(split_part(annual_rent::text, '.', 2)) > 2)
                  )
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        total_excess = int(excessive_precision) + int(excessive_is) + int(excessive_cf) + int(excessive_rr)
        status = "PASS" if total_excess == 0 else "FAIL"
        self._add_result(
            rule_id="DQ-18",
            rule_name="Appropriate Precision",
            category="Data Quality",
            status=status,
            source_value=float(total_excess),
            target_value=0.0,
            difference=float(total_excess),
            variance_pct=0.0,
            details=(
                f"Rows with >2 decimals: BS {excessive_precision}, IS {excessive_is}, "
                f"CF {excessive_cf}, RR {excessive_rr}"
            ),
            severity="low" if status == "FAIL" else "info",
            formula="Monetary values should use 2 decimals",
        )

    def _rule_dq_19_rounding(self):
        self._add_result(
            rule_id="DQ-19",
            rule_name="Rounding Consistency",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Rounding consistency requires source vs calculated comparisons",
            severity="low",
            formula="Consistent rounding practices",
        )

    def _rule_dq_20_sign_convention(self):
        negative_revenue = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%revenue%'
                  AND period_amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        negative_expenses = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%expense%'
                  AND period_amount < 0
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        self._add_result(
            rule_id="DQ-20",
            rule_name="Sign Convention Consistency",
            category="Data Quality",
            status="FAIL" if negative_revenue or negative_expenses else "PASS",
            source_value=float(negative_revenue + negative_expenses),
            target_value=0.0,
            difference=float(negative_revenue + negative_expenses),
            variance_pct=0.0,
            details=f"Negative revenue rows: {negative_revenue}, negative expense rows: {negative_expenses}",
            severity="medium" if (negative_revenue or negative_expenses) else "info",
            formula="Sign conventions consistent across statements",
        )

    def _rule_dq_21_unusual_values(self):
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not prior_id:
            self._add_result(
                rule_id="DQ-21",
                rule_name="Unusual Value Detection",
                category="Data Quality",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable for change detection",
                severity="medium",
                formula="Flag large MoM changes",
            )
            return
        curr_rev = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior_rev = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        curr_exp = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total expense%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior_exp = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%total expense%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        curr_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%cash%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%cash%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        curr_ar = self.db.execute(
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
        prior_ar = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%a/r%' AND account_name ILIKE '%tenant%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        changes = {
            "revenue": ((float(curr_rev) - float(prior_rev)) / float(prior_rev)) if prior_rev else 0.0,
            "expenses": ((float(curr_exp) - float(prior_exp)) / float(prior_exp)) if prior_exp else 0.0,
            "cash": ((float(curr_cash) - float(prior_cash)) / float(prior_cash)) if prior_cash else 0.0,
            "ar": ((float(curr_ar) - float(prior_ar)) / float(prior_ar)) if prior_ar else 0.0,
        }
        curr_noi = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net operating income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior_noi = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net operating income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        curr_net_income = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        prior_net_income = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%net income%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        changes["noi"] = ((float(curr_noi) - float(prior_noi)) / float(prior_noi)) if prior_noi else 0.0
        changes["net_income"] = (
            (float(curr_net_income) - float(prior_net_income)) / float(prior_net_income)
        ) if prior_net_income else 0.0
        flagged = (
            (prior_rev and abs(changes["revenue"]) > 0.15)
            or (prior_exp and abs(changes["expenses"]) > 0.25)
            or (prior_cash and abs(changes["cash"]) > 0.30)
            or (prior_ar and abs(changes["ar"]) > 0.40)
            or (prior_noi and abs(changes["noi"]) > 0.25)
            or (prior_net_income and abs(changes["net_income"]) > 0.40)
        )
        status = "FAIL" if flagged else "PASS"
        self._add_result(
            rule_id="DQ-21",
            rule_name="Unusual Value Detection",
            category="Data Quality",
            status=status,
            source_value=float(changes["revenue"]),
            target_value=0.15,
            difference=float(changes["revenue"] - 0.15),
            variance_pct=0.0,
            details=(
                f"Revenue {changes['revenue']:.1%}, Expenses {changes['expenses']:.1%}, "
                f"Cash {changes['cash']:.1%}, A/R {changes['ar']:.1%}, "
                f"NOI {changes['noi']:.1%}, Net Income {changes['net_income']:.1%}"
            ),
            severity="medium" if status == "FAIL" else "info",
            formula="Flag MoM change > 15%",
        )

    def _rule_dq_22_authenticity(self):
        self._add_result(
            rule_id="DQ-22",
            rule_name="Source Document Authenticity",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Authenticity verification not available in DB",
            severity="high",
            formula="Verify source documents",
        )

    def _rule_dq_23_version_control(self):
        versions = self.db.execute(
            text(
                """
                SELECT document_type, COUNT(*)
                FROM document_uploads
                WHERE property_id = :property_id
                  AND period_id = :period_id
                GROUP BY document_type
                HAVING COUNT(*) > 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        self._add_result(
            rule_id="DQ-23",
            rule_name="Version Control",
            category="Data Quality",
            status="PASS" if not versions else "INFO",
            source_value=float(len(versions)),
            target_value=0.0,
            difference=float(len(versions)),
            variance_pct=0.0,
            details="Multiple versions detected" if versions else "Single version per document",
            severity="medium",
            formula="Versioning tracked in document uploads",
        )

    def _rule_dq_24_extraction_accuracy(self):
        low_conf = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND extraction_confidence IS NOT NULL
                  AND extraction_confidence < 90
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        low_conf_is = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND extraction_confidence IS NOT NULL
                  AND extraction_confidence < 90
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        low_conf_cf = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND extraction_confidence IS NOT NULL
                  AND extraction_confidence < 90
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        low_conf_rr = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND extraction_confidence IS NOT NULL
                  AND extraction_confidence < 90
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0
        total_low = int(low_conf) + int(low_conf_is) + int(low_conf_cf) + int(low_conf_rr)
        status = "PASS" if total_low == 0 else "INFO"
        self._add_result(
            rule_id="DQ-24",
            rule_name="Extraction Accuracy",
            category="Data Quality",
            status=status,
            source_value=float(total_low),
            target_value=0.0,
            difference=float(total_low),
            variance_pct=0.0,
            details=(
                f"Low extraction confidence rows: BS {low_conf}, IS {low_conf_is}, "
                f"CF {low_conf_cf}, RR {low_conf_rr}"
            ),
            severity="high" if total_low else "info",
            formula="Extraction accuracy >= 99.9%",
        )

    def _rule_dq_25_calculation_accuracy(self):
        self._add_result(
            rule_id="DQ-25",
            rule_name="Calculation Accuracy",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Calculation accuracy enforced via DQ-4 to DQ-8",
            severity="high",
            formula="Derived values must be correct",
        )

    def _rule_dq_26_scorecard(self):
        self._add_result(
            rule_id="DQ-26",
            rule_name="Data Quality Scorecard",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Scorecard requires aggregation of DQ results over time",
            severity="medium",
            formula="Composite data quality score",
        )

    def _rule_dq_27_trend_analysis(self):
        self._add_result(
            rule_id="DQ-27",
            rule_name="Data Quality Trend Analysis",
            category="Data Quality",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="DQ trend analysis requires historical DQ results",
            severity="medium",
            formula="Track data quality trends",
        )

    def _rule_dq_28_data_ownership(self):
        owners = self._safe_count("SELECT COUNT(*) FROM data_owners")
        policies = self._safe_count(
            "SELECT COUNT(*) FROM data_governance_policies WHERE policy_type ILIKE 'ownership'"
        )
        status = "PASS" if owners and policies else "INFO"
        self._add_result(
            rule_id="DQ-28",
            rule_name="Data Ownership and Stewardship",
            category="Data Quality",
            status=status,
            source_value=float(owners),
            target_value=1.0,
            difference=float(owners - 1),
            variance_pct=0.0,
            details=f"Owners: {owners}, ownership policies: {policies}",
            severity="medium" if status == "INFO" else "info",
            formula="Ownership and stewardship defined",
        )

    def _rule_dq_29_access_controls(self):
        controls = self._safe_count("SELECT COUNT(*) FROM data_access_controls")
        status = "PASS" if controls else "INFO"
        self._add_result(
            rule_id="DQ-29",
            rule_name="Data Access Controls",
            category="Data Quality",
            status=status,
            source_value=float(controls),
            target_value=1.0,
            difference=float(controls - 1),
            variance_pct=0.0,
            details=f"Access control rules: {controls}",
            severity="high" if status == "INFO" else "info",
            formula="Appropriate access controls",
        )

    def _rule_dq_30_retention_policy(self):
        policies = self._safe_count("SELECT COUNT(*) FROM data_retention_policies")
        status = "PASS" if policies else "INFO"
        self._add_result(
            rule_id="DQ-30",
            rule_name="Data Retention and Archival",
            category="Data Quality",
            status=status,
            source_value=float(policies),
            target_value=1.0,
            difference=float(policies - 1),
            variance_pct=0.0,
            details=f"Retention policies: {policies}",
            severity="high" if status == "INFO" else "info",
            formula="Retention and archival compliance",
        )

    def _rule_dq_31_error_classification(self):
        issues = self._safe_count("SELECT COUNT(*) FROM data_quality_issues")
        status = "PASS" if issues else "INFO"
        self._add_result(
            rule_id="DQ-31",
            rule_name="Error Classification",
            category="Data Quality",
            status=status,
            source_value=float(issues),
            target_value=0.0,
            difference=float(issues),
            variance_pct=0.0,
            details=f"DQ issues logged: {issues}",
            severity="medium" if status == "INFO" else "info",
            formula="Classify errors by type",
        )

    def _rule_dq_32_error_correction_process(self):
        corrections = self._safe_count("SELECT COUNT(*) FROM data_quality_corrections")
        status = "PASS" if corrections else "INFO"
        self._add_result(
            rule_id="DQ-32",
            rule_name="Error Correction Process",
            category="Data Quality",
            status=status,
            source_value=float(corrections),
            target_value=0.0,
            difference=float(corrections),
            variance_pct=0.0,
            details=f"Corrections logged: {corrections}",
            severity="high" if status == "INFO" else "info",
            formula="Standardized correction process",
        )

    def _rule_dq_33_preventive_controls(self):
        policies = self._safe_count(
            "SELECT COUNT(*) FROM data_governance_policies WHERE policy_type ILIKE 'preventive'"
        )
        status = "PASS" if policies else "INFO"
        self._add_result(
            rule_id="DQ-33",
            rule_name="Preventive Controls",
            category="Data Quality",
            status=status,
            source_value=float(policies),
            target_value=1.0,
            difference=float(policies - 1),
            variance_pct=0.0,
            details=f"Preventive control policies: {policies}",
            severity="medium" if status == "INFO" else "info",
            formula="Input/processing/output controls",
        )
