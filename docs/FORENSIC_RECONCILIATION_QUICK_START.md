# Forensic Reconciliation - Quick Start Guide

**Version**: 1.0  
**Date**: December 23, 2025

---

## Overview

The Forensic Reconciliation System automates matching and reconciliation across five financial document types:
- Balance Sheet
- Income Statement  
- Cash Flow Statement
- Rent Roll
- Mortgage Statement

---

## Quick Start

### 1. Database Setup

Run the Alembic migration to create the required tables:

```bash
cd backend
alembic upgrade head
```

This creates three tables:
- `forensic_reconciliation_sessions`
- `forensic_matches`
- `forensic_discrepancies`

### 2. Start a Reconciliation Session

**API Endpoint**: `POST /api/v1/forensic-reconciliation/sessions`

```json
{
  "property_id": 1,
  "period_id": 1,
  "session_type": "full_reconciliation",
  "auditor_id": 1
}
```

**Response**:
```json
{
  "id": 1,
  "property_id": 1,
  "period_id": 1,
  "session_type": "full_reconciliation",
  "status": "in_progress",
  "started_at": "2025-12-23T10:00:00Z"
}
```

### 3. Run Reconciliation

**API Endpoint**: `POST /api/v1/forensic-reconciliation/sessions/{session_id}/run`

```json
{
  "use_exact": true,
  "use_fuzzy": true,
  "use_calculated": true,
  "use_inferred": false,
  "use_rules": true
}
```

This will:
- Execute all matching rules (11+ cross-document relationships)
- Find matches using exact, fuzzy, and calculated engines
- Store matches in the database with confidence scores
- Return summary statistics

### 4. Review Matches

**API Endpoint**: `GET /api/v1/forensic-reconciliation/sessions/{session_id}/matches`

**Query Parameters**:
- `match_type`: Filter by type (exact, fuzzy, calculated, inferred)
- `status_filter`: Filter by status (pending, approved, rejected)
- `min_confidence`: Minimum confidence score (0-100)

**Response**:
```json
{
  "session_id": 1,
  "total": 25,
  "matches": [
    {
      "id": 1,
      "match_type": "calculated",
      "confidence_score": 95.0,
      "source_document_type": "balance_sheet",
      "target_document_type": "income_statement",
      "relationship_formula": "BS.CurrentPeriodEarnings = IS.NetIncome",
      "status": "pending"
    }
  ]
}
```

### 5. Approve/Reject Matches

**Approve Match**: `POST /api/v1/forensic-reconciliation/matches/{match_id}/approve`

```json
{
  "notes": "Verified - matches correctly"
}
```

**Reject Match**: `POST /api/v1/forensic-reconciliation/matches/{match_id}/reject`

```json
{
  "reason": "Amount mismatch too large - requires investigation"
}
```

### 6. Review Discrepancies

**API Endpoint**: `GET /api/v1/forensic-reconciliation/sessions/{session_id}/discrepancies`

**Query Parameters**:
- `severity`: Filter by severity (critical, high, medium, low)
- `status_filter`: Filter by status (open, investigating, resolved)

**Response**:
```json
{
  "session_id": 1,
  "total": 3,
  "discrepancies": [
    {
      "id": 1,
      "severity": "high",
      "discrepancy_type": "amount_mismatch",
      "difference": 1000.00,
      "description": "Large amount difference between Balance Sheet and Income Statement",
      "status": "open"
    }
  ]
}
```

### 7. Resolve Discrepancies

**API Endpoint**: `POST /api/v1/forensic-reconciliation/discrepancies/{discrepancy_id}/resolve`

```json
{
  "resolution_notes": "Corrected data entry error - updated Balance Sheet value",
  "new_value": 125000.00
}
```

### 8. Get Health Score

**API Endpoint**: `GET /api/v1/forensic-reconciliation/health-score/{property_id}/{period_id}`

**Response**:
```json
{
  "property_id": 1,
  "period_id": 1,
  "session_id": 1,
  "health_score": 85.5,
  "total_matches": 25,
  "discrepancies": 3
}
```

**Health Score Interpretation**:
- **80-100**: Excellent - Minimal issues, high confidence matches
- **60-79**: Good - Some discrepancies, mostly resolved
- **40-59**: Fair - Multiple discrepancies requiring attention
- **0-39**: Poor - Significant issues, requires investigation

### 9. Complete Session

**API Endpoint**: `POST /api/v1/forensic-reconciliation/sessions/{session_id}/complete`

Marks the session as approved and finalizes the reconciliation.

---

## Frontend Usage

### Access the Dashboard

Navigate to: `#forensic-reconciliation` in the REIMS2 application

### Workflow

1. **Select Property & Period**: Choose property and financial period from dropdowns
2. **Start Reconciliation**: Click "Start Reconciliation" button
3. **Review Matches**: 
   - View matches in the "Matches" tab
   - Filter by type, status, or confidence
   - Click match to see detailed comparison
4. **Approve/Reject**: 
   - Approve high-confidence matches (≥90%) with single click
   - Review medium-confidence matches (70-89%) in detail
   - Reject matches with reason
5. **Resolve Discrepancies**:
   - Review discrepancies grouped by severity
   - Resolve with notes and optional corrected value
6. **Complete Session**: Click "Complete Session" when finished

---

## Matching Rules Reference

### Balance Sheet ↔ Income Statement

1. **Current Period Earnings = Net Income**
   - Formula: `BS.account_code('3995-0000') = IS.account_code('9090-0000')`
   - Confidence: 95% if exact, 60% if mismatch
   - Tolerance: $0.01

2. **Retained Earnings Reconciliation**
   - Formula: `Ending RE = Beginning RE + Net Income - Distributions`
   - Confidence: 90% if within tolerance
   - Tolerance: $100

### Balance Sheet ↔ Mortgage Statement

3. **Long-Term Debt = Mortgage Principal**
   - Formula: `BS.sum('261%') = SUM(mortgage.principal_balance)`
   - Confidence: 95% if within tolerance
   - Tolerance: $100

4. **Escrow Accounts**
   - Formula: `BS.sum(['1310-0000', '1320-0000', '1330-0000']) = SUM(mortgage.escrow_balances)`
   - Confidence: 85% if within tolerance
   - Tolerance: $1,000

### Income Statement ↔ Rent Roll

5. **Base Rentals = Sum of Rents**
   - Formula: `IS.account_code('4010-0000') = SUM(rent_roll.annual_rent)`
   - Confidence: 95% if within tolerance
   - Tolerance: 2%

6. **Occupancy Rate**
   - Formula: `IS.occupancy_rate = (rent_roll.occupied_units / rent_roll.total_units) × 100`
   - Confidence: 90% if within tolerance
   - Tolerance: 1%

### Cash Flow ↔ Balance Sheet

7. **Ending Cash = Cash Operating Account**
   - Formula: `CF.ending_cash = BS.account_code('0122-0000')`
   - Confidence: 95% if within tolerance
   - Tolerance: $100

8. **Cash Flow Reconciliation**
   - Formula: `Ending Cash = Beginning Cash + Net Cash Flow`
   - Confidence: 95% if within tolerance
   - Tolerance: $100

### Additional Rules

See `docs/FORENSIC_RECONCILIATION_METHODOLOGY.md` for complete list of all 11+ rules.

---

## Confidence Scores

### Score Calculation

```
confidence = (
    account_match_score × 0.4 +
    amount_match_score × 0.4 +
    date_match_score × 0.1 +
    context_match_score × 0.1
)
```

### Score Interpretation

- **≥90%**: High confidence - Single-click approval recommended
- **70-89%**: Medium confidence - Full review required
- **50-69%**: Low confidence - Always requires explicit approval
- **<50%**: Very low confidence - Likely not a match

---

## Troubleshooting

### No Matches Found

**Possible Causes**:
- Documents not uploaded for property/period
- Account codes don't match
- Data extraction incomplete

**Solutions**:
- Verify all documents are uploaded and extracted
- Check account code mappings
- Review extraction confidence scores

### Low Health Score

**Possible Causes**:
- Many low-confidence matches
- Critical discrepancies present
- Missing documents

**Solutions**:
- Review and approve high-confidence matches first
- Resolve critical discrepancies
- Ensure all documents are present

### Performance Issues

**If reconciliation takes >30 seconds**:
- Check database indexes are created
- Verify document data is properly indexed
- Consider running reconciliation in background job

---

## API Reference

### Base URL
`/api/v1/forensic-reconciliation`

### Authentication
All endpoints require authentication via session cookie or JWT token.

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | Create session |
| GET | `/sessions/{id}` | Get session |
| POST | `/sessions/{id}/run` | Run reconciliation |
| GET | `/sessions/{id}/matches` | List matches |
| GET | `/sessions/{id}/discrepancies` | List discrepancies |
| POST | `/sessions/{id}/complete` | Complete session |
| POST | `/matches/{id}/approve` | Approve match |
| POST | `/matches/{id}/reject` | Reject match |
| POST | `/discrepancies/{id}/resolve` | Resolve discrepancy |
| GET | `/dashboard/{property_id}/{period_id}` | Get dashboard |
| GET | `/health-score/{property_id}/{period_id}` | Get health score |
| POST | `/sessions/{id}/validate` | Validate matches |

---

## Best Practices

1. **Start with High-Confidence Matches**: Approve exact matches first to build confidence
2. **Review Calculated Matches Carefully**: Verify relationship formulas are correct
3. **Document All Rejections**: Provide clear reasons for rejected matches
4. **Resolve Discrepancies Promptly**: Address critical discrepancies immediately
5. **Complete Sessions Regularly**: Don't leave sessions in "in_progress" state
6. **Monitor Health Scores**: Track health scores over time to identify trends

---

## Support

For detailed methodology and technical documentation, see:
- `docs/FORENSIC_RECONCILIATION_METHODOLOGY.md` - Complete methodology
- `FORENSIC_RECONCILIATION_IMPLEMENTATION_SUMMARY.md` - Implementation details

---

*Last Updated: December 23, 2025*

