from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text


@dataclass
class PeriodAlignmentContext:
    """Resolved alignment window for cross-statement reconciliation."""

    property_id: int
    end_period_id: int
    end_year: int
    end_month: int

    begin_period_id: Optional[int] = None
    begin_year: Optional[int] = None
    begin_month: Optional[int] = None

    # March -> May should be 2 months (Apr, May).
    window_months: int = 1

    period_type_by_statement: Dict[str, str] = field(default_factory=dict)
    alignment_method: str = "prior_month_fallback"
    alignment_confidence: float = 0.0

    # Cash alignment signals
    cf_beginning_cash: float = 0.0
    cf_ending_cash: float = 0.0
    cf_cash_delta: float = 0.0

    bs_beginning_cash: float = 0.0
    bs_ending_cash: float = 0.0
    bs_cash_delta: float = 0.0

    # Cash begin-match diagnostics (PAL-3 transparency)
    cash_match_period_id: Optional[int] = None
    cash_match_bs_cash: float = 0.0
    cash_match_diff: float = 0.0
    cash_match_best_diff: float = 0.0
    cash_match_candidate_count: int = 0
    cash_match_within_tolerance: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for intermediate_calculations JSON storage."""
        return asdict(self)


class PeriodAlignmentMixin:
    """
    Period alignment helpers for mixed single-month and rolling-window statements.

    Implements the core PAL / FA-PAL rules:
    - Determine period types by statement
    - Infer begin month from CF beginning cash matched to BS total cash
    - Provide begin/end window helpers for delta calculations
    """

    alignment_context: Optional[PeriodAlignmentContext] = None

    # Matching tolerance for cash alignment (PAL-3 / FA-PAL-3)
    CASH_MATCH_TOLERANCE = 1.00

    def _initialize_period_alignment(self) -> PeriodAlignmentContext:
        """Resolve the alignment window once per rule-engine run."""
        end_year, end_month = self._get_period_year_month(self.period_id)

        context = PeriodAlignmentContext(
            property_id=int(self.property_id),
            end_period_id=int(self.period_id),
            end_year=end_year,
            end_month=end_month,
        )

        context.period_type_by_statement = self._detect_period_types()

        cf_begin, cf_end, cf_delta = self._get_cf_cash_table_totals()
        context.cf_beginning_cash = cf_begin
        context.cf_ending_cash = cf_end
        context.cf_cash_delta = cf_delta

        context.bs_ending_cash = self._get_bs_total_cash(self.period_id)

        begin_period_id, method, confidence = self._infer_begin_period_id(context)
        context.begin_period_id = begin_period_id
        context.alignment_method = method
        context.alignment_confidence = confidence

        if begin_period_id:
            begin_year, begin_month = self._get_period_year_month(begin_period_id)
            context.begin_year = begin_year
            context.begin_month = begin_month

            context.window_months = max(
                1, self._months_between(begin_year, begin_month, end_year, end_month)
            )

            context.bs_beginning_cash = self._get_bs_total_cash(begin_period_id)
            context.bs_cash_delta = context.bs_ending_cash - context.bs_beginning_cash
        else:
            # Prior-month fallback (still useful for single-month statements)
            prior_id = self._get_prior_period_id()
            if prior_id:
                prior_year, prior_month = self._get_period_year_month(prior_id)
                context.begin_period_id = prior_id
                context.begin_year = prior_year
                context.begin_month = prior_month
                context.window_months = 1
                context.bs_beginning_cash = self._get_bs_total_cash(prior_id)
                context.bs_cash_delta = context.bs_ending_cash - context.bs_beginning_cash
                context.alignment_method = "prior_month_fallback"
                context.alignment_confidence = max(context.alignment_confidence, 0.5)

        self.alignment_context = context
        return context

    def _get_alignment_context(self) -> PeriodAlignmentContext:
        """Get cached alignment context, initializing if necessary."""
        if self.alignment_context is None:
            try:
                return self._initialize_period_alignment()
            except Exception:
                end_year, end_month = self._get_period_year_month(self.period_id)
                fallback = PeriodAlignmentContext(
                    property_id=int(self.property_id),
                    end_period_id=int(self.period_id),
                    end_year=end_year,
                    end_month=end_month,
                )
                prior_id = self._get_prior_period_id()
                if prior_id:
                    prior_year, prior_month = self._get_period_year_month(prior_id)
                    fallback.begin_period_id = prior_id
                    fallback.begin_year = prior_year
                    fallback.begin_month = prior_month
                    fallback.window_months = 1
                    fallback.alignment_method = "alignment_error_fallback"
                    fallback.alignment_confidence = 0.25
                self.alignment_context = fallback
                return fallback
        return self.alignment_context

    def _get_effective_begin_period_id(self) -> Optional[int]:
        """Best available begin period for window deltas."""
        ctx = self._get_alignment_context()
        return ctx.begin_period_id or self._get_prior_period_id()

    def _get_window_months(self) -> int:
        """Length of the rolling window in months (PAL-4 helper)."""
        return self._get_alignment_context().window_months

    def _get_bs_delta_in_window(
        self,
        *,
        account_code_pattern: Optional[str] = None,
        account_name_pattern: Optional[str] = None,
    ) -> Tuple[float, float, float, Optional[int]]:
        """
        Compute Δ(Account) across the aligned window (PAL-4).

        Returns:
            delta, begin_value, end_value, begin_period_id
        """
        begin_period_id = self._get_effective_begin_period_id()
        if not begin_period_id:
            return 0.0, 0.0, 0.0, None

        end_value = self._get_bs_value(
            account_code_pattern=account_code_pattern,
            account_name_pattern=account_name_pattern,
            period_id=self.period_id,
        )
        begin_value = self._get_bs_value(
            account_code_pattern=account_code_pattern,
            account_name_pattern=account_name_pattern,
            period_id=begin_period_id,
        )

        delta = end_value - begin_value
        return delta, begin_value, end_value, begin_period_id

    # ------------------------------------------------------------------
    # Alignment internals
    # ------------------------------------------------------------------

    def _detect_period_types(self) -> Dict[str, str]:
        """
        Determine period type by statement using header date ranges (PAL-1).

        Balance sheet / rent roll / mortgage statements remain single-month.
        Income statement and cash flow may be rolling windows.
        """
        period_types = {
            "balance_sheet": "SINGLE_MONTH",
            "income_statement": "SINGLE_MONTH",
            "cash_flow": "SINGLE_MONTH",
            "rent_roll": "SINGLE_MONTH",
            "mortgage_statement": "SINGLE_MONTH",
        }

        # Income Statement header window
        is_row = self.db.execute(
            text(
                """
                SELECT report_period_start, report_period_end
                FROM income_statement_headers
                WHERE property_id = :property_id AND period_id = :period_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()
        if is_row:
            period_types["income_statement"] = self._classify_period_type(is_row[0], is_row[1])

        # Cash Flow header window
        cf_row = self.db.execute(
            text(
                """
                SELECT report_period_start, report_period_end
                FROM cash_flow_headers
                WHERE property_id = :property_id AND period_id = :period_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()
        if cf_row:
            period_types["cash_flow"] = self._classify_period_type(cf_row[0], cf_row[1])

        return period_types

    def _classify_period_type(self, start_date: Any, end_date: Any) -> str:
        """Classify as rolling window when start/end months differ."""
        if not start_date or not end_date:
            return "SINGLE_MONTH"

        try:
            start_year, start_month = start_date.year, start_date.month
            end_year, end_month = end_date.year, end_date.month
        except AttributeError:
            return "SINGLE_MONTH"

        return "ROLLING_WINDOW" if (start_year, start_month) != (end_year, end_month) else "SINGLE_MONTH"

    def _get_cf_cash_table_totals(self) -> Tuple[float, float, float]:
        """
        Extract CF beginning/ending total cash from the cash table (PAL-3).

        Falls back to cash flow header and then to CF line items.
        """
        # Primary: cash account reconciliation total row
        total_row = self.db.execute(
            text(
                """
                SELECT beginning_balance, ending_balance
                FROM cash_account_reconciliations
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND is_total_row = true
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()

        if total_row and total_row[0] is not None and total_row[1] is not None:
            begin_cash = float(total_row[0])
            end_cash = float(total_row[1])
            return begin_cash, end_cash, end_cash - begin_cash

        # Secondary: cash flow header
        header_row = self.db.execute(
            text(
                """
                SELECT beginning_cash_balance, ending_cash_balance
                FROM cash_flow_headers
                WHERE property_id = :property_id AND period_id = :period_id
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"property_id": int(self.property_id), "period_id": int(self.period_id)},
        ).fetchone()
        if header_row and header_row[0] is not None and header_row[1] is not None:
            begin_cash = float(header_row[0])
            end_cash = float(header_row[1])
            return begin_cash, end_cash, end_cash - begin_cash

        # Tertiary: CF line items (best-effort)
        begin_cash = self._get_cf_value(account_name_pattern="%BEGINNING%CASH%")
        end_cash = self._get_cf_value(account_name_pattern="%ENDING%CASH%")
        return begin_cash, end_cash, end_cash - begin_cash

    def _get_bs_total_cash(self, period_id: int) -> float:
        """
        Compute total cash for a balance sheet period.

        Strategy:
        1) Sum detail cash accounts (non-total/subtotal rows)
        2) Fall back to explicit "Total Cash" line if present
        3) Fall back to broad 01% cash code patterns
        """
        detail_sum = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE :cash_pattern
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(period_id),
                "cash_pattern": "%cash%",
            },
        ).scalar()

        detail_cash = float(detail_sum or 0.0)
        if abs(detail_cash) > 0.01:
            return detail_cash

        total_cash_row = self.db.execute(
            text(
                """
                SELECT amount
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_name ILIKE :total_cash_pattern
                ORDER BY ABS(amount) DESC
                LIMIT 1
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(period_id),
                "total_cash_pattern": "%total cash%",
            },
        ).scalar()
        if total_cash_row is not None:
            return float(total_cash_row)

        code_cash_row = self.db.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM balance_sheet_data
                WHERE property_id = :property_id
                  AND period_id = :period_id
                  AND account_code LIKE :cash_code_pattern
                  AND (is_total IS NOT TRUE)
                  AND (is_subtotal IS NOT TRUE)
                """
            ),
            {
                "property_id": int(self.property_id),
                "period_id": int(period_id),
                "cash_code_pattern": "01%",
            },
        ).scalar()
        return float(code_cash_row or 0.0)

    def _infer_begin_period_id(
        self, context: PeriodAlignmentContext
    ) -> Tuple[Optional[int], str, float]:
        """
        Infer the begin period using CF beginning cash matched to BS cash (PAL-3).
        """
        cf_beginning_cash = context.cf_beginning_cash
        if abs(cf_beginning_cash) <= 0.01:
            return None, "cash_begin_missing", 0.0

        candidates = self._get_candidate_periods(
            context.end_year, context.end_month, limit=24
        )
        context.cash_match_candidate_count = len(candidates)

        best_match: Optional[Tuple[int, int, int, float, float]] = None
        for period_id, year, month in candidates:
            # Skip the end period. We want the opening balance period.
            if int(period_id) == int(context.end_period_id):
                continue

            bs_cash = self._get_bs_total_cash(period_id)
            diff = abs(bs_cash - cf_beginning_cash)

            if best_match is None or diff < best_match[4]:
                best_match = (period_id, year, month, bs_cash, diff)

        if best_match is None:
            return None, "no_candidates", 0.0

        period_id, year, month, bs_cash, diff = best_match
        context.cash_match_period_id = int(period_id)
        context.cash_match_bs_cash = float(bs_cash)
        context.cash_match_best_diff = float(diff)
        context.cash_match_diff = float(diff)
        context.cash_match_within_tolerance = diff <= self.CASH_MATCH_TOLERANCE
        if diff <= self.CASH_MATCH_TOLERANCE:
            # Confidence degrades as we approach the tolerance boundary.
            confidence = max(0.5, 1.0 - (diff / max(self.CASH_MATCH_TOLERANCE, 1.0)))
            return int(period_id), "cash_begin_match", confidence

        # We found a "nearest" match but it is outside tolerance.
        return None, "cash_begin_no_match", 0.1

    def _get_candidate_periods(
        self, end_year: int, end_month: int, *, limit: int
    ) -> List[Tuple[int, int, int]]:
        """Get candidate periods up to the end period."""
        rows = self.db.execute(
            text(
                """
                SELECT id, period_year, period_month
                FROM financial_periods
                WHERE property_id = :property_id
                  AND (
                    period_year < :end_year
                    OR (period_year = :end_year AND period_month <= :end_month)
                  )
                ORDER BY period_year DESC, period_month DESC
                LIMIT :limit
                """
            ),
            {
                "property_id": int(self.property_id),
                "end_year": int(end_year),
                "end_month": int(end_month),
                "limit": int(limit),
            },
        ).fetchall()
        return [(int(r[0]), int(r[1]), int(r[2])) for r in rows]

    def _get_period_year_month(self, period_id: int) -> Tuple[int, int]:
        """Get period year/month for a financial period ID."""
        row = self.db.execute(
            text(
                """
                SELECT period_year, period_month
                FROM financial_periods
                WHERE id = :period_id AND property_id = :property_id
                LIMIT 1
                """
            ),
            {"period_id": int(period_id), "property_id": int(self.property_id)},
        ).fetchone()
        if not row:
            # Safe default to avoid hard failures in rules.
            return 0, 0
        return int(row[0]), int(row[1])

    def _months_between(
        self, start_year: int, start_month: int, end_year: int, end_month: int
    ) -> int:
        """
        Count months between period endpoints.

        March -> May should return 2 (Apr, May).
        """
        return max(0, (end_year - start_year) * 12 + (end_month - start_month))
