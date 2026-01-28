# REIMS2 Reconciliation Rules - Actual Implementation Count

**Date**: January 28, 2026  
**Verification Method**: Direct code analysis of rule execution methods

---

## TOTAL ACTIVE RULES: **311 Rules**

This is significantly **higher** than the 138 shown in your UI, indicating either:
1. The UI is counting a subset (e.g., only failed/warning rules)
2. The UI is counting only certain categories
3. Some rules produce multiple sub-results (e.g., AUDIT-46 creates 3 sub-rules)

---

## BREAKDOWN BY MIXIN

Based on actual `self._rule_*()` calls in each `_execute_*_rules()` method:

| Mixin Module | Rule Calls | Category |
|-------------|-----------|----------|
| **Analytics Rules** | 54 | ANALYTICS-*, COVENANT-*, BENCHMARK-*, TREND-*, STRESS-*, DASHBOARD-* |
| **Audit Rules** | 59 | AUDIT-*, WCR-* (Working Capital Reconciliation) |
| **Data Quality Rules** | 33 | DQ-* |
| **Cash Flow Rules** | 32 | CF-* |
| **Balance Sheet Rules** | 35 | BS-* |
| **Income Statement Rules** | 31 | IS-* |
| **Three Statement Rules** | 23 | 3S-* |
| **Mortgage Rules** | 20 | MS-*, RECON-* |
| **Forensic Anomaly Rules** | 11 | FA-*, FA-WC-*, FA-MORT-*, FA-RR-* |
| **Rent Roll Rules** | 9 | RR-* |
| **Rent Roll-Balance Sheet Rules** | 4 | RRBS-* |
| **TOTAL** | **311** | All categories |

---

## EXECUTION ORDER

Per `ReconciliationRuleEngine.execute_all_rules()`:

1. **Balance Sheet** (35 rules)
2. **Income Statement** (31 rules)
3. **Three Statement** (23 rules)
4. **Cash Flow** (32 rules)
5. **Mortgage** (20 rules)
6. **Audit** (59 rules)
7. **Analytics** (54 rules)
8. **Data Quality** (33 rules)
9. **Forensic** (11 rules)
10. **RR-BS** (4 rules)
11. **Rent Roll** (9 rules)

---

## MAJOR RULE CATEGORIES

### Critical Foundation Rules (AUDIT-*)
**59 rules** covering:
- AUDIT-1 to AUDIT-3: Fundamental accounting equation
- AUDIT-4 to AUDIT-7: Mortgage integration
- AUDIT-8 to AUDIT-11: Rent roll integration
- AUDIT-12 to AUDIT-14: Working capital reconciliation
- AUDIT-15 to AUDIT-17: Depreciation & amortization
- AUDIT-18 to AUDIT-20: Capital expenditure tracking
- AUDIT-21 to AUDIT-23: Debt service reconciliation
- AUDIT-24 to AUDIT-26: Cash flow validation
- AUDIT-27 to AUDIT-29: Period-over-period consistency
- AUDIT-30 to AUDIT-32: YTD accumulation
- AUDIT-33 to AUDIT-36: Ratios and metrics
- AUDIT-37 to AUDIT-42: Data quality validation
- AUDIT-43 to AUDIT-46: Covenant compliance
- AUDIT-47 to AUDIT-55: Comprehensive checklists
- WCR-1 to WCR-3: Working capital reconciliation

### Advanced Analytics Rules (ANALYTICS-*)
**54 rules** covering:
- ANALYTICS-1 to ANALYTICS-5: Property operating metrics (NOI, margins, cap rate)
- ANALYTICS-6 to ANALYTICS-10: Occupancy and leasing metrics
- ANALYTICS-11 to ANALYTICS-14: Financial leverage (LTV, DSCR, interest coverage, debt yield)
- ANALYTICS-15 to ANALYTICS-18: Liquidity metrics
- ANALYTICS-19 to ANALYTICS-24: Operating performance (ROA, ROE, per-SF metrics)
- ANALYTICS-25 to ANALYTICS-33: Risk metrics
- COVENANT-1 to COVENANT-6: Covenant compliance rules
- BENCHMARK-1 to BENCHMARK-4: Market benchmarking
- TREND-1 to TREND-3: Trend analysis
- STRESS-1 to STRESS-5: Stress testing
- DASHBOARD-1 to DASHBOARD-3: Dashboard metrics

### Data Quality Rules (DQ-*)
**33 rules** covering:
- DQ-1 to DQ-3: Data completeness
- DQ-4 to DQ-8: Mathematical accuracy
- DQ-9 to DQ-12: Data consistency
- DQ-13 to DQ-15: Data integrity
- DQ-16 to DQ-17: Timeliness
- DQ-18 to DQ-19: Precision
- DQ-20 to DQ-21: Validation
- DQ-22 to DQ-23: Source validation
- DQ-24 to DQ-25: Transformation validation
- DQ-26 to DQ-27: Metrics
- DQ-28 to DQ-30: Governance
- DQ-31 to DQ-33: Error correction

### Statement-Specific Rules
- **Balance Sheet**: 35 rules (BS-*)
- **Income Statement**: 31 rules (IS-*)
- **Cash Flow**: 32 rules (CF-*)
- **Three Statement**: 23 rules (3S-*)
- **Mortgage**: 20 rules (MS-*, RECON-*)
- **Rent Roll**: 9 rules (RR-*)
- **Rent Roll-Balance Sheet**: 4 rules (RRBS-*)

### Forensic Rules (FA-*)
**11 rules** covering:
- FA-1 to FA-7: Cash flow consistency, sign tests, non-cash detection, fraud detection
- FA-WC-1: Working capital attribution
- FA-MORT-1 to FA-MORT-2: Mortgage payment continuity, escrow reasonableness
- FA-RR-1: Lease term consistency

---

## NOTES ON RULE COUNTING

### Why 311 vs 138 in UI?

Several possibilities:

1. **Rule Execution vs Display**:
   - The engine executes 311 rule methods
   - Some rules may be SKIPPED if data is unavailable
   - UI may only show FAIL/WARNING/PASS (excluding INFO/SKIP)

2. **Sub-Rules**:
   - Some rules create multiple results (e.g., AUDIT-46 creates 3 sub-results for TAX/INSURANCE/RESERVE)
   - These may be counted differently in UI vs execution

3. **Category Filtering**:
   - UI may be filtering to specific categories
   - May exclude informational-only rules

4. **Period Alignment Context**:
   - Some rules require prior period data and skip if unavailable
   - First period of data would have fewer active rules

---

## VERIFICATION COMMAND

To see exactly what the engine executes:

```bash
cd backend/app/services/rules
grep "self._rule_" *.py | wc -l
```

Result: **311 rule calls**

To count unique rule methods defined:

```bash
grep "def _rule_" *.py | wc -l
```

Result: **311 unique rule methods**

---

## CONCLUSION

**✅ The REIMS2 system has 311 implemented reconciliation rules.**

The "138 Rules Active" in your UI is likely:
- Showing only rules that actually ran (excluding skipped rules due to missing data)
- Counting parent rules only (some rules have sub-components)
- Filtering by status (only FAIL/WARNING/PASS, not INFO/SKIP)

To get the exact UI count, we'd need to see the specific filtering logic in the frontend or the API endpoint that provides the rule count.

---

## DOWNLOADED RULES COVERAGE

From the analysis document (`RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md`):

| Source Document | Total Rules | Implemented | Coverage % |
|----------------|-------------|-------------|------------|
| **FORENSIC_ACCOUNTING_RULES_ENHANCED.md** | ~25 | 23 | 92% |
| **CROSS_DOCUMENT_AUDIT_RULES.md** | 55 | 55 | 100% |
| **DATA_QUALITY_INTEGRITY_RULES.md** | 33 | 33 | 100% |
| **ADVANCED_ANALYTICS_COVENANTS_RULES.md** | 54 | 54 | 100% |
| **Other Rules** | ~158 | ~146 | 92% |
| **TOTAL** | **~325** | **~311** | **96%** |

The REIMS2 implementation covers **96% of the comprehensive 325+ rule framework** from the downloaded documents.

---

**Document Version**: 1.0  
**Last Updated**: January 28, 2026
