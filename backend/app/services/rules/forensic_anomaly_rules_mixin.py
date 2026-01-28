from collections import Counter
from sqlalchemy import text

from app.services.reconciliation_types import ReconciliationResult


class ForensicAnomalyRulesMixin:
    """
    Forensic anomaly detection rules.
    Source: forensic_anomaly_rules.md
    """

    def _execute_forensic_anomaly_rules(self):
        self._rule_fa_1_cash_flow_internal_consistency()
        self._rule_fa_2_working_capital_sign_test()
        self._rule_fa_3_non_cash_journal_detector()
        self._rule_fa_4_duplicate_round_numbers()
        self._rule_fa_5_benford_screen()
        self._rule_fa_6_tenant_concentration_sanity()
        self._rule_fa_7_accrual_reversals()

        # Enhanced forensic rules from FORENSIC_ACCOUNTING_RULES_ENHANCED.md
        self._rule_fa_wc_1_working_capital_attribution()
        self._rule_fa_mort_1_payment_history_continuity()
        self._rule_fa_mort_2_escrow_balance_reasonableness()
        self._rule_fa_rr_1_lease_term_consistency()

    def _add_result(self, **kwargs):
        self.results.append(ReconciliationResult(**kwargs))

    def _rule_fa_1_cash_flow_internal_consistency(self):
        begin_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(beginning_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        end_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(ending_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        net_cf = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(net_cash_flow), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        expected_end = float(begin_cash) + float(net_cf)
        diff = float(end_cash) - expected_end
        status = "PASS" if abs(diff) <= 1.0 else "FAIL"
        self._add_result(
            rule_id="FA-1",
            rule_name="Cash Flow Internal Consistency",
            category="Forensic",
            status=status,
            source_value=float(end_cash),
            target_value=float(expected_end),
            difference=float(diff),
            variance_pct=0.0,
            details=f"Ending cash ${end_cash:,.2f} vs expected ${expected_end:,.2f}",
            severity="critical" if status == "FAIL" else "info",
            formula="Ending Cash = Beginning Cash + Net Cash Flow",
        )

    def _rule_fa_2_working_capital_sign_test(self):
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not prior_id:
            self._add_result(
                rule_id="FA-2",
                rule_name="Working Capital Sign Test",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable",
                severity="high",
                formula="WC changes should match CF adjustment sign",
            )
            return
        mappings = [
            {
                "name": "Accounts Receivable",
                "bs_pattern": "%A/R%",
                "cf_pattern": "%ACCOUNTS RECEIVABLE%",
                "asset": True,
            },
            {
                "name": "Prepaid Expenses",
                "bs_pattern": "%PREPAID%",
                "cf_pattern": "%PREPAID%",
                "asset": True,
            },
            {
                "name": "Accounts Payable",
                "bs_pattern": "%ACCOUNTS PAYABLE%",
                "cf_pattern": "%ACCOUNTS PAYABLE%",
                "asset": False,
            },
            {
                "name": "Accrued Expenses",
                "bs_pattern": "%ACCRUED%",
                "cf_pattern": "%ACCRUED%",
                "asset": False,
            },
            {
                "name": "Rent Received in Advance",
                "bs_pattern": "%RENT RECEIVED%",
                "cf_pattern": "%RENT RECEIVED%",
                "asset": False,
            },
        ]
        failures = []
        for mapping in mappings:
            curr = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "pattern": mapping["bs_pattern"],
                },
            ).scalar() or 0.0
            prior = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(prior_id),
                    "pattern": mapping["bs_pattern"],
                },
            ).scalar() or 0.0
            delta = float(curr) - float(prior)
            cf_adj = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(period_amount), 0)
                    FROM cash_flow_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "pattern": mapping["cf_pattern"],
                },
            ).scalar() or 0.0
            expected_sign = -1 if mapping["asset"] else 1
            if delta == 0 or cf_adj == 0:
                continue
            sign_ok = (delta * expected_sign) * cf_adj >= 0
            if not sign_ok:
                failures.append(mapping["name"])
        status = "PASS" if not failures else "FAIL"
        self._add_result(
            rule_id="FA-2",
            rule_name="Working Capital Sign Test",
            category="Forensic",
            status=status,
            source_value=float(len(failures)),
            target_value=0.0,
            difference=float(len(failures)),
            variance_pct=0.0,
            details="Sign mismatches: " + (", ".join(failures) if failures else "None"),
            severity="high" if status == "FAIL" else "info",
            formula="BS delta sign should match CF adjustment sign",
        )

    def _rule_fa_3_non_cash_journal_detector(self):
        begin_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(beginning_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        end_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(ending_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        net_cf = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(net_cash_flow), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        expected_end = float(begin_cash) + float(net_cf)
        variance = float(end_cash) - expected_end
        if abs(variance) <= 1.0:
            self._add_result(
                rule_id="FA-3",
                rule_name="Non-Cash Journal Entry Detector",
                category="Forensic",
                status="PASS",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No significant cash variance detected",
                severity="high",
                formula="Variance matched to BS account changes",
            )
            return
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        matches = self.db.execute(
            text(
                """
                SELECT account_name, amount
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND ABS(amount - :variance) <= 1.0
                LIMIT 5
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(self.period_id),
                "variance": float(variance),
            },
        ).fetchall()
        delta_matches = []
        if prior_id:
            delta_matches = self.db.execute(
                text(
                    """
                    SELECT curr.account_name, (curr.amount - prior.amount) AS delta
                    FROM balance_sheet_data curr
                    JOIN balance_sheet_data prior
                      ON curr.account_code = prior.account_code
                     AND curr.property_id = prior.property_id
                     AND prior.period_id = :prior_id
                    WHERE curr.property_id = :property_id
                      AND curr.period_id = :period_id
                      AND ABS((curr.amount - prior.amount) - :variance) <= 1.0
                    LIMIT 5
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "prior_id": int(prior_id),
                    "variance": float(variance),
                },
            ).fetchall()
        details = (
            f"Variance ${variance:,.2f} matches BS accounts: "
            + ", ".join(f"{row[0]} (${row[1]:,.2f})" for row in matches)
            if matches
            else f"Variance ${variance:,.2f} with no matching BS accounts"
        )
        if delta_matches:
            details += "; Delta matches: " + ", ".join(
                f"{row[0]} (Δ ${row[1]:,.2f})" for row in delta_matches
            )
        self._add_result(
            rule_id="FA-3",
            rule_name="Non-Cash Journal Entry Detector",
            category="Forensic",
            status="FAIL",
            source_value=float(variance),
            target_value=0.0,
            difference=float(variance),
            variance_pct=0.0,
            details=details,
            severity="high",
            formula="Detect BS accounts matching cash variance",
        )

    def _rule_fa_4_duplicate_round_numbers(self):
        try:
            gl_rows = self.db.execute(
                text(
                    """
                    SELECT amount
                    FROM general_ledger_entries
                    WHERE property_id = :property_id AND period_id = :period_id
                    """
                ),
                {"property_id": int(self.property_id), "period_id": int(self.period_id)},
            ).fetchall()
        except Exception:
            gl_rows = []
        data_source = "GL"
        if gl_rows:
            amounts = [round(abs(float(r[0] or 0.0)), 2) for r in gl_rows if r[0] is not None]
        else:
            rows = self.db.execute(
                text(
                    """
                    SELECT account_name, period_amount
                    FROM income_statement_data
                    WHERE property_id = :property_id AND period_id = :period_id
                    UNION ALL
                    SELECT account_name, period_amount
                    FROM cash_flow_data
                    WHERE property_id = :property_id AND period_id = :period_id
                    """
                ),
                {"property_id": int(self.property_id), "period_id": int(self.period_id)},
            ).fetchall()
            amounts = [round(abs(float(r[1] or 0.0)), 2) for r in rows if r[1] is not None]
            data_source = "IS/CF"
        round_amounts = [amt for amt in amounts if abs(amt) >= 1000 and str(amt).endswith(".00")]
        counts = Counter(round_amounts)
        repeated = {amt: cnt for amt, cnt in counts.items() if cnt >= 3}
        status = "FAIL" if repeated else "PASS"
        detail = (
            f"No repeated round amounts (source={data_source})"
            if not repeated
            else f"Repeated amounts (source={data_source}): {repeated}"
        )
        self._add_result(
            rule_id="FA-4",
            rule_name="Duplicate Round-Number Patterns",
            category="Forensic",
            status=status,
            source_value=float(len(repeated)),
            target_value=0.0,
            difference=float(len(repeated)),
            variance_pct=0.0,
            details=detail,
            severity="medium" if status == "FAIL" else "info",
            formula="Detect repeated round-number postings",
        )

    def _rule_fa_5_benford_screen(self):
        try:
            gl_rows = self.db.execute(
                text(
                    """
                    SELECT amount
                    FROM general_ledger_entries
                    WHERE property_id = :property_id AND period_id = :period_id
                    """
                ),
                {"property_id": int(self.property_id), "period_id": int(self.period_id)},
            ).fetchall()
        except Exception:
            gl_rows = []
        data_source = "GL"
        if gl_rows:
            values = [abs(float(r[0])) for r in gl_rows if r[0] is not None and abs(float(r[0])) >= 100]
        else:
            rows = self.db.execute(
                text(
                    """
                    SELECT period_amount
                    FROM income_statement_data
                    WHERE property_id = :property_id AND period_id = :period_id
                    UNION ALL
                    SELECT period_amount
                    FROM cash_flow_data
                    WHERE property_id = :property_id AND period_id = :period_id
                    """
                ),
                {"property_id": int(self.property_id), "period_id": int(self.period_id)},
            ).fetchall()
            values = [abs(float(r[0])) for r in rows if r[0] is not None and abs(float(r[0])) >= 100]
            data_source = "IS/CF"
        if len(values) < 30:
            self._add_result(
                rule_id="FA-5",
                rule_name="Benford's Law Screen",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details=f"Insufficient line items for Benford analysis (source={data_source})",
                severity="low",
                formula="Benford deviation screen",
            )
            return
        first_digits = [int(str(v)[0]) for v in values if v > 0]
        counts = Counter(first_digits)
        total = sum(counts.values())
        # Compute using log10 formula
        import math
        benford_prop = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
        mad = sum(abs((counts.get(d, 0) / total) - benford_prop[d]) for d in range(1, 10)) / 9
        status = "FAIL" if mad > 0.015 else "PASS"
        self._add_result(
            rule_id="FA-5",
            rule_name="Benford's Law Screen",
            category="Forensic",
            status=status,
            source_value=float(mad),
            target_value=0.015,
            difference=float(mad - 0.015),
            variance_pct=0.0,
            details=f"Benford MAD {mad:.4f} (threshold 0.015, source={data_source})",
            severity="low" if status == "FAIL" else "info",
            formula="Benford deviation screen",
        )

    def _rule_fa_6_tenant_concentration_sanity(self):
        rows = self.db.execute(
            text(
                """
                SELECT COALESCE(annual_rent, monthly_rent * 12, 0) AS rent
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="FA-6",
                rule_name="Tenant Concentration & Roll-Forward",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Rent roll data unavailable",
                severity="medium",
                formula="Top tenants vs AR volatility",
            )
            return
        total = sum(float(r[0] or 0.0) for r in rows)
        sorted_rent = sorted([float(r[0] or 0.0) for r in rows], reverse=True)
        top1 = (sorted_rent[0] / total) if total and sorted_rent else 0.0
        top3 = (sum(sorted_rent[:3]) / total) if total else 0.0
        ar = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(tenant_receivables), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        status = "FAIL" if top1 > 0.35 and ar > 0 else "PASS"
        self._add_result(
            rule_id="FA-6",
            rule_name="Tenant Concentration & Roll-Forward",
            category="Forensic",
            status=status,
            source_value=float(top1),
            target_value=0.35,
            difference=float(top1 - 0.35),
            variance_pct=0.0,
            details=f"Top1 {top1:.1%}, Top3 {top3:.1%}, A/R ${ar:,.2f}",
            severity="medium" if status == "FAIL" else "info",
            formula="Flag high concentration with elevated A/R",
        )

    def _rule_fa_7_accrual_reversals(self):
        prior_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not prior_id:
            self._add_result(
                rule_id="FA-7",
                rule_name="Accrual Reversals",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable",
                severity="medium",
                formula="Accrual balance changes should have CF impact",
            )
            return
        accrual_curr = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%accrued%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        accrual_prior = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%accrued%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(prior_id)},
        ).scalar() or 0.0
        delta = float(accrual_curr) - float(accrual_prior)
        cf_adj = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(period_amount), 0)
                FROM cash_flow_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%accrued%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        if abs(delta) <= 1000:
            status = "PASS"
        else:
            status = "FAIL" if abs(cf_adj) < 0.01 else "PASS"
        self._add_result(
            rule_id="FA-7",
            rule_name="Accrual Reversals",
            category="Forensic",
            status=status,
            source_value=float(delta),
            target_value=float(cf_adj),
            difference=float(delta - cf_adj),
            variance_pct=0.0,
            details=f"Accrual delta ${delta:,.2f}, CF adj ${cf_adj:,.2f}",
            severity="medium" if status == "FAIL" else "info",
            formula="Accrual changes should align with CF adjustments",
        )

    def _rule_fa_wc_1_working_capital_attribution(self):
        """
        FA-WC-1: Working-capital attribution for non-cash variance.

        When there is a significant variance between CF-derived ending cash
        and BS ending cash, attribute that variance to specific BS working-
        capital accounts (A/R, prepaids, A/P, accruals, rent received in
        advance, escrows).
        """
        begin_id = getattr(self, "_get_prior_period_id", lambda: None)()
        if not begin_id:
            self._add_result(
                rule_id="FA-WC-1",
                rule_name="Working Capital Attribution",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior period unavailable for attribution window",
                severity="high",
                formula="Attribute non-cash variance to BS WC accounts",
            )
            return

        # Reuse FA-3 math to detect variance.
        begin_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(beginning_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        end_cash = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(ending_cash_balance), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        net_cf = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(net_cash_flow), 0)
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        expected_end = float(begin_cash) + float(net_cf)
        variance = float(end_cash) - expected_end

        if abs(variance) <= 1.0:
            self._add_result(
                rule_id="FA-WC-1",
                rule_name="Working Capital Attribution",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No material non-cash variance to attribute",
                severity="info",
                formula="Attribute non-cash variance to BS WC accounts",
            )
            return

        mappings = [
            ("%A/R%", "Accounts Receivable"),
            ("%PREPAID%", "Prepaid"),
            ("%ACCOUNTS PAYABLE%", "Accounts Payable"),
            ("%ACCRUED%", "Accrued"),
            ("%RENT RECEIVED IN ADVANCE%", "Rent Received in Advance"),
            ("%ESCROW%", "Escrows"),
        ]
        attributions = []
        for pattern, label in mappings:
            curr = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(self.period_id),
                    "pattern": pattern,
                },
            ).scalar() or 0.0
            prior = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM balance_sheet_data
                    WHERE property_id = :property_id
                      AND period_id = :period_id
                      AND account_name ILIKE :pattern
                    """
                ),
                {
                    "property_id": int(self.property_id),
                    "period_id": int(begin_id),
                    "pattern": pattern,
                },
            ).scalar() or 0.0
            delta = float(curr) - float(prior)
            if abs(delta) > 0.01:
                attributions.append(
                    {"account": label, "delta": delta, "current": float(curr), "prior": float(prior)}
                )

        self._add_result(
            rule_id="FA-WC-1",
            rule_name="Working Capital Attribution",
            category="Forensic",
            status="FAIL",
            source_value=float(variance),
            target_value=0.0,
            difference=float(variance),
            variance_pct=0.0,
            details=(
                f"Non-cash variance ${variance:,.2f} attributed to working-capital deltas; "
                f"{len(attributions)} WC accounts moved materially"
            ),
            severity="high",
            formula="Attribute non-cash variance to BS WC accounts",
            intermediate_calculations={
                "variance": variance,
                "begin_id": int(begin_id),
                "attributions": attributions,
            },
        )

    def _rule_fa_mort_1_payment_history_continuity(self):
        """
        FA-MORT-1: Mortgage payment history continuity.

        Flags months where the number of mortgage statement payments is zero
        or unusually large, relative to expectation (1 payment per month).
        """
        start_date = None
        end_date = None
        try:
            start_date, end_date = self._get_window_date_range(self.period_id)  # type: ignore[attr-defined]
        except Exception:
            # Fallback: use the current period only if helper not available.
            pass

        if not start_date or not end_date:
            self._add_result(
                rule_id="FA-MORT-1",
                rule_name="Mortgage Payment History Continuity",
                category="Forensic",
                status="INFO",
                source_value=0.0,
                target_value=1.0,
                difference=0.0,
                variance_pct=0.0,
                details="Payment window dates unavailable; skipping continuity check",
                severity="medium",
                formula="One scheduled mortgage payment per month expected",
            )
            return

        rows = self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM mortgage_payment_history
                WHERE property_id = :property_id
                  AND payment_date >= :start_date
                  AND payment_date <= :end_date
                """
            ),
            {
                "property_id": int(self.property_id),
                "start_date": start_date,
                "end_date": end_date,
            },
        ).scalar() or 0

        count = int(rows)
        status = "PASS" if count == 1 else "FAIL"
        self._add_result(
            rule_id="FA-MORT-1",
            rule_name="Mortgage Payment History Continuity",
            category="Forensic",
            status=status,
            source_value=float(count),
            target_value=1.0,
            difference=float(count - 1),
            variance_pct=0.0,
            details=f"{count} mortgage payments found in window (expected 1)",
            severity="medium" if status == "FAIL" else "info",
            formula="One scheduled mortgage payment per month expected",
        )

    def _rule_fa_mort_2_escrow_balance_reasonableness(self):
        """
        FA-MORT-2: Escrow balance reasonableness.

        Checks that BS escrow balances are non-negative and broadly consistent
        with mortgage statement escrow balances.
        """
        bs_escrow = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE '%escrow%'
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        ms_tax = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(tax_escrow_balance), 0)
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        ms_ins = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(insurance_escrow_balance), 0)
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0
        ms_res = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(reserve_balance), 0)
                FROM mortgage_statement_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).scalar() or 0.0

        ms_total = float(ms_tax + ms_ins + ms_res)
        diff = float(bs_escrow) - ms_total
        status = "PASS" if bs_escrow >= -1.0 and abs(diff) <= max(1000.0, abs(ms_total) * 0.10) else "FAIL"

        self._add_result(
            rule_id="FA-MORT-2",
            rule_name="Escrow Balance Reasonableness",
            category="Forensic",
            status=status,
            source_value=float(bs_escrow),
            target_value=float(ms_total),
            difference=float(diff),
            variance_pct=0.0,
            details=(
                f"BS escrows ${bs_escrow:,.2f} vs MS escrows ${ms_total:,.2f} "
                f"(Δ ${diff:,.2f})"
            ),
            severity="medium" if status == "FAIL" else "info",
            formula="BS escrow ≈ MS tax+insurance+reserve escrows",
        )

    def _rule_fa_rr_1_lease_term_consistency(self):
        """
        FA-RR-1: Lease term consistency.

        Ensures lease_end_date is not before lease_start_date and that
        remaining_lease_years is broadly consistent with the dates.
        """
        rows = self.db.execute(
            text(
                """
                SELECT lease_start_date, lease_end_date, remaining_lease_years
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND lease_end_date IS NOT NULL
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()

        bad_rows = 0
        for start_date, end_date, remaining_years in rows:
            if start_date and end_date and end_date < start_date:
                bad_rows += 1
                continue
            if start_date and end_date and remaining_years is not None:
                total_days = (end_date - start_date).days
                approx_years = max(total_days / 365.0, 0.0)
                if approx_years < float(remaining_years) - 1.0:
                    bad_rows += 1

        status = "PASS" if bad_rows == 0 else "FAIL"
        self._add_result(
            rule_id="FA-RR-1",
            rule_name="Lease Term Consistency",
            category="Forensic",
            status=status,
            source_value=float(bad_rows),
            target_value=0.0,
            difference=float(bad_rows),
            variance_pct=0.0,
            details=f"{bad_rows} leases with inconsistent start/end/remaining term",
            severity="medium" if status == "FAIL" else "info",
            formula="Lease start/end dates and remaining years consistent",
        )
