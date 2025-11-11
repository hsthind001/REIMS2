# Balance Sheet Accounts Comparison Report

## Executive Summary

- **Template Accounts:** 63
- **Seed File Accounts:** 143
- **Matched Accounts:** 59 (93.7% coverage)
- **In Template Only:** 4
- **In Seed Only:** 84
- **Property Mismatches:** 33

**Status:** ⚠️ MISSING ACCOUNTS

There are 4 accounts defined in the template but missing from seed files.

---

## ❌ Accounts in Template Only (4)

These accounts are specified in the template but missing from seed SQL files:

| Code | Name | Type | Required | Notes |
|------|------|------|----------|-------|
| `0100-0000` | ASSETS | header | ✅ Yes | CRITICAL |
| `1999-0000` | TOTAL ASSETS | calculated_total | ✅ Yes | CRITICAL |
| `2999-0000` | TOTAL LIABILITIES | calculated_total | ✅ Yes | CRITICAL |
| `3999-9000` | TOTAL LIABILITIES & CAPITAL | section_total | ✅ Yes | CRITICAL |

**Action Required:** Add these accounts to seed SQL files.

---

## ℹ️ Accounts in Seed Only (84)

These accounts are in seed files but not explicitly defined in the template:

- **Assets:** 41
- **Liabilities:** 41
- **Equity:** 2

**Analysis:** This is normal and indicates comprehensive coverage. The template defines core/example accounts, while seed files contain the complete chart of accounts for all properties.

### Sample (first 20):

| Code | Name | Category | Type |
|------|------|----------|------|
| `0101-0000` | Current Assets | current_asset | asset |
| `0120-0000` | Cash on Hand | current_asset | asset |
| `0121-0000` | Cash - Savings | current_asset | asset |
| `0124-0000` | Cash - Operating III WF | current_asset | asset |
| `0126-0000` | Cash - Depository - PNC | current_asset | asset |
| `0127-0000` | Cash - Escrow - PNC | current_asset | asset |
| `0199-0000` | Non-Cash (Adjustments) | current_asset | asset |
| `0307-0000` | A/R Other | current_asset | asset |
| `0310-0000` | Title Escrow/Lender App | current_asset | asset |
| `0315-0000` | A/R Eastern Shore Plaza | current_asset | asset |
| `0316-0000` | A/R Frayser Village | current_asset | asset |
| `0317-0000` | A/R Hammond Aire LP | current_asset | asset |
| `0318-0000` | A/R TCSH, LP | current_asset | asset |
| `0319-0000` | A/R Wendover Commons LP | current_asset | asset |
| `0320-0000` | A/R Oxford Exchange, LP | current_asset | asset |
| `0500-0000` | Property & Equipment | fixed_asset | asset |
| `0715-0000` | 7 Year - Signage | fixed_asset | asset |
| `0955-0000` | White box / Spec Suites Major | fixed_asset | asset |
| `1083-0000` | Accum. Depr.-Roof2008 | fixed_asset | asset |
| `1084-0000` | Accum. Depr.-PL-2009 | fixed_asset | asset |

... and 64 more

---

## ⚠️ Property Mismatches (33)

These accounts exist in both but have different properties:

| Code | Template Name | Seed Name | Issues |
|------|---------------|-----------|--------|
| `3050-0000` | Partners? Contributions? | Common Stock | Name mismatch: 'Partners? Contributions?' vs 'Common Stock' |
| `0210-0000` | Accounts Receivable.*Trade | Accounts Receivables - Trade | Template marks as contra account but seed name doesn't indicate it |
| `0122-0000` | Cash.*Operating | Cash - Operating | Template marks as contra account but seed name doesn't indicate it |
| `1210-0000` | Deposits | Deposits | Template marks as contra account but seed name doesn't indicate it |
| `0305-0000` | A/R Tenants? | A/R Tenants | Template marks as contra account but seed name doesn't indicate it |
| `0125-0000` | Cash.*Operating.*PNC | Cash - Operating IV-PNC | Name mismatch: 'Cash.*Operating.*PNC' vs 'Cash - Operating IV-PNC'; Template marks as contra account but seed name doesn't indicate it |
| `1310-0000` | Escrow.*Property Tax | Escrow - Property Tax | Template marks as contra account but seed name doesn't indicate it |
| `0710-0000` | 5 Year Improvements? | 5 Year Improvements | Template marks as contra account but seed name doesn't indicate it |
| `1330-0000` | Escrow.*TI/LC | Escrow - TI/LC | Template marks as contra account but seed name doesn't indicate it |
| `1950-5000` | Internal.*Lease Commission | Internal - Lease Commission | Template marks as contra account but seed name doesn't indicate it |
| `0347-0000` | Escrow.*Other | Escrow - Other | Template marks as contra account but seed name doesn't indicate it |
| `0123-0000` | Cash.*Operating II | Cash - Operating II | Template marks as contra account but seed name doesn't indicate it |
| `2616-0000` | MidLand Loan Services.*PNC | MidLand Loan Services (PNC) | Name mismatch: 'MidLand Loan Services.*PNC' vs 'MidLand Loan Services (PNC)' |
| `0510-0000` | Land | Land | Template marks as contra account but seed name doesn't indicate it |
| `0610-0000` | Buildings | Buildings | Template marks as contra account but seed name doesn't indicate it |
| `1320-0000` | Escrow.*Insurance | Escrow - Insurance | Template marks as contra account but seed name doesn't indicate it |
| `1340-0000` | Escrow.*Replacement Reserves? | Escrow - Replacement Reserves | Template marks as contra account but seed name doesn't indicate it |
| `1081-0000` | Accum\\.? Depr\\..*15 Year | Accum. Depr. 15 Yr Impr. | Name mismatch: 'Accum\\.? Depr\\..*15 Year' vs 'Accum. Depr. 15 Yr Impr.' |
| `1082-0000` | Accum\\.? Depr\\..*Roof | Accum. Depr.-15Yr-09Remodel | Name mismatch: 'Accum\\.? Depr\\..*Roof' vs 'Accum. Depr.-15Yr-09Remodel' |
| `1099-0000` | Total Property & Equipment | Total Property & Equipment | Template marks as contra account but seed name doesn't indicate it |
| `2614-0000` | Wells Fargo | RAIT Financial | Name mismatch: 'Wells Fargo' vs 'RAIT Financial' |
| `2612-0000` | NorthMarq Capital | KeyBank | Name mismatch: 'NorthMarq Capital' vs 'KeyBank' |
| `0912-0000` | PARKING[- ]LOT | PARKING-LOT | Template marks as contra account but seed name doesn't indicate it |
| `0499-9000` | Total Current Assets | Total Current Assets | Template marks as contra account but seed name doesn't indicate it |
| `0950-0000` | TI/Current Improvements? | TI/Current Improvements | Template marks as contra account but seed name doesn't indicate it |
| `1920-0000` | Loan Costs? | Loan Costs | Template marks as contra account but seed name doesn't indicate it |
| `0910-0000` | Other Improvements? | Other Improvements | Template marks as contra account but seed name doesn't indicate it |
| `2139-0000` | Insurance Claim | A/P Wendover Commons LP | Name mismatch: 'Insurance Claim' vs 'A/P Wendover Commons LP' |
| `1950-0000` | External.*Lease Commission | External - Lease Commission | Template marks as contra account but seed name doesn't indicate it |
| `0810-0000` | 15 Year Improvements? | 15 Year Improvements | Template marks as contra account but seed name doesn't indicate it |
| `0306-0000` | A/R Other | A/R - Allowance for Doubtful | Template marks as contra account but seed name doesn't indicate it |
| `0816-0000` | 30 Year.*HVAC | 30 Year - HVAC | Template marks as contra account but seed name doesn't indicate it |
| `0815-0000` | 30 Year.*Roof | 30 Year - Roof | Template marks as contra account but seed name doesn't indicate it |

**Note:** Minor differences are expected due to regex patterns in template vs actual names in seed files.

---

## ✅ Successfully Matched (59 accounts)

Coverage: 93.7%

- **Assets:** 35
- **Liabilities:** 19
- **Equity:** 5

### Critical Accounts Verification:

⚠️ 6/9 critical accounts present
Missing critical accounts: 1999-0000, 2999-0000, 3999-9000

---

## Recommendations

### Action Items:

1. Add 4 missing accounts to seed SQL files
2. Review property mismatches (33 accounts)

### Notes:

- The template defines **core/example accounts** from the extraction requirements document
- The seed files contain **143 comprehensive accounts** for all 4 properties
- Having 84 additional accounts in seed files is **normal and beneficial**
- This indicates comprehensive coverage beyond the minimum requirements

---

## Conclusion

**Status: NEEDS ATTENTION ⚠️**

Some template-specified accounts are missing from seed files. Add these accounts before production deployment.
