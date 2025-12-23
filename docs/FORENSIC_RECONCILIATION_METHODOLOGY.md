# Forensic Financial Document Reconciliation Methodology

**Version**: 1.0  
**Date**: December 23, 2025  
**Status**: Production Ready  
**Audience**: Forensic Auditors, Financial Analysts, Big 5 Accounting Firms

---

## Executive Summary

This document outlines the comprehensive forensic auditing methodology implemented in REIMS2 for automated matching and reconciliation across five critical financial document types: Balance Sheet, Income Statement, Cash Flow Statement, Rent Roll, and Mortgage Statement. The system employs a three-tier matching approach with confidence scoring, auditor review workflows, and complete audit trails aligned with Big 5 accounting firm standards.

### Key Principles

1. **Automated Matching with Human Oversight**: All matches require auditor approval for non-exact matches
2. **Complete Audit Trail**: Every decision is logged with user, timestamp, and rationale
3. **Confidence-Based Prioritization**: Matches are prioritized by confidence scores for efficient review
4. **Cross-Document Validation**: Ensures consistency across all financial statements
5. **Industry-Standard Tools**: Uses proven open-source libraries (rapidfuzz, networkx) for reliability

---

## 1. Forensic Auditing Principles

### 1.1 Fundamental Accounting Relationships

Financial statements are interconnected through fundamental accounting relationships that must be validated:

- **Balance Sheet Equation**: Assets = Liabilities + Equity
- **Income Statement Linkage**: Net Income flows to Balance Sheet as Current Period Earnings
- **Cash Flow Reconciliation**: Beginning Cash + Net Cash Flow = Ending Cash
- **Debt Reconciliation**: All mortgage balances must equal Balance Sheet long-term debt
- **Revenue Reconciliation**: Income Statement revenue must equal Rent Roll totals plus other income

### 1.2 Matching Hierarchy

Matches are classified by confidence and reliability:

1. **Exact Matches** (100% confidence): Account codes and amounts match exactly within $0.01
2. **Fuzzy Matches** (70-99% confidence): Account names similar, amounts within 1% tolerance
3. **Calculated Matches** (50-95% confidence): Relationship-based matches (e.g., Net Income = Current Period Earnings)
4. **Inferred Matches** (50-69% confidence): ML-based suggestions requiring auditor confirmation

### 1.3 Auditor Review Requirements

- **Exact Matches**: Auto-approved (no review required)
- **Fuzzy Matches (≥90% confidence)**: Single-click approval recommended
- **Fuzzy Matches (70-89% confidence)**: Full review required
- **Calculated Matches**: Review required to verify relationship validity
- **Inferred Matches**: Always require explicit auditor approval

---

## 2. Core Matching Relationships

### 2.1 Balance Sheet ↔ Income Statement

#### Relationship 1: Current Period Earnings = Net Income

**Formula**: `BS.account_code('3995-0000') = IS.account_code('9090-0000')`

**Validation Rules**:
- Must match exactly within $0.01 (rounding tolerance)
- If difference > $0.01, flag as critical discrepancy
- Confidence: 95% if exact, 60% if mismatch

**Business Logic**: Net Income from Income Statement flows directly to Balance Sheet as Current Period Earnings. This is a fundamental accounting relationship.

#### Relationship 2: Retained Earnings Reconciliation

**Formula**: `Ending RE = Beginning RE + Net Income - Distributions`

**Validation Rules**:
- Beginning RE from prior period Balance Sheet
- Net Income from current Income Statement
- Distributions from Balance Sheet (account_code '3990-0000')
- Allow $100 tolerance for rounding and timing differences
- Confidence: 90% if within tolerance, 50% if significant difference

### 2.2 Balance Sheet ↔ Mortgage Statement

#### Relationship 3: Long-Term Debt = Mortgage Principal Balances

**Formula**: `BS.sum(account_code.like('261%')) = SUM(mortgage.principal_balance)`

**Validation Rules**:
- Sum all long-term debt accounts (2610-xxxx series)
- Sum all mortgage principal balances
- Allow $100 tolerance for other debt obligations
- Confidence: 95% if within tolerance, 70% if significant difference

**Business Logic**: All mortgage obligations should be reflected in Balance Sheet long-term debt accounts.

#### Relationship 4: Escrow Accounts Reconciliation

**Formula**: `BS.sum(['1310-0000', '1320-0000', '1330-0000']) = SUM(mortgage.escrow_balances)`

**Validation Rules**:
- Sum Balance Sheet escrow accounts (tax, insurance, reserve)
- Sum mortgage escrow balances (tax_escrow + insurance_escrow + reserve_balance)
- Allow $1,000 tolerance (escrow can vary due to timing)
- Confidence: 85% if within tolerance, 60% if significant difference

### 2.3 Income Statement ↔ Mortgage Statement

#### Relationship 5: Interest Expense = YTD Interest Paid

**Formula**: `IS.sum(account_code.like('652%')) = mortgage.ytd_interest_paid (annualized)`

**Validation Rules**:
- Sum all interest expense accounts (6520-xxxx series)
- Annualize YTD interest if period < 12 months
- Allow 5% tolerance for accruals and timing differences
- Confidence: 90% if within tolerance, 65% if significant difference

**Business Logic**: Income Statement interest expense should match mortgage interest payments, accounting for accrual vs. cash basis differences.

### 2.4 Income Statement ↔ Rent Roll

#### Relationship 6: Base Rentals = Sum of Rent Roll Annual Rents

**Formula**: `IS.account_code('4010-0000') = SUM(rent_roll.annual_rent)`

**Validation Rules**:
- Base Rentals from Income Statement (4010-0000)
- Sum all annual rents from Rent Roll
- If annual_rent not available, calculate from monthly_rent × 12
- Allow 2% tolerance for vacancies and timing
- Confidence: 95% if within tolerance, 70% if significant difference

**Business Logic**: Income Statement rental income should equal the sum of all tenant rents from Rent Roll.

#### Relationship 7: Occupancy Rate Match

**Formula**: `IS.occupancy_rate = (rent_roll.occupied_units / rent_roll.total_units) × 100`

**Validation Rules**:
- Calculate occupancy from Rent Roll (occupied / total units)
- Compare with Income Statement occupancy metric (if stored)
- Allow 1% tolerance
- Confidence: 90% if within tolerance, 70% if significant difference

### 2.5 Cash Flow ↔ Balance Sheet

#### Relationship 8: Ending Cash = Cash Operating Account

**Formula**: `CF.ending_cash = BS.account_code('0122-0000')`

**Validation Rules**:
- Ending cash from Cash Flow Statement
- Cash Operating Account from Balance Sheet (0122-0000)
- Allow $100 tolerance (multiple cash accounts possible)
- Confidence: 95% if within tolerance, 75% if significant difference

#### Relationship 9: Cash Flow Reconciliation

**Formula**: `Ending Cash = Beginning Cash + Net Cash Flow`

**Validation Rules**:
- Beginning cash from prior period Balance Sheet
- Net Cash Flow from Cash Flow Statement
- Actual ending cash from current Balance Sheet
- Allow $100 tolerance
- Confidence: 95% if within tolerance, 70% if significant difference

**Business Logic**: Cash flow statement must reconcile with balance sheet cash balances.

### 2.6 Cash Flow ↔ Mortgage Statement

#### Relationship 10: Principal Payments = Financing Cash Outflow

**Formula**: `CF.sum(account_code.like('8%'), account_name.contains('principal')) = mortgage.ytd_principal_paid`

**Validation Rules**:
- Sum principal payments from Cash Flow financing section
- Compare with mortgage YTD principal paid
- Allow $1,000 tolerance (timing differences possible)
- Confidence: 90% if within tolerance, 65% if significant difference

### 2.7 Additional Relationships

#### Relationship 11: Security Deposits

**Formula**: `BS.security_deposits_liability = SUM(rent_roll.security_deposit)`

**Validation Rules**:
- Security deposits from Balance Sheet liabilities
- Sum all security deposits from Rent Roll
- Allow 5% tolerance (deposits can be refunded/added)
- Confidence: 85% if within tolerance, 60% if significant difference

---

## 3. Three-Tier Matching Approach

### 3.1 Exact Match Engine

**Purpose**: Identify perfect matches with 100% confidence

**Algorithm**:
1. Match account codes exactly
2. Compare amounts within $0.01 tolerance
3. Verify date alignment (if applicable)

**Confidence Score**: 100.0

**Use Cases**:
- Standard account codes that match exactly
- Amounts that match within rounding tolerance
- High-volume, routine reconciliations

**Example**:
```python
# Balance Sheet: account_code='0122-0000', amount=150000.00
# Income Statement: account_code='0122-0000', period_amount=150000.00
# Result: EXACT MATCH (confidence: 100%)
```

### 3.2 Fuzzy Match Engine

**Purpose**: Identify similar accounts using string similarity

**Algorithm**:
1. Use rapidfuzz library for string matching
2. Calculate account name similarity (WRatio scorer)
3. Check account code range matching (e.g., 2610-xxxx = Long-term debt)
4. Combine name similarity (60% weight) and amount similarity (40% weight)

**Confidence Score**: 70-99%

**Parameters**:
- Minimum confidence threshold: 70%
- Account name weight: 60%
- Account code weight: 40%
- Amount tolerance: 1% for high confidence, 5% for medium confidence

**Use Cases**:
- Account name variations ("Cash Operating" vs "Operating Cash")
- Account code ranges (2610-0000 vs 2610-0100)
- Typos and formatting differences

**Example**:
```python
# Source: account_name="Cash - Operating Account", amount=150000.00
# Target: account_name="Operating Cash", amount=150500.00
# Name similarity: 85% (rapidfuzz WRatio)
# Amount similarity: 99.7% (within 1%)
# Combined confidence: 85% × 0.6 + 99.7% × 0.4 = 90.9%
# Result: FUZZY MATCH (confidence: 90.9%)
```

### 3.3 Calculated Match Engine

**Purpose**: Match based on accounting relationships and formulas

**Algorithm**:
1. Parse relationship formulas (e.g., "BS.current_period_earnings = IS.net_income")
2. Extract account codes or patterns from formula
3. Calculate expected values based on relationship
4. Compare actual vs. expected with appropriate tolerance

**Confidence Score**: 50-95%

**Tolerance Rules**:
- Equality relationships: $0.01 tolerance (95% confidence)
- Sum relationships: 1% tolerance (95% confidence), 5% tolerance (85% confidence)
- Calculation relationships: $100 tolerance (90% confidence)

**Use Cases**:
- Net Income = Current Period Earnings
- Long-term Debt = Sum of Mortgage Balances
- Base Rentals = Sum of Rent Roll Rents

**Example**:
```python
# Formula: "BS.current_period_earnings = IS.net_income"
# BS: account_code='3995-0000', amount=125000.00
# IS: account_code='9090-0000', period_amount=125000.01
# Difference: $0.01 (within tolerance)
# Result: CALCULATED MATCH (confidence: 95%)
```

### 3.4 Inferred Match Engine

**Purpose**: ML-based suggestions using historical patterns

**Algorithm**:
1. Learn patterns from historical matches (if available)
2. Use context-aware matching (account categories, amounts)
3. Calculate similarity based on historical accuracy
4. Require explicit auditor approval

**Confidence Score**: 50-69%

**Learning Mechanism**:
- Track historical match accuracy by account code
- Adjust confidence based on past performance
- Use account category matching as fallback

**Use Cases**:
- New account codes not in historical data
- Unusual transactions requiring pattern recognition
- Cross-document relationships not covered by rules

**Example**:
```python
# Historical pattern: account_code '4010-0000' matched to rent_roll with 85% accuracy
# Current match: account_code '4010-0000' to rent_roll
# Historical accuracy: 85%
# Amount similarity: 95%
# Combined confidence: 85% × 0.7 + 95% × 0.3 = 88% (but capped at 69% for inferred)
# Result: INFERRED MATCH (confidence: 69%, requires approval)
```

---

## 4. Confidence Scoring Formula

### 4.1 Base Formula

The confidence score combines multiple factors:

```
confidence = (
    account_match_score × 0.4 +
    amount_match_score × 0.4 +
    date_match_score × 0.1 +
    context_match_score × 0.1
)
```

### 4.2 Component Scoring

#### Account Match Score (0-100)

- **Exact account code match**: 100
- **Account code range match** (e.g., 2610-xxxx): 85
- **Account name similarity** (rapidfuzz WRatio): 0-100
- **No match**: 0

#### Amount Match Score (0-100)

- **Exact match** (within $0.01): 100
- **Within 1%**: 100 - (difference_percent × 50), minimum 50
- **Within 5%**: 90 - ((difference_percent - 1) × 10), minimum 70
- **Within 10%**: 70 - ((difference_percent - 5) × 2), minimum 50
- **>10% difference**: max(0, 50 - (difference_percent - 10))

#### Date Match Score (0-100)

- **Exact date match**: 100
- **Same period**: 90
- **Adjacent period**: 70
- **Different period**: 0

#### Context Match Score (0-100)

- **Same document type category**: 80
- **Related account categories**: 60
- **Unrelated**: 0

### 4.3 Confidence Thresholds

- **≥90%**: High confidence, single-click approval recommended
- **70-89%**: Medium confidence, full review required
- **50-69%**: Low confidence, always requires explicit approval
- **<50%**: Very low confidence, likely not a match

---

## 5. Open Source Tools Integration

### 5.1 RapidFuzz (v3.14.3+)

**Purpose**: Fast fuzzy string matching for account names

**Usage**:
```python
from rapidfuzz import fuzz, process

# Find best matching account name
result = process.extractOne(
    source_account_name,
    target_account_names,
    scorer=fuzz.WRatio,  # Weighted ratio for better accuracy
    score_cutoff=70  # Minimum confidence threshold
)
```

**Why RapidFuzz**:
- 10-100x faster than fuzzywuzzy
- MIT licensed, actively maintained
- Supports multiple scoring algorithms (ratio, partial_ratio, token_sort_ratio, WRatio)
- Handles Unicode and special characters

### 5.2 NetworkX (v3.0+)

**Purpose**: Graph-based relationship mapping (optional, for future enhancements)

**Usage**:
```python
import networkx as nx

# Build relationship graph
G = nx.DiGraph()
G.add_edge(
    f"{source_doc}:{source_account}",
    f"{target_doc}:{target_account}",
    weight=confidence_score,
    relationship=relationship_type
)
```

**Why NetworkX**:
- Industry-standard graph library
- Supports complex relationship analysis
- Can identify circular dependencies
- Useful for multi-hop relationship validation

### 5.3 Pydantic (v2.12.3+)

**Purpose**: Data validation and schema enforcement

**Usage**:
- Validates API request/response models
- Ensures type safety
- Provides clear error messages

### 5.4 Pandas & NumPy

**Purpose**: Data manipulation and numerical calculations

**Usage**:
- Efficient data aggregation
- Statistical calculations
- Time series analysis

---

## 6. Matching Rules Documentation

### 6.1 Rule Configuration

Each matching rule is defined with:

- **Rule ID**: Unique identifier
- **Name**: Human-readable name
- **Source Document**: Document type (balance_sheet, income_statement, etc.)
- **Target Document**: Document type to match against
- **Relationship Type**: equality, sum, difference, calculation
- **Formula**: Mathematical or logical expression
- **Tolerance**: Absolute or percentage tolerance
- **Confidence Calculation**: How to compute confidence score
- **Severity**: Impact if rule fails (critical, high, medium, low)

### 6.2 Rule Execution Order

Rules are executed in priority order:

1. **Critical Rules** (must pass):
   - Balance Sheet Equation
   - Current Period Earnings = Net Income
   - Cash Flow Reconciliation

2. **High Priority Rules**:
   - Long-term Debt = Mortgage Principal
   - Base Rentals = Rent Roll Total
   - Interest Expense = Mortgage Interest

3. **Medium Priority Rules**:
   - Escrow Accounts Reconciliation
   - Security Deposits Match
   - Occupancy Rate Match

4. **Low Priority Rules**:
   - Inferred relationships
   - Historical pattern matches

### 6.3 Rule Validation

Each rule validates:

- **Existence**: Both source and target records exist
- **Completeness**: All required fields are present
- **Accuracy**: Values match within tolerance
- **Consistency**: Relationship holds across periods

---

## 7. Reconciliation Workflow

### 7.1 Session Initiation

1. **Select Property and Period**: User selects property and financial period
2. **Document Validation**: System verifies all required documents exist:
   - Balance Sheet
   - Income Statement
   - Cash Flow Statement
   - Rent Roll
   - Mortgage Statement (if applicable)
3. **Session Creation**: System creates `ForensicReconciliationSession` record

### 7.2 Match Finding Phase

1. **Cross-Document Rules Execution**: Run all 11+ matching rules
2. **Engine Execution**: Run Exact, Fuzzy, Calculated, and Inferred engines
3. **Match Storage**: Store all matches in `ForensicMatch` table with confidence scores
4. **Grouping**: Group matches by type (exact, fuzzy, calculated, inferred)

### 7.3 Validation Phase

1. **Discrepancy Detection**: Identify matches with:
   - Confidence < 70%
   - Amount difference > $1,000
   - Relationship violations
2. **Health Score Calculation**: Compute overall reconciliation health (0-100)
3. **Discrepancy Creation**: Create `ForensicDiscrepancy` records for issues

### 7.4 Auditor Review Phase

1. **Match Review**: Auditor reviews matches by confidence level:
   - High confidence (≥90%): Quick review, bulk approval
   - Medium confidence (70-89%): Detailed review
   - Low confidence (<70%): Full investigation
2. **Approval/Rejection**: Auditor approves or rejects each match with notes
3. **Discrepancy Resolution**: Auditor resolves discrepancies with rationale

### 7.5 Session Completion

1. **Final Validation**: Re-run validation after all approvals
2. **Health Score Update**: Recalculate health score
3. **Session Closure**: Mark session as approved/rejected
4. **Audit Trail**: All decisions logged with timestamps

---

## 8. Auditor Review Process

### 8.1 Review Dashboard

The dashboard displays:

- **Summary Cards**: Total matches, approved, pending, discrepancies
- **Health Score**: Overall reconciliation quality (0-100)
- **Match Table**: Sortable, filterable list of all matches
- **Discrepancy Panel**: Grouped by severity (critical, high, medium, low)

### 8.2 Match Review Workflow

1. **Filter Matches**: By type, status, or confidence score
2. **View Details**: Click match to see side-by-side comparison
3. **Approve**: Single-click for high-confidence matches
4. **Reject**: Provide reason for rejection
5. **Modify**: Override values with auditor notes

### 8.3 Discrepancy Resolution Workflow

1. **Identify Issue**: Review discrepancy description and suggested resolution
2. **Investigate**: Examine source documents and related records
3. **Resolve**: 
   - Accept as-is (if expected difference)
   - Correct value (with new value and rationale)
   - Flag for further investigation
4. **Document**: Provide detailed resolution notes

### 8.4 Approval Requirements

**Single Approval** (Low-Impact Items):
- Amount difference < $1,000
- Non-covenant affecting
- DSCR not impacted

**Dual Approval** (High-Impact Items):
- Amount difference > $10,000
- Covenant-impacting changes
- DSCR-affecting corrections

---

## 9. Discrepancy Resolution Procedures

### 9.1 Discrepancy Types

#### Amount Mismatch

**Definition**: Source and target amounts differ beyond tolerance

**Resolution Steps**:
1. Verify source document accuracy
2. Check for data entry errors
3. Validate calculation formulas
4. Determine correct value
5. Update database with corrected value
6. Document resolution rationale

#### Missing Source

**Definition**: Target document has record, but source document missing

**Resolution Steps**:
1. Verify source document completeness
2. Check if account should exist in source
3. Add missing record if valid
4. Document why record was missing

#### Missing Target

**Definition**: Source document has record, but target document missing

**Resolution Steps**:
1. Verify target document completeness
2. Check if account should exist in target
3. Add missing record if valid
4. Document why record was missing

#### Date Mismatch

**Definition**: Records exist but dates don't align

**Resolution Steps**:
1. Verify period alignment
2. Check for timing differences (accrual vs. cash)
3. Document timing rationale

### 9.2 Resolution Actions

**Accept as-is**: Difference is expected and valid
- Example: Timing differences in accrual accounting
- Requires: Brief explanation

**Correct Value**: Update database with correct value
- Example: Data entry error identified
- Requires: New value and detailed rationale

**Flag for Investigation**: Requires further research
- Example: Unusual transaction pattern
- Requires: Investigation plan and timeline

**Ignore**: Difference is immaterial
- Example: Rounding differences < $1
- Requires: Materiality justification

### 9.3 Resolution Documentation

All resolutions must include:

- **Resolution Type**: Accept, Correct, Flag, Ignore
- **Rationale**: Detailed explanation of decision
- **New Value**: If correcting, the corrected value
- **Investigation Notes**: If flagging, investigation plan
- **Auditor Signature**: User ID and timestamp

---

## 10. Best Practices (Big 5 Accounting Firm Standards)

### 10.1 Independence and Objectivity

- **Separation of Duties**: Match finding (automated) vs. approval (human)
- **No Auto-Approval**: All non-exact matches require auditor review
- **Documentation**: Complete audit trail for all decisions

### 10.2 Professional Skepticism

- **Question Low Confidence**: Investigate matches < 70% confidence
- **Verify Relationships**: Don't assume calculated matches are correct
- **Cross-Reference**: Verify against source documents

### 10.3 Materiality

- **Threshold-Based Review**: Focus on high-impact discrepancies
- **Risk Assessment**: Prioritize covenant-affecting items
- **Documentation**: Justify immaterial differences

### 10.4 Documentation Standards

- **Complete Audit Trail**: Every decision logged with:
  - User ID
  - Timestamp
  - Rationale
  - Before/after values (if applicable)
- **Review Notes**: Detailed explanations for all approvals/rejections
- **Resolution Documentation**: Complete resolution procedures

### 10.5 Quality Control

- **Health Score Monitoring**: Track reconciliation quality over time
- **Pattern Analysis**: Identify systemic issues
- **Continuous Improvement**: Learn from historical matches

### 10.6 Compliance

- **GAAP Compliance**: Ensure all relationships follow Generally Accepted Accounting Principles
- **Regulatory Requirements**: Meet audit trail requirements for regulators
- **Internal Controls**: Maintain separation of duties and approval workflows

---

## 11. Performance Metrics

### 11.1 Accuracy Metrics

- **Match Accuracy**: >95% of exact matches correctly identified
- **False Positive Rate**: <5% of suggested matches are incorrect
- **Discrepancy Detection**: 100% of critical discrepancies identified

### 11.2 Performance Metrics

- **Reconciliation Time**: <30 seconds for full property/period reconciliation
- **Match Generation**: <10 seconds for 1000+ potential matches
- **Dashboard Load**: <2 seconds for reconciliation dashboard

### 11.3 User Adoption Metrics

- **Auditor Usage**: 80% of reconciliations use forensic system
- **Time Savings**: 70% reduction in manual reconciliation time
- **Error Reduction**: 90% reduction in reconciliation errors

---

## 12. Troubleshooting Guide

### 12.1 Common Issues

#### No Matches Found

**Possible Causes**:
- Documents not uploaded for property/period
- Account codes don't match
- Data extraction incomplete

**Solutions**:
- Verify all documents are uploaded and extracted
- Check account code mappings
- Review extraction confidence scores

#### Low Health Score

**Possible Causes**:
- Many low-confidence matches
- Critical discrepancies present
- Missing documents

**Solutions**:
- Review and approve high-confidence matches first
- Resolve critical discrepancies
- Ensure all documents are present

#### High False Positive Rate

**Possible Causes**:
- Fuzzy matching threshold too low
- Account name variations not accounted for
- Historical patterns inaccurate

**Solutions**:
- Adjust fuzzy matching parameters
- Improve account name normalization
- Retrain inferred matching engine

---

## 13. Future Enhancements

### Phase 2 (3-6 months)

- Machine learning model training on historical matches
- Automated discrepancy resolution suggestions
- Multi-period trend analysis
- Portfolio-wide reconciliation

### Phase 3 (6-12 months)

- Real-time reconciliation on document upload
- Predictive discrepancy detection
- Integration with external accounting systems
- Advanced visualization and reporting

---

## 14. References

### Accounting Standards

- Generally Accepted Accounting Principles (GAAP)
- Financial Accounting Standards Board (FASB) standards
- International Financial Reporting Standards (IFRS)

### Tools Documentation

- RapidFuzz: https://github.com/maxbachmann/rapidfuzz
- NetworkX: https://networkx.org/
- Pydantic: https://docs.pydantic.dev/

### Industry Best Practices

- Big 4 Accounting Firm Audit Methodologies
- Forensic Accounting Standards
- Financial Statement Analysis Best Practices

---

## Appendix A: Account Code Reference

### Balance Sheet Accounts

- **0122-0000**: Cash - Operating Account
- **0305-0000**: Accounts Receivable - Tenants
- **1310-0000**: Escrow - Taxes
- **1320-0000**: Escrow - Insurance
- **1330-0000**: Escrow - Reserve
- **2610-xxxx**: Long-Term Debt (series)
- **3910-0000**: Retained Earnings
- **3990-0000**: Distributions
- **3995-0000**: Current Period Earnings

### Income Statement Accounts

- **4010-0000**: Base Rentals
- **4020-0000**: Tenant Recoveries - CAM
- **4030-0000**: Tenant Recoveries - Other
- **6520-xxxx**: Interest Expense (series)
- **9090-0000**: Net Income

### Cash Flow Accounts

- **8xxxx-xxxx**: Financing Section (principal payments)
- **9999-0000**: Ending Cash Balance

---

## Appendix B: Confidence Score Examples

### Example 1: Exact Match

```
Account Code Match: 100 (exact)
Amount Match: 100 (within $0.01)
Date Match: 100 (same period)
Context Match: 100 (same category)

Confidence = 100 × 0.4 + 100 × 0.4 + 100 × 0.1 + 100 × 0.1 = 100%
```

### Example 2: Fuzzy Match

```
Account Code Match: 85 (range match)
Amount Match: 95 (within 1%)
Date Match: 100 (same period)
Context Match: 80 (related category)

Confidence = 85 × 0.4 + 95 × 0.4 + 100 × 0.1 + 80 × 0.1 = 90.0%
```

### Example 3: Calculated Match

```
Account Code Match: 100 (exact)
Amount Match: 98 (within 0.5%)
Date Match: 100 (same period)
Context Match: 100 (calculated relationship)

Confidence = 100 × 0.4 + 98 × 0.4 + 100 × 0.1 + 100 × 0.1 = 99.2%
(Adjusted to 95% for calculated match type)
```

---

## Document Control

**Author**: REIMS2 Development Team  
**Reviewer**: Forensic Auditing Expert  
**Approved By**: Chief Financial Officer  
**Last Updated**: December 23, 2025  
**Next Review**: March 23, 2026

---

*This methodology document is a living document and will be updated as the system evolves and best practices are refined.*

