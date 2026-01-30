"""Unit tests for covenant_resolver (per-property covenant thresholds)."""
import calendar
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.services.rules.covenant_resolver import (
    get_period_end_date,
    get_covenant_threshold_sync,
    get_numeric_config_sync,
    resolve_covenant_threshold_sync,
    COVENANT_TYPE_TO_CONFIG_KEY,
    COVENANT_CONFIG_DEFAULTS,
)


def test_covenant_type_to_config_key():
    assert COVENANT_TYPE_TO_CONFIG_KEY["DSCR"] == "covenant_dscr_minimum"
    assert COVENANT_TYPE_TO_CONFIG_KEY["LTV"] == "covenant_ltv_maximum"
    assert COVENANT_TYPE_TO_CONFIG_KEY["MIN_LIQUIDITY"] == "covenant_liquidity_months"
    assert COVENANT_TYPE_TO_CONFIG_KEY["OCCUPANCY"] == "covenant_occupancy_minimum"
    assert COVENANT_TYPE_TO_CONFIG_KEY["SINGLE_TENANT_MAX"] == "covenant_single_tenant_maximum"


def test_covenant_config_defaults():
    assert COVENANT_CONFIG_DEFAULTS["DSCR"] == 1.25
    assert COVENANT_CONFIG_DEFAULTS["LTV"] == 75.0
    assert COVENANT_CONFIG_DEFAULTS["MIN_LIQUIDITY"] == 3.0
    assert COVENANT_CONFIG_DEFAULTS["OCCUPANCY"] == 85.0
    assert COVENANT_CONFIG_DEFAULTS["SINGLE_TENANT_MAX"] == 20.0


def test_get_period_end_date():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (2025, 6)
    end = get_period_end_date(db, 1)
    assert end == date(2025, 6, 30)
    db.execute.return_value.fetchone.return_value = (2024, 2)
    end = get_period_end_date(db, 2)
    assert end == date(2024, 2, 29)


def test_get_period_end_date_missing():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    assert get_period_end_date(db, 999) is None


def test_resolve_covenant_threshold_sync_ltv_conversion():
    """LTV stored as percent (75) should be returned as ratio (0.75)."""
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (2025, 6)
    chain_ct = MagicMock()
    chain_ct.filter.return_value.order_by.return_value.limit.return_value.first.return_value = None
    chain_sc = MagicMock()
    chain_sc.filter.return_value.limit.return_value.first.return_value = ("75",)
    db.query.side_effect = [chain_ct, chain_sc]
    result = resolve_covenant_threshold_sync(db, 1, 1, "LTV")
    assert result == 0.75


def test_resolve_covenant_threshold_sync_dscr_default():
    """DSCR with no config returns default 1.25."""
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = (2025, 1)
    ct_chain = MagicMock()
    ct_chain.filter.return_value.order_by.return_value.limit.return_value.first.return_value = None
    sc_chain = MagicMock()
    sc_chain.filter.return_value.limit.return_value.first.return_value = None
    db.query.side_effect = [ct_chain, sc_chain]
    result = resolve_covenant_threshold_sync(db, 1, 1, "DSCR")
    assert result == 1.25


def test_get_numeric_config_sync_missing():
    db = MagicMock()
    db.query.return_value.filter.return_value.limit.return_value.first.return_value = None
    assert get_numeric_config_sync(db, "unknown_key", 99.0) == 99.0


def test_get_numeric_config_sync_present():
    db = MagicMock()
    db.query.return_value.filter.return_value.limit.return_value.first.return_value = ("2.5",)
    assert get_numeric_config_sync(db, "some_key", 1.0) == 2.5
