# Configure Rule Page Implementation

## Summary

Changed the "Configure Rule" button behavior from opening a modal to navigating to a dedicated full page for rule configuration.

## Changes Made

### 1. Updated Rule Click Behavior (`src/components/financial_integrity/tabs/ByRuleTab.tsx`)

**Before:**
- Clicking "Configure Rule" called `onRuleClick(rule.rule_id)` which opened `EditRuleModal` as an overlay

**After:**
- Clicking "Configure Rule" navigates to dedicated page: `#rule-configuration/{ruleId}`
- Example: `#rule-configuration/BS-1`

```typescript
<button 
    onClick={() => {
        // Navigate to dedicated rule configuration page
        window.location.hash = `rule-configuration/${rule.rule_id}`;
    }}
    className="text-sm font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-auto"
>
    Configure Rule <ArrowRight className="w-4 h-4" />
</button>
```

### 2. Implemented Rule Update API (`src/lib/forensic_reconciliation.ts`)

**Before:**
- `updateCalculatedRule` was a placeholder that only logged to console

**After:**
- Properly calls backend API to create a new version of the rule
- Backend uses versioning system for audit trail

```typescript
async updateCalculatedRule(ruleId: string, ruleData: any): Promise<any> {
  const payload = {
    rule_id: ruleId,
    rule_name: ruleData.name,
    formula: ruleData.formula,
    description: ruleData.description,
    tolerance_absolute: ruleData.threshold || 0.01,
    // ... other fields
  };
  
  return api.post('/forensic-reconciliation/calculated-rules', payload);
}
```

### 3. Connected Rule Configuration Page to API (`src/pages/RuleConfigurationPage.tsx`)

**Before:**
- Save button only logged to console

**After:**
- Calls `forensicReconciliationService.updateCalculatedRule()`
- Refreshes data after save
- Closes modal automatically

```typescript
onSave={async (data) => {
    try {
       await forensicReconciliationService.updateCalculatedRule(ruleId, data);
       queryClient.invalidateQueries({ queryKey: ['rule-evaluation'] });
       setIsEditModalOpen(false);
    } catch (err) {
       console.error("Error updating rule:", err);
    }
}}
```

## How It Works

### Navigation Flow

1. User clicks "Configure Rule" on any rule in Financial Integrity Hub
2. Browser navigates to `#rule-configuration/{ruleId}`
3. `RuleConfigurationPage` component loads (already existed, now properly wired)
4. Page displays full rule details with ability to edit

### Data Persistence

#### UI Context (localStorage)
- **Property ID**: `forensic_selectedPropertyId`
- **Period ID**: `forensic_selectedPeriodId`
- Stored by `FinancialIntegrityHub` automatically
- Used by `RuleConfigurationPage` to fetch rule evaluation data
- Persists across page refreshes (not needed after service restart)

#### Rule Changes (Database)
- **Backend Endpoint**: `POST /api/v1/forensic-reconciliation/calculated-rules`
- **Versioning System**: Each update creates a new version (audit trail)
- **Database**: PostgreSQL `calculated_rules` table
- **Persistence**: ✅ Survives service restarts (stored in database)

### Backend Rule Versioning

The backend uses an intelligent versioning system:
- When POSTing with an existing `rule_id`, it creates a new version
- Original rule remains for historical reference
- Latest version is automatically used for new evaluations
- Full audit trail maintained

Example:
```
BS-1 v1 → Original rule
BS-1 v2 → Updated on Jan 24, 2026
BS-1 v3 → Updated on Jan 25, 2026 (active)
```

## Files Modified

1. **`src/components/financial_integrity/tabs/ByRuleTab.tsx`**
   - Changed button onClick to navigate instead of callback

2. **`src/lib/forensic_reconciliation.ts`**
   - Implemented `updateCalculatedRule` method with proper API call

3. **`src/pages/RuleConfigurationPage.tsx`**
   - Connected save handler to actual API service
   - Added query invalidation for data refresh

## Testing Checklist

### ✅ Verification Steps

1. **Navigation Test**
   - [ ] Click "Configure Rule" button
   - [ ] Verify browser navigates to new page (not modal)
   - [ ] URL should be `#rule-configuration/{ruleId}`

2. **Page Display Test**
   - [ ] Rule details should load correctly
   - [ ] Formula, description, values should display
   - [ ] "Edit Logic" button should be visible

3. **Edit Test**
   - [ ] Click "Edit Logic" button
   - [ ] Modal should open (now on dedicated page)
   - [ ] Make changes to rule (name, formula, threshold)
   - [ ] Click "Save Changes"

4. **Persistence Test**
   - [ ] Refresh the rule configuration page
   - [ ] Changes should still be visible
   - [ ] Restart backend service (`docker-compose restart backend`)
   - [ ] Navigate back to rule configuration page
   - [ ] Changes should still be visible ✅

5. **Navigation Test**
   - [ ] Click "Back to Hub" button
   - [ ] Should return to Financial Integrity Hub
   - [ ] Click "Configure Rule" on another rule
   - [ ] Should navigate to that rule's page

## Benefits of This Implementation

1. **Better UX**: Full page provides more space for rule details and editing
2. **Shareable Links**: Can bookmark or share direct links to specific rules
3. **Browser History**: Back button works naturally
4. **Data Persistence**: Changes saved to database, survive all restarts
5. **Audit Trail**: Backend versioning system tracks all changes
6. **No Breaking Changes**: Existing modal can still be used elsewhere if needed

## Database Schema

The rule updates are persisted in the `calculated_rules` table:

```sql
CREATE TABLE calculated_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    rule_name VARCHAR NOT NULL,
    formula TEXT NOT NULL,
    description TEXT,
    tolerance_absolute DECIMAL,
    tolerance_percent DECIMAL,
    severity VARCHAR DEFAULT 'medium',
    effective_date DATE NOT NULL,
    expires_at DATE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(rule_id, version)
);
```

## API Endpoint Details

### Create/Update Rule (Versioning)

**Endpoint**: `POST /api/v1/forensic-reconciliation/calculated-rules`

**Request Body**:
```json
{
  "rule_id": "BS-1",
  "rule_name": "Accounting Equation",
  "formula": "Total Assets - (Total Liabilities & Capital)",
  "description": "Total Assets must equal Total Liabilities & Capital",
  "tolerance_absolute": 0.01,
  "tolerance_percent": null,
  "severity": "medium",
  "property_scope": null,
  "doc_scope": {"all": true},
  "effective_date": "2026-01-24",
  "expires_at": null
}
```

**Response**:
```json
{
  "id": 123,
  "rule_id": "BS-1",
  "version": 2,
  "rule_name": "Accounting Equation"
}
```

## Troubleshooting

### Rule not saving?
- Check browser console for API errors
- Verify backend is running: `docker-compose ps`
- Check backend logs: `docker-compose logs backend | tail -50`

### Page shows "Context Missing"?
- Navigate via Financial Integrity Hub first
- Don't access rule configuration page directly via URL on first visit

### Changes not visible after refresh?
- Check database directly: `SELECT * FROM calculated_rules WHERE rule_id = 'BS-1' ORDER BY version DESC;`
- Verify API returned success (200/201 status)

## Future Enhancements

- [ ] Add toast notifications for save success/failure
- [ ] Show version history in the UI
- [ ] Add "Restore Previous Version" functionality
- [ ] Add rule validation before saving
- [ ] Add real-time preview of formula evaluation
