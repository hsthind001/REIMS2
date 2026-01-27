from sqlalchemy import text

from app.services.reconciliation_types import ReconciliationResult


class AuditRulesMixin:
    """
    Cross-document audit checklist rules (CROSS_DOCUMENT_AUDIT_RULES.md).

    This mixin focuses on the critical foundation rules that benefit most
    from the new period-alignment layer.
    """

    def _execute_audit_rules(self):
        """Execute cross-document audit checklist rules."""
        self._rule_audit_1_balance_sheet_equation()
        self._rule_audit_2_cash_reconciliation()
        self._rule_audit_3_net_income_three_way()
        self._rule_audit_4_mortgage_principal_balance()
        self._rule_audit_5_escrow_three_way()
        self._rule_audit_6_mortgage_interest_flow()
        self._rule_audit_7_mortgage_payment_composition()
        self._rule_audit_8_rent_roll_to_base_rentals()
        self._rule_audit_9_rent_roll_change_to_is_change()
        self._rule_audit_10_occupancy_impact_on_revenue()
        self._rule_audit_11_tenant_count_vs_ar()
        self._rule_audit_12_ar_three_way_collections()
        self._rule_audit_13_property_tax_flow()
        self._rule_audit_14_prepaid_insurance_cycle()
        self._rule_audit_15_depreciation_perfect_circle()
        self._rule_audit_16_amortization_perfect_circle()
        self._rule_audit_17_depreciation_cessation_consistency()
        self._rule_audit_18_capex_flow()
        self._rule_audit_19_escrow_funded_capex()
        self._rule_audit_20_fixed_asset_additions()
        self._rule_audit_21_principal_payment_flow()
        self._rule_audit_22_ytd_principal_reduction()
        self._rule_audit_24_cash_flow_cash_bridge()
        self._rule_audit_26_operating_activities_reconciliation()
        self._rule_audit_27_period_contiguity()
        self._rule_audit_28_constant_accounts_validation()
        self._rule_audit_29_predictable_monthly_changes()
        self._rule_audit_33_occupancy_percentage()
        self._rule_audit_40_completeness_validation()
        self._rule_audit_41_timing_difference_signals()
        self._rule_audit_42_period_cutoff_consistency()
        self._rule_audit_44_ltv_ratio()
        self._rule_audit_37_negative_balance_validation()
        self._rule_audit_43_dscr()
        self._rule_audit_45_minimum_liquidity()
        self._rule_audit_46_escrow_funding_requirements()
        self._rule_audit_38_magnitude_reasonability_checks()
        self._rule_audit_39_related_account_validations()
        self._rule_audit_48_variance_investigation_triggers()

    def _sum_bs_accounts(self, patterns, period_id):
        """Sum balance-sheet accounts matching name patterns."""
        total = 0.0
        for pattern in patterns:
            amount = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                      AND (is_total IS NOT TRUE)
                      AND (is_subtotal IS NOT TRUE)
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(period_id),
                    "pattern": pattern,
                },
            ).scalar()
            total += float(amount or 0.0)
        return total

    def _sum_cf_accounts(self, patterns):
        """Sum cash-flow accounts matching name patterns."""
        total = 0.0
        for pattern in patterns:
            amount = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(period_amount), 0)
                    FROM cash_flow_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                      AND (is_total IS NOT TRUE)
                      AND (is_subtotal IS NOT TRUE)
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "pattern": pattern,
                },
            ).scalar()
            total += float(amount or 0.0)
        return total

    def _get_year_start_period_id(self, year: int):
        """Return the earliest period_id available for a given year."""
        row = self.db.execute(
            text(
                """
                SELECT id
                FROM financial_periods
                WHERE property_id = :property_id
                  AND period_year = :year
                ORDER BY period_month ASC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "year": int(year)},
        ).fetchone()
        return int(row[0]) if row and row[0] else None

    def _get_earliest_period_id(self):
        """Return the earliest period_id available for the property."""
        row = self.db.execute(
            text(
                """
                SELECT id
                FROM financial_periods
                WHERE property_id = :property_id
                ORDER BY period_year ASC, period_month ASC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id)},
        ).fetchone()
        return int(row[0]) if row and row[0] else None

    def _get_financial_metric(self, column_name: str, period_id=None) -> float:
        """Safely fetch a value from financial_metrics for the given period."""
        pid = int(period_id) if period_id is not None else int(self.period_id)

        if hasattr(self, "_safe_get_value"):
            return float(
                self._safe_get_value(
                    "financial_metrics",
                    column_name,
                    {"p_id": int(self.property_id), "period_id": pid},
                )
                or 0.0
            )

        row = self.db.execute(
            text(
                f"""
                SELECT {column_name}
                FROM financial_metrics
                WHERE property_id = :p_id AND period_id = :period_id
                LIMIT 1
                """
            ),
            {"p_id": int(self.property_id), "period_id": pid},
        ).fetchone()
        return float(row[0] or 0.0) if row else 0.0

    def _get_is_value_for_period(self, account_name_pattern: str, period_id: int) -> float:
        """Fetch a single income-statement value for a specific period."""
        row = self.db.execute(
            text(
                """
                SELECT period_amount
                FROM income_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE :pattern
                ORDER BY ABS(period_amount) DESC
                LIMIT 1
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(period_id),
                "pattern": account_name_pattern,
            },
        ).fetchone()
        return float(row[0] or 0.0) if row else 0.0

    def _sum_is_accounts(self, patterns, period_id=None) -> float:
        """Sum income-statement accounts matching name patterns."""
        pid = int(period_id) if period_id is not None else int(self.period_id)

        total = 0.0
        for pattern in patterns:
            amount = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(period_amount), 0)
                    FROM income_statement_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                      AND (is_total IS NOT TRUE)
                      AND (is_subtotal IS NOT TRUE)
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": pid,
                    "pattern": pattern,
                },
            ).scalar()
            total += float(amount or 0.0)
        return total

    def _get_rent_roll_summary(self, period_id=None):
        """Return rent roll summary stats for a period."""
        pid = int(period_id) if period_id is not None else int(self.period_id)

        row = self.db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(unit_area_sqft), 0) AS total_sqft,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN occupancy_status ILIKE 'vacant' THEN 0
                                ELSE unit_area_sqft
                            END
                        ),
                        0
                    ) AS occupied_sqft,
                    COALESCE(SUM(monthly_rent), 0) AS total_monthly_rent,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN occupancy_status ILIKE 'vacant' THEN 0
                                ELSE monthly_rent
                            END
                        ),
                        0
                    ) AS occupied_monthly_rent,
                    COUNT(*) AS tenant_count,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN occupancy_status ILIKE 'vacant' THEN 0
                                ELSE 1
                            END
                        ),
                        0
                    ) AS occupied_tenant_count
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (is_gross_rent_row IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": pid},
        ).fetchone()

        if not row:
            return {
                "total_sqft": 0.0,
                "occupied_sqft": 0.0,
                "total_monthly_rent": 0.0,
                "occupied_monthly_rent": 0.0,
                "tenant_count": 0,
                "occupied_tenant_count": 0,
                "occupancy_pct": 0.0,
            }

        total_sqft = float(row[0] or 0.0)
        occupied_sqft = float(row[1] or 0.0)
        total_monthly_rent = float(row[2] or 0.0)
        occupied_monthly_rent = float(row[3] or 0.0)
        tenant_count = int(row[4] or 0)
        occupied_tenant_count = int(row[5] or 0)
        occupancy_pct = (occupied_sqft / total_sqft) * 100.0 if total_sqft else 0.0

        return {
            "total_sqft": total_sqft,
            "occupied_sqft": occupied_sqft,
            "total_monthly_rent": total_monthly_rent,
            "occupied_monthly_rent": occupied_monthly_rent,
            "tenant_count": tenant_count,
            "occupied_tenant_count": occupied_tenant_count,
            "occupancy_pct": occupancy_pct,
        }

    def _get_report_period_end(self, header_table: str, period_id=None):
        """Fetch report_period_end from a header table (IS or CF)."""
        pid = int(period_id) if period_id is not None else int(self.period_id)

        row = self.db.execute(
            text(
                f"""
                SELECT report_period_end
                FROM {header_table}
                WHERE property_id = :property_id
                  AND period_id = :period_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": pid},
        ).fetchone()

        return row[0] if row and row[0] else None

    def _sum_cf_operating_total(self, period_id=None):
        """
        Sum operating cash flow lines, excluding cash table and net-change lines.

        Falls back to a broad non-cash-line sum if cash_flow_category is not set.
        """
        pid = int(period_id) if period_id is not None else int(self.period_id)

        exclusions = {
            "ex1": "%BEGINNING%CASH%",
            "ex2": "%ENDING%CASH%",
            "ex3": "%NET CHANGE%CASH%",
            "ex4": "%CASH FLOW%",
            "ex5": "%TOTAL CASH%",
        }

        op_total = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND cash_flow_category ILIKE 'operating'
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                  AND account_name NOT ILIKE :ex1
                  AND account_name NOT ILIKE :ex2
                  AND account_name NOT ILIKE :ex3
                  AND account_name NOT ILIKE :ex4
                  AND account_name NOT ILIKE :ex5
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": pid,
                **exclusions,
            },
        ).scalar()
        op_total = float(op_total or 0.0)

        if abs(op_total) > 0.01:
            return op_total, "operating_category"

        fallback_total = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                  AND account_name NOT ILIKE :ex1
                  AND account_name NOT ILIKE :ex2
                  AND account_name NOT ILIKE :ex3
                  AND account_name NOT ILIKE :ex4
                  AND account_name NOT ILIKE :ex5
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": pid,
                **exclusions,
            },
        ).scalar()
        return float(fallback_total or 0.0), "fallback_non_cash_lines"

    def _find_negative_bs_accounts(self, patterns, exclusions=None, limit=5):
        """Return (count, examples) of negative BS accounts matching patterns."""
        exclusions = exclusions or []
        total_count = 0
        examples = []

        for pattern in patterns:
            where_exclusions = "".join(
                [f" AND account_name NOT ILIKE :ex{i}" for i, _ in enumerate(exclusions)]
            )
            params = {
                "property_id": int(self.property_id),
                "period_id": int(self.period_id),
                "pattern": pattern,
            }
            for i, ex in enumerate(exclusions):
                params[f"ex{i}"] = ex

            rows = self.db.execute(
                text(
                    f"""
                    SELECT account_name, amount
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                      AND amount < -1.0
                      AND (is_total IS NOT TRUE)
                      AND (is_subtotal IS NOT TRUE)
                      {where_exclusions}
                    ORDER BY amount ASC
                    LIMIT :limit
                    """
                ),
                {**params, "limit": int(limit)},
            ).fetchall()

            total_count += len(rows)
            for row in rows:
                if len(examples) >= limit:
                    break
                examples.append({"account_name": row[0], "amount": float(row[1] or 0.0)})

        return total_count, examples

    # ------------------------------------------------------------------
    # AUDIT-1..AUDIT-5 critical rules
    # ------------------------------------------------------------------

    def _rule_audit_1_balance_sheet_equation(self):
        """AUDIT-1: Balance sheet equation integrity."""
        assets = self._get_bs_value(account_name_pattern="TOTAL ASSETS")
        liab_cap = self._get_bs_value(account_name_pattern="TOTAL LIABILITIES & CAPITAL")

        if liab_cap == 0:
            total_liabilities = self._get_bs_value(account_name_pattern="Total Liabilities")
            total_capital = self._get_bs_value(account_name_pattern="Total Capital")
            liab_cap = total_liabilities + total_capital

        diff = assets - liab_cap
        tolerance = 1.00
        status = "PASS" if abs(diff) <= tolerance else "FAIL"

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-1",
                rule_name="Balance Sheet Equation",
                category="Audit",
                status=status,
                source_value=assets,
                target_value=liab_cap,
                difference=diff,
                variance_pct=0,
                details=f"Assets ${assets:,.2f} vs Liabilities+Capital ${liab_cap:,.2f}",
                severity="critical",
                formula="Total Assets = Total Liabilities & Capital",
            )
        )

    def _rule_audit_2_cash_reconciliation(self):
        """AUDIT-2: Cash reconciliation across statements."""
        ctx = self._get_alignment_context()

        bs_cash_end = self._get_bs_total_cash(self.period_id)
        cf_cash_end = ctx.cf_ending_cash
        if abs(cf_cash_end) <= 0.01:
            cf_cash_end = self._get_cf_value(account_name_pattern="%ENDING%CASH%")

        diff = bs_cash_end - cf_cash_end
        tolerance = 1.00
        status = "PASS" if abs(diff) <= tolerance else "FAIL"

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-2",
                rule_name="Cash Reconciliation (BS vs CF)",
                category="Audit",
                status=status,
                source_value=bs_cash_end,
                target_value=cf_cash_end,
                difference=diff,
                variance_pct=0,
                details=(
                    f"BS cash ${bs_cash_end:,.2f} vs CF ending cash ${cf_cash_end:,.2f} "
                    f"(method={ctx.alignment_method})"
                ),
                severity="critical",
                formula="BS Cash = CF Ending Cash",
                intermediate_calculations={"alignment": ctx.to_dict()},
            )
        )

    def _rule_audit_3_net_income_three_way(self):
        """AUDIT-3: Net income three-way tie (IS ↔ BS ↔ CF)."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            self.results.append(
                ReconciliationResult(
                    rule_id="AUDIT-3",
                    rule_name="Net Income Three-Way Tie",
                    category="Audit",
                    status="SKIP",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details="No aligned begin period available for net income tie",
                    severity="critical",
                )
            )
            return

        ctx = self._get_alignment_context()

        is_net_income = self._get_is_value(account_name_pattern="%NET INCOME%")
        cf_net_income = self._get_cf_value(account_name_pattern="%NET%INCOME%")

        bs_curr = self._get_bs_value(account_name_pattern="%CURRENT PERIOD EARNINGS%")
        bs_begin = self._get_bs_value(
            account_name_pattern="%CURRENT PERIOD EARNINGS%", period_id=begin_period_id
        )
        if bs_curr == 0 and bs_begin == 0:
            bs_curr = self._get_bs_value(account_name_pattern="%RETAINED EARNINGS%")
            bs_begin = self._get_bs_value(
                account_name_pattern="%RETAINED EARNINGS%", period_id=begin_period_id
            )

        bs_change = bs_curr - bs_begin

        diff_is_bs = is_net_income - bs_change
        diff_is_cf = is_net_income - cf_net_income
        tolerance = 1.00

        is_bs_ok = abs(diff_is_bs) <= tolerance
        is_cf_ok = abs(diff_is_cf) <= tolerance or abs(cf_net_income) <= 0.01
        status = "PASS" if is_bs_ok and is_cf_ok else "FAIL"

        details = (
            f"IS ${is_net_income:,.2f} vs BS change ${bs_change:,.2f} (Δ ${diff_is_bs:,.2f}); "
            f"CF start ${cf_net_income:,.2f} (Δ ${diff_is_cf:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-3",
                rule_name="Net Income Three-Way Tie",
                category="Audit",
                status=status,
                source_value=is_net_income,
                target_value=bs_change,
                difference=diff_is_bs,
                variance_pct=0,
                details=details,
                severity="critical",
                formula="IS Net Income = ΔBS Earnings = CF Starting Net Income",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "is_net_income": is_net_income,
                    "bs_curr": bs_curr,
                    "bs_begin": bs_begin,
                    "bs_change": bs_change,
                    "cf_net_income": cf_net_income,
                    "diff_is_bs": diff_is_bs,
                    "diff_is_cf": diff_is_cf,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_4_mortgage_principal_balance(self):
        """AUDIT-4: Mortgage principal balance ties to BS Wells Fargo."""
        ctx = self._get_alignment_context()

        bs_wells = self._get_bs_value(account_name_pattern="%Wells%Fargo%")
        ms_principal = self._get_mst_value("principal_balance")
        diff = bs_wells - ms_principal
        tolerance = 1.00
        status = "PASS" if abs(diff) <= tolerance else "FAIL"

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-4",
                rule_name="Mortgage Principal Balance Tie",
                category="Audit",
                status=status,
                source_value=bs_wells,
                target_value=ms_principal,
                difference=diff,
                variance_pct=0,
                details=f"BS Wells Fargo ${bs_wells:,.2f} vs Mortgage ${ms_principal:,.2f}",
                severity="high",
                formula="BS.Wells Fargo = MS.Principal Balance",
                intermediate_calculations={"alignment": ctx.to_dict()},
            )
        )

    def _rule_audit_5_escrow_three_way(self):
        """AUDIT-5: Escrow three-way reconciliation (BS ↔ MS ↔ CF deltas)."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            self.results.append(
                ReconciliationResult(
                    rule_id="AUDIT-5",
                    rule_name="Escrow Three-Way Reconciliation",
                    category="Audit",
                    status="SKIP",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details="No aligned begin period available for escrow reconciliation",
                    severity="high",
                )
            )
            return

        ctx = self._get_alignment_context()

        escrow_configs = [
            {
                "suffix": "TAX",
                "bs_patterns": ["%ESCROW%PROPERTY%TAX%", "%ESCROW%TAX%"],
                "ms_column": "tax_escrow_balance",
                "cf_patterns": ["%ESCROW%TAX%"],
                "account_type": "asset",
            },
            {
                "suffix": "INSURANCE",
                "bs_patterns": ["%ESCROW%INSURANCE%"],
                "ms_column": "insurance_escrow_balance",
                "cf_patterns": ["%ESCROW%INSURANCE%"],
                "account_type": "asset",
            },
            {
                "suffix": "RESERVE",
                "bs_patterns": ["%ESCROW%TI%LC%", "%ESCROW%RESERVE%"],
                "ms_column": "reserve_balance",
                "cf_patterns": ["%ESCROW%TI%LC%", "%ESCROW%RESERVE%"],
                "account_type": "asset",
            },
        ]

        tolerance = 10.00
        for config in escrow_configs:
            bs_begin = self._sum_bs_accounts(config["bs_patterns"], begin_period_id)
            bs_end = self._sum_bs_accounts(config["bs_patterns"], self.period_id)
            bs_delta = bs_end - bs_begin

            ms_end = self._get_mst_value(config["ms_column"])
            cf_value = self._sum_cf_accounts(config["cf_patterns"])
            expected_cf = -bs_delta if config["account_type"] == "asset" else bs_delta

            bs_ms_diff = bs_end - ms_end
            cf_diff = cf_value - expected_cf

            bs_ms_ok = abs(bs_ms_diff) <= tolerance
            cf_ok = abs(cf_diff) <= tolerance
            status = "PASS" if bs_ms_ok and cf_ok else "WARNING"

            details = (
                f"BS end ${bs_end:,.2f} vs MS ${ms_end:,.2f} (Δ ${bs_ms_diff:,.2f}); "
                f"BS Δ ${bs_delta:,.2f} ⇒ expected CF ${expected_cf:,.2f}, actual CF ${cf_value:,.2f}"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-5-{config['suffix']}",
                    rule_name=f"Escrow Three-Way ({config['suffix']})",
                    category="Audit",
                    status=status,
                    source_value=cf_value,
                    target_value=expected_cf,
                    difference=cf_diff,
                    variance_pct=0,
                    details=details,
                    severity="high",
                    formula="BS escrow ties to MS and BS deltas tie to CF",
                    intermediate_calculations={
                        "begin_period_id": begin_period_id,
                        "bs_begin": bs_begin,
                        "bs_end": bs_end,
                        "bs_delta": bs_delta,
                        "ms_end": ms_end,
                        "cf_value": cf_value,
                        "expected_cf": expected_cf,
                        "bs_ms_diff": bs_ms_diff,
                        "cf_diff": cf_diff,
                        "tolerance": tolerance,
                        "alignment": ctx.to_dict(),
                    },
                )
            )

    def _rule_audit_6_mortgage_interest_flow(self):
        """AUDIT-6: Mortgage interest flow (MS/payment history ↔ IS)."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        is_interest = self._get_is_value(account_name_pattern="%MORTGAGE INTEREST%")
        if abs(is_interest) <= 0.01:
            is_interest = self._get_is_value(account_name_pattern="%INTEREST%")

        start_date, end_date = self._get_window_date_range(begin_period_id)
        principal_paid, interest_paid, escrow_paid, payment_count = self._sum_payment_history_in_window(
            start_date, end_date
        )

        history_available = payment_count > 0 and abs(interest_paid) > 0.01
        if history_available:
            ms_interest = interest_paid
            basis = "payment_history_interest_paid"
        else:
            interest_due = self._get_mst_value("interest_due")
            ms_interest = interest_due * max(ctx.window_months, 1)
            basis = "interest_due_x_window"

        if abs(is_interest) <= 0.01 and abs(ms_interest) <= 0.01:
            status = "SKIP"
            diff = 0.0
            tolerance = 0.0
            details = "No mortgage interest detected on IS or mortgage statement"
        else:
            tolerance = max(1000.0, abs(ms_interest) * 0.10)
            diff = is_interest - ms_interest
            status = "PASS" if abs(diff) <= tolerance else "WARNING"
            details = (
                f"IS interest ${is_interest:,.2f} vs MS basis ${ms_interest:,.2f} "
                f"(basis={basis}, tolerance=${tolerance:,.2f})"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-6",
                rule_name="Mortgage Interest Flow",
                category="Audit",
                status=status,
                source_value=is_interest,
                target_value=ms_interest,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="IS Mortgage Interest ≈ Mortgage Interest Applied",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "payment_count": payment_count,
                    "history_available": history_available,
                    "interest_paid": interest_paid,
                    "basis": basis,
                    "window_months": ctx.window_months,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_7_mortgage_payment_composition(self):
        """AUDIT-7: Mortgage payment composition integrity."""
        total_payment = self._get_mst_value("total_payment_due")
        principal_due = self._get_mst_value("principal_due")
        interest_due = self._get_mst_value("interest_due")
        tax_due = self._get_mst_value("tax_escrow_due")
        insurance_due = self._get_mst_value("insurance_escrow_due")
        reserve_due = self._get_mst_value("reserve_due")
        late_fees = self._get_mst_value("late_fees")
        other_fees = self._get_mst_value("other_fees")

        calculated_total = (
            principal_due
            + interest_due
            + tax_due
            + insurance_due
            + reserve_due
            + late_fees
            + other_fees
        )
        escrow_total = tax_due + insurance_due + reserve_due
        principal_interest_total = principal_due + interest_due

        diff = total_payment - calculated_total
        tolerance = 1.0

        if abs(total_payment) <= 0.01 and abs(calculated_total) <= 0.01:
            status = "SKIP"
            details = "No mortgage payment composition data available"
        else:
            status = "PASS" if abs(diff) <= tolerance else "FAIL"
            details = (
                f"Total ${total_payment:,.2f} vs components ${calculated_total:,.2f} "
                f"(P+I ${principal_interest_total:,.2f}, Escrow ${escrow_total:,.2f})"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-7",
                rule_name="Mortgage Payment Composition",
                category="Audit",
                status=status,
                source_value=total_payment,
                target_value=calculated_total,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="high",
                formula="Total Payment = Principal + Interest + Escrows + Fees",
                intermediate_calculations={
                    "principal_due": principal_due,
                    "interest_due": interest_due,
                    "tax_due": tax_due,
                    "insurance_due": insurance_due,
                    "reserve_due": reserve_due,
                    "late_fees": late_fees,
                    "other_fees": other_fees,
                    "escrow_total": escrow_total,
                    "principal_interest_total": principal_interest_total,
                    "tolerance": tolerance,
                },
            )
        )

    # ------------------------------------------------------------------
    # Rent roll integration rules (AUDIT-8..11)
    # ------------------------------------------------------------------

    def _rule_audit_8_rent_roll_to_base_rentals(self):
        """AUDIT-8: Rent roll monthly rent ties to IS base rentals."""
        ctx = self._get_alignment_context()

        rr = self._get_rent_roll_summary(self.period_id)
        rr_monthly_rent = rr["occupied_monthly_rent"] or rr["total_monthly_rent"]

        base_rent_patterns = ["%BASE RENT%", "%BASE RENTAL%", "%BASE RENTALS%"]
        is_base_rent = self._sum_is_accounts(base_rent_patterns, self.period_id)

        window_months = max(ctx.window_months, 1)
        expected_is_base_rent = rr_monthly_rent * window_months
        diff = is_base_rent - expected_is_base_rent

        no_rr_data = rr_monthly_rent <= 0.01
        no_is_data = is_base_rent <= 0.01
        if no_rr_data and no_is_data:
            status = "SKIP"
            tolerance = 0.0
            details = "No rent roll or base rent data available"
        else:
            tolerance = max(1000.0, abs(expected_is_base_rent) * 0.05)
            status = "PASS" if abs(diff) <= tolerance else "WARNING"
            details = (
                f"RR monthly ${rr_monthly_rent:,.2f} × {window_months} = "
                f"${expected_is_base_rent:,.2f} vs IS base rent ${is_base_rent:,.2f}"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-8",
                rule_name="Rent Roll to Base Rentals",
                category="Audit",
                status=status,
                source_value=is_base_rent,
                target_value=expected_is_base_rent,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="IS Base Rentals ≈ RR Monthly Rent × Window Months",
                intermediate_calculations={
                    "rr_summary": rr,
                    "rr_monthly_rent": rr_monthly_rent,
                    "window_months": window_months,
                    "expected_is_base_rent": expected_is_base_rent,
                    "is_base_rent": is_base_rent,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_9_rent_roll_change_to_is_change(self):
        """AUDIT-9: Rent roll rent changes should flow to IS base rentals."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        rr_curr = self._get_rent_roll_summary(self.period_id)
        rr_prior = self._get_rent_roll_summary(prior_id)
        rr_curr_rent = rr_curr["occupied_monthly_rent"] or rr_curr["total_monthly_rent"]
        rr_prior_rent = rr_prior["occupied_monthly_rent"] or rr_prior["total_monthly_rent"]
        rr_delta = rr_curr_rent - rr_prior_rent

        base_rent_patterns = ["%BASE RENT%", "%BASE RENTAL%", "%BASE RENTALS%"]
        is_curr = self._sum_is_accounts(base_rent_patterns, self.period_id)
        is_prior = self._sum_is_accounts(base_rent_patterns, prior_id)
        is_delta = is_curr - is_prior

        no_activity = abs(rr_delta) <= 0.01 and abs(is_delta) <= 0.01
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
            details = "No rent roll or base rent change detected"
        else:
            rr_sign = self._sign(rr_delta)
            is_sign = self._sign(is_delta)
            sign_match = rr_sign == 0 or is_sign == 0 or rr_sign == is_sign

            diff = is_delta - rr_delta
            tolerance = max(2500.0, abs(rr_delta) * 3.0)
            status = "PASS" if sign_match and abs(diff) <= tolerance else "WARNING"
            details = (
                f"RR Δ ${rr_delta:,.2f} vs IS Δ ${is_delta:,.2f} "
                f"(sign_match={sign_match})"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-9",
                rule_name="Rent Roll Change to IS Change",
                category="Audit",
                status=status,
                source_value=is_delta,
                target_value=rr_delta,
                difference=is_delta - rr_delta,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="ΔIS Base Rentals should directionally follow ΔRR Monthly Rent",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "rr_curr_rent": rr_curr_rent,
                    "rr_prior_rent": rr_prior_rent,
                    "rr_delta": rr_delta,
                    "is_curr": is_curr,
                    "is_prior": is_prior,
                    "is_delta": is_delta,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_10_occupancy_impact_on_revenue(self):
        """AUDIT-10: Occupancy changes should correlate with base rental changes."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        rr_curr = self._get_rent_roll_summary(self.period_id)
        rr_prior = self._get_rent_roll_summary(prior_id)
        occ_delta_pp = rr_curr["occupancy_pct"] - rr_prior["occupancy_pct"]

        base_rent_patterns = ["%BASE RENT%", "%BASE RENTAL%", "%BASE RENTALS%"]
        is_curr = self._sum_is_accounts(base_rent_patterns, self.period_id)
        is_prior = self._sum_is_accounts(base_rent_patterns, prior_id)
        is_delta = is_curr - is_prior

        no_rr_data = rr_curr["tenant_count"] == 0 or rr_prior["tenant_count"] == 0
        if no_rr_data:
            status = "SKIP"
            details = "Insufficient rent roll data for occupancy change analysis"
        else:
            material_occ_change = abs(occ_delta_pp) >= 3.0
            revenue_moved_opposite = (occ_delta_pp < 0 and is_delta > 1000.0) or (
                occ_delta_pp > 0 and is_delta < -1000.0
            )

            if material_occ_change and revenue_moved_opposite:
                status = "WARNING"
            else:
                status = "INFO"

            details = (
                f"Occupancy Δ {occ_delta_pp:.2f}pp vs base rent Δ ${is_delta:,.2f}"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-10",
                rule_name="Occupancy Impact on Revenue",
                category="Audit",
                status=status,
                source_value=occ_delta_pp,
                target_value=is_delta,
                difference=0,
                variance_pct=0,
                details=details,
                severity="low",
                formula="Material occupancy changes should directionally align with base rent changes",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "occupancy_curr_pct": rr_curr["occupancy_pct"],
                    "occupancy_prior_pct": rr_prior["occupancy_pct"],
                    "occupancy_delta_pp": occ_delta_pp,
                    "is_curr": is_curr,
                    "is_prior": is_prior,
                    "is_delta": is_delta,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_11_tenant_count_vs_ar(self):
        """AUDIT-11: Tenant count changes should be consistent with A/R signals."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        rr_curr = self._get_rent_roll_summary(self.period_id)
        rr_prior = self._get_rent_roll_summary(prior_id)
        tenant_delta = rr_curr["occupied_tenant_count"] - rr_prior["occupied_tenant_count"]

        ar_patterns = [
            "%A/R%TENANT%",
            "%ACCOUNTS RECEIVABLE%TENANT%",
            "%A/R%TRADE%",
            "%ACCOUNTS RECEIVABLE%TRADE%",
        ]
        ar_curr = self._sum_bs_accounts(ar_patterns, self.period_id)
        ar_prior = self._sum_bs_accounts(ar_patterns, prior_id)
        ar_delta = ar_curr - ar_prior

        rr_rent = rr_curr["occupied_monthly_rent"] or rr_curr["total_monthly_rent"]
        threshold = max(10000.0, rr_rent * 0.25)

        warning = (tenant_delta < 0 and ar_delta > threshold) or (
            tenant_delta > 0 and ar_delta < -threshold
        )

        status = "WARNING" if warning else "INFO"
        details = (
            f"Occupied tenants Δ {tenant_delta:+d}, A/R Δ ${ar_delta:,.2f} "
            f"(threshold ${threshold:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-11",
                rule_name="Tenant Count vs A/R",
                category="Audit",
                status=status,
                source_value=float(tenant_delta),
                target_value=ar_delta,
                difference=0,
                variance_pct=0,
                details=details,
                severity="low",
                formula="Tenant-count direction should be broadly consistent with A/R movements",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "tenant_count_curr": rr_curr["occupied_tenant_count"],
                    "tenant_count_prior": rr_prior["occupied_tenant_count"],
                    "tenant_delta": tenant_delta,
                    "ar_curr": ar_curr,
                    "ar_prior": ar_prior,
                    "ar_delta": ar_delta,
                    "threshold": threshold,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    # ------------------------------------------------------------------
    # Working-capital and high-value integration rules (AUDIT-12+)
    # ------------------------------------------------------------------

    def _rule_audit_12_ar_three_way_collections(self):
        """AUDIT-12: A/R tenants three-way collections bridge."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        revenue = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
        if abs(revenue) <= 0.01:
            revenue = self._get_is_value(account_name_pattern="%TOTAL REVENUE%")

        ar_patterns = [
            "%A/R%TENANT%",
            "%ACCOUNTS RECEIVABLE%TENANT%",
            "%A/R%TRADE%",
            "%ACCOUNTS RECEIVABLE%TRADE%",
        ]

        ar_begin = self._sum_bs_accounts(ar_patterns, begin_period_id)
        ar_end = self._sum_bs_accounts(ar_patterns, self.period_id)
        ar_change = ar_end - ar_begin
        ar_decrease = ar_begin - ar_end

        implied_collections = revenue + ar_decrease

        cf_ar_adj = self._sum_cf_accounts(ar_patterns)
        expected_cf = -ar_change  # A/R is an asset.
        diff = cf_ar_adj - expected_cf

        no_activity = (
            abs(revenue) <= 0.01 and abs(ar_change) <= 0.01 and abs(cf_ar_adj) <= 0.01
        )
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
            details = "No revenue or A/R activity detected"
        else:
            scale = max(abs(expected_cf), abs(cf_ar_adj), 1.0)
            tolerance = max(100.0, scale * 0.05)
            status = "PASS" if abs(diff) <= tolerance else "WARNING"
            details = (
                f"CF A/R ${cf_ar_adj:,.2f} vs expected ${expected_cf:,.2f}; "
                f"implied collections ${implied_collections:,.2f}"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-12",
                rule_name="A/R Three-Way Collections Bridge",
                category="Audit",
                status=status,
                source_value=cf_ar_adj,
                target_value=expected_cf,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="CF A/R = -(BS[end] - BS[begin]); collections = revenue + (begin AR - end AR)",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "revenue": revenue,
                    "ar_begin": ar_begin,
                    "ar_end": ar_end,
                    "ar_change": ar_change,
                    "implied_collections": implied_collections,
                    "cf_ar_adj": cf_ar_adj,
                    "expected_cf": expected_cf,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_13_property_tax_flow(self):
        """AUDIT-13: Property tax expense ↔ payable ↔ disbursement ↔ CF."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        is_tax_expense = self._get_is_value(account_name_pattern="%PROPERTY TAX%")

        bs_tax_patterns = ["%PROPERTY TAX%PAYABLE%", "%PROPERTY TAX PAYABLE%"]
        bs_begin = self._sum_bs_accounts(bs_tax_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(bs_tax_patterns, self.period_id)
        bs_delta = bs_end - bs_begin

        cf_tax_adj = self._sum_cf_accounts(bs_tax_patterns)
        ms_disb_window = self._get_ytd_delta("ytd_taxes_disbursed", begin_period_id)

        expected_bs_delta = is_tax_expense - ms_disb_window
        bs_diff = bs_delta - expected_bs_delta
        cf_diff = cf_tax_adj - bs_delta

        no_activity = (
            abs(is_tax_expense) <= 0.01
            and abs(bs_delta) <= 0.01
            and abs(cf_tax_adj) <= 0.01
            and abs(ms_disb_window) <= 0.01
        )
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(
                abs(expected_bs_delta), abs(bs_delta), abs(cf_tax_adj), abs(ms_disb_window), 1.0
            )
            tolerance = max(1000.0, scale * 0.10)
            status = "PASS" if abs(bs_diff) <= tolerance and abs(cf_diff) <= tolerance else "WARNING"

        details = (
            f"IS tax ${is_tax_expense:,.2f}, MS disb ${ms_disb_window:,.2f}, "
            f"BS Δ ${bs_delta:,.2f}, CF ${cf_tax_adj:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-13",
                rule_name="Property Tax Three-Way Flow",
                category="Audit",
                status=status,
                source_value=bs_delta,
                target_value=expected_bs_delta,
                difference=bs_diff,
                variance_pct=0,
                details=details,
                severity="high",
                formula="ΔTax Payable ≈ Tax Expense - Tax Disbursement; CF ≈ ΔPayable",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "is_tax_expense": is_tax_expense,
                    "ms_disb_window": ms_disb_window,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_delta": bs_delta,
                    "expected_bs_delta": expected_bs_delta,
                    "cf_tax_adj": cf_tax_adj,
                    "bs_diff": bs_diff,
                    "cf_diff": cf_diff,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_14_prepaid_insurance_cycle(self):
        """AUDIT-14: Prepaid insurance cycle across MS ↔ BS ↔ IS ↔ CF."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        prepaid_patterns = ["%PREPAID%INSURANCE%"]
        bs_begin = self._sum_bs_accounts(prepaid_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(prepaid_patterns, self.period_id)
        bs_delta = bs_end - bs_begin

        is_insurance_expense = self._get_is_value(account_name_pattern="%INSURANCE%")
        ms_disb_window = self._get_ytd_delta("ytd_insurance_disbursed", begin_period_id)

        expected_bs_delta = ms_disb_window - is_insurance_expense

        cf_insurance_escrow = self._sum_cf_accounts(["%ESCROW%INSURANCE%"])
        expected_cf = -bs_delta  # Prepaid insurance is an asset.

        bs_diff = bs_delta - expected_bs_delta
        cf_diff = cf_insurance_escrow - expected_cf

        no_activity = (
            abs(bs_delta) <= 0.01
            and abs(is_insurance_expense) <= 0.01
            and abs(ms_disb_window) <= 0.01
            and abs(cf_insurance_escrow) <= 0.01
        )
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(
                abs(bs_delta),
                abs(expected_bs_delta),
                abs(ms_disb_window),
                abs(is_insurance_expense),
                abs(cf_insurance_escrow),
                1.0,
            )
            tolerance = max(5000.0, scale * 0.20)
            status = "PASS" if abs(bs_diff) <= tolerance and abs(cf_diff) <= tolerance else "WARNING"

        details = (
            f"MS disb ${ms_disb_window:,.2f}, IS insurance ${is_insurance_expense:,.2f}, "
            f"BS Δ prepaid ${bs_delta:,.2f}, CF escrow ${cf_insurance_escrow:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-14",
                rule_name="Prepaid Insurance Cycle",
                category="Audit",
                status=status,
                source_value=bs_delta,
                target_value=expected_bs_delta,
                difference=bs_diff,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="ΔPrepaid ≈ Insurance Disbursed - Insurance Expense; CF ≈ -ΔPrepaid",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_delta": bs_delta,
                    "is_insurance_expense": is_insurance_expense,
                    "ms_disb_window": ms_disb_window,
                    "expected_bs_delta": expected_bs_delta,
                    "cf_insurance_escrow": cf_insurance_escrow,
                    "expected_cf": expected_cf,
                    "bs_diff": bs_diff,
                    "cf_diff": cf_diff,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_15_depreciation_perfect_circle(self):
        """AUDIT-15: Depreciation perfect circle across IS ↔ BS ↔ CF."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        is_depr = abs(self._get_is_value(account_name_pattern="%DEPRECIATION%"))
        cf_depr = self._get_cf_value(account_name_pattern="%DEPRECIATION%", category="Operating")
        if abs(cf_depr) <= 0.01:
            cf_depr = self._get_cf_value(account_name_pattern="%DEPRECIATION%")

        bs_accum_patterns = ["%ACCUM%DEPR%"]
        bs_begin = self._sum_bs_accounts(bs_accum_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(bs_accum_patterns, self.period_id)
        bs_delta = abs(bs_end - bs_begin)

        no_activity = is_depr <= 0.01 and cf_depr <= 0.01 and bs_delta <= 0.01
        scale = max(is_depr, cf_depr, bs_delta, 1.0)
        tolerance = 0.0 if no_activity else max(1.0, scale * 0.01)

        diff_is_cf = is_depr - cf_depr
        diff_is_bs = is_depr - bs_delta
        diff_cf_bs = cf_depr - bs_delta

        if no_activity:
            status = "SKIP"
        else:
            status = (
                "PASS"
                if abs(diff_is_cf) <= tolerance
                and abs(diff_is_bs) <= tolerance
                and abs(diff_cf_bs) <= tolerance
                else "WARNING"
            )

        details = (
            f"IS ${is_depr:,.2f}, BS Δ ${bs_delta:,.2f}, CF ${cf_depr:,.2f} "
            f"(tol ${tolerance:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-15",
                rule_name="Depreciation Perfect Circle",
                category="Audit",
                status=status,
                source_value=is_depr,
                target_value=bs_delta,
                difference=diff_is_bs,
                variance_pct=0,
                details=details,
                severity="high",
                formula="IS Depreciation = ΔBS Accum Depreciation = CF Depreciation Add-Back",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "is_depr": is_depr,
                    "cf_depr": cf_depr,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_delta": bs_delta,
                    "diff_is_cf": diff_is_cf,
                    "diff_is_bs": diff_is_bs,
                    "diff_cf_bs": diff_cf_bs,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_16_amortization_perfect_circle(self):
        """AUDIT-16: Amortization perfect circle across IS ↔ BS ↔ CF."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        is_amort = abs(self._get_is_value(account_name_pattern="%AMORTIZATION%"))
        cf_amort = self._get_cf_value(account_name_pattern="%AMORTIZATION%")

        bs_accum_patterns = ["%ACCUM%AMORT%"]
        bs_begin = self._sum_bs_accounts(bs_accum_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(bs_accum_patterns, self.period_id)
        bs_delta = abs(bs_end - bs_begin)

        no_activity = is_amort <= 0.01 and cf_amort <= 0.01 and bs_delta <= 0.01
        scale = max(is_amort, cf_amort, bs_delta, 1.0)
        tolerance = 0.0 if no_activity else max(1.0, scale * 0.05)

        diff_is_cf = is_amort - cf_amort
        diff_is_bs = is_amort - bs_delta
        diff_cf_bs = cf_amort - bs_delta

        if no_activity:
            status = "SKIP"
        else:
            status = (
                "PASS"
                if abs(diff_is_cf) <= tolerance
                and abs(diff_is_bs) <= tolerance
                and abs(diff_cf_bs) <= tolerance
                else "WARNING"
            )

        details = (
            f"IS ${is_amort:,.2f}, BS Δ ${bs_delta:,.2f}, CF ${cf_amort:,.2f} "
            f"(tol ${tolerance:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-16",
                rule_name="Amortization Perfect Circle",
                category="Audit",
                status=status,
                source_value=is_amort,
                target_value=bs_delta,
                difference=diff_is_bs,
                variance_pct=0,
                details=details,
                severity="high",
                formula="IS Amortization = ΔBS Accum Amortization = CF Amortization Add-Back",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "is_amort": is_amort,
                    "cf_amort": cf_amort,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_delta": bs_delta,
                    "diff_is_cf": diff_is_cf,
                    "diff_is_bs": diff_is_bs,
                    "diff_cf_bs": diff_cf_bs,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_17_depreciation_cessation_consistency(self):
        """AUDIT-17: Depreciation cessation must be consistent across statements."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        is_depr = abs(self._get_is_value(account_name_pattern="%DEPRECIATION%"))
        cf_depr = self._get_cf_value(account_name_pattern="%DEPRECIATION%", category="Operating")
        if abs(cf_depr) <= 0.01:
            cf_depr = self._get_cf_value(account_name_pattern="%DEPRECIATION%")

        bs_accum_patterns = ["%ACCUM%DEPR%"]
        bs_begin = self._sum_bs_accounts(bs_accum_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(bs_accum_patterns, self.period_id)
        bs_delta = abs(bs_end - bs_begin)

        stop_threshold = 100.0
        is_zero = is_depr <= stop_threshold
        cf_zero = cf_depr <= stop_threshold
        bs_zero = bs_delta <= stop_threshold

        if is_zero and cf_zero and bs_zero:
            status = "PASS"
            details = "Depreciation appears to have stopped consistently across IS, BS, and CF"
        elif (is_zero, cf_zero, bs_zero).count(True) in (1, 2):
            status = "WARNING"
            details = (
                f"Inconsistent cessation signals: IS ${is_depr:,.2f}, "
                f"BS Δ ${bs_delta:,.2f}, CF ${cf_depr:,.2f}"
            )
        else:
            status = "INFO"
            details = "Depreciation still active across statements"

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-17",
                rule_name="Depreciation Cessation Consistency",
                category="Audit",
                status=status,
                source_value=is_depr,
                target_value=bs_delta,
                difference=is_depr - bs_delta,
                variance_pct=0,
                details=details,
                severity="high",
                formula="When depreciation stops, it should stop on IS, BS accumulation, and CF add-back",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "is_depr": is_depr,
                    "cf_depr": cf_depr,
                    "bs_delta": bs_delta,
                    "stop_threshold": stop_threshold,
                    "is_zero": is_zero,
                    "cf_zero": cf_zero,
                    "bs_zero": bs_zero,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_18_capex_flow(self):
        """AUDIT-18: CapEx flow (CF) must tie to BS asset growth."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        bs_patterns = [
            "%TENANT%IMPROV%",
            "%TI%CURRENT%IMPROV%",
            "%CURRENT%IMPROV%",
        ]
        cf_patterns = [
            "%TI%CURRENT%IMPROV%",
            "%TENANT%IMPROV%",
            "%CURRENT%IMPROV%",
        ]

        bs_begin = self._sum_bs_accounts(bs_patterns, begin_period_id)
        bs_end = self._sum_bs_accounts(bs_patterns, self.period_id)
        bs_delta = bs_end - bs_begin

        cf_capex = self._sum_cf_accounts(cf_patterns)
        expected_cf = -bs_delta
        diff = cf_capex - expected_cf

        no_activity = abs(bs_delta) <= 0.01 and abs(cf_capex) <= 0.01
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(abs(bs_delta), abs(cf_capex), 1.0)
            tolerance = max(1000.0, scale * 0.05)
            status = "PASS" if abs(diff) <= tolerance else "WARNING"

        details = (
            f"BS Δ TI ${bs_delta:,.2f} vs CF CapEx ${cf_capex:,.2f} "
            f"(expected ${expected_cf:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-18",
                rule_name="CapEx Flow to Balance Sheet",
                category="Audit",
                status=status,
                source_value=cf_capex,
                target_value=expected_cf,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="high",
                formula="CF CapEx = -(BS[end] - BS[begin])",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_delta": bs_delta,
                    "cf_capex": cf_capex,
                    "expected_cf": expected_cf,
                    "diff": diff,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_19_escrow_funded_capex(self):
        """AUDIT-19: Reserve escrow disbursements should support TI additions."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        reserve_disb_window = self._get_ytd_delta("ytd_reserve_disbursed", begin_period_id)

        ti_patterns = [
            "%TENANT%IMPROV%",
            "%TI%CURRENT%IMPROV%",
            "%CURRENT%IMPROV%",
        ]
        ti_begin = self._sum_bs_accounts(ti_patterns, begin_period_id)
        ti_end = self._sum_bs_accounts(ti_patterns, self.period_id)
        ti_delta = ti_end - ti_begin

        no_activity = abs(reserve_disb_window) <= 0.01 and abs(ti_delta) <= 0.01
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(abs(reserve_disb_window), abs(ti_delta), 1.0)
            tolerance = max(5000.0, scale * 0.10)
            status = "PASS" if abs(reserve_disb_window - ti_delta) <= tolerance else "WARNING"

        details = (
            f"Reserve disbursed ${reserve_disb_window:,.2f} vs TI growth ${ti_delta:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-19",
                rule_name="Escrow-Funded CapEx",
                category="Audit",
                status=status,
                source_value=reserve_disb_window,
                target_value=ti_delta,
                difference=reserve_disb_window - ti_delta,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="MS Reserve Disbursed ≈ BS TI/Current Improvements Increase",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "reserve_disb_window": reserve_disb_window,
                    "ti_begin": ti_begin,
                    "ti_end": ti_end,
                    "ti_delta": ti_delta,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_20_fixed_asset_additions(self):
        """AUDIT-20: Fixed asset additions should tie to CF cash outflows."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        configs = [
            {
                "suffix": "ROOF",
                "bs_patterns": ["%30%YEAR%ROOF%", "%ROOF%"],
                "cf_patterns": ["%ROOF%"],
            },
            {
                "suffix": "HVAC",
                "bs_patterns": ["%HVAC%"],
                "cf_patterns": ["%HVAC%"],
            },
            {
                "suffix": "EQUIPMENT",
                "bs_patterns": ["%EQUIPMENT%", "%MACHINERY%"],
                "cf_patterns": ["%EQUIPMENT%", "%MACHINERY%"],
            },
            {
                "suffix": "TI",
                "bs_patterns": [
                    "%TENANT%IMPROV%",
                    "%TI%CURRENT%IMPROV%",
                    "%CURRENT%IMPROV%",
                ],
                "cf_patterns": [
                    "%TI%CURRENT%IMPROV%",
                    "%TENANT%IMPROV%",
                    "%CURRENT%IMPROV%",
                ],
            },
        ]

        for cfg in configs:
            bs_begin = self._sum_bs_accounts(cfg["bs_patterns"], begin_period_id)
            bs_end = self._sum_bs_accounts(cfg["bs_patterns"], self.period_id)
            bs_delta = bs_end - bs_begin

            cf_total = self._sum_cf_accounts(cfg["cf_patterns"])
            expected_cf = -bs_delta  # Fixed assets are assets.
            diff = cf_total - expected_cf

            no_activity = abs(bs_delta) <= 0.01 and abs(cf_total) <= 0.01
            if no_activity:
                status = "SKIP"
                tolerance = 0.0
            else:
                scale = max(abs(bs_delta), abs(cf_total), 1.0)
                tolerance = max(10.0, scale * 0.05)
                status = "PASS" if abs(diff) <= tolerance else "WARNING"

            details = (
                f"BS Δ ${bs_delta:,.2f} vs CF ${cf_total:,.2f} "
                f"(expected ${expected_cf:,.2f})"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-20-{cfg['suffix']}",
                    rule_name=f"Fixed Asset Additions ({cfg['suffix']})",
                    category="Audit",
                    status=status,
                    source_value=cf_total,
                    target_value=expected_cf,
                    difference=diff,
                    variance_pct=0,
                    details=details,
                    severity="high",
                    formula="CF additions = -(BS[end] - BS[begin])",
                    intermediate_calculations={
                        "begin_period_id": begin_period_id,
                        "bs_begin": bs_begin,
                        "bs_end": bs_end,
                        "bs_delta": bs_delta,
                        "cf_total": cf_total,
                        "expected_cf": expected_cf,
                        "diff": diff,
                        "tolerance": tolerance,
                        "alignment": ctx.to_dict(),
                    },
                )
            )

    def _rule_audit_21_principal_payment_flow(self):
        """AUDIT-21: Principal applied should tie to BS reduction and CF line."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        bs_begin = self._get_bs_value(account_name_pattern="%Wells%Fargo%", period_id=begin_period_id)
        bs_end = self._get_bs_value(account_name_pattern="%Wells%Fargo%")
        bs_reduction = bs_begin - bs_end

        start_date, end_date = self._get_window_date_range(begin_period_id)
        principal_paid, interest_paid, escrow_paid, payment_count = self._sum_payment_history_in_window(
            start_date, end_date
        )
        history_available = payment_count > 0 and abs(principal_paid) > 0.01

        if history_available:
            principal_applied = principal_paid
            basis = "payment_history_principal_paid"
        else:
            principal_due = self._get_mst_value("principal_due")
            principal_applied = principal_due * max(ctx.window_months, 1)
            basis = "principal_due_x_window"

        cf_wells = abs(self._sum_cf_accounts(["%WELLS%FARGO%"]))

        diff_bs = principal_applied - bs_reduction
        diff_cf = cf_wells - principal_applied

        no_activity = (
            abs(principal_applied) <= 0.01 and abs(bs_reduction) <= 0.01 and abs(cf_wells) <= 0.01
        )
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(abs(principal_applied), abs(bs_reduction), abs(cf_wells), 1.0)
            tolerance = max(100.0, scale * 0.05)
            status = "PASS" if abs(diff_bs) <= tolerance and abs(diff_cf) <= tolerance else "WARNING"

        details = (
            f"Applied ${principal_applied:,.2f} vs BS reduction ${bs_reduction:,.2f} "
            f"and CF ${cf_wells:,.2f} (basis={basis})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-21",
                rule_name="Principal Payment Flow",
                category="Audit",
                status=status,
                source_value=principal_applied,
                target_value=bs_reduction,
                difference=diff_bs,
                variance_pct=0,
                details=details,
                severity="high",
                formula="Principal Applied ≈ BS Reduction ≈ |CF Wells Fargo|",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "bs_begin": bs_begin,
                    "bs_end": bs_end,
                    "bs_reduction": bs_reduction,
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "payment_count": payment_count,
                    "principal_paid": principal_paid,
                    "basis": basis,
                    "principal_applied": principal_applied,
                    "cf_wells": cf_wells,
                    "diff_bs": diff_bs,
                    "diff_cf": diff_cf,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_22_ytd_principal_reduction(self):
        """AUDIT-22: YTD BS mortgage reduction vs YTD principal paid."""
        ctx = self._get_alignment_context()

        year_start_period_id = self._get_year_start_period_id(ctx.end_year)
        if not year_start_period_id:
            return

        bs_start = self._get_bs_value(account_name_pattern="%Wells%Fargo%", period_id=year_start_period_id)
        bs_end = self._get_bs_value(account_name_pattern="%Wells%Fargo%")
        bs_reduction_ytd = bs_start - bs_end

        ytd_start = self._get_mst_value("ytd_principal_paid", period_id=year_start_period_id)
        ytd_end = self._get_mst_value("ytd_principal_paid")
        ytd_delta = ytd_end - ytd_start
        if ytd_delta < 0:
            ytd_delta = ytd_end

        no_activity = abs(bs_reduction_ytd) <= 0.01 and abs(ytd_delta) <= 0.01
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(abs(bs_reduction_ytd), abs(ytd_delta), 1.0)
            tolerance = max(1000.0, scale * 0.10)
            status = "PASS" if abs(bs_reduction_ytd - ytd_delta) <= tolerance else "INFO"

        details = (
            f"BS YTD reduction ${bs_reduction_ytd:,.2f} vs MS YTD principal ${ytd_delta:,.2f} "
            f"(start period {year_start_period_id})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-22",
                rule_name="YTD Principal Reduction",
                category="Audit",
                status=status,
                source_value=bs_reduction_ytd,
                target_value=ytd_delta,
                difference=bs_reduction_ytd - ytd_delta,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="BS[YTD Start] - BS[Current] ≈ MS YTD Principal Paid",
                intermediate_calculations={
                    "year_start_period_id": year_start_period_id,
                    "bs_start": bs_start,
                    "bs_end": bs_end,
                    "bs_reduction_ytd": bs_reduction_ytd,
                    "ytd_start": ytd_start,
                    "ytd_end": ytd_end,
                    "ytd_delta": ytd_delta,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_24_cash_flow_cash_bridge(self):
        """AUDIT-24: CF cash bridge must tie CF table and BS cash."""
        ctx = self._get_alignment_context()

        no_cf_cash_table = (
            abs(ctx.cf_beginning_cash) <= 0.01
            and abs(ctx.cf_cash_delta) <= 0.01
            and abs(ctx.cf_ending_cash) <= 0.01
        )
        if no_cf_cash_table:
            self.results.append(
                ReconciliationResult(
                    rule_id="AUDIT-24",
                    rule_name="Cash Flow Cash Bridge",
                    category="Audit",
                    status="SKIP",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details="Cash table not available on CF statement",
                    severity="critical",
                    intermediate_calculations={"alignment": ctx.to_dict()},
                )
            )
            return

        bs_cash_end = self._get_bs_total_cash(self.period_id)

        computed_end = ctx.cf_beginning_cash + ctx.cf_cash_delta
        diff_table = computed_end - ctx.cf_ending_cash
        diff_bs = ctx.cf_ending_cash - bs_cash_end

        tolerance = 1.0
        status = "PASS" if abs(diff_table) <= tolerance and abs(diff_bs) <= tolerance else "FAIL"

        details = (
            f"Begin ${ctx.cf_beginning_cash:,.2f} + Flow ${ctx.cf_cash_delta:,.2f} = "
            f"${computed_end:,.2f}; CF end ${ctx.cf_ending_cash:,.2f}; BS cash ${bs_cash_end:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-24",
                rule_name="Cash Flow to Balance Sheet Cash Bridge",
                category="Audit",
                status=status,
                source_value=computed_end,
                target_value=bs_cash_end,
                difference=computed_end - bs_cash_end,
                variance_pct=0,
                details=details,
                severity="critical",
                formula="CF Begin + CF Flow = CF End = BS Cash",
                intermediate_calculations={
                    "cf_beginning_cash": ctx.cf_beginning_cash,
                    "cf_cash_delta": ctx.cf_cash_delta,
                    "computed_end": computed_end,
                    "cf_ending_cash": ctx.cf_ending_cash,
                    "bs_cash_end": bs_cash_end,
                    "diff_table": diff_table,
                    "diff_bs": diff_bs,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_26_operating_activities_reconciliation(self):
        """AUDIT-26: Reconstruct operating cash flow from core components."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        net_income = self._get_is_value(account_name_pattern="%NET INCOME%")
        depreciation = self._get_cf_value(account_name_pattern="%DEPRECIATION%", category="Operating")
        if abs(depreciation) <= 0.01:
            depreciation = self._get_cf_value(account_name_pattern="%DEPRECIATION%")
        amortization = self._get_cf_value(account_name_pattern="%AMORTIZATION%")

        wc_expected_total = 0.0
        wc_details = []
        for mapping in self._working_capital_mappings():
            if mapping["rule_suffix"].startswith("ESCROW") or mapping["rule_suffix"] == "WELLS-FARGO":
                continue
            begin_value = self._sum_bs_accounts(mapping["bs_patterns"], begin_period_id)
            end_value = self._sum_bs_accounts(mapping["bs_patterns"], self.period_id)
            bs_delta = end_value - begin_value
            expected_cf = self._expected_cf_amount(mapping["account_type"], bs_delta)
            wc_expected_total += expected_cf
            wc_details.append(
                {
                    "rule_suffix": mapping["rule_suffix"],
                    "bs_delta": bs_delta,
                    "expected_cf": expected_cf,
                }
            )

        reconstructed_operating = net_income + depreciation + amortization + wc_expected_total

        operating_total, operating_basis = self._sum_cf_operating_total()
        diff = operating_total - reconstructed_operating

        no_activity = abs(operating_total) <= 0.01 and abs(reconstructed_operating) <= 0.01
        if no_activity:
            status = "SKIP"
            tolerance = 0.0
        else:
            scale = max(abs(operating_total), abs(reconstructed_operating), 1.0)
            tolerance = max(5000.0, scale * 0.10)
            status = "PASS" if abs(diff) <= tolerance else "WARNING"

        details = (
            f"Operating total ${operating_total:,.2f} ({operating_basis}) vs reconstructed "
            f"${reconstructed_operating:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-26",
                rule_name="Operating Activities Reconciliation",
                category="Audit",
                status=status,
                source_value=operating_total,
                target_value=reconstructed_operating,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="high",
                formula="Operating CF ≈ Net Income + Non-Cash + Working Capital Deltas",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "net_income": net_income,
                    "depreciation": depreciation,
                    "amortization": amortization,
                    "wc_expected_total": wc_expected_total,
                    "wc_details": wc_details,
                    "reconstructed_operating": reconstructed_operating,
                    "operating_total": operating_total,
                    "operating_basis": operating_basis,
                    "diff": diff,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_27_period_contiguity(self):
        """AUDIT-27: Ensure the prior period is the immediately preceding month."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        curr_year, curr_month = self._get_period_year_month(self.period_id)
        prior_year, prior_month = self._get_period_year_month(prior_id)

        if curr_month == 1:
            expected_year, expected_month = curr_year - 1, 12
        else:
            expected_year, expected_month = curr_year, curr_month - 1

        is_contiguous = prior_year == expected_year and prior_month == expected_month
        status = "PASS" if is_contiguous else "WARNING"
        details = (
            f"Current {curr_year}-{curr_month:02d}, prior {prior_year}-{prior_month:02d}, "
            f"expected prior {expected_year}-{expected_month:02d}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-27",
                rule_name="Sequential Period Contiguity",
                category="Audit",
                status=status,
                source_value=float(prior_id),
                target_value=0,
                difference=0,
                variance_pct=0,
                details=details,
                severity="critical",
                formula="Prior period should be the immediately preceding month",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "curr_year": curr_year,
                    "curr_month": curr_month,
                    "prior_year": prior_year,
                    "prior_month": prior_month,
                    "expected_year": expected_year,
                    "expected_month": expected_month,
                },
            )
        )

    def _rule_audit_37_negative_balance_validation(self):
        """AUDIT-37: Scan for negative balances in accounts that should be positive."""
        ctx = self._get_alignment_context()

        exclusions = ["%ACCUM%", "%DEPR%", "%AMORT%", "%DISTRIBUT%"]

        cash_count, cash_examples = self._find_negative_bs_accounts(["%CASH%"], exclusions)
        escrow_count, escrow_examples = self._find_negative_bs_accounts(["%ESCROW%"], exclusions)
        deposit_count, deposit_examples = self._find_negative_bs_accounts(["%DEPOSIT%"], exclusions)

        total_count = cash_count + escrow_count + deposit_count
        status = "PASS" if total_count == 0 else "FAIL"

        examples = cash_examples + escrow_examples + deposit_examples
        examples = examples[:5]

        details = "No unexpected negative balances detected"
        if total_count > 0:
            formatted = ", ".join(
                [f"{ex['account_name']}: ${ex['amount']:,.2f}" for ex in examples]
            )
            details = f"Found {total_count} negative balance(s): {formatted}"

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-37",
                rule_name="Negative Balance Validation",
                category="Audit",
                status=status,
                source_value=float(total_count),
                target_value=0,
                difference=float(total_count),
                variance_pct=0,
                details=details,
                severity="high",
                formula="Cash, escrow, and deposits should not be negative",
                intermediate_calculations={
                    "cash_count": cash_count,
                    "escrow_count": escrow_count,
                    "deposit_count": deposit_count,
                    "examples": examples,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_43_dscr(self):
        """AUDIT-43: Debt Service Coverage Ratio (DSCR) covenant check."""
        ctx = self._get_alignment_context()

        noi = self._get_is_value(account_name_pattern="%NET OPERATING INCOME%")
        if abs(noi) <= 0.01:
            total_income = self._get_is_value(account_name_pattern="%TOTAL INCOME%")
            total_expenses = self._get_is_value(account_name_pattern="%TOTAL EXPENSE%")
            if abs(total_income) > 0.01 and abs(total_expenses) > 0.01:
                noi = total_income - total_expenses

        monthly_payment = self._get_mst_value("total_payment_due")
        if abs(monthly_payment) <= 0.01:
            monthly_payment = (
                self._get_mst_value("principal_due")
                + self._get_mst_value("interest_due")
                + self._get_mst_value("tax_escrow_due")
                + self._get_mst_value("insurance_escrow_due")
                + self._get_mst_value("reserve_due")
                + self._get_mst_value("late_fees")
                + self._get_mst_value("other_fees")
            )

        if abs(noi) <= 0.01 or abs(monthly_payment) <= 0.01:
            self.results.append(
                ReconciliationResult(
                    rule_id="AUDIT-43",
                    rule_name="Debt Service Coverage Ratio (DSCR)",
                    category="Audit",
                    status="SKIP",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details="Insufficient NOI or debt-service data for DSCR",
                    severity="critical",
                    intermediate_calculations={"alignment": ctx.to_dict()},
                )
            )
            return

        annualized_noi = noi * (12.0 / max(ctx.window_months, 1))
        annual_debt_service = monthly_payment * 12.0
        dscr = annualized_noi / annual_debt_service if annual_debt_service else 0.0

        covenant = 1.20
        if dscr >= covenant:
            status = "PASS"
        elif dscr >= 1.0:
            status = "WARNING"
        else:
            status = "FAIL"

        details = (
            f"DSCR {dscr:.2f}x (annualized NOI ${annualized_noi:,.2f} / "
            f"debt service ${annual_debt_service:,.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-43",
                rule_name="Debt Service Coverage Ratio (DSCR)",
                category="Audit",
                status=status,
                source_value=dscr,
                target_value=covenant,
                difference=dscr - covenant,
                variance_pct=0,
                details=details,
                severity="critical",
                formula="DSCR = Annualized NOI / Annual Debt Service",
                intermediate_calculations={
                    "noi_period": noi,
                    "window_months": ctx.window_months,
                    "annualized_noi": annualized_noi,
                    "monthly_payment": monthly_payment,
                    "annual_debt_service": annual_debt_service,
                    "covenant": covenant,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_45_minimum_liquidity(self):
        """AUDIT-45: Minimum liquidity based on months of debt service coverage."""
        ctx = self._get_alignment_context()

        total_cash = self._get_bs_total_cash(self.period_id)
        monthly_payment = self._get_mst_value("total_payment_due")
        if abs(monthly_payment) <= 0.01:
            return

        coverage_months = total_cash / monthly_payment if monthly_payment else 0.0
        required_months = 1.0
        status = "PASS" if coverage_months >= required_months else "WARNING"

        details = (
            f"Cash ${total_cash:,.2f} covers {coverage_months:.2f} months "
            f"of debt service (required {required_months:.2f})"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-45",
                rule_name="Minimum Liquidity",
                category="Audit",
                status=status,
                source_value=coverage_months,
                target_value=required_months,
                difference=coverage_months - required_months,
                variance_pct=0,
                details=details,
                severity="high",
                formula="Liquidity Months = Total Cash / Monthly Debt Service",
                intermediate_calculations={
                    "total_cash": total_cash,
                    "monthly_payment": monthly_payment,
                    "coverage_months": coverage_months,
                    "required_months": required_months,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_46_escrow_funding_requirements(self):
        """AUDIT-46: Escrow balances should cover upcoming escrow dues."""
        ctx = self._get_alignment_context()

        configs = [
            {
                "suffix": "TAX",
                "balance_col": "tax_escrow_balance",
                "due_col": "tax_escrow_due",
            },
            {
                "suffix": "INSURANCE",
                "balance_col": "insurance_escrow_balance",
                "due_col": "insurance_escrow_due",
            },
            {
                "suffix": "RESERVE",
                "balance_col": "reserve_balance",
                "due_col": "reserve_due",
            },
        ]

        for cfg in configs:
            balance = self._get_mst_value(cfg["balance_col"])
            due = self._get_mst_value(cfg["due_col"])

            if abs(balance) <= 0.01 and abs(due) <= 0.01:
                status = "SKIP"
                coverage = 0.0
                diff = 0.0
            else:
                coverage = balance / due if due else float("inf")
                diff = balance - due
                status = "PASS" if diff >= -1.0 else "WARNING"

            details = f"Balance ${balance:,.2f} vs due ${due:,.2f}"

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-46-{cfg['suffix']}",
                    rule_name=f"Escrow Funding Requirement ({cfg['suffix']})",
                    category="Audit",
                    status=status,
                    source_value=balance,
                    target_value=due,
                    difference=diff,
                    variance_pct=0,
                    details=details,
                    severity="medium",
                    formula="Escrow balance should cover upcoming due amount",
                    intermediate_calculations={
                        "balance": balance,
                        "due": due,
                        "coverage": coverage,
                        "alignment": ctx.to_dict(),
                    },
                )
            )

    def _rule_audit_28_constant_accounts_validation(self):
        """AUDIT-28: Accounts designated as constant should not change."""
        baseline_period_id = self._get_earliest_period_id()
        if not baseline_period_id:
            return

        ctx = self._get_alignment_context()

        configs = [
            {
                "suffix": "CASH-OPERATING",
                "patterns": ["%CASH%OPERATING%"],
            },
            {
                "suffix": "LAND",
                "patterns": ["%LAND%"],
            },
            {
                "suffix": "BUILDINGS",
                "patterns": ["%BUILDINGS%"],
            },
            {
                "suffix": "DEPOSITS",
                "patterns": ["%DEPOSIT%"],
            },
            {
                "suffix": "LOAN-COSTS",
                "patterns": ["%LOAN%COST%"],
            },
            {
                "suffix": "PARTNERS-CONTRIBUTION",
                "patterns": ["%PARTNER%CONTRIBUT%"],
            },
            {
                "suffix": "BEGINNING-EQUITY",
                "patterns": ["%BEGINNING%EQUITY%", "%RETAINED EARNINGS%"],
            },
        ]

        failures = 0
        for cfg in configs:
            baseline_value = self._sum_bs_accounts(cfg["patterns"], baseline_period_id)
            current_value = self._sum_bs_accounts(cfg["patterns"], self.period_id)

            if abs(baseline_value) <= 0.01 and abs(current_value) <= 0.01:
                status = "SKIP"
                diff = 0.0
                tolerance = 0.0
            else:
                diff = current_value - baseline_value
                tolerance = max(1.0, abs(baseline_value) * 0.001)
                status = "PASS" if abs(diff) <= tolerance else "WARNING"
                if status != "PASS":
                    failures += 1

            details = (
                f"Baseline ${baseline_value:,.2f} (period {baseline_period_id}) vs "
                f"current ${current_value:,.2f}"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-28-{cfg['suffix']}",
                    rule_name=f"Constant Account Validation ({cfg['suffix']})",
                    category="Audit",
                    status=status,
                    source_value=current_value,
                    target_value=baseline_value,
                    difference=diff,
                    variance_pct=0,
                    details=details,
                    severity="high",
                    formula="Constant accounts should not change from baseline",
                    intermediate_calculations={
                        "baseline_period_id": baseline_period_id,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "tolerance": tolerance,
                        "patterns": cfg["patterns"],
                        "alignment": ctx.to_dict(),
                    },
                )
            )

        summary_status = "PASS" if failures == 0 else "WARNING"
        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-28",
                rule_name="Constant Accounts Summary",
                category="Audit",
                status=summary_status,
                source_value=float(failures),
                target_value=0.0,
                difference=float(failures),
                variance_pct=0,
                details=f"{failures} constant account check(s) outside tolerance",
                severity="high",
                formula="All constant accounts should remain unchanged",
                intermediate_calculations={
                    "baseline_period_id": baseline_period_id,
                    "failure_count": failures,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_33_occupancy_percentage(self):
        """AUDIT-33: Occupancy percentage calculation from rent roll."""
        ctx = self._get_alignment_context()

        row = self.db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(unit_area_sqft), 0) AS total_sqft,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN occupancy_status ILIKE 'vacant' THEN 0
                                ELSE unit_area_sqft
                            END
                        ),
                        0
                    ) AS occupied_sqft,
                    COUNT(*) AS unit_count
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (is_gross_rent_row IS NOT TRUE)
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()

        total_sqft = float(row[0] or 0.0) if row else 0.0
        occupied_sqft = float(row[1] or 0.0) if row else 0.0
        unit_count = int(row[2] or 0) if row else 0

        if total_sqft <= 0.01 or unit_count == 0:
            self.results.append(
                ReconciliationResult(
                    rule_id="AUDIT-33",
                    rule_name="Occupancy Percentage",
                    category="Audit",
                    status="SKIP",
                    source_value=0,
                    target_value=0,
                    difference=0,
                    variance_pct=0,
                    details="No rent roll area data available for occupancy calculation",
                    severity="medium",
                    intermediate_calculations={"alignment": ctx.to_dict()},
                )
            )
            return

        occupancy_pct = (occupied_sqft / total_sqft) * 100.0 if total_sqft else 0.0
        metrics_occ = self._get_financial_metric("occupancy_rate")

        if metrics_occ > 0.01:
            diff = metrics_occ - occupancy_pct
            tolerance = 0.5
            status = "PASS" if abs(diff) <= tolerance else "WARNING"
            target_value = metrics_occ
            details = (
                f"Calculated {occupancy_pct:.2f}% vs metrics {metrics_occ:.2f}% "
                f"(occupied {occupied_sqft:,.0f} / total {total_sqft:,.0f} sqft)"
            )
        else:
            diff = 0.0
            tolerance = 0.0
            status = "PASS"
            target_value = occupancy_pct
            details = (
                f"Calculated occupancy {occupancy_pct:.2f}% "
                f"(occupied {occupied_sqft:,.0f} / total {total_sqft:,.0f} sqft)"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-33",
                rule_name="Occupancy Percentage",
                category="Audit",
                status=status,
                source_value=occupancy_pct,
                target_value=target_value,
                difference=diff,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="Occupancy % = Occupied SqFt / Total SqFt",
                intermediate_calculations={
                    "total_sqft": total_sqft,
                    "occupied_sqft": occupied_sqft,
                    "unit_count": unit_count,
                    "occupancy_pct": occupancy_pct,
                    "metrics_occupancy_pct": metrics_occ,
                    "tolerance": tolerance,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_40_completeness_validation(self):
        """AUDIT-40: Ensure expected documents/data exist for the period."""
        ctx = self._get_alignment_context()

        configs = [
            {
                "doc_type": "balance_sheet",
                "table": "balance_sheet_data",
                "critical": True,
            },
            {
                "doc_type": "income_statement",
                "table": "income_statement_data",
                "critical": True,
            },
            {
                "doc_type": "cash_flow",
                "table": "cash_flow_data",
                "critical": True,
            },
            {
                "doc_type": "rent_roll",
                "table": "rent_roll_data",
                "critical": False,
            },
            {
                "doc_type": "mortgage_statement",
                "table": "mortgage_statement_data",
                "critical": False,
            },
        ]

        missing_critical = 0
        results_summary = []

        for cfg in configs:
            upload_count = self.db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM document_uploads
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND document_type = :doc_type
                      AND is_active IS TRUE
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "doc_type": cfg["doc_type"],
                },
            ).scalar()
            upload_count = int(upload_count or 0)

            data_count = self.db.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM {cfg['table']}
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                },
            ).scalar()
            data_count = int(data_count or 0)

            has_data = upload_count > 0 and data_count > 0
            if has_data:
                status = "PASS"
            elif cfg["critical"]:
                status = "FAIL"
                missing_critical += 1
            else:
                status = "WARNING"

            details = (
                f"Uploads {upload_count}, data rows {data_count} "
                f"for {cfg['doc_type']}"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-40-{cfg['doc_type']}",
                    rule_name=f"Completeness ({cfg['doc_type']})",
                    category="Audit",
                    status=status,
                    source_value=float(data_count),
                    target_value=1.0,
                    difference=float(data_count - 1),
                    variance_pct=0,
                    details=details,
                    severity="high" if cfg["critical"] else "medium",
                    formula="Expected uploads and extracted data should be present",
                    intermediate_calculations={
                        "doc_type": cfg["doc_type"],
                        "upload_count": upload_count,
                        "data_count": data_count,
                        "critical": cfg["critical"],
                        "alignment": ctx.to_dict(),
                    },
                )
            )

            results_summary.append(
                {
                    "doc_type": cfg["doc_type"],
                    "upload_count": upload_count,
                    "data_count": data_count,
                    "status": status,
                }
            )

        summary_status = "PASS" if missing_critical == 0 else "FAIL"
        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-40",
                rule_name="Completeness Validation Summary",
                category="Audit",
                status=summary_status,
                source_value=float(missing_critical),
                target_value=0.0,
                difference=float(missing_critical),
                variance_pct=0,
                details=f"{missing_critical} critical document type(s) missing data",
                severity="high",
                formula="All critical statements should be present and extracted",
                intermediate_calculations={
                    "missing_critical": missing_critical,
                    "results": results_summary,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_44_ltv_ratio(self):
        """AUDIT-44: Loan-to-Value (LTV) covenant proxy check."""
        ctx = self._get_alignment_context()

        ltv_ratio = self._get_financial_metric("ltv_ratio")
        basis = "financial_metrics_ltv_ratio"

        if ltv_ratio <= 0.0:
            loan_balance = self._get_mst_value("principal_balance")
            if loan_balance <= 0.01:
                loan_balance = self._get_bs_value(account_name_pattern="%Wells%Fargo%")

            property_value = self._get_financial_metric("net_property_value")
            if property_value <= 0.01:
                property_value = self._get_financial_metric("total_assets")
            if property_value <= 0.01:
                property_value = self._get_bs_value(account_name_pattern="%TOTAL ASSETS%")

            if property_value <= 0.01 or loan_balance <= 0.01:
                self.results.append(
                    ReconciliationResult(
                        rule_id="AUDIT-44",
                        rule_name="Loan-to-Value (LTV)",
                        category="Audit",
                        status="SKIP",
                        source_value=0,
                        target_value=0,
                        difference=0,
                        variance_pct=0,
                        details="Insufficient loan balance or property value for LTV",
                        severity="high",
                        intermediate_calculations={"alignment": ctx.to_dict()},
                    )
                )
                return

            ltv_ratio = loan_balance / property_value
            basis = "loan_balance_div_property_value"
        else:
            loan_balance = self._get_financial_metric("total_mortgage_debt") or self._get_mst_value(
                "principal_balance"
            )
            property_value = self._get_financial_metric("net_property_value") or self._get_financial_metric(
                "total_assets"
            )

        covenant = 0.75
        if ltv_ratio <= covenant:
            status = "PASS"
        elif ltv_ratio <= 0.80:
            status = "WARNING"
        else:
            status = "FAIL"

        details = (
            f"LTV {ltv_ratio * 100:.2f}% (loan ${loan_balance:,.2f} / "
            f"value ${property_value:,.2f}, covenant {covenant * 100:.0f}%)"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-44",
                rule_name="Loan-to-Value (LTV)",
                category="Audit",
                status=status,
                source_value=ltv_ratio,
                target_value=covenant,
                difference=ltv_ratio - covenant,
                variance_pct=0,
                details=details,
                severity="high",
                formula="LTV = Loan Balance / Property Value",
                intermediate_calculations={
                    "ltv_ratio": ltv_ratio,
                    "loan_balance": loan_balance,
                    "property_value": property_value,
                    "covenant": covenant,
                    "basis": basis,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_48_variance_investigation_triggers(self):
        """AUDIT-48: Trigger variance investigations for large swings."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        total_assets_curr = self._get_bs_value(account_name_pattern="%TOTAL ASSETS%")
        total_assets_prior = self._get_bs_value(
            account_name_pattern="%TOTAL ASSETS%", period_id=prior_id
        )
        assets_change_pct = (
            ((total_assets_curr - total_assets_prior) / total_assets_prior) * 100.0
            if abs(total_assets_prior) > 0.01
            else 0.0
        )

        revenue_curr = self._get_is_value_for_period("%TOTAL INCOME%", self.period_id)
        revenue_prior = self._get_is_value_for_period("%TOTAL INCOME%", prior_id)
        revenue_change_pct = (
            ((revenue_curr - revenue_prior) / revenue_prior) * 100.0
            if abs(revenue_prior) > 0.01
            else 0.0
        )

        cash_curr = self._get_bs_total_cash(self.period_id)
        cash_prior = self._get_bs_total_cash(prior_id)
        cash_change_pct = (
            ((cash_curr - cash_prior) / cash_prior) * 100.0 if abs(cash_prior) > 0.01 else 0.0
        )

        op_curr, op_basis_curr = self._sum_cf_operating_total(self.period_id)
        op_prior, op_basis_prior = self._sum_cf_operating_total(prior_id)

        distributions_cf = self._sum_cf_accounts(["%DISTRIBUT%"])

        triggers = []
        if abs(assets_change_pct) > 5.0:
            triggers.append(f"Total assets change {assets_change_pct:.1f}% (>5%)")
        if revenue_prior > 0.01 and revenue_change_pct < -10.0:
            triggers.append(f"Revenue change {revenue_change_pct:.1f}% (<-10%)")
        if cash_prior > 0.01 and cash_change_pct < -30.0:
            triggers.append(f"Cash change {cash_change_pct:.1f}% (<-30%)")
        if op_curr < 0 and op_prior < 0:
            triggers.append("Operating cash flow negative for 2 consecutive periods")
        if op_curr < 0 and distributions_cf < 0:
            triggers.append("Distributions made while operating cash flow is negative")

        status = "PASS" if not triggers else "WARNING"
        details = (
            "No variance investigation triggers detected"
            if not triggers
            else "; ".join(triggers)
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-48",
                rule_name="Variance Investigation Triggers",
                category="Audit",
                status=status,
                source_value=float(len(triggers)),
                target_value=0.0,
                difference=float(len(triggers)),
                variance_pct=0,
                details=details,
                severity="medium",
                formula="Trigger investigation on large period-over-period swings",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "total_assets_curr": total_assets_curr,
                    "total_assets_prior": total_assets_prior,
                    "assets_change_pct": assets_change_pct,
                    "revenue_curr": revenue_curr,
                    "revenue_prior": revenue_prior,
                    "revenue_change_pct": revenue_change_pct,
                    "cash_curr": cash_curr,
                    "cash_prior": cash_prior,
                    "cash_change_pct": cash_change_pct,
                    "operating_curr": op_curr,
                    "operating_prior": op_prior,
                    "operating_basis_curr": op_basis_curr,
                    "operating_basis_prior": op_basis_prior,
                    "distributions_cf": distributions_cf,
                    "triggers": triggers,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_29_predictable_monthly_changes(self):
        """AUDIT-29: Validate predictable monthly escrow funding patterns."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        configs = [
            {
                "suffix": "TAX",
                "bs_patterns": ["%ESCROW%PROPERTY%TAX%", "%ESCROW%TAX%"],
                "due_col": "tax_escrow_due",
                "ytd_disb_col": "ytd_taxes_disbursed",
            },
            {
                "suffix": "INSURANCE",
                "bs_patterns": ["%ESCROW%INSURANCE%"],
                "due_col": "insurance_escrow_due",
                "ytd_disb_col": "ytd_insurance_disbursed",
            },
            {
                "suffix": "RESERVE",
                "bs_patterns": ["%ESCROW%TI%LC%", "%ESCROW%RESERVE%"],
                "due_col": "reserve_due",
                "ytd_disb_col": "ytd_reserve_disbursed",
            },
        ]

        failures = 0
        for cfg in configs:
            bs_prior = self._sum_bs_accounts(cfg["bs_patterns"], prior_id)
            bs_curr = self._sum_bs_accounts(cfg["bs_patterns"], self.period_id)
            bs_delta = bs_curr - bs_prior

            due = self._get_mst_value(cfg["due_col"])
            ytd_prior = self._get_mst_value(cfg["ytd_disb_col"], period_id=prior_id)
            ytd_curr = self._get_mst_value(cfg["ytd_disb_col"])
            disb_delta = ytd_curr - ytd_prior
            if disb_delta < 0:
                disb_delta = ytd_curr

            expected_delta = due - disb_delta
            diff = bs_delta - expected_delta

            no_activity = (
                abs(bs_delta) <= 0.01 and abs(due) <= 0.01 and abs(disb_delta) <= 0.01
            )
            if no_activity:
                status = "SKIP"
                tolerance = 0.0
            else:
                scale = max(abs(expected_delta), abs(bs_delta), abs(due), abs(disb_delta), 1.0)
                tolerance = max(500.0, scale * 0.20)
                status = "PASS" if abs(diff) <= tolerance else "WARNING"
                if status != "PASS":
                    failures += 1

            details = (
                f"BS Δ ${bs_delta:,.2f} vs expected ${expected_delta:,.2f} "
                f"(due ${due:,.2f}, disb ${disb_delta:,.2f})"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-29-{cfg['suffix']}",
                    rule_name=f"Predictable Escrow Funding ({cfg['suffix']})",
                    category="Audit",
                    status=status,
                    source_value=bs_delta,
                    target_value=expected_delta,
                    difference=diff,
                    variance_pct=0,
                    details=details,
                    severity="medium",
                    formula="Escrow Δ ≈ Due - Disbursements (monthly)",
                    intermediate_calculations={
                        "prior_id": prior_id,
                        "bs_prior": bs_prior,
                        "bs_curr": bs_curr,
                        "bs_delta": bs_delta,
                        "due": due,
                        "ytd_prior": ytd_prior,
                        "ytd_curr": ytd_curr,
                        "disb_delta": disb_delta,
                        "expected_delta": expected_delta,
                        "tolerance": tolerance,
                        "alignment": ctx.to_dict(),
                    },
                )
            )

        summary_status = "PASS" if failures == 0 else "WARNING"
        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-29",
                rule_name="Predictable Monthly Changes Summary",
                category="Audit",
                status=summary_status,
                source_value=float(failures),
                target_value=0.0,
                difference=float(failures),
                variance_pct=0,
                details=f"{failures} predictable-change check(s) outside tolerance",
                severity="medium",
                formula="Escrow funding patterns should be consistent month to month",
                intermediate_calculations={"prior_id": prior_id, "failures": failures},
            )
        )

    def _rule_audit_38_magnitude_reasonability_checks(self):
        """AUDIT-38: Magnitude reasonability checks for large swings."""
        prior_id = self._get_prior_period_id()
        if not prior_id:
            return

        ctx = self._get_alignment_context()

        total_assets_curr = self._get_bs_value(account_name_pattern="%TOTAL ASSETS%")
        total_assets_prior = self._get_bs_value(
            account_name_pattern="%TOTAL ASSETS%", period_id=prior_id
        )
        assets_change_pct = (
            ((total_assets_curr - total_assets_prior) / total_assets_prior) * 100.0
            if abs(total_assets_prior) > 0.01
            else 0.0
        )

        revenue_curr = self._get_is_value_for_period("%TOTAL INCOME%", self.period_id)
        revenue_prior = self._get_is_value_for_period("%TOTAL INCOME%", prior_id)
        revenue_change_pct = (
            ((revenue_curr - revenue_prior) / revenue_prior) * 100.0
            if abs(revenue_prior) > 0.01
            else 0.0
        )

        total_cash = self._get_bs_total_cash(self.period_id)
        monthly_payment = self._get_mst_value("total_payment_due")
        cash_vs_debt_service = total_cash - monthly_payment

        triggers = []
        if abs(assets_change_pct) > 10.0:
            triggers.append(f"Total assets change {assets_change_pct:.1f}% (>10%)")
        if abs(revenue_prior) > 0.01 and abs(revenue_change_pct) > 20.0:
            triggers.append(f"Revenue change {revenue_change_pct:.1f}% (>20%)")
        if abs(monthly_payment) > 0.01 and cash_vs_debt_service < 0:
            triggers.append("Total cash below one month of debt service")

        status = "PASS" if not triggers else "WARNING"
        details = "No magnitude reasonability triggers detected" if not triggers else "; ".join(triggers)

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-38",
                rule_name="Magnitude Reasonability Checks",
                category="Audit",
                status=status,
                source_value=float(len(triggers)),
                target_value=0.0,
                difference=float(len(triggers)),
                variance_pct=0,
                details=details,
                severity="medium",
                formula="Flag unusually large swings in key balances and revenue",
                intermediate_calculations={
                    "prior_id": prior_id,
                    "total_assets_curr": total_assets_curr,
                    "total_assets_prior": total_assets_prior,
                    "assets_change_pct": assets_change_pct,
                    "revenue_curr": revenue_curr,
                    "revenue_prior": revenue_prior,
                    "revenue_change_pct": revenue_change_pct,
                    "total_cash": total_cash,
                    "monthly_payment": monthly_payment,
                    "cash_vs_debt_service": cash_vs_debt_service,
                    "triggers": triggers,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_39_related_account_validations(self):
        """AUDIT-39: Validate key related account balances across documents."""
        ctx = self._get_alignment_context()

        bs_cash = self._get_bs_total_cash(self.period_id)
        cf_cash = ctx.cf_ending_cash or self._get_cf_value(account_name_pattern="%ENDING%CASH%")
        cash_diff = bs_cash - cf_cash

        bs_wells = self._get_bs_value(account_name_pattern="%Wells%Fargo%")
        ms_principal = self._get_mst_value("principal_balance")
        wells_diff = bs_wells - ms_principal

        bs_tax = self._sum_bs_accounts(["%ESCROW%TAX%"], self.period_id)
        bs_insurance = self._sum_bs_accounts(["%ESCROW%INSURANCE%"], self.period_id)
        bs_reserve = self._sum_bs_accounts(["%ESCROW%TI%LC%", "%ESCROW%RESERVE%"], self.period_id)
        bs_escrow_total = bs_tax + bs_insurance + bs_reserve
        ms_escrow_total = (
            self._get_mst_value("tax_escrow_balance")
            + self._get_mst_value("insurance_escrow_balance")
            + self._get_mst_value("reserve_balance")
        )
        escrow_diff = bs_escrow_total - ms_escrow_total

        tolerance_cash = 1.0
        tolerance_wells = 1.0
        tolerance_escrow = 10.0

        failures = 0
        if abs(cash_diff) > tolerance_cash:
            failures += 1
        if abs(wells_diff) > tolerance_wells:
            failures += 1
        if abs(escrow_diff) > tolerance_escrow:
            failures += 1

        status = "PASS" if failures == 0 else "WARNING"
        details = (
            f"Cash Δ ${cash_diff:,.2f}; Wells Δ ${wells_diff:,.2f}; "
            f"Escrow Δ ${escrow_diff:,.2f}"
        )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-39",
                rule_name="Related Account Validations",
                category="Audit",
                status=status,
                source_value=float(failures),
                target_value=0.0,
                difference=float(failures),
                variance_pct=0,
                details=details,
                severity="high",
                formula="Key related balances should align across statements",
                intermediate_calculations={
                    "bs_cash": bs_cash,
                    "cf_cash": cf_cash,
                    "cash_diff": cash_diff,
                    "bs_wells": bs_wells,
                    "ms_principal": ms_principal,
                    "wells_diff": wells_diff,
                    "bs_tax_escrow": bs_tax,
                    "bs_insurance_escrow": bs_insurance,
                    "bs_reserve_escrow": bs_reserve,
                    "bs_escrow_total": bs_escrow_total,
                    "ms_escrow_total": ms_escrow_total,
                    "escrow_diff": escrow_diff,
                    "tolerances": {
                        "cash": tolerance_cash,
                        "wells": tolerance_wells,
                        "escrow": tolerance_escrow,
                    },
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_41_timing_difference_signals(self):
        """AUDIT-41: Detect likely timing differences around large disbursements."""
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return

        ctx = self._get_alignment_context()

        tax_disb_window = self._get_ytd_delta("ytd_taxes_disbursed", begin_period_id)
        tax_payable_begin = self._sum_bs_accounts(["%PROPERTY%TAX%PAYABLE%"], begin_period_id)
        tax_payable_end = self._sum_bs_accounts(["%PROPERTY%TAX%PAYABLE%"], self.period_id)
        tax_payable_delta = tax_payable_end - tax_payable_begin

        threshold = 1000.0
        payable_small = abs(tax_payable_delta) <= max(500.0, abs(tax_disb_window) * 0.05)

        if tax_disb_window > threshold and payable_small:
            status = "WARNING"
            details = (
                f"Tax disbursement ${tax_disb_window:,.2f} detected but tax payable "
                f"changed only ${tax_payable_delta:,.2f} (possible timing difference)"
            )
        else:
            status = "PASS"
            details = (
                f"Tax disbursement ${tax_disb_window:,.2f}, tax payable Δ ${tax_payable_delta:,.2f}"
            )

        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-41",
                rule_name="Timing Difference Signals",
                category="Audit",
                status=status,
                source_value=tax_disb_window,
                target_value=tax_payable_delta,
                difference=tax_disb_window - tax_payable_delta,
                variance_pct=0,
                details=details,
                severity="medium",
                formula="Large disbursements with minimal payable movement suggest timing differences",
                intermediate_calculations={
                    "begin_period_id": begin_period_id,
                    "tax_disb_window": tax_disb_window,
                    "tax_payable_begin": tax_payable_begin,
                    "tax_payable_end": tax_payable_end,
                    "tax_payable_delta": tax_payable_delta,
                    "threshold": threshold,
                    "alignment": ctx.to_dict(),
                },
            )
        )

    def _rule_audit_42_period_cutoff_consistency(self):
        """AUDIT-42: Verify statement cutoff dates align to the reporting period."""
        ctx = self._get_alignment_context()

        period_row = self.db.execute(
            text(
                """
                SELECT period_end_date
                FROM financial_periods
                WHERE id = :period_id AND property_id = :property_id
                LIMIT 1
                """
            ),
            {"period_id": int(self.period_id), "property_id": int(self.property_id)},
        ).fetchone()
        period_end = period_row[0] if period_row and period_row[0] else None
        if not period_end:
            return

        checks = [
            ("IS", "income_statement_headers"),
            ("CF", "cash_flow_headers"),
        ]

        failures = 0
        for suffix, table in checks:
            report_end = self._get_report_period_end(table)
            if not report_end:
                status = "SKIP"
                days_diff = 0
            else:
                days_diff = abs((period_end - report_end).days)
                status = "PASS" if days_diff <= 45 else "WARNING"
                if status != "PASS":
                    failures += 1

            details = (
                f"Period end {period_end} vs {suffix} report end {report_end} (Δ {days_diff} days)"
            )

            self.results.append(
                ReconciliationResult(
                    rule_id=f"AUDIT-42-{suffix}",
                    rule_name=f"Period Cutoff Consistency ({suffix})",
                    category="Audit",
                    status=status,
                    source_value=float(days_diff),
                    target_value=45.0,
                    difference=float(days_diff - 45.0),
                    variance_pct=0,
                    details=details,
                    severity="medium",
                    formula="Report cutoff dates should align with the reporting period end",
                    intermediate_calculations={
                        "period_end": str(period_end),
                        "report_end": str(report_end) if report_end else None,
                        "days_diff": days_diff,
                        "alignment": ctx.to_dict(),
                    },
                )
            )

        summary_status = "PASS" if failures == 0 else "WARNING"
        self.results.append(
            ReconciliationResult(
                rule_id="AUDIT-42",
                rule_name="Period Cutoff Consistency Summary",
                category="Audit",
                status=summary_status,
                source_value=float(failures),
                target_value=0.0,
                difference=float(failures),
                variance_pct=0,
                details=f"{failures} cutoff consistency check(s) outside tolerance",
                severity="medium",
                formula="Statement cutoff dates should align with the reporting period",
                intermediate_calculations={"failures": failures, "alignment": ctx.to_dict()},
            )
        )
