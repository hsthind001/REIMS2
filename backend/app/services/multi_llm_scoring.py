"""
Deterministic scoring and gate routing for multi-LLM extraction (AbeAI-style).
Confidence is computed from evidence strength, concordance, and invariant checks; model self-confidence is ignored.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.master_json import (
    MasterJSON,
    MasterJSONCandidates,
    MasterJSONEvidence,
    MasterJSONValidation,
    MasterJSONDecision,
    FieldDecision,
)

logger = logging.getLogger(__name__)

# Gate outcome constants
AUTO_ACCEPT = "AUTO_ACCEPT"
AUTO_RETRY = "AUTO_RETRY"
ESCALATE_LLM = "ESCALATE_LLM"
NEEDS_REVIEW = "NEEDS_REVIEW"

# Default thresholds (from plan Appendix A)
AUTO_ACCEPT_CONFIDENCE = 0.85
AUTO_ACCEPT_EVIDENCE_COVERAGE = 0.90
ESCALATE_LLM_CONFIDENCE_MIN = 0.60
ESCALATE_LLM_CONFIDENCE_MAX = 0.85
ESCALATE_LLM_EVIDENCE_MIN = 0.60
NEEDS_REVIEW_CONFIDENCE_MAX = 0.60
NEEDS_REVIEW_EVIDENCE_MAX = 0.60


def _concordance_score(candidates: MasterJSONCandidates) -> float:
    """Compute concordance: fraction of candidates that agree on key numeric fields (e.g. totals)."""
    entries = [e for e in candidates.entries if e.parsed_json and not e.error]
    if len(entries) < 2:
        return 1.0
    totals_keys = ["total_assets", "total_liabilities", "total_equity", "total_revenue", "total_expenses", "net_operating_income"]
    agreements = 0
    total_checks = 0
    for key in totals_keys:
        values = []
        for e in entries:
            v = e.parsed_json.get(key)
            if v is not None:
                values.append(round(float(v), 2))
        if len(values) >= 2:
            total_checks += 1
            if len(set(values)) == 1:
                agreements += 1
    if total_checks == 0:
        return 1.0
    return agreements / total_checks


def _invariant_checks_balance_sheet(parsed_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check Assets = Liabilities + Equity (with tolerance). Returns (pass, fail_reasons)."""
    fail_reasons = []
    total_assets = parsed_json.get("total_assets")
    total_liabilities = parsed_json.get("total_liabilities")
    total_equity = parsed_json.get("total_equity")
    if total_assets is None and total_liabilities is None and total_equity is None:
        return True, []
    try:
        a = float(total_assets or 0)
        l = float(total_liabilities or 0)
        e = float(total_equity or 0)
    except (TypeError, ValueError):
        return False, ["Invalid numeric totals"]
    diff = abs(a - (l + e))
    if diff > 0.01:
        fail_reasons.append(f"Assets ({a}) != Liabilities + Equity ({l + e}), diff={diff}")
        return False, fail_reasons
    return True, []


def run_invariant_checks(doc_type: str, parsed_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Run invariant checks for document type. Returns (all_passed, fail_reasons)."""
    if doc_type == "balance_sheet":
        return _invariant_checks_balance_sheet(parsed_json)
    return True, []


def compute_confidence(
    master: MasterJSON,
    rule_pass_rate: Optional[float] = None,
    invariant_pass: Optional[bool] = None,
) -> float:
    """
    Compute deterministic confidence from evidence coverage, concordance, extraction quality, rule pass rate, invariants.
    Model self-confidence is never used.
    """
    evidence_coverage = master.evidence.coverage_pct
    if evidence_coverage is None:
        evidence_coverage = 1.0 if not master.evidence.entries else (
            sum(1 for e in master.evidence.entries if e.snippet) / max(1, len(master.evidence.entries))
        )
    concordance = _concordance_score(master.candidates)
    extraction_score = (master.extraction.confidence_score or 0) / 100.0 if master.extraction.confidence_score else 0.5
    rule_score = rule_pass_rate if rule_pass_rate is not None else 1.0
    invariant_score = 1.0 if invariant_pass is True else (0.0 if invariant_pass is False else 0.5)
    # Weighted combination
    confidence = (
        0.25 * evidence_coverage
        + 0.25 * concordance
        + 0.20 * extraction_score
        + 0.15 * rule_score
        + 0.15 * invariant_score
    )
    return round(min(1.0, max(0.0, confidence)), 4)


def compute_gate(
    confidence: float,
    evidence_coverage: float,
    invariant_pass: bool,
    extraction_quality_low: bool = False,
) -> str:
    """
    Map confidence, evidence coverage, and invariants to gate outcome.
    """
    if not invariant_pass:
        return NEEDS_REVIEW
    if extraction_quality_low:
        return AUTO_RETRY
    if confidence >= AUTO_ACCEPT_CONFIDENCE and evidence_coverage >= AUTO_ACCEPT_EVIDENCE_COVERAGE:
        return AUTO_ACCEPT
    if confidence < NEEDS_REVIEW_CONFIDENCE_MAX or evidence_coverage < NEEDS_REVIEW_EVIDENCE_MAX:
        return NEEDS_REVIEW
    if ESCALATE_LLM_CONFIDENCE_MIN <= confidence < ESCALATE_LLM_CONFIDENCE_MAX or (
        evidence_coverage >= ESCALATE_LLM_EVIDENCE_MIN and evidence_coverage < AUTO_ACCEPT_EVIDENCE_COVERAGE
    ):
        return ESCALATE_LLM
    return NEEDS_REVIEW


def score_and_route(
    master: MasterJSON,
    rule_pass_rate: Optional[float] = None,
    validation_results_ref: Optional[Dict[str, Any]] = None,
) -> Tuple[float, str, MasterJSONDecision]:
    """
    Compute confidence, gate, and decision section from Master JSON and optional validation/rule pass rate.
    Returns (confidence, overall_gate, decision_section).
    """
    # Pick first valid candidate for invariant check
    chosen_parsed = None
    for e in master.candidates.entries:
        if e.parsed_json and not e.error:
            chosen_parsed = e.parsed_json
            break
    invariant_pass = True
    fail_reasons: List[str] = []
    if chosen_parsed and master.header.doc_type:
        invariant_pass, fail_reasons = run_invariant_checks(master.header.doc_type, chosen_parsed)
    evidence_coverage = master.evidence.coverage_pct or 0.0
    if master.evidence.entries and evidence_coverage == 0:
        evidence_coverage = sum(1 for e in master.evidence.entries if e.snippet) / max(1, len(master.evidence.entries))
    confidence = compute_confidence(master, rule_pass_rate=rule_pass_rate, invariant_pass=invariant_pass)
    extraction_quality_low = (master.extraction.confidence_score or 0) < 50
    overall_gate = compute_gate(
        confidence,
        evidence_coverage,
        invariant_pass,
        extraction_quality_low=extraction_quality_low,
    )
    field_decisions: List[FieldDecision] = []
    if chosen_parsed and chosen_parsed.get("line_items"):
        for i, item in enumerate(chosen_parsed["line_items"][:50]):
            name = item.get("account_name") or item.get("tenant_name") or item.get("unit_id") or f"item_{i}"
            val = item.get("amount") or item.get("monthly_rent")
            field_decisions.append(
                FieldDecision(
                    field_name=name,
                    chosen_value=val,
                    confidence=confidence,
                    gate_outcome=overall_gate,
                    rationale="deterministic_scoring",
                )
            )
    synthesis_rationale = f"confidence={confidence:.2f}, evidence_coverage={evidence_coverage:.2f}, invariant_pass={invariant_pass}"
    if fail_reasons:
        synthesis_rationale += "; fail_reasons=" + "; ".join(fail_reasons[:3])
    decision = MasterJSONDecision(
        overall_gate=overall_gate,
        field_decisions=field_decisions,
        synthesis_rationale=synthesis_rationale,
        challenge_suggestions=[],
    )
    return confidence, overall_gate, decision
