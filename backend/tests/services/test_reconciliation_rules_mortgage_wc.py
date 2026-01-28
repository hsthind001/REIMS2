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
        def __init__(self, scalar_value=0.0, rows=None):
            self._scalar_value = scalar_value
            self._rows = rows or []

        def scalar(self):
            return self._scalar_value

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

