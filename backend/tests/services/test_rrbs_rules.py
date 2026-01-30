"""Unit tests for Rent Roll / Balance Sheet rules (RRBS-2 bands, RRBS-3 threshold)."""
from unittest.mock import MagicMock

import pytest

from app.services.rules.rent_roll_balance_sheet_rules_mixin import RentRollBalanceSheetRulesMixin
from app.services.reconciliation_types import ReconciliationResult


def _band_for_ar_months(ar_months: float) -> str:
    """Replicate spec bands for testing."""
    if ar_months < 0.5:
        return "Excellent"
    if ar_months < 1.0:
        return "Good"
    if ar_months < 2.0:
        return "Acceptable"
    if ar_months < 3.0:
        return "Concerning"
    return "Critical"


@pytest.mark.parametrize(
    "ar_months,expected_band",
    [
        (0.3, "Excellent"),
        (0.5, "Good"),
        (0.99, "Good"),
        (1.0, "Acceptable"),
        (1.5, "Acceptable"),
        (2.0, "Concerning"),
        (2.5, "Concerning"),
        (3.0, "Critical"),
        (4.0, "Critical"),
    ],
)
def test_rrbs_2_ar_reasonableness_bands(ar_months: float, expected_band: str):
    assert _band_for_ar_months(ar_months) == expected_band


def test_rrbs_2_ar_reasonableness_emits_band_and_ar_months():
    """RRBS-2 should emit details containing AR_Months and band."""
    db = MagicMock()
    # AR = 1500, RR monthly = 1000 -> AR_Months = 1.5, band = Acceptable
    call_count = [0]

    def scalar_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 1500.0  # ar
        return 1000.0  # rr_monthly

    db.execute.return_value.scalar.side_effect = scalar_side_effect

    class Engine(RentRollBalanceSheetRulesMixin):
        def __init__(self):
            self.db = db
            self.results = []
            self.property_id = 1
            self.period_id = 1

    engine = Engine()
    engine._rule_rrbs_2_ar_reasonableness()

    assert len(engine.results) == 1
    r = engine.results[0]
    assert r.rule_id == "RRBS-2"
    assert "AR_Months=1.50" in r.details or "1.5" in r.details
    assert "Acceptable" in r.details
    assert r.intermediate_calculations.get("ar_months") == 1.5
    assert r.intermediate_calculations.get("band") == "Acceptable"


def test_rrbs_3_uses_default_20k_threshold():
    """RRBS-3 with no _get_config_threshold uses 20000 default."""
    db = MagicMock()
    call_count = [0]

    def scalar_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 2  # prior_id
        if call_count[0] == 2:
            return 15000.0  # curr prepaid
        return 0.0  # prior prepaid -> delta 15000, below 20k -> PASS

    db.execute.return_value.scalar.side_effect = scalar_side_effect

    class Engine(RentRollBalanceSheetRulesMixin):
        def __init__(self):
            self.db = db
            self.results = []
            self.property_id = 1
            self.period_id = 1

        def _get_prior_period_id(self):
            return 2

    engine = Engine()
    engine._rule_rrbs_3_prepaid_rent()

    assert len(engine.results) == 1
    r = engine.results[0]
    assert r.rule_id == "RRBS-3"
    assert r.status == "PASS"
    assert "20,000" in r.details or "20000" in r.details


def test_rrbs_3_fail_above_threshold():
    """RRBS-3 delta above 20k should FAIL."""
    db = MagicMock()
    call_count = [0]

    def scalar_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 2
        if call_count[0] == 2:
            return 50000.0  # curr
        return 10000.0  # prior -> delta 40000 -> FAIL

    db.execute.return_value.scalar.side_effect = scalar_side_effect

    class Engine(RentRollBalanceSheetRulesMixin):
        def __init__(self):
            self.db = db
            self.results = []
            self.property_id = 1
            self.period_id = 1

        def _get_prior_period_id(self):
            return 2

    engine = Engine()
    engine._rule_rrbs_3_prepaid_rent()

    assert len(engine.results) == 1
    assert engine.results[0].status == "FAIL"
