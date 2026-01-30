import calendar
from datetime import date, timedelta
from sqlalchemy import text, select

from app.models import SystemConfig

from app.services.reconciliation_types import ReconciliationResult
from app.services.rules.covenant_resolver import resolve_covenant_threshold_sync


class AnalyticsRulesMixin:
    """
    Advanced analytics, covenant, benchmark, trend, and stress test rules.
    Source: ADVANCED_ANALYTICS_COVENANTS_RULES.md
    """

    def _execute_analytics_rules(self):
        self._rule_analytics_1_noi()
        self._rule_analytics_2_noi_margin()
        self._rule_analytics_3_operating_expense_ratio()
        self._rule_analytics_4_cash_on_cash()
        self._rule_analytics_5_cap_rate()
        self._rule_analytics_6_economic_occupancy()
        self._rule_analytics_7_lease_rollover()
        self._rule_analytics_8_retention_rate()
        self._rule_analytics_9_walt()
        self._rule_analytics_10_rent_roll_growth()
        self._rule_analytics_11_ltv()
        self._rule_analytics_12_dscr()
        self._rule_analytics_13_interest_coverage()
        self._rule_analytics_14_debt_yield()
        self._rule_analytics_15_current_ratio()
        self._rule_analytics_16_cash_flow_coverage()
        self._rule_analytics_17_days_cash()
        self._rule_analytics_18_ar_days()
        self._rule_analytics_19_roa()
        self._rule_analytics_20_roe()
        self._rule_analytics_21_profit_margin()
        self._rule_analytics_22_revenue_per_sf()
        self._rule_analytics_23_opex_per_sf()
        self._rule_analytics_24_management_efficiency()
        self._rule_analytics_25_debt_to_equity()
        self._rule_analytics_26_equity_multiplier()
        self._rule_analytics_27_distribution_coverage()
        self._rule_analytics_28_same_store_noi_growth()
        self._rule_analytics_29_revenue_growth()
        self._rule_analytics_30_capex_intensity()
        self._rule_analytics_31_tenant_concentration()
        self._rule_analytics_32_lease_expiration_risk()
        self._rule_analytics_33_occupancy_volatility()
        self._rule_covenant_1_dscr()
        self._rule_covenant_2_ltv()
        self._rule_covenant_3_min_liquidity()
        self._rule_covenant_4_occupancy()
        self._rule_covenant_5_tenant_concentration()
        self._rule_covenant_6_reporting_requirements()
        self._rule_benchmark_1_market_rent()
        self._rule_benchmark_2_opex_benchmark()
        self._rule_benchmark_3_occupancy_vs_market()
        self._rule_benchmark_4_cap_rate_vs_market()
        self._rule_trend_1_moving_average()
        self._rule_trend_2_year_over_year()
        self._rule_trend_3_variance_analysis()
        self._rule_stress_1_occupancy()
        self._rule_stress_2_rent_rate()
        self._rule_stress_3_expense_inflation()
        self._rule_stress_4_interest_rate()
        self._rule_stress_5_tenant_loss()
        self._rule_dashboard_1_exec_summary()
        self._rule_dashboard_2_operational()
        self._rule_dashboard_3_lender_package()

    def _add_result(self, **kwargs):
        self.results.append(ReconciliationResult(**kwargs))

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

    def _get_metric(self, column_name: str, period_id=None) -> float:
        if hasattr(self, "_get_financial_metric"):
            return float(self._get_financial_metric(column_name, period_id=period_id) or 0.0)
        row = self.db.execute(
            text(
                f"""
                SELECT {column_name}
                FROM financial_metrics
                WHERE property_id = :property_id AND period_id = :period_id
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(period_id or self.period_id)},
        ).fetchone()
        return float(row[0] or 0.0) if row else 0.0

    def _get_prior_year_period_id(self):
        year, month = self._get_period_year_month()
        if not year or not month:
            return None
        if hasattr(self, "_get_period_id_for_year_month"):
            return self._get_period_id_for_year_month(year - 1, month)
        return None

    def _get_config_threshold(self, key: str, default: float) -> float:
        """
        Lightweight helper to fetch a numeric threshold from system_config.

        Falls back to the provided default if the key is missing or cannot
        be parsed as a float. This mirrors the async logic used by
        CovenantComplianceService but in a synchronous context.
        """
        try:
            row = self.db.execute(
                select(SystemConfig.config_value).where(SystemConfig.config_key == key).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return float(default)
            return float(str(row))
        except Exception:
            return float(default)

    def _sum_is(self, patterns, period_id=None):
        if hasattr(self, "_sum_is_accounts"):
            return self._sum_is_accounts(patterns, period_id=period_id)[0]
        return 0.0

    def _sum_cf(self, patterns, period_id=None):
        if hasattr(self, "_sum_cf_amounts"):
            return self._sum_cf_amounts(patterns, period_id=period_id)[0]
        return 0.0

    def _rule_analytics_1_noi(self):
        noi = self._get_metric("net_operating_income")
        revenue = self._get_metric("total_revenue")
        if noi == 0.0 and hasattr(self, "_sum_is_accounts"):
            revenue = self._sum_is(["%TOTAL INCOME%", "%TOTAL REVENUE%", "%REVENUE%"], period_id=self.period_id)
            expenses = self._sum_is(["%TOTAL EXPENSE%", "%TOTAL OPERATING EXPENSE%"], period_id=self.period_id)
            noi = revenue - expenses
        status = "PASS" if revenue != 0 or noi != 0 else "INFO"
        self._add_result(
            rule_id="ANALYTICS-1",
            rule_name="Net Operating Income (NOI)",
            category="Analytics",
            status=status,
            source_value=float(noi),
            target_value=float(noi),
            difference=0.0,
            variance_pct=0.0,
            details=f"NOI ${noi:,.2f}",
            severity="info",
            formula="NOI = Total Income - Total Operating Expenses",
        )

    def _rule_analytics_2_noi_margin(self):
        noi = self._get_metric("net_operating_income")
        revenue = self._get_metric("total_revenue")
        margin = (noi / revenue) if revenue else 0.0
        status = "PASS" if revenue else "INFO"
        self._add_result(
            rule_id="ANALYTICS-2",
            rule_name="NOI Margin",
            category="Analytics",
            status=status,
            source_value=float(margin),
            target_value=float(margin),
            difference=0.0,
            variance_pct=0.0,
            details=f"NOI margin {margin:.1%} (NOI ${noi:,.2f} / revenue ${revenue:,.2f})",
            severity="info",
            formula="NOI Margin = NOI / Total Income",
        )

    def _rule_analytics_3_operating_expense_ratio(self):
        revenue = self._get_metric("total_revenue")
        expenses = self._get_metric("total_expenses")
        ratio = (expenses / revenue) if revenue else 0.0
        status = "PASS" if revenue else "INFO"
        self._add_result(
            rule_id="ANALYTICS-3",
            rule_name="Operating Expense Ratio",
            category="Analytics",
            status=status,
            source_value=float(ratio),
            target_value=float(ratio),
            difference=0.0,
            variance_pct=0.0,
            details=f"Operating expense ratio {ratio:.1%} (Expenses ${expenses:,.2f} / Revenue ${revenue:,.2f})",
            severity="info",
            formula="Operating Expense Ratio = Total Operating Expenses / Total Income",
        )

    def _rule_analytics_4_cash_on_cash(self):
        noi = self._get_metric("net_operating_income")
        annual_debt_service = self._get_metric("total_annual_debt_service")
        partners = self._get_metric("partners_contribution")
        beginning_equity = self._get_metric("beginning_equity")
        distributions = self._get_metric("distributions")
        equity_invested = partners + beginning_equity - distributions
        cash_flow_before_tax = noi - annual_debt_service
        if equity_invested == 0:
            self._add_result(
                rule_id="ANALYTICS-4",
                rule_name="Cash-on-Cash Return",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Insufficient equity invested data for cash-on-cash calculation",
                severity="info",
                formula="(NOI - Debt Service) / Equity Invested",
            )
            return
        coc = cash_flow_before_tax / equity_invested
        self._add_result(
            rule_id="ANALYTICS-4",
            rule_name="Cash-on-Cash Return",
            category="Analytics",
            status="PASS",
            source_value=float(coc),
            target_value=float(coc),
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Cash-on-cash {coc:.1%} (NOI ${noi:,.2f} - Debt Service ${annual_debt_service:,.2f}) "
                f"/ Equity Invested ${equity_invested:,.2f}"
            ),
            severity="info",
            formula="Cash-on-Cash = (NOI - Debt Service) / Equity Invested",
        )

    def _rule_analytics_5_cap_rate(self):
        noi = self._get_metric("net_operating_income")
        property_value = self._get_metric("net_property_value") or self._get_metric("gross_property_value")
        if property_value == 0:
            self._add_result(
                rule_id="ANALYTICS-5",
                rule_name="Cap Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Property value unavailable for cap rate calculation",
                severity="info",
                formula="Cap Rate = NOI / Property Value",
            )
            return
        cap_rate = noi / property_value
        self._add_result(
            rule_id="ANALYTICS-5",
            rule_name="Cap Rate",
            category="Analytics",
            status="PASS",
            source_value=float(cap_rate),
            target_value=float(cap_rate),
            difference=0.0,
            variance_pct=0.0,
            details=f"Cap rate {cap_rate:.2%} (NOI ${noi:,.2f} / Value ${property_value:,.2f})",
            severity="info",
            formula="Cap Rate = NOI / Property Value",
        )

    def _rule_analytics_6_economic_occupancy(self):
        rr = self._get_rent_roll_summary(self.period_id) if hasattr(self, "_get_rent_roll_summary") else None
        if not rr or rr["total_monthly_rent"] == 0:
            self._add_result(
                rule_id="ANALYTICS-6",
                rule_name="Economic Occupancy",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Rent roll data unavailable for economic occupancy",
                severity="info",
                formula="Economic Occupancy = Actual Rent / Potential Rent",
            )
            return
        economic_occ = rr["occupied_monthly_rent"] / rr["total_monthly_rent"]
        self._add_result(
            rule_id="ANALYTICS-6",
            rule_name="Economic Occupancy",
            category="Analytics",
            status="PASS",
            source_value=float(economic_occ),
            target_value=float(economic_occ),
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Economic occupancy {economic_occ:.1%} (Occupied rent ${rr['occupied_monthly_rent']:,.2f} / "
                f"Total rent ${rr['total_monthly_rent']:,.2f})"
            ),
            severity="info",
            formula="Economic Occupancy = Actual Rent Collected / Potential Gross Rent",
        )

    def _rule_analytics_7_lease_rollover(self):
        rows = self.db.execute(
            text(
                """
                SELECT lease_end_date, COALESCE(annual_rent, monthly_rent * 12, 0)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND lease_end_date IS NOT NULL
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="ANALYTICS-7",
                rule_name="Lease Rollover Analysis",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No lease expiration data available",
                severity="info",
                formula="Expiring Rent / Total Annual Rent by year",
            )
            return
        totals_by_year = {}
        total_rent = 0.0
        for lease_end, annual_rent in rows:
            year = lease_end.year if lease_end else None
            if not year:
                continue
            annual_rent = float(annual_rent or 0.0)
            total_rent += annual_rent
            totals_by_year[year] = totals_by_year.get(year, 0.0) + annual_rent
        summary = ", ".join(
            f"{year}: {amount / total_rent:.1%}" for year, amount in sorted(totals_by_year.items()) if total_rent
        )
        self._add_result(
            rule_id="ANALYTICS-7",
            rule_name="Lease Rollover Analysis",
            category="Analytics",
            status="PASS",
            source_value=float(total_rent),
            target_value=float(total_rent),
            difference=0.0,
            variance_pct=0.0,
            details=f"Lease rollover by year (share of rent): {summary}",
            severity="info",
            formula="Expiring Rent / Total Annual Rent",
        )

    def _rule_analytics_8_retention_rate(self):
        """ANALYTICS-8: Tenant Retention Rate = Renewed Leases / Expiring Leases (lookback 12 months)."""
        period_end = self._get_period_end_date()
        if not period_end:
            self._add_result(
                rule_id="ANALYTICS-8",
                rule_name="Tenant Retention Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Period end date unavailable",
                severity="info",
                formula="Retention Rate = Renewed Leases / Expiring Leases",
            )
            return
        # Lookback 12 months: same month, previous year
        start_year = period_end.year - 1
        start_month = period_end.month
        last_day = calendar.monthrange(start_year, start_month)[1]
        start_day = min(period_end.day, last_day)
        lookback_start = date(start_year, start_month, start_day)
        rows = self.db.execute(
            text(
                """
                SELECT renewal_status, COUNT(*) AS cnt
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND lease_end_date IS NOT NULL
                  AND lease_end_date >= :lookback_start
                  AND lease_end_date <= :period_end
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                GROUP BY renewal_status
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(self.period_id),
                "lookback_start": lookback_start,
                "period_end": period_end,
            },
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="ANALYTICS-8",
                rule_name="Tenant Retention Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No leases expiring in the last 12 months",
                severity="info",
                formula="Retention Rate = Renewed Leases / Expiring Leases",
            )
            return
        expiring = sum(int(r[1]) for r in rows)
        renewed = sum(int(r[1]) for r in rows if r[0] and str(r[0]).strip().lower() == "renewed")
        has_renewal_data = any(r[0] is not None and str(r[0]).strip() for r in rows)
        if not has_renewal_data:
            self._add_result(
                rule_id="ANALYTICS-8",
                rule_name="Tenant Retention Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Retention rate requires renewal_status (New/Renewed/Expired) in rent roll",
                severity="info",
                formula="Retention Rate = Renewed Leases / Expiring Leases",
            )
            return
        retention = (renewed / expiring) if expiring else 0.0
        status = "PASS" if expiring else "INFO"
        self._add_result(
            rule_id="ANALYTICS-8",
            rule_name="Tenant Retention Rate",
            category="Analytics",
            status=status,
            source_value=float(retention),
            target_value=float(retention),
            difference=0.0,
            variance_pct=0.0,
            details=f"Retention {retention:.1%} ({renewed} renewed / {expiring} expiring in last 12 months)",
            severity="info",
            formula="Retention Rate = Renewed Leases / Expiring Leases",
            intermediate_calculations={
                "expiring": expiring,
                "renewed": renewed,
                "lookback_start": str(lookback_start),
                "period_end": str(period_end),
            },
        )

    def _rule_analytics_9_walt(self):
        rows = self.db.execute(
            text(
                """
                SELECT annual_rent, remaining_lease_years, lease_end_date
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
                rule_id="ANALYTICS-9",
                rule_name="Weighted Average Lease Term (WALT)",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Lease term data unavailable",
                severity="info",
                formula="WALT = Σ(Rent × Years Remaining) / Total Rent",
            )
            return
        total_rent = 0.0
        weighted_sum = 0.0
        period_end = self._get_period_end_date()
        for annual_rent, remaining_years, lease_end in rows:
            rent = float(annual_rent or 0.0)
            if rent == 0.0:
                continue
            if remaining_years is None and lease_end and period_end:
                remaining_years = max((lease_end - period_end).days / 365.0, 0.0)
            remaining_years = float(remaining_years or 0.0)
            total_rent += rent
            weighted_sum += rent * remaining_years
        if total_rent == 0:
            self._add_result(
                rule_id="ANALYTICS-9",
                rule_name="Weighted Average Lease Term (WALT)",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Lease term data available but rent totals are zero",
                severity="info",
                formula="WALT = Σ(Rent × Years Remaining) / Total Rent",
            )
            return
        walt = weighted_sum / total_rent
        self._add_result(
            rule_id="ANALYTICS-9",
            rule_name="Weighted Average Lease Term (WALT)",
            category="Analytics",
            status="PASS",
            source_value=float(walt),
            target_value=float(walt),
            difference=0.0,
            variance_pct=0.0,
            details=f"WALT {walt:.2f} years",
            severity="info",
            formula="WALT = Σ(Rent × Years Remaining) / Total Rent",
        )

    def _rule_analytics_10_rent_roll_growth(self):
        prior_id = self._get_prior_year_period_id()
        if not prior_id or not hasattr(self, "_get_rent_roll_summary"):
            self._add_result(
                rule_id="ANALYTICS-10",
                rule_name="Rent Roll Growth Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior-year rent roll unavailable",
                severity="info",
                formula="(Current Rent - Prior Rent) / Prior Rent",
            )
            return
        rr_curr = self._get_rent_roll_summary(self.period_id)
        rr_prior = self._get_rent_roll_summary(prior_id)
        prior_rent = rr_prior.get("total_monthly_rent", 0.0)
        if prior_rent == 0:
            self._add_result(
                rule_id="ANALYTICS-10",
                rule_name="Rent Roll Growth Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior-year rent roll is zero or missing",
                severity="info",
                formula="(Current Rent - Prior Rent) / Prior Rent",
            )
            return
        growth = (rr_curr["total_monthly_rent"] - prior_rent) / prior_rent
        self._add_result(
            rule_id="ANALYTICS-10",
            rule_name="Rent Roll Growth Rate",
            category="Analytics",
            status="PASS",
            source_value=float(growth),
            target_value=float(growth),
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"Rent roll growth {growth:.1%} (Current ${rr_curr['total_monthly_rent']:,.2f} / "
                f"Prior ${prior_rent:,.2f})"
            ),
            severity="info",
            formula="(Current Rent - Prior Rent) / Prior Rent",
        )

    def _rule_analytics_11_ltv(self):
        ltv = self._get_metric("ltv_ratio")
        total_debt = self._get_metric("total_debt") or self._get_metric("total_mortgage_debt")
        property_value = self._get_metric("net_property_value") or self._get_metric("gross_property_value")
        if ltv == 0.0 and property_value:
            ltv = total_debt / property_value if property_value else 0.0
        status = "PASS" if ltv else "INFO"
        self._add_result(
            rule_id="ANALYTICS-11",
            rule_name="Loan-to-Value (LTV)",
            category="Analytics",
            status=status,
            source_value=float(ltv),
            target_value=float(ltv),
            difference=0.0,
            variance_pct=0.0,
            details=f"LTV {ltv:.2%} (Debt ${total_debt:,.2f} / Value ${property_value:,.2f})",
            severity="info",
            formula="LTV = Outstanding Debt / Property Value",
        )

    def _rule_analytics_12_dscr(self):
        dscr = self._get_metric("dscr")
        if dscr == 0.0:
            noi = self._get_metric("net_operating_income")
            debt_service = self._get_metric("total_annual_debt_service")
            dscr = noi / debt_service if debt_service else 0.0
        status = "PASS" if dscr else "INFO"
        self._add_result(
            rule_id="ANALYTICS-12",
            rule_name="Debt Service Coverage Ratio (DSCR)",
            category="Analytics",
            status=status,
            source_value=float(dscr),
            target_value=float(dscr),
            difference=0.0,
            variance_pct=0.0,
            details=f"DSCR {dscr:.2f}x",
            severity="info",
            formula="DSCR = NOI / Annual Debt Service",
        )

    def _rule_analytics_13_interest_coverage(self):
        ratio = self._get_metric("interest_coverage_ratio")
        if ratio == 0.0 and hasattr(self, "_sum_is_accounts"):
            noi = self._get_metric("net_operating_income")
            interest = self._sum_is(["%INTEREST%"], period_id=self.period_id)
            ratio = noi / (interest * 12) if interest else 0.0
        status = "PASS" if ratio else "INFO"
        self._add_result(
            rule_id="ANALYTICS-13",
            rule_name="Interest Coverage Ratio",
            category="Analytics",
            status=status,
            source_value=float(ratio),
            target_value=float(ratio),
            difference=0.0,
            variance_pct=0.0,
            details=f"Interest coverage {ratio:.2f}x",
            severity="info",
            formula="Interest Coverage = NOI / Interest Expense",
        )

    def _rule_analytics_14_debt_yield(self):
        debt_yield = self._get_metric("debt_yield")
        if debt_yield == 0.0:
            noi = self._get_metric("net_operating_income")
            total_debt = self._get_metric("total_debt") or self._get_metric("total_mortgage_debt")
            debt_yield = (noi / total_debt) if total_debt else 0.0
        status = "PASS" if debt_yield else "INFO"
        self._add_result(
            rule_id="ANALYTICS-14",
            rule_name="Debt Yield",
            category="Analytics",
            status=status,
            source_value=float(debt_yield),
            target_value=float(debt_yield),
            difference=0.0,
            variance_pct=0.0,
            details=f"Debt yield {debt_yield:.2%}",
            severity="info",
            formula="Debt Yield = NOI / Loan Balance",
        )

    def _rule_analytics_15_current_ratio(self):
        ratio = self._get_metric("current_ratio")
        if ratio == 0.0:
            current_assets = self._get_metric("total_current_assets")
            current_liabilities = self._get_metric("total_current_liabilities")
            ratio = current_assets / current_liabilities if current_liabilities else 0.0
        status = "PASS" if ratio else "INFO"
        self._add_result(
            rule_id="ANALYTICS-15",
            rule_name="Current Ratio",
            category="Analytics",
            status=status,
            source_value=float(ratio),
            target_value=float(ratio),
            difference=0.0,
            variance_pct=0.0,
            details=f"Current ratio {ratio:.2f}x",
            severity="info",
            formula="Current Ratio = Current Assets / Current Liabilities",
        )

    def _rule_analytics_16_cash_flow_coverage(self):
        operating_cash_flow = self._get_metric("operating_cash_flow")
        annual_debt_service = self._get_metric("total_annual_debt_service")
        if annual_debt_service == 0:
            self._add_result(
                rule_id="ANALYTICS-16",
                rule_name="Cash Flow Coverage",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Debt service data unavailable for cash flow coverage",
                severity="info",
                formula="Operating Cash Flow / Required Payments",
            )
            return
        coverage = (operating_cash_flow * 12) / annual_debt_service if operating_cash_flow else 0.0
        self._add_result(
            rule_id="ANALYTICS-16",
            rule_name="Cash Flow Coverage",
            category="Analytics",
            status="PASS" if coverage else "INFO",
            source_value=float(coverage),
            target_value=float(coverage),
            difference=0.0,
            variance_pct=0.0,
            details=f"Operating cash flow coverage {coverage:.2f}x",
            severity="info",
            formula="Operating Cash Flow / Required Payments",
        )

    def _rule_analytics_17_days_cash(self):
        cash = self._get_metric("total_cash_position") or self._get_metric("operating_cash")
        expenses = self._get_metric("total_expenses")
        if expenses == 0:
            self._add_result(
                rule_id="ANALYTICS-17",
                rule_name="Days Cash on Hand",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Expense data unavailable for days cash",
                severity="info",
                formula="Days Cash = Cash Balance / Average Daily Expenses",
            )
            return
        avg_daily = expenses / 30.0
        days_cash = cash / avg_daily if avg_daily else 0.0
        self._add_result(
            rule_id="ANALYTICS-17",
            rule_name="Days Cash on Hand",
            category="Analytics",
            status="PASS",
            source_value=float(days_cash),
            target_value=float(days_cash),
            difference=0.0,
            variance_pct=0.0,
            details=f"Days cash {days_cash:.0f} days (Cash ${cash:,.2f})",
            severity="info",
            formula="Days Cash = Cash Balance / Average Daily Expenses",
        )

    def _rule_analytics_18_ar_days(self):
        ar = self._get_metric("tenant_receivables")
        revenue = self._get_metric("total_revenue")
        if revenue == 0:
            self._add_result(
                rule_id="ANALYTICS-18",
                rule_name="Accounts Receivable Days",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Revenue data unavailable for AR days",
                severity="info",
                formula="A/R Days = A/R / Average Daily Revenue",
            )
            return
        avg_daily = revenue / 30.0
        ar_days = ar / avg_daily if avg_daily else 0.0
        self._add_result(
            rule_id="ANALYTICS-18",
            rule_name="Accounts Receivable Days",
            category="Analytics",
            status="PASS",
            source_value=float(ar_days),
            target_value=float(ar_days),
            difference=0.0,
            variance_pct=0.0,
            details=f"A/R Days {ar_days:.1f} (A/R ${ar:,.2f})",
            severity="info",
            formula="A/R Days = A/R Tenants / Average Daily Revenue",
        )

    def _rule_analytics_19_roa(self):
        net_income = self._get_metric("net_income")
        total_assets = self._get_metric("total_assets")
        roa = (net_income / total_assets) if total_assets else 0.0
        status = "PASS" if total_assets else "INFO"
        self._add_result(
            rule_id="ANALYTICS-19",
            rule_name="Return on Assets (ROA)",
            category="Analytics",
            status=status,
            source_value=float(roa),
            target_value=float(roa),
            difference=0.0,
            variance_pct=0.0,
            details=f"ROA {roa:.2%}",
            severity="info",
            formula="ROA = Net Income / Total Assets",
        )

    def _rule_analytics_20_roe(self):
        net_income = self._get_metric("net_income")
        equity = self._get_metric("total_equity")
        roe = (net_income / equity) if equity else 0.0
        status = "PASS" if equity else "INFO"
        self._add_result(
            rule_id="ANALYTICS-20",
            rule_name="Return on Equity (ROE)",
            category="Analytics",
            status=status,
            source_value=float(roe),
            target_value=float(roe),
            difference=0.0,
            variance_pct=0.0,
            details=f"ROE {roe:.2%}",
            severity="info",
            formula="ROE = Net Income / Total Equity",
        )

    def _rule_analytics_21_profit_margin(self):
        net_income = self._get_metric("net_income")
        revenue = self._get_metric("total_revenue")
        margin = (net_income / revenue) if revenue else 0.0
        status = "PASS" if revenue else "INFO"
        self._add_result(
            rule_id="ANALYTICS-21",
            rule_name="Profit Margin",
            category="Analytics",
            status=status,
            source_value=float(margin),
            target_value=float(margin),
            difference=0.0,
            variance_pct=0.0,
            details=f"Profit margin {margin:.2%}",
            severity="info",
            formula="Profit Margin = Net Income / Total Income",
        )

    def _rule_analytics_22_revenue_per_sf(self):
        revenue = self._get_metric("total_revenue")
        sqft = self._get_metric("total_leasable_sqft")
        if sqft == 0:
            self._add_result(
                rule_id="ANALYTICS-22",
                rule_name="Revenue per SF",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Total leasable SF unavailable",
                severity="info",
                formula="Revenue per SF = Annual Revenue / Total SF",
            )
            return
        annual_revenue = revenue * 12
        rev_per_sf = annual_revenue / sqft
        self._add_result(
            rule_id="ANALYTICS-22",
            rule_name="Revenue per SF",
            category="Analytics",
            status="PASS",
            source_value=float(rev_per_sf),
            target_value=float(rev_per_sf),
            difference=0.0,
            variance_pct=0.0,
            details=f"Revenue per SF ${rev_per_sf:,.2f} (Annual revenue ${annual_revenue:,.2f} / SF {sqft:,.0f})",
            severity="info",
            formula="Revenue per SF = Annual Revenue / Total SF",
        )

    def _rule_analytics_23_opex_per_sf(self):
        expenses = self._get_metric("total_expenses")
        sqft = self._get_metric("total_leasable_sqft")
        if sqft == 0:
            self._add_result(
                rule_id="ANALYTICS-23",
                rule_name="Operating Expense per SF",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Total leasable SF unavailable",
                severity="info",
                formula="OpEx per SF = Annual Operating Expenses / Total SF",
            )
            return
        annual_expenses = expenses * 12
        opex_per_sf = annual_expenses / sqft
        self._add_result(
            rule_id="ANALYTICS-23",
            rule_name="Operating Expense per SF",
            category="Analytics",
            status="PASS",
            source_value=float(opex_per_sf),
            target_value=float(opex_per_sf),
            difference=0.0,
            variance_pct=0.0,
            details=f"OpEx per SF ${opex_per_sf:,.2f} (Annual expenses ${annual_expenses:,.2f} / SF {sqft:,.0f})",
            severity="info",
            formula="OpEx per SF = Annual Operating Expenses / Total SF",
        )

    def _rule_analytics_24_management_efficiency(self):
        revenue = self._get_metric("total_revenue")
        if not hasattr(self, "_sum_is_accounts") or revenue == 0:
            self._add_result(
                rule_id="ANALYTICS-24",
                rule_name="Management Fee Ratio",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Management fee data unavailable",
                severity="info",
                formula="Management Ratio = Management Fees / Total Income",
            )
            return
        mgmt = self._sum_is(["%MANAGEMENT%"], period_id=self.period_id)
        ratio = mgmt / revenue if revenue else 0.0
        self._add_result(
            rule_id="ANALYTICS-24",
            rule_name="Management Fee Ratio",
            category="Analytics",
            status="PASS",
            source_value=float(ratio),
            target_value=float(ratio),
            difference=0.0,
            variance_pct=0.0,
            details=f"Management ratio {ratio:.2%} (Fees ${mgmt:,.2f} / Revenue ${revenue:,.2f})",
            severity="info",
            formula="Management Ratio = Management Fees / Total Income",
        )

    def _rule_analytics_25_debt_to_equity(self):
        ratio = self._get_metric("debt_to_equity_ratio")
        if ratio == 0.0:
            liabilities = self._get_metric("total_liabilities")
            equity = self._get_metric("total_equity")
            ratio = liabilities / equity if equity else 0.0
        status = "PASS" if ratio else "INFO"
        self._add_result(
            rule_id="ANALYTICS-25",
            rule_name="Debt-to-Equity Ratio",
            category="Analytics",
            status=status,
            source_value=float(ratio),
            target_value=float(ratio),
            difference=0.0,
            variance_pct=0.0,
            details=f"Debt-to-equity {ratio:.2f}x",
            severity="info",
            formula="Debt-to-Equity = Total Liabilities / Total Equity",
        )

    def _rule_analytics_26_equity_multiplier(self):
        assets = self._get_metric("total_assets")
        equity = self._get_metric("total_equity")
        multiplier = assets / equity if equity else 0.0
        status = "PASS" if equity else "INFO"
        self._add_result(
            rule_id="ANALYTICS-26",
            rule_name="Equity Multiplier",
            category="Analytics",
            status=status,
            source_value=float(multiplier),
            target_value=float(multiplier),
            difference=0.0,
            variance_pct=0.0,
            details=f"Equity multiplier {multiplier:.2f}x",
            severity="info",
            formula="Equity Multiplier = Total Assets / Total Equity",
        )

    def _rule_analytics_27_distribution_coverage(self):
        net_income = self._get_metric("net_income")
        distributions = self._get_metric("distributions")
        if distributions == 0:
            self._add_result(
                rule_id="ANALYTICS-27",
                rule_name="Distribution Coverage Ratio",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Distribution data unavailable",
                severity="info",
                formula="Distribution Coverage = Net Income / Distributions",
            )
            return
        coverage = net_income / distributions
        self._add_result(
            rule_id="ANALYTICS-27",
            rule_name="Distribution Coverage Ratio",
            category="Analytics",
            status="PASS",
            source_value=float(coverage),
            target_value=float(coverage),
            difference=0.0,
            variance_pct=0.0,
            details=f"Distribution coverage {coverage:.2f}x",
            severity="info",
            formula="Distribution Coverage = Net Income / Distributions",
        )

    def _rule_analytics_28_same_store_noi_growth(self):
        prior_id = self._get_prior_year_period_id()
        if not prior_id:
            self._add_result(
                rule_id="ANALYTICS-28",
                rule_name="Same-Store NOI Growth",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year period unavailable",
                severity="info",
                formula="(Current NOI - Prior NOI) / Prior NOI",
            )
            return
        noi_curr = self._get_metric("net_operating_income", period_id=self.period_id)
        noi_prior = self._get_metric("net_operating_income", period_id=prior_id)
        if noi_prior == 0:
            self._add_result(
                rule_id="ANALYTICS-28",
                rule_name="Same-Store NOI Growth",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year NOI unavailable",
                severity="info",
                formula="(Current NOI - Prior NOI) / Prior NOI",
            )
            return
        growth = (noi_curr - noi_prior) / noi_prior
        self._add_result(
            rule_id="ANALYTICS-28",
            rule_name="Same-Store NOI Growth",
            category="Analytics",
            status="PASS",
            source_value=float(growth),
            target_value=float(growth),
            difference=0.0,
            variance_pct=0.0,
            details=f"NOI growth {growth:.1%} (Current ${noi_curr:,.2f} / Prior ${noi_prior:,.2f})",
            severity="info",
            formula="(Current NOI - Prior NOI) / Prior NOI",
        )

    def _rule_analytics_29_revenue_growth(self):
        prior_id = self._get_prior_year_period_id()
        if not prior_id:
            self._add_result(
                rule_id="ANALYTICS-29",
                rule_name="Revenue Growth Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year period unavailable",
                severity="info",
                formula="(Current Revenue - Prior Revenue) / Prior Revenue",
            )
            return
        rev_curr = self._get_metric("total_revenue", period_id=self.period_id)
        rev_prior = self._get_metric("total_revenue", period_id=prior_id)
        if rev_prior == 0:
            self._add_result(
                rule_id="ANALYTICS-29",
                rule_name="Revenue Growth Rate",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year revenue unavailable",
                severity="info",
                formula="(Current Revenue - Prior Revenue) / Prior Revenue",
            )
            return
        growth = (rev_curr - rev_prior) / rev_prior
        self._add_result(
            rule_id="ANALYTICS-29",
            rule_name="Revenue Growth Rate",
            category="Analytics",
            status="PASS",
            source_value=float(growth),
            target_value=float(growth),
            difference=0.0,
            variance_pct=0.0,
            details=f"Revenue growth {growth:.1%} (Current ${rev_curr:,.2f} / Prior ${rev_prior:,.2f})",
            severity="info",
            formula="(Current Revenue - Prior Revenue) / Prior Revenue",
        )

    def _rule_analytics_30_capex_intensity(self):
        capex = 0.0
        if hasattr(self, "_sum_cf_amounts"):
            capex = self._sum_cf(["%CAPEX%", "%CAPITAL%", "%IMPROVEMENT%", "%FIXED ASSET%"], period_id=self.period_id)
        revenue = self._get_metric("total_revenue")
        property_value = self._get_metric("net_property_value") or self._get_metric("gross_property_value")
        if revenue == 0 or property_value == 0:
            self._add_result(
                rule_id="ANALYTICS-30",
                rule_name="CapEx Intensity",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Insufficient data for CapEx intensity",
                severity="info",
                formula="CapEx / Revenue and CapEx / Property Value",
            )
            return
        capex_annual = capex * 12
        intensity_rev = capex_annual / (revenue * 12) if revenue else 0.0
        intensity_val = capex_annual / property_value if property_value else 0.0
        self._add_result(
            rule_id="ANALYTICS-30",
            rule_name="CapEx Intensity",
            category="Analytics",
            status="PASS",
            source_value=float(intensity_rev),
            target_value=float(intensity_rev),
            difference=0.0,
            variance_pct=0.0,
            details=(
                f"CapEx intensity {intensity_rev:.1%} of revenue, {intensity_val:.2%} of value "
                f"(CapEx ${capex_annual:,.2f})"
            ),
            severity="info",
            formula="CapEx / Revenue, CapEx / Property Value",
        )

    def _rule_analytics_31_tenant_concentration(self):
        rows = self.db.execute(
            text(
                """
                SELECT tenant_name, COALESCE(annual_rent, monthly_rent * 12, 0) AS rent
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
                rule_id="ANALYTICS-31",
                rule_name="Tenant Concentration Risk",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Rent roll tenant data unavailable",
                severity="info",
                formula="Top tenants as % of total rent",
            )
            return
        total_rent = sum(float(rent or 0.0) for _, rent in rows)
        sorted_rent = sorted([float(rent or 0.0) for _, rent in rows], reverse=True)
        top1 = (sorted_rent[0] / total_rent) if total_rent and sorted_rent else 0.0
        top3 = (sum(sorted_rent[:3]) / total_rent) if total_rent else 0.0
        self._add_result(
            rule_id="ANALYTICS-31",
            rule_name="Tenant Concentration Risk",
            category="Analytics",
            status="PASS",
            source_value=float(top1),
            target_value=float(top1),
            difference=0.0,
            variance_pct=0.0,
            details=f"Top1 {top1:.1%}, Top3 {top3:.1%} of rent",
            severity="info",
            formula="Top tenants as % of total scheduled rent",
        )

    def _rule_analytics_32_lease_expiration_risk(self):
        rows = self.db.execute(
            text(
                """
                SELECT lease_end_date, COALESCE(annual_rent, monthly_rent * 12, 0)
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND lease_end_date IS NOT NULL
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="ANALYTICS-32",
                rule_name="Lease Expiration Risk",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Lease expiration data unavailable",
                severity="info",
                formula="% of rent expiring next 2 years",
            )
            return
        period_end = self._get_period_end_date() or date.today()
        total_rent = 0.0
        two_year_rent = 0.0
        for lease_end, rent in rows:
            rent = float(rent or 0.0)
            total_rent += rent
            if lease_end and (lease_end - period_end).days <= 730:
                two_year_rent += rent
        pct = (two_year_rent / total_rent) if total_rent else 0.0
        self._add_result(
            rule_id="ANALYTICS-32",
            rule_name="Lease Expiration Risk",
            category="Analytics",
            status="PASS",
            source_value=float(pct),
            target_value=float(pct),
            difference=0.0,
            variance_pct=0.0,
            details=f"{pct:.1%} of rent expiring within 2 years",
            severity="info",
            formula="Expiring Rent (2 yrs) / Total Rent",
        )

    def _rule_analytics_33_occupancy_volatility(self):
        rows = self.db.execute(
            text(
                """
                SELECT fm.occupancy_rate
                FROM financial_periods fp
                JOIN financial_metrics fm ON fm.period_id = fp.id
                WHERE fp.property_id = :property_id
                  AND (fp.period_year, fp.period_month) <= (
                    SELECT period_year, period_month FROM financial_periods WHERE id = :period_id
                  )
                ORDER BY fp.period_year DESC, fp.period_month DESC
                LIMIT 6
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        rates = [float(r[0] or 0.0) for r in rows if r and r[0] is not None]
        if len(rates) < 2:
            self._add_result(
                rule_id="ANALYTICS-33",
                rule_name="Occupancy Volatility",
                category="Analytics",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Insufficient occupancy history",
                severity="info",
                formula="Std dev of occupancy %",
            )
            return
        mean = sum(rates) / len(rates)
        variance = sum((r - mean) ** 2 for r in rates) / len(rates)
        std_dev = variance ** 0.5
        self._add_result(
            rule_id="ANALYTICS-33",
            rule_name="Occupancy Volatility",
            category="Analytics",
            status="PASS",
            source_value=float(std_dev),
            target_value=float(std_dev),
            difference=0.0,
            variance_pct=0.0,
            details=f"Occupancy std dev {std_dev:.2f} over last {len(rates)} periods",
            severity="info",
            formula="Std dev of occupancy %",
        )

    def _rule_covenant_1_dscr(self):
        dscr = self._get_metric("dscr")
        if dscr == 0.0:
            noi = self._get_metric("net_operating_income")
            debt_service = self._get_metric("total_annual_debt_service")
            dscr = noi / debt_service if debt_service else 0.0
        threshold = resolve_covenant_threshold_sync(
            self.db, int(self.property_id), int(self.period_id), "DSCR"
        )
        status = "PASS" if dscr >= threshold else "FAIL"
        self._add_result(
            rule_id="COVENANT-1",
            rule_name="DSCR Covenant",
            category="Covenant",
            status=status,
            source_value=float(dscr),
            target_value=float(threshold),
            difference=float(dscr - threshold),
            variance_pct=0.0,
            details=f"DSCR {dscr:.2f}x (min {threshold:.2f}x)",
            severity="high" if status == "FAIL" else "info",
            formula="DSCR >= 1.25x",
        )

    def _rule_covenant_2_ltv(self):
        ltv = self._get_metric("ltv_ratio")
        if ltv == 0.0:
            debt = self._get_metric("total_debt")
            value = self._get_metric("net_property_value") or self._get_metric("gross_property_value")
            ltv = debt / value if value else 0.0
        # Resolver returns ratio (0.75) for LTV when stored as percent (75).
        threshold = resolve_covenant_threshold_sync(
            self.db, int(self.property_id), int(self.period_id), "LTV"
        )
        status = "PASS" if ltv <= threshold and ltv > 0 else "FAIL"
        self._add_result(
            rule_id="COVENANT-2",
            rule_name="LTV Covenant",
            category="Covenant",
            status=status if ltv else "INFO",
            source_value=float(ltv),
            target_value=float(threshold),
            difference=float(threshold - ltv),
            variance_pct=0.0,
            details=f"LTV {ltv:.2%} (max {threshold:.2%})",
            severity="high" if status == "FAIL" else "info",
            formula="LTV <= 75%",
        )

    def _rule_covenant_3_min_liquidity(self):
        cash = self._get_metric("operating_cash")
        escrow = self._get_metric("restricted_cash")
        debt_service = self._get_metric("total_monthly_debt_service")
        if debt_service == 0:
            self._add_result(
                rule_id="COVENANT-3",
                rule_name="Minimum Liquidity Covenant",
                category="Covenant",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Debt service data unavailable for liquidity covenant",
                severity="info",
                formula="Cash >= 3 months debt service",
            )
            return
        min_months = resolve_covenant_threshold_sync(
            self.db, int(self.property_id), int(self.period_id), "MIN_LIQUIDITY"
        )
        required = debt_service * min_months
        available = cash + escrow
        status = "PASS" if available >= required else "FAIL"
        self._add_result(
            rule_id="COVENANT-3",
            rule_name="Minimum Liquidity Covenant",
            category="Covenant",
            status=status,
            source_value=float(available),
            target_value=float(required),
            difference=float(available - required),
            variance_pct=0.0,
            details=f"Liquidity ${available:,.2f} vs required ${required:,.2f} ({min_months} months)",
            severity="high" if status == "FAIL" else "info",
            formula="Cash + Escrows >= 3 months debt service",
        )

    def _rule_covenant_4_occupancy(self):
        occ = self._get_metric("occupancy_rate")
        occ_min_pct = resolve_covenant_threshold_sync(
            self.db, int(self.property_id), int(self.period_id), "OCCUPANCY"
        )
        threshold = occ_min_pct / 100.0
        if occ == 0.0 and hasattr(self, "_get_rent_roll_summary"):
            occ = (self._get_rent_roll_summary(self.period_id).get("occupancy_pct", 0.0) / 100.0)
        status = "PASS" if occ >= threshold else "FAIL"
        self._add_result(
            rule_id="COVENANT-4",
            rule_name="Occupancy Covenant",
            category="Covenant",
            status=status if occ else "INFO",
            source_value=float(occ),
            target_value=float(threshold),
            difference=float(occ - threshold),
            variance_pct=0.0,
            details=f"Occupancy {occ:.1%} (min {threshold:.1%})",
            severity="high" if status == "FAIL" else "info",
            formula="Occupancy >= 85%",
        )

    def _rule_covenant_5_tenant_concentration(self):
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
                rule_id="COVENANT-5",
                rule_name="Single Tenant Concentration",
                category="Covenant",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Rent roll data unavailable",
                severity="info",
                formula="Top tenant % <= 20%",
            )
            return
        total = sum(float(r[0] or 0.0) for r in rows)
        top = max(float(r[0] or 0.0) for r in rows) if total else 0.0
        pct = top / total if total else 0.0
        tenant_max_pct = resolve_covenant_threshold_sync(
            self.db, int(self.property_id), int(self.period_id), "SINGLE_TENANT_MAX"
        )
        threshold = tenant_max_pct / 100.0
        status = "PASS" if pct <= threshold else "FAIL"
        self._add_result(
            rule_id="COVENANT-5",
            rule_name="Single Tenant Concentration",
            category="Covenant",
            status=status,
            source_value=float(pct),
            target_value=float(threshold),
            difference=float(threshold - pct),
            variance_pct=0.0,
            details=f"Top tenant {pct:.1%} (max {threshold:.1%})",
            severity="high" if status == "FAIL" else "info",
            formula="Top tenant <= 20% of rent",
        )

    def _rule_covenant_6_reporting_requirements(self):
        """COVENANT-6: Reporting requirements – documents must be submitted by deadline (config: covenant_reporting_deadline_days)."""
        deadline_days = int(self._get_config_threshold("covenant_reporting_deadline_days", 0))
        if deadline_days <= 0:
            self._add_result(
                rule_id="COVENANT-6",
                rule_name="Reporting Requirements",
                category="Covenant",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Configure covenant_reporting_deadline_days in system_config for compliance check (days after period end).",
                severity="info",
                formula="Timely submission of required reports",
            )
            return
        period_end = self._get_period_end_date()
        if not period_end:
            self._add_result(
                rule_id="COVENANT-6",
                rule_name="Reporting Requirements",
                category="Covenant",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Period end date unavailable",
                severity="info",
                formula="Timely submission of required reports",
            )
            return
        deadline_date = period_end + timedelta(days=deadline_days)
        row = self.db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE (upload_date AT TIME ZONE 'UTC')::date <= :deadline) AS on_time,
                    COUNT(*) AS total
                FROM document_uploads
                WHERE property_id = :property_id AND period_id = :period_id AND is_active
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id), "deadline": deadline_date},
        ).fetchone()
        on_time = int(row[0] or 0)
        total = int(row[1] or 0)
        if total == 0:
            self._add_result(
                rule_id="COVENANT-6",
                rule_name="Reporting Requirements",
                category="Covenant",
                status="INFO",
                source_value=0.0,
                target_value=float(deadline_days),
                difference=0.0,
                variance_pct=0.0,
                details=f"No documents uploaded for period (deadline {deadline_date})",
                severity="info",
                formula="Timely submission of required reports",
            )
            return
        if on_time == 0:
            status = "FAIL"
            details = f"No documents submitted by deadline {deadline_date} ({total} uploaded after)"
        else:
            status = "PASS"
            details = f"Reporting submitted by deadline {deadline_date} ({on_time} document(s) on time)"
        self._add_result(
            rule_id="COVENANT-6",
            rule_name="Reporting Requirements",
            category="Covenant",
            status=status,
            source_value=float(on_time),
            target_value=float(total),
            difference=float(on_time - total),
            variance_pct=0.0,
            details=details,
            severity="high" if status == "FAIL" else "info",
            formula="Timely submission of required reports",
        )

    def _rule_benchmark_1_market_rent(self):
        target = self._get_config_threshold("benchmark_market_rent_per_sf", 0)
        revenue = self._get_metric("total_revenue")
        sqft = self._get_metric("total_leasable_sqft")
        actual = (revenue * 12 / sqft) if sqft else 0.0
        if target <= 0:
            if hasattr(self, "market_data_integration"):
                try:
                    market_rent = self.market_data_integration.get_market_rent_per_sf(self.property_id)
                except Exception:
                    market_rent = None
            else:
                market_rent = None
            self._add_result(
                rule_id="BENCHMARK-1",
                rule_name="Market Rent Comparison",
                category="Benchmark",
                status="INFO",
                source_value=float(actual),
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details=(
                    "Set benchmark_market_rent_per_sf in system_config to compare. "
                    "Market rent data not available in REIMS (external data required)"
                    if market_rent is None and actual == 0
                    else f"Rent/SF ${actual:,.2f}. Set benchmark_market_rent_per_sf to compare to market."
                ),
                severity="info",
                formula="Compare rent/SF to market",
            )
            return
        variance_pct = ((actual - target) / target * 100.0) if target else 0.0
        status = "PASS" if abs(variance_pct) <= 10.0 else "WARNING"
        self._add_result(
            rule_id="BENCHMARK-1",
            rule_name="Market Rent Comparison",
            category="Benchmark",
            status=status,
            source_value=float(actual),
            target_value=float(target),
            difference=float(actual - target),
            variance_pct=variance_pct,
            details=f"Rent/SF ${actual:,.2f} vs target ${target:,.2f} ({variance_pct:+.1f}%)",
            severity="info" if status == "PASS" else "medium",
            formula="Compare rent/SF to market",
        )

    def _rule_benchmark_2_opex_benchmark(self):
        target = self._get_config_threshold("benchmark_market_opex_per_sf", 0)
        expenses = self._get_metric("total_expenses")
        sqft = self._get_metric("total_leasable_sqft")
        actual = (expenses * 12 / sqft) if sqft else 0.0
        if target <= 0:
            self._add_result(
                rule_id="BENCHMARK-2",
                rule_name="Operating Expense Benchmark",
                category="Benchmark",
                status="INFO",
                source_value=float(actual),
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Set benchmark_market_opex_per_sf in system_config to compare to peers.",
                severity="info",
                formula="Compare OpEx/SF to peers",
            )
            return
        variance_pct = ((actual - target) / target * 100.0) if target else 0.0
        status = "PASS" if abs(variance_pct) <= 15.0 else "WARNING"
        self._add_result(
            rule_id="BENCHMARK-2",
            rule_name="Operating Expense Benchmark",
            category="Benchmark",
            status=status,
            source_value=float(actual),
            target_value=float(target),
            difference=float(actual - target),
            variance_pct=variance_pct,
            details=f"OpEx/SF ${actual:,.2f} vs target ${target:,.2f} ({variance_pct:+.1f}%)",
            severity="info" if status == "PASS" else "medium",
            formula="Compare OpEx/SF to peers",
        )

    def _rule_benchmark_3_occupancy_vs_market(self):
        target_pct = self._get_config_threshold("benchmark_market_occupancy_pct", 0)
        occ = self._get_metric("occupancy_rate")
        if occ == 0.0 and hasattr(self, "_get_rent_roll_summary"):
            rr = self._get_rent_roll_summary(self.period_id)
            if rr and rr.get("occupancy_pct") is not None:
                occ = rr["occupancy_pct"] / 100.0
        actual_pct = occ * 100.0
        if target_pct <= 0:
            self._add_result(
                rule_id="BENCHMARK-3",
                rule_name="Occupancy vs Market",
                category="Benchmark",
                status="INFO",
                source_value=float(actual_pct),
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Set benchmark_market_occupancy_pct in system_config (e.g. 90 for 90%) to compare.",
                severity="info",
                formula="Compare occupancy to market",
            )
            return
        variance_pct = (actual_pct - target_pct) if target_pct else 0.0
        status = "PASS" if actual_pct >= target_pct - 5.0 else "WARNING"
        self._add_result(
            rule_id="BENCHMARK-3",
            rule_name="Occupancy vs Market",
            category="Benchmark",
            status=status,
            source_value=float(actual_pct),
            target_value=float(target_pct),
            difference=float(actual_pct - target_pct),
            variance_pct=variance_pct,
            details=f"Occupancy {actual_pct:.1f}% vs target {target_pct:.1f}% ({variance_pct:+.1f} pp)",
            severity="info" if status == "PASS" else "medium",
            formula="Compare occupancy to market",
        )

    def _rule_benchmark_4_cap_rate_vs_market(self):
        target_pct = self._get_config_threshold("benchmark_market_cap_rate_pct", 0)
        noi = self._get_metric("net_operating_income")
        value = self._get_metric("net_property_value") or self._get_metric("gross_property_value")
        actual_pct = (noi / value * 100.0) if value else 0.0
        if target_pct <= 0:
            self._add_result(
                rule_id="BENCHMARK-4",
                rule_name="Cap Rate vs Market",
                category="Benchmark",
                status="INFO",
                source_value=float(actual_pct),
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Set benchmark_market_cap_rate_pct in system_config (e.g. 5 for 5%) to compare.",
                severity="info",
                formula="Compare cap rate to market",
            )
            return
        variance_pp = actual_pct - target_pct
        status = "PASS" if abs(variance_pp) <= 1.5 else "WARNING"
        self._add_result(
            rule_id="BENCHMARK-4",
            rule_name="Cap Rate vs Market",
            category="Benchmark",
            status=status,
            source_value=float(actual_pct),
            target_value=float(target_pct),
            difference=float(variance_pp),
            variance_pct=variance_pp,
            details=f"Cap rate {actual_pct:.2f}% vs target {target_pct:.2f}% ({variance_pp:+.2f} pp)",
            severity="info" if status == "PASS" else "medium",
            formula="Compare cap rate to market",
        )

    def _rule_trend_1_moving_average(self):
        rows = self.db.execute(
            text(
                """
                SELECT fm.total_revenue, fm.net_operating_income
                FROM financial_periods fp
                JOIN financial_metrics fm ON fm.period_id = fp.id
                WHERE fp.property_id = :property_id
                  AND (fp.period_year, fp.period_month) <= (
                    SELECT period_year, period_month FROM financial_periods WHERE id = :period_id
                  )
                ORDER BY fp.period_year DESC, fp.period_month DESC
                LIMIT 3
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if len(rows) < 3:
            self._add_result(
                rule_id="TREND-1",
                rule_name="3-Month Moving Average",
                category="Trend",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Insufficient periods for 3-month moving average",
                severity="info",
                formula="MA(3) for revenue and NOI",
            )
            return
        revenue_ma = sum(float(r[0] or 0.0) for r in rows) / 3
        noi_ma = sum(float(r[1] or 0.0) for r in rows) / 3
        self._add_result(
            rule_id="TREND-1",
            rule_name="3-Month Moving Average",
            category="Trend",
            status="PASS",
            source_value=float(revenue_ma),
            target_value=float(revenue_ma),
            difference=0.0,
            variance_pct=0.0,
            details=f"MA Revenue ${revenue_ma:,.2f}, MA NOI ${noi_ma:,.2f}",
            severity="info",
            formula="MA(3) for Revenue and NOI",
        )

    def _rule_trend_2_year_over_year(self):
        prior_id = self._get_prior_year_period_id()
        if not prior_id:
            self._add_result(
                rule_id="TREND-2",
                rule_name="Year-over-Year Comparison",
                category="Trend",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year period unavailable",
                severity="info",
                formula="YoY change for revenue/NOI",
            )
            return
        revenue_curr = self._get_metric("total_revenue", period_id=self.period_id)
        revenue_prior = self._get_metric("total_revenue", period_id=prior_id)
        noi_curr = self._get_metric("net_operating_income", period_id=self.period_id)
        noi_prior = self._get_metric("net_operating_income", period_id=prior_id)
        if revenue_prior == 0 or noi_prior == 0:
            self._add_result(
                rule_id="TREND-2",
                rule_name="Year-over-Year Comparison",
                category="Trend",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Prior year metrics unavailable",
                severity="info",
                formula="YoY change for revenue/NOI",
            )
            return
        rev_change = (revenue_curr - revenue_prior) / revenue_prior
        noi_change = (noi_curr - noi_prior) / noi_prior
        self._add_result(
            rule_id="TREND-2",
            rule_name="Year-over-Year Comparison",
            category="Trend",
            status="PASS",
            source_value=float(rev_change),
            target_value=float(rev_change),
            difference=0.0,
            variance_pct=0.0,
            details=f"YoY Revenue {rev_change:.1%}, NOI {noi_change:.1%}",
            severity="info",
            formula="YoY change for Revenue and NOI",
        )

    def _rule_trend_3_variance_analysis(self):
        """TREND-3: Variance analysis – budget vs actual by account (summary); complements AUDIT-51."""
        rows = self.db.execute(
            text(
                """
                SELECT
                    b.account_code,
                    COALESCE(b.account_name, '') AS account_name,
                    COALESCE(SUM(b.budgeted_amount), 0) AS budgeted,
                    COALESCE(SUM(i.period_amount), 0) AS actual
                FROM budgets b
                LEFT JOIN income_statement_data i
                  ON i.property_id = b.property_id
                 AND i.period_id = b.period_id
                 AND i.account_code = b.account_code
                WHERE b.property_id = :property_id
                  AND b.period_id = :period_id
                  AND b.status = 'approved'
                GROUP BY b.account_code, b.account_name
                HAVING ABS(COALESCE(SUM(b.budgeted_amount), 0)) > 0.01
                ORDER BY ABS(COALESCE(SUM(b.budgeted_amount), 0)) DESC
                LIMIT 10
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="TREND-3",
                rule_name="Variance Analysis",
                category="Trend",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="No approved budget data for period; see AUDIT-51/52 when budget/forecast exist.",
                severity="info",
                formula="Actual vs Budget variance",
            )
            return
        parts = []
        total_budget = total_actual = 0.0
        for r in rows:
            code, name, budgeted, actual = r[0], (r[1] or ""), float(r[2] or 0), float(r[3] or 0)
            total_budget += budgeted
            total_actual += actual
            var_pct = ((actual - budgeted) / budgeted * 100.0) if budgeted else 0.0
            parts.append(f"{code}: ${actual:,.0f} vs ${budgeted:,.0f} ({var_pct:+.1f}%)")
        overall_pct = ((total_actual - total_budget) / total_budget * 100.0) if total_budget else 0.0
        status = "PASS" if abs(overall_pct) <= 10.0 else "INFO"
        self._add_result(
            rule_id="TREND-3",
            rule_name="Variance Analysis",
            category="Trend",
            status=status,
            source_value=float(total_actual),
            target_value=float(total_budget),
            difference=float(total_actual - total_budget),
            variance_pct=overall_pct,
            details="Top accounts: " + "; ".join(parts),
            severity="info",
            formula="Actual vs Budget variance",
        )

    def _rule_stress_1_occupancy(self):
        rr = self._get_rent_roll_summary(self.period_id) if hasattr(self, "_get_rent_roll_summary") else None
        base_revenue = self._get_metric("total_revenue")
        base_noi = self._get_metric("net_operating_income")
        if not rr or base_revenue == 0:
            self._add_result(
                rule_id="STRESS-1",
                rule_name="Occupancy Stress Test",
                category="Stress",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Insufficient data for occupancy stress test",
                severity="info",
                formula="Revenue/NOI impact at lower occupancy",
            )
            return
        scenarios = [0.85, 0.80, 0.75]
        results = []
        current_occ = rr["occupancy_pct"] / 100.0 if rr else 0.0
        for occ in scenarios:
            if current_occ == 0:
                continue
            revenue = base_revenue * (occ / current_occ)
            noi = base_noi - (base_revenue - revenue)
            results.append(f"{int(occ*100)}% occ → NOI ${noi:,.2f}")
        self._add_result(
            rule_id="STRESS-1",
            rule_name="Occupancy Stress Test",
            category="Stress",
            status="PASS",
            source_value=float(base_revenue),
            target_value=float(base_revenue),
            difference=0.0,
            variance_pct=0.0,
            details="; ".join(results),
            severity="info",
            formula="Scenario analysis for occupancy decline",
        )

    def _rule_stress_2_rent_rate(self):
        revenue = self._get_metric("total_revenue")
        noi = self._get_metric("net_operating_income")
        if revenue == 0:
            self._add_result(
                rule_id="STRESS-2",
                rule_name="Rent Rate Stress Test",
                category="Stress",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Revenue data unavailable for rent rate stress",
                severity="info",
                formula="Revenue/NOI impact at lower rents",
            )
            return
        results = []
        for pct in [0.95, 0.90, 0.85]:
            rev = revenue * pct
            noi_stress = noi - (revenue - rev)
            results.append(f"{int((1-pct)*100)}% rent drop → NOI ${noi_stress:,.2f}")
        self._add_result(
            rule_id="STRESS-2",
            rule_name="Rent Rate Stress Test",
            category="Stress",
            status="PASS",
            source_value=float(revenue),
            target_value=float(revenue),
            difference=0.0,
            variance_pct=0.0,
            details="; ".join(results),
            severity="info",
            formula="Scenario analysis for rent rate reduction",
        )

    def _rule_stress_3_expense_inflation(self):
        expenses = self._get_metric("total_expenses")
        noi = self._get_metric("net_operating_income")
        if expenses == 0:
            self._add_result(
                rule_id="STRESS-3",
                rule_name="Expense Inflation Stress",
                category="Stress",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Expense data unavailable for inflation stress",
                severity="info",
                formula="NOI impact at higher expenses",
            )
            return
        results = []
        for pct in [0.05, 0.10, 0.15]:
            inflated = expenses * (1 + pct)
            noi_stress = noi - (inflated - expenses)
            results.append(f"+{int(pct*100)}% expenses → NOI ${noi_stress:,.2f}")
        self._add_result(
            rule_id="STRESS-3",
            rule_name="Expense Inflation Stress",
            category="Stress",
            status="PASS",
            source_value=float(expenses),
            target_value=float(expenses),
            difference=0.0,
            variance_pct=0.0,
            details="; ".join(results),
            severity="info",
            formula="Scenario analysis for expense inflation",
        )

    def _rule_stress_4_interest_rate(self):
        annual_debt_service = self._get_metric("total_annual_debt_service")
        base_rate = self._get_metric("weighted_avg_interest_rate")
        if annual_debt_service == 0 or base_rate == 0:
            self._add_result(
                rule_id="STRESS-4",
                rule_name="Interest Rate Stress",
                category="Stress",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Interest rate data unavailable for stress test",
                severity="info",
                formula="Debt service impact with rate shocks",
            )
            return
        results = []
        for delta in [0.01, 0.02, 0.03]:
            new_rate = base_rate + delta
            adjusted_debt_service = annual_debt_service * (new_rate / base_rate)
            results.append(f"+{int(delta*100)}% rate → debt service ${adjusted_debt_service:,.2f}")
        self._add_result(
            rule_id="STRESS-4",
            rule_name="Interest Rate Stress",
            category="Stress",
            status="PASS",
            source_value=float(annual_debt_service),
            target_value=float(annual_debt_service),
            difference=0.0,
            variance_pct=0.0,
            details="; ".join(results),
            severity="info",
            formula="Debt service impact with rate shocks",
        )

    def _rule_stress_5_tenant_loss(self):
        rows = self.db.execute(
            text(
                """
                SELECT tenant_name, COALESCE(annual_rent, monthly_rent * 12, 0) AS rent
                FROM rent_roll_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND (occupancy_status IS NULL OR occupancy_status NOT ILIKE 'vacant')
                ORDER BY rent DESC
                LIMIT 2
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchall()
        if not rows:
            self._add_result(
                rule_id="STRESS-5",
                rule_name="Tenant Loss Scenario",
                category="Stress",
                status="INFO",
                source_value=0.0,
                target_value=0.0,
                difference=0.0,
                variance_pct=0.0,
                details="Rent roll data unavailable for tenant loss scenario",
                severity="info",
                formula="Impact of losing top two tenants",
            )
            return
        lost_rent = sum(float(r[1] or 0.0) for r in rows)
        total_rent = self._get_metric("total_revenue") * 12
        pct = (lost_rent / total_rent) if total_rent else 0.0
        self._add_result(
            rule_id="STRESS-5",
            rule_name="Tenant Loss Scenario",
            category="Stress",
            status="PASS",
            source_value=float(pct),
            target_value=float(pct),
            difference=0.0,
            variance_pct=0.0,
            details=f"Top 2 tenants represent {pct:.1%} of annual revenue (rent loss ${lost_rent:,.2f})",
            severity="info",
            formula="Impact of losing top two tenants",
        )

    def _rule_dashboard_1_exec_summary(self):
        self._add_result(
            rule_id="DASHBOARD-1",
            rule_name="Executive Summary Dashboard",
            category="Dashboard",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Dashboard metrics assembled from Analytics/Covenant rules",
            severity="info",
            formula="Summary dashboard metrics",
        )

    def _rule_dashboard_2_operational(self):
        self._add_result(
            rule_id="DASHBOARD-2",
            rule_name="Operational Dashboard",
            category="Dashboard",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Operational dashboard supported by analytics and audit outputs",
            severity="info",
            formula="Operational metrics dashboard",
        )

    def _rule_dashboard_3_lender_package(self):
        self._add_result(
            rule_id="DASHBOARD-3",
            rule_name="Lender Reporting Package",
            category="Dashboard",
            status="INFO",
            source_value=0.0,
            target_value=0.0,
            difference=0.0,
            variance_pct=0.0,
            details="Lender package includes DSCR, LTV, occupancy, rent roll, delinquency",
            severity="info",
            formula="Lender reporting package completeness",
        )
