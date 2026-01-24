# Testing Guide: Configure Rule Page Navigation

## Quick Test Steps

### 1. Access Financial Integrity Hub

```bash
# Start the application if not running
cd /home/hsthind/Documents/GitHub/REIMS2
docker-compose up -d

# Open in browser
http://localhost:5173/#forensic-reconciliation
```

**Expected:** Financial Integrity Hub page loads with property/period selector

### 2. Navigate to "By Rule" Tab

1. Select a property from dropdown
2. Select a period from dropdown
3. Click "Run Reconciliation" or "Validate" button
4. Wait for rules to evaluate
5. Click on the "By Rule" tab

**Expected:** See list of rules with their pass/fail status

### 3. Test "Configure Rule" Button

1. Hover over any rule card
2. Observe "Configure Rule" button appears on the right
3. Click "Configure Rule" button

**Expected:** 
- ❌ Should NOT open a modal overlay
- ✅ Should navigate to new page
- ✅ URL should change to `#rule-configuration/BS-1` (or similar)
- ✅ Page should show full rule details

### 4. Verify Rule Configuration Page

**Expected Elements:**
- [ ] "Back to Hub" button at top left
- [ ] Rule ID badge (e.g., "BS-1")
- [ ] Rule name as heading (e.g., "Accounting Equation")
- [ ] Status badge (Passing/Failing/Missing Data)
- [ ] Formula section with code block
- [ ] Source Value and Target Value comparison cards
- [ ] Execution History table (may be empty)
- [ ] "Edit Logic" button at bottom right

### 5. Test Rule Editing

1. Click "Edit Logic" button at bottom right
2. Modal should open (EditRuleModal)
3. Make a change:
   - Change rule name (e.g., add " - Updated")
   - Change description
   - Change threshold value
4. Click "Save Changes"

**Expected:**
- [ ] Modal closes automatically
- [ ] Page shows updated values immediately
- [ ] No console errors

### 6. Test Persistence (Browser Refresh)

1. Press F5 or Ctrl+R to refresh the page
2. Wait for page to reload

**Expected:**
- [ ] Rule configuration page loads again
- [ ] All your changes are still visible
- [ ] URL is still `#rule-configuration/{ruleId}`

### 7. Test Persistence (Service Restart)

```bash
# Restart backend service
cd /home/hsthind/Documents/GitHub/REIMS2
docker-compose restart backend

# Wait 10 seconds for backend to restart
sleep 10

# Check backend is running
docker-compose ps backend
```

**In Browser:**
1. Refresh the rule configuration page
2. Or navigate back to hub and click "Configure Rule" again

**Expected:**
- [ ] Rule changes are still visible
- [ ] Data loaded from database successfully

### 8. Test Navigation Back

1. Click "Back to Hub" button
2. Should return to Financial Integrity Hub
3. Click "Configure Rule" on a different rule
4. Should navigate to that rule's page

**Expected:**
- [ ] Back navigation works
- [ ] Can view different rules sequentially
- [ ] Browser back button also works

## Visual Test Checklist

### Before Changes (Old Behavior)
```
Financial Integrity Hub → Click "Configure Rule"
                       ↓
                   Modal Opens (Overlay)
                       ↓
              Edit & Save in Modal
                       ↓
              Modal Closes
                       ↓
                Still on Hub Page
```

### After Changes (New Behavior)  
```
Financial Integrity Hub → Click "Configure Rule"
                       ↓
         Navigate to New Page (#rule-configuration/BS-1)
                       ↓
            Full Page with Rule Details
                       ↓
         Click "Edit Logic" → Modal Opens
                       ↓
              Edit & Save
                       ↓
         Modal Closes, Data Refreshes
                       ↓
         Still on Rule Configuration Page
                       ↓
         Click "Back to Hub"
                       ↓
         Return to Financial Integrity Hub
```

## API Verification

### Check Rule Version in Database

```bash
# Connect to PostgreSQL container
docker-compose exec postgres psql -U postgres -d reims

# Check rule versions
SELECT rule_id, version, rule_name, created_at 
FROM calculated_rules 
WHERE rule_id = 'BS-1' 
ORDER BY version DESC;

# Expected output:
# rule_id | version |      rule_name        |      created_at
# --------+---------+----------------------+---------------------
# BS-1    |    2    | Accounting Equation  | 2026-01-24 16:00:00
# BS-1    |    1    | Accounting Equation  | 2026-01-20 10:00:00
```

### Check Backend Logs

```bash
# Watch backend logs while saving
docker-compose logs -f backend

# Look for these log entries after saving:
# - POST /api/v1/forensic-reconciliation/calculated-rules
# - Status: 201 (Created)
# - Response contains new version number
```

### Check Network Traffic

**In Browser DevTools (F12):**
1. Go to Network tab
2. Click "Save Changes" on a rule
3. Look for POST request to `/api/v1/forensic-reconciliation/calculated-rules`

**Expected:**
- Request Method: POST
- Status: 201 Created
- Response: `{"id": 123, "rule_id": "BS-1", "version": 2, "rule_name": "..."}`

## Troubleshooting

### Issue: "Configure Rule" button not visible
**Solution:** Hover over the rule card - button appears on hover

### Issue: Page shows "Context Missing"
**Solution:** 
1. Go back to Financial Integrity Hub
2. Select property and period
3. Then navigate to rule configuration

### Issue: Changes not saving
**Check:**
1. Browser console for errors (F12 → Console)
2. Network tab for failed requests (F12 → Network)
3. Backend logs: `docker-compose logs backend | tail -50`

### Issue: Old data showing after refresh
**Check:**
1. Clear browser cache (Ctrl+Shift+R)
2. Verify backend database has new version
3. Check if browser is caching API responses

## Success Criteria

✅ All these should work:
- [ ] Click "Configure Rule" navigates to new page (not modal)
- [ ] Rule details display correctly on full page
- [ ] Can edit rule via "Edit Logic" button
- [ ] Changes save successfully to backend
- [ ] Changes persist after browser refresh
- [ ] Changes persist after backend restart
- [ ] Can navigate back to hub
- [ ] Can view multiple different rules
- [ ] Browser back/forward buttons work
- [ ] No console errors during navigation or saving

## Performance Test

1. Click "Configure Rule" - should navigate instantly (<100ms)
2. Page should load within 1 second
3. Editing modal should open instantly
4. Save should complete within 2 seconds
5. Data refresh should be automatic after save

## Accessibility Test

1. Tab through the page with keyboard
2. "Configure Rule" button should be focusable
3. Can press Enter to activate button
4. "Back to Hub" button should be focusable
5. Modal should trap focus
6. Escape key should close modal

## Browser Compatibility

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox  
- [ ] Safari (if available)

All functionality should work identically across browsers.
