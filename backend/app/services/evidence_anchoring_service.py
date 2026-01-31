"""
Evidence anchoring: attach page + snippet (and optional bbox) per field for audit trail.
Used by multi-LLM extraction to satisfy evidence coverage targets.
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.master_json import EvidenceEntry, MasterJSONEvidence

logger = logging.getLogger(__name__)

# Snippet context: chars before/after match
SNIPPET_CONTEXT = 80


def _normalize_value_for_search(value: Any) -> str:
    """Normalize value for substring search (e.g. number to string, strip)."""
    if value is None:
        return ""
    s = str(value).strip()
    # Remove common formatting for numbers
    if isinstance(value, (int, float)):
        s = re.sub(r"\.0+$", "", s)
    return s


def _format_number_with_commas(s: str) -> str:
    """Format a numeric string with thousand separators (e.g. 1234.56 -> 1,234.56)."""
    if not s or not re.match(r"^-?[\d.]+$", s.strip()):
        return s
    parts = s.strip().split(".", 1)
    int_part = parts[0].lstrip("-")
    neg = "-" if parts[0].startswith("-") else ""
    if len(int_part) <= 3:
        formatted = neg + int_part
    else:
        # Insert comma every 3 digits from the right
        rev = int_part[::-1]
        chunks = [rev[i : i + 3] for i in range(0, len(rev), 3)]
        formatted = neg + ",".join(chunks)[::-1]
    if len(parts) == 2:
        formatted += "." + parts[1]
    return formatted


def _find_snippet_in_text(text: str, value_str: str, context_chars: int = SNIPPET_CONTEXT) -> Optional[str]:
    """Find value_str in text and return a snippet (context around match). Tries literal, then no-comma, then comma-formatted."""
    if not value_str or not text:
        return None
    candidates = [value_str]
    # Try without commas (e.g. 1,234.56 -> 1234.56)
    no_comma = value_str.replace(",", "").replace(" ", "")
    if no_comma != value_str:
        candidates.append(no_comma)
    # Try with commas (e.g. 1234.56 -> 1,234.56)
    with_comma = _format_number_with_commas(no_comma if re.match(r"^-?[\d.]+$", no_comma) else value_str)
    if with_comma and with_comma not in candidates:
        candidates.append(with_comma)
    for cand in candidates:
        idx = text.find(cand)
        if idx != -1:
            start = max(0, idx - context_chars)
            end = min(len(text), idx + len(cand) + context_chars)
            snippet = text[start:end]
            return snippet.strip() or None
    return None


def anchor_evidence(
    full_text: str,
    fields: List[Dict[str, Any]],
    pages: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[EvidenceEntry], float]:
    """
    For each field (with field_name and value), try to find value in text and record page + snippet.

    Args:
        full_text: Full extracted document text.
        fields: List of {"field_name": str, "value": Any} (e.g. from chosen candidate line_items or header fields).
        pages: Optional list of {"text": str, "page_index": int} for per-page anchoring.

    Returns:
        (list of EvidenceEntry, coverage_pct 0.0–1.0).
    """
    entries: List[EvidenceEntry] = []
    found = 0
    for f in fields:
        field_name = f.get("field_name") or f.get("account_name") or f.get("unit_id") or "unknown"
        value = f.get("value") or f.get("amount") or f.get("monthly_rent")
        value_str = _normalize_value_for_search(value)
        page_index: Optional[int] = None
        snippet: Optional[str] = None

        if pages:
            for p in pages:
                page_text = p.get("text") or ""
                snippet = _find_snippet_in_text(page_text, value_str) if value_str else None
                if snippet:
                    page_index = p.get("page_index", 0)
                    break
        if snippet is None and full_text:
            snippet = _find_snippet_in_text(full_text, value_str)
            if snippet and pages:
                # Approximate page by character offset
                char_offset = full_text.find(value_str) if value_str else -1
                if char_offset >= 0 and pages:
                    approx_chars_per_page = len(full_text) / max(1, len(pages))
                    page_index = min(int(char_offset / approx_chars_per_page), len(pages) - 1)

        entries.append(
            EvidenceEntry(
                field_name=field_name,
                page_index=page_index,
                snippet=snippet,
                bbox=None,
            )
        )
        if snippet:
            found += 1

    coverage = (found / len(entries)) if entries else 1.0
    return entries, coverage


def fields_from_candidate_parsed_json(parsed_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten chosen candidate parsed_json into list of {field_name, value} for evidence anchoring.
    Handles line_items, units, and top-level totals.
    """
    out: List[Dict[str, Any]] = []
    line_items = parsed_json.get("line_items") or parsed_json.get("units") or []
    for i, item in enumerate(line_items):
        if isinstance(item, dict):
            name = item.get("account_name") or item.get("tenant_name") or item.get("unit_id") or f"item_{i}"
            val = item.get("amount") or item.get("monthly_rent")
            out.append({"field_name": name, "value": val})
    for key in ("total_assets", "total_liabilities", "total_equity", "total_revenue", "total_expenses", "net_operating_income"):
        if key in parsed_json and parsed_json[key] is not None:
            out.append({"field_name": key, "value": parsed_json[key]})
    return out
