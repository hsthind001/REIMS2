# REIMS2 Reconciliation System - User Guide

**Version**: 1.0  
**For**: End Users  
**Date**: November 8, 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Starting a Reconciliation](#starting-a-reconciliation)
4. [Understanding the Interface](#understanding-the-interface)
5. [Reviewing Differences](#reviewing-differences)
6. [Resolving Discrepancies](#resolving-discrepancies)
7. [Bulk Operations](#bulk-operations)
8. [Generating Reports](#generating-reports)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

The Reconciliation System ensures **100% data quality** by allowing you to compare original PDF financial documents with extracted database records side-by-side. This helps identify and correct any discrepancies, ensuring zero data loss.

### What You Can Do

✅ Compare PDF documents with database records  
✅ View differences color-coded by severity  
✅ Resolve discrepancies individually or in bulk  
✅ Generate reconciliation reports  
✅ Maintain complete audit trail  

---

## Getting Started

### Prerequisites

1. **Login**: You must be logged into REIMS2
2. **Documents**: Financial documents should be uploaded first
3. **Permissions**: Ensure you have reconciliation access

### Accessing Reconciliation

1. Click on the **🔄 Reconciliation** menu item in the left sidebar
2. The Reconciliation page will open

---

## Starting a Reconciliation

### Step 1: Select Document

At the top of the page, you'll see a selection panel with five dropdowns:

1. **Property**: Choose the property you want to reconcile
   - Example: `ESP001 - Eastern Shore Plaza`

2. **Year**: Select the financial year
   - Example: `2024`

3. **Month**: Choose the financial month
   - Example: `December`

4. **Document Type**: Pick the type of financial statement
   - 📊 Balance Sheet
   - 💰 Income Statement
   - 💵 Cash Flow
   - 🏠 Rent Roll

5. Click **"Start Reconciliation"** button

### Step 2: Wait for Processing

The system will:
1. Retrieve the PDF from storage
2. Extract database records
3. Compare field-by-field
4. Calculate differences
5. Display results (typically takes 2-5 seconds)

---

## Understanding the Interface

### Summary Statistics

After starting reconciliation, you'll see four cards at the top:

| Card | Meaning |
|------|---------|
| **📊 Total Records** | Total number of accounts/line items |
| **✓ Matches** | Records that match exactly or within tolerance |
| **⚠ Differences** | Records with discrepancies |
| **📝 Selected** | Number of records you've selected for bulk actions |

### Split-Screen View

The main area is divided into two panels:

#### Left Panel: Original PDF
- Shows the original PDF document
- You can scroll through pages
- This is your "source of truth"

#### Right Panel: Database Records
- Shows extracted data in a table format
- Color-coded by match status
- Includes checkboxes for selection
- Action buttons for each row

---

## Reviewing Differences

### Color Coding

Each row in the data table is color-coded:

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 **Green** | Match | Values match exactly (within $0.01) |
| 🟡 **Yellow** | Within Tolerance | Values differ by less than 1% |
| 🔴 **Red** | Mismatch | Significant difference |
| ⚪ **Gray** | Missing in PDF | Record exists in database but not in PDF |
| 🟣 **Purple** | Missing in DB | Record exists in PDF but not in database |

### Filter Options

Use the filter buttons to focus on specific records:

- **All**: Show all records
- **Matches**: Show only exact matches
- **Differences**: Show only mismatches and missing records

### Table Columns

| Column | Description |
|--------|-------------|
| Checkbox | Select for bulk operations |
| Account Code | Account identifier (e.g., "0122-0000") |
| Account Name | Description (e.g., "Cash - Operating") |
| PDF Value | Amount extracted from PDF |
| DB Value | Amount currently in database |
| Difference | Absolute difference between values |
| Status | Color-coded match status |
| Actions | "Resolve" button for mismatches |

---

## Resolving Discrepancies

### Option 1: Individual Resolution

For each difference:

1. Click the **"Resolve"** button in the Actions column
2. A dialog will appear (future feature) OR
3. Use bulk operations (see below)

### Option 2: Bulk Resolution

For multiple differences at once:

1. **Check the boxes** next to records you want to resolve
2. Click **"Accept PDF Values (X)"** button at the top
3. The system will:
   - Update all selected records
   - Set values to match PDF
   - Create audit trail entries
   - Refresh the view

### Resolution Actions

| Action | When to Use |
|--------|-------------|
| **Accept PDF** | PDF is correct, update database to match |
| **Accept DB** | Database is correct, PDF had errors |
| **Manual Entry** | Both are wrong, enter correct value |
| **Ignore** | Acceptable difference, no action needed |

---

## Bulk Operations

### Step-by-Step Guide

1. **Filter** to show only the records you want to resolve
   - Example: Click "Differences" to show only mismatches

2. **Select Records**
   - Check individual boxes, OR
   - Check the header checkbox to select all visible records

3. **Choose Action**
   - Click "Accept PDF Values (X)" button
   - X = number of selected records

4. **Confirm**
   - Review the summary
   - Confirm the bulk operation

5. **Verify**
   - The page will refresh
   - Selected records should now show as "Match"

### Bulk Operation Tips

✅ **DO**: Start with exact matches (green) to verify extraction is correct  
✅ **DO**: Review high-value mismatches individually  
✅ **DO**: Export report before bulk operations for backup  
❌ **DON'T**: Bulk accept without reviewing sample records  
❌ **DON'T**: Mix different types of issues in one bulk operation  

---

## Generating Reports

### Export Reconciliation Report

1. Click **"📊 Export Report"** button
2. Report will download as CSV file
3. Filename format: `reconciliation_ESP001_2024-12.csv`

### Report Contents

The report includes:

**Columns**:
- Account Code
- Account Name  
- PDF Value
- DB Value
- Difference
- Difference %
- Type (exact, mismatch, etc.)
- Status (pending, resolved)

**Use Cases**:
- Share with accounting team
- Archive for compliance
- Analyze patterns in discrepancies
- Present to auditors

---

## Best Practices

### Before Reconciliation

1. **Verify Upload**: Ensure PDF uploaded successfully
2. **Check Extraction**: Review extraction status on Documents page
3. **Understand Data**: Know which accounts are expected

### During Reconciliation

1. **Review Systematically**:
   - Start with totals (Assets, Liabilities, etc.)
   - Work through sections (Current Assets, Long-Term Debt, etc.)
   - Check detail accounts last

2. **Prioritize by Severity**:
   - Critical: Missing accounts (gray/purple)
   - High: Large mismatches (red, >$10K)
   - Medium: Small mismatches (red, <$10K)
   - Low: Within tolerance (yellow)

3. **Investigate Before Resolving**:
   - Compare PDF visually with table
   - Check for OCR errors
   - Verify calculations
   - Consult source documents if needed

### After Reconciliation

1. **Export Report**: Always export for your records
2. **Review Summary**: Check total matches vs differences
3. **Mark Complete**: (Future feature) Lock the reconciliation
4. **Notify Team**: Share results with relevant stakeholders

---

## Troubleshooting

### PDF Not Displaying

**Problem**: Left panel shows "PDF not available"

**Solutions**:
1. Check that document was uploaded for this property/period
2. Verify document type matches your selection
3. Try refreshing the page
4. Contact support if issue persists

### No Differences Showing

**Problem**: Table shows "No records found"

**Solutions**:
1. Verify documents have been extracted (check Documents page)
2. Ensure extraction status is "completed"
3. Try a different property/period that has data
4. Contact support if data should exist

### All Records Show as Mismatches

**Problem**: Every record is marked as red

**Possible Causes**:
1. Wrong document uploaded (e.g., different property)
2. Extraction errors
3. Database corruption

**Solutions**:
1. Verify PDF property matches selection
2. Re-upload and re-extract the document
3. Contact support for database check

### Bulk Operation Fails

**Problem**: "Bulk resolve failed" error message

**Solutions**:
1. Check you're still logged in
2. Reduce number of selected records
3. Try resolving individually
4. Check browser console for detailed error
5. Contact support with error message

### Slow Performance

**Problem**: Reconciliation takes >10 seconds to load

**Solutions**:
1. Check internet connection
2. Verify server is running (IT team)
3. Try with fewer records (different document type)
4. Clear browser cache
5. Try different browser

---

## Frequently Asked Questions

### Q: How often should I reconcile?

**A**: Reconcile immediately after each document upload, or at minimum monthly for each property.

### Q: What tolerance is used for "exact match"?

**A**: $0.01 for absolute difference, or 1% for percentage difference.

### Q: Can I undo a bulk operation?

**A**: Not directly. You can re-run reconciliation and accept database values to revert. Always export a report before bulk operations.

### Q: Who can see my reconciliation sessions?

**A**: All users with reconciliation access can see all sessions. Individual resolutions are attributed to the user who made them.

### Q: How long are reconciliation sessions kept?

**A**: Indefinitely. All sessions and resolutions are maintained for audit purposes.

### Q: Can I reconcile across multiple properties at once?

**A**: Not currently. Reconcile each property individually for accuracy.

### Q: What if I find errors in the original PDF?

**A**: Mark the database value as correct, or use manual entry to input the correct value. Add notes explaining the discrepancy.

---

## Getting Help

### In-App Support

- Look for **ℹ️ Info** icons for tooltips
- Check the **Help** menu for documentation links

### Documentation

- Technical Documentation: `RECONCILIATION_SYSTEM.md`
- API Documentation: http://localhost:8000/docs

### Contact Support

For assistance:
- Email: support@reims2.example.com
- Phone: (555) 123-4567
- Hours: Mon-Fri 9am-5pm EST

---

## Keyboard Shortcuts (Future Feature)

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all visible records |
| `Ctrl+D` | Deselect all |
| `Ctrl+E` | Export report |
| `Ctrl+R` | Refresh reconciliation |
| `Esc` | Close dialog |
| `Space` | Toggle selection on focused row |

---

## Tips & Tricks

### Tip 1: Use Filters Efficiently

Filter to "Differences" first, then work through high-value items before bulk resolving small items.

### Tip 2: Export Before Bulk Operations

Always export a report before doing bulk operations. This gives you a backup in case you need to revert.

### Tip 3: Check Totals First

Verify section totals (Total Assets, Total Liabilities, etc.) match before worrying about individual line items.

### Tip 4: Look for Patterns

If many accounts in the same section are off by the same amount, there may be a systematic issue.

### Tip 5: Document Your Decisions

Use the "reason" field when resolving differences to explain your decision for audit purposes.

---

## Success Criteria

A successful reconciliation session should have:

✅ **High Match Rate**: >95% of records showing green or yellow  
✅ **Zero Missing Accounts**: No gray or purple entries  
✅ **Resolved Differences**: All red entries either resolved or documented  
✅ **Exported Report**: CSV file downloaded for records  
✅ **Audit Trail**: All resolutions have reasons documented  

---

## Glossary

| Term | Definition |
|------|------------|
| **Reconciliation** | Process of comparing and verifying two sets of records |
| **Difference** | Discrepancy between PDF and database values |
| **Tolerance** | Acceptable margin of error (±$0.01 or ±1%) |
| **Match** | Records that agree within tolerance |
| **Resolution** | Action taken to correct a difference |
| **Bulk Operation** | Applying same action to multiple records |
| **Session** | Single reconciliation event with start and end times |
| **Audit Trail** | Complete history of who changed what and when |

---

## Appendix: Sample Workflow

### Monthly Reconciliation Workflow

**Monday Morning**:
1. Upload all monthly financial PDFs for all properties
2. Wait for extraction to complete (check Documents page)

**Monday Afternoon**:
3. Start reconciliation for Property 1, Balance Sheet
4. Review differences, resolve any critical issues
5. Export report for Property 1 Balance Sheet
6. Repeat for Income Statement, Cash Flow, Rent Roll
7. Move to Property 2, repeat steps 3-6

**Tuesday**:
8. Continue with remaining properties
9. Compile all exported reports
10. Share summary with accounting team
11. File reports for audit trail

**End of Month**:
12. Generate summary report of all reconciliations
13. Track improvement trends (fewer differences over time)

---

**Thank you for using REIMS2 Reconciliation System!**

For feedback or feature requests, contact the development team.

---

**Last Updated**: November 8, 2025  
**Version**: 1.0

