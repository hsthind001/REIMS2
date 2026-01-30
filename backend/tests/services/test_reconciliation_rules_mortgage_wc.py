import types

import pytest

from app.services.rules.audit_rules_mixin import AuditRulesMixin
from app.services.rules.forensic_anomaly_rules_mixin import ForensicAnomalyRulesMixin
from app.services.reconciliation_types import ReconciliationResult


class DummyDB:
    """
    Minimal DB stub that returns 0 for all scalar values and empty lists
    for fetchall(), so rule methods can be smoke-tested without a real DB.
    """

    class _Result:
        def __init__(self, scalar_value=0.0, rows=None, one=None):
            self._scalar_value = scalar_value
            self._rows = rows or []
            self._one = one  # for fetchone(); None = no row

        def scalar(self):
            return self._scalar_value

        def fetchone(self):
            return self._one

        def fetchall(self):
            return list(self._rows)

    def execute(self, *_args, **_kwargs):
        return self._Result()


class DummyEngine(AuditRulesMixin, ForensicAnomalyRulesMixin):
    def __init__(self):
        # attributes expected by the mixins
        self.db = DummyDB()
        self.results: list[ReconciliationResult] = []
        self.property_id = 1
        self.period_id = 1

    # helpers referenced from mixins but not relevant for smoke tests
    def _get_effective_begin_period_id(self):
        return 1

    def _get_alignment_context(self):
        class Ctx:
            window_months = 1

            def to_dict(self):
                return {"window_months": 1}

        return Ctx()

    def _get_bs_value(self, *_, **__):
        return 0.0

    def _get_is_value(self, *_, **__):
        return 0.0

    def _get_cf_value(self, *_, **__):
        return 0.0

    def _sum_bs_accounts(self, *_args, **_kwargs):
        return 0.0

    def _sum_cf_accounts(self, *_args, **_kwargs):
        return 0.0

    def _get_mst_value(self, *_args, **_kwargs):
        return 0.0

    def _get_window_date_range(self, *_args, **_kwargs):
        # return a dummy (start, end) window
        return None, None

    # Stubs so AUDIT-49, AUDIT-50, FA-MORT-4 can run without real DB
    def _get_period_year_month(self, period_id):
        return 2025, 1  # January so AUDIT-49 runs full path

    def _get_period_id_for_year_month(self, year, month):
        return 1  # prior period exists so AUDIT-50 runs

    def _get_numeric_config(self, key, default):
        return default


@pytest.fixture
def engine():
    return DummyEngine()


def _collect_ids(results: list[ReconciliationResult]) -> set[str]:
    return {r.rule_id for r in results}


def test_mortgage_and_working_capital_rules_do_not_crash(engine: DummyEngine):
    """
    Smoke test: calling newly added mortgage/WC rules should not raise,
    and should append well-formed ReconciliationResult objects.
    """
    # Clear any previous results
    engine.results = []

    # Call new audit rules
    engine._rule_wcr_1_generic_delta_reconciliation()
    engine._rule_wcr_2_account_appearance_disappearance()
    engine._rule_wcr_3_escrow_activity_three_way()
    engine._rule_mci_4_principal_reduction_validation()
    engine._rule_mci_6_escrow_funding_vs_disbursements()

    rule_ids = _collect_ids(engine.results)

    # Expect each rule to have produced at least one result
    assert "WCR-1" in rule_ids
    assert "WCR-2" in rule_ids
    assert "WCR-3" in rule_ids
    assert "MCI-4" in rule_ids
    assert any(rid.startswith("MCI-6-") for rid in rule_ids)


def test_forensic_enhancement_rules_do_not_crash(engine: DummyEngine):
    """
    Smoke test: calling new forensic rules should not raise and should
    append ReconciliationResult objects with expected IDs.
    """
    engine.results = []

    engine._rule_fa_wc_1_working_capital_attribution()
    engine._rule_fa_mort_1_payment_history_continuity()
    engine._rule_fa_mort_2_escrow_balance_reasonableness()
    engine._rule_fa_rr_1_lease_term_consistency()

    rule_ids = _collect_ids(engine.results)

    assert "FA-WC-1" in rule_ids
    assert "FA-MORT-1" in rule_ids
    assert "FA-MORT-2" in rule_ids
    assert "FA-RR-1" in rule_ids


def test_audit_49_50_fa_mort_4_produce_result(engine: DummyEngine):
    """
    Regression: AUDIT-49 (year-end), AUDIT-50 (YoY), FA-MORT-4 (escrow docs)
    run without error and each append exactly one result with expected rule_id.
    """
    engine.results = []

    engine._rule_audit_49_year_end_validation()
    engine._rule_audit_50_year_over_year_comparison()
    engine._rule_fa_mort_4_escrow_documentation_link()

    rule_ids = [r.rule_id for r in engine.results]
    assert "AUDIT-49" in rule_ids, "AUDIT-49 should produce a result"
    assert "AUDIT-50" in rule_ids, "AUDIT-50 should produce a result"
    assert "FA-MORT-4" in rule_ids, "FA-MORT-4 should produce a result"

    audit_49 = [r for r in engine.results if r.rule_id == "AUDIT-49"]
    audit_50 = [r for r in engine.results if r.rule_id == "AUDIT-50"]
    fa_mort_4 = [r for r in engine.results if r.rule_id == "FA-MORT-4"]
    assert len(audit_49) == 1, "AUDIT-49 should append exactly one result"
    assert len(audit_50) == 1, "AUDIT-50 should append exactly one result"
    assert len(fa_mort_4) == 1, "FA-MORT-4 should append exactly one result"

    # With dummy data (zeros/empty), AUDIT-49 runs January path; AUDIT-50 runs YoY; FA-MORT-4 runs with no material disbursements
    assert audit_49[0].status in ("PASS", "WARNING", "INFO")
    assert audit_50[0].status in ("PASS", "WARNING", "INFO")
    assert fa_mort_4[0].status in ("PASS", "WARNING")

