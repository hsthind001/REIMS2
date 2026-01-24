# Testing Guide: Edit Logic Page Navigation

## Quick Test Steps

### 1. Navigate to Rule Configuration Page

```bash
# Ensure application is running
cd /home/hsthind/Documents/GitHub/REIMS2
docker-compose ps

# Open in browser
http://localhost:5173/#forensic-reconciliation
```

1. Select a property from dropdown
2. Select a period from dropdown
3. Click "Run Reconciliation" or "Validate"
4. Click on "By Rule" tab
5. Click "Configure Rule" on any rule (e.g., "BS-1 Accounting Equation")

**Expected:** Rule configuration page loads showing rule details

### 2. Test "Edit Logic" Button

1. Scroll down to bottom of rule configuration page
2. Find "Edit Logic" button on the right side
3. Click "Edit Logic" button

**Expected:** 
- ❌ Should NOT open a modal overlay
- ❌ Should NOT see a semi-transparent backdrop
- ✅ Should navigate to new page
- ✅ URL should change to `#rule-edit/BS-1` (or similar)
- ✅ Page shows full-screen edit form

### 3. Verify Edit Page Layout

**Expected Elements:**
- [ ] "Back to Rule" button at top left
- [ ] "Edit Rule Logic" heading
- [ ] Rule ID badge (e.g., "BS-1")
- [ ] "Editing Logic" blue badge
- [ ] "Configure Rule" heading
- [ ] Warning banner about advanced configuration
- [ ] Rule Name input field (pre-filled)
- [ ] Description textarea (pre-filled)
- [ ] Execution Formula textarea with dark background (pre-filled)
- [ ] Variance Threshold number input (pre-filled)
- [ ] "Cancel" button at bottom
- [ ] "Save Changes" button at bottom

### 4. Test Form Editing

1. Change the rule name:
   - Add " - Updated" to the end
   - Example: "Accounting Equation" → "Accounting Equation - Updated"

2. Change the description:
   - Modify the text or add new information

3. Change the threshold:
   - Change from 0.01 to 0.05

**Expected:**
- [ ] All fields are editable
- [ ] Changes are reflected immediately in form
- [ ] No console errors

### 5. Test Save Functionality

1. Click "Save Changes" button

**Expected:**
- [ ] Button shows loading spinner
- [ ] Button text might change or show loading state
- [ ] After ~1 second, automatically navigate back
- [ ] URL changes back to `#rule-configuration/BS-1`
- [ ] Rule configuration page loads
- [ ] Changes are visible immediately

### 6. Verify Changes Persisted

1. Check rule name on configuration page
2. Scroll down and click "Edit Logic" again
3. Verify changes are still there

**Expected:**
- [ ] Rule name shows " - Updated" suffix
- [ ] Description shows modified text
- [ ] Threshold shows 0.05

### 7. Test Cancel Functionality

1. Click "Edit Logic" button
2. Make some changes (don't save)
3. Click "Cancel" button

**Expected:**
- [ ] Navigate back to rule configuration page
- [ ] Original values unchanged (no " - Updated" in name if you remove it)
- [ ] URL back to `#rule-configuration/BS-1`

### 8. Test "Back to Rule" Button

1. Click "Edit Logic" button
2. Click "Back to Rule" button at top left

**Expected:**
- [ ] Navigate back to rule configuration page
- [ ] Same behavior as Cancel button
- [ ] Any unsaved changes are lost

### 9. Test Browser Navigation

1. Click "Edit Logic" button
2. Use browser back button (or Alt+Left Arrow)

**Expected:**
- [ ] Navigate back to rule configuration page
- [ ] Browser back button works correctly
- [ ] Can use browser forward button to return to edit page

### 10. Test Service Restart Persistence

```bash
# After making and saving changes
cd /home/hsthind/Documents/GitHub/REIMS2
docker-compose restart backend

# Wait 10 seconds
sleep 10

# Check backend is running
docker-compose ps backend
```

**In Browser:**
1. Refresh the page (F5)
2. Or navigate back to rule and open edit page

**Expected:**
- [ ] All saved changes still visible
- [ ] Data loaded from database successfully
- [ ] No data loss after restart

## Visual Test Checklist

### Modal vs Page Comparison

#### Old Behavior (Modal) ❌
```
Click "Edit Logic"
        ↓
Modal appears with semi-transparent backdrop
        ↓
Background page still visible
        ↓
Limited space for editing
        ↓
URL doesn't change
        ↓
Can't bookmark or share
```

#### New Behavior (Full Page) ✅
```
Click "Edit Logic"
        ↓
Navigate to new page (#rule-edit/BS-1)
        ↓
Full screen edit form
        ↓
Previous page hidden (clean view)
        ↓
URL changes (can bookmark/share)
        ↓
Browser back button works
        ↓
After save, auto-return to previous page
```

## Form Validation Test

### 1. Test Required Fields

1. Click "Edit Logic"
2. Clear the "Rule Name" field
3. Try to save

**Expected:**
- [ ] Error message appears: "Rule name is required"
- [ ] Form doesn't submit
- [ ] Border turns red on invalid field

### 2. Test Formula Field

1. Clear the formula field
2. Try to save

**Expected:**
- [ ] Error message appears: "Formula is required"
- [ ] Form doesn't submit

### 3. Test Threshold Field

1. Enter a negative number in threshold
2. Try to save

**Expected:**
- [ ] Should accept negative values (valid use case)
- [ ] Or show error if business logic prevents it

## API Verification

### Check Network Traffic

**In Browser DevTools (F12):**
1. Open Network tab
2. Click "Save Changes"
3. Look for POST request

**Expected:**
- Request URL: `/api/v1/forensic-reconciliation/calculated-rules`
- Request Method: POST
- Status: 201 Created
- Response: Contains new version number

### Check Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d reims

# Check latest rule version
SELECT rule_id, version, rule_name, formula, tolerance_absolute, created_at 
FROM calculated_rules 
WHERE rule_id = 'BS-1' 
ORDER BY version DESC 
LIMIT 5;

# Expected output:
# rule_id | version |      rule_name           | formula | tolerance_absolute |      created_at
# --------+---------+-------------------------+---------+-------------------+---------------------
# BS-1    |    3    | Accounting Equation - U…| ...     | 0.05              | 2026-01-24 16:30:00
# BS-1    |    2    | Accounting Equation     | ...     | 0.01              | 2026-01-24 16:00:00
# BS-1    |    1    | Accounting Equation     | ...     | 0.01              | 2026-01-20 10:00:00
```

### Check Backend Logs

```bash
# Watch logs during save
docker-compose logs -f backend

# Look for:
# - POST /api/v1/forensic-reconciliation/calculated-rules
# - Status: 201
# - "Created new version X for rule BS-1"
```

## Edge Cases

### 1. Direct URL Access

1. Copy the edit page URL: `http://localhost:5173/#rule-edit/BS-1`
2. Open in new tab
3. Paste URL

**Expected:**
- [ ] Page loads but shows loading spinner
- [ ] May show error if localStorage empty
- [ ] Should handle gracefully

### 2. Rapid Navigation

1. Click "Edit Logic"
2. Immediately click "Back to Rule"
3. Immediately click "Edit Logic" again

**Expected:**
- [ ] No errors
- [ ] Navigation works smoothly
- [ ] Data loads correctly each time

### 3. Concurrent Edits (Multiple Tabs)

1. Open rule configuration in two tabs
2. Edit in tab 1 and save
3. Edit in tab 2 and save

**Expected:**
- [ ] Both saves create new versions
- [ ] No data loss
- [ ] Version numbers increment correctly (v1, v2, v3)

### 4. Very Long Formula

1. Enter a very long formula (500+ characters)
2. Save

**Expected:**
- [ ] Form accepts long text
- [ ] Save succeeds
- [ ] No truncation of data

## Mobile/Responsive Test

### Desktop (1920x1080)
- [ ] Form displays in center
- [ ] Good spacing and readability
- [ ] Buttons aligned properly

### Tablet (768x1024)
- [ ] Form scales appropriately
- [ ] All elements visible
- [ ] Touch-friendly buttons

### Mobile (375x667)
- [ ] Form takes full width
- [ ] Buttons stack vertically if needed
- [ ] Easy to type in fields
- [ ] Better than modal approach

## Performance Test

1. Click "Edit Logic" - measure time to navigate
2. Make changes - measure input responsiveness
3. Click "Save Changes" - measure save time
4. Observe auto-navigation back

**Expected Times:**
- Navigation: < 100ms
- Page load: < 500ms
- Form render: < 100ms
- Save + navigate: < 2 seconds
- Overall smooth experience

## Accessibility Test

### Keyboard Navigation

1. Tab through all form fields
2. Shift+Tab to go backwards
3. Enter to submit form
4. Escape to cancel (optional enhancement)

**Expected:**
- [ ] All fields are keyboard accessible
- [ ] Logical tab order
- [ ] Visible focus indicators
- [ ] Can complete full workflow with keyboard only

### Screen Reader Test

1. Use screen reader (NVDA, JAWS, or VoiceOver)
2. Navigate through form
3. Listen to field labels and descriptions

**Expected:**
- [ ] All fields have proper labels
- [ ] Error messages are announced
- [ ] Button purposes are clear

## Success Criteria

✅ All these should work:
- [ ] Click "Edit Logic" navigates to new page (not modal)
- [ ] Full-screen edit form displays correctly
- [ ] All rule data pre-populated in form
- [ ] Can edit all fields
- [ ] Save creates new rule version in database
- [ ] Auto-navigate back after save
- [ ] Changes visible immediately on rule page
- [ ] Changes persist after browser refresh
- [ ] Changes persist after backend restart
- [ ] Cancel returns to rule page without saving
- [ ] Back button works correctly
- [ ] Browser history works properly
- [ ] No console errors during any operation
- [ ] Form validation works correctly
- [ ] API calls succeed (check Network tab)
- [ ] Database shows new version (check DB)

## Comparison Test Results

| Feature | Modal (Old) | Full Page (New) | Status |
|---------|-------------|-----------------|--------|
| Opens in overlay | ✅ Yes | ❌ No | ✅ Fixed |
| URL changes | ❌ No | ✅ Yes | ✅ Improved |
| Can bookmark | ❌ No | ✅ Yes | ✅ Improved |
| Browser back works | ❌ No | ✅ Yes | ✅ Improved |
| Full screen space | ❌ No | ✅ Yes | ✅ Improved |
| Changes persist | ✅ Yes | ✅ Yes | ✅ Maintained |
| Mobile friendly | ⚠️ Small | ✅ Full screen | ✅ Improved |

## Troubleshooting

### Issue: Page shows blank/loading forever
**Solution:**
1. Check browser console for errors
2. Verify localStorage has `editingRule` key
3. Navigate from rule configuration page (don't use direct URL)

### Issue: Save button doesn't work
**Solution:**
1. Check form validation errors
2. Check browser console for API errors
3. Verify backend is running: `docker-compose ps`
4. Check backend logs: `docker-compose logs backend | tail -20`

### Issue: Changes not persisting
**Solution:**
1. Check Network tab for failed API requests
2. Verify database connection
3. Check backend logs for errors
4. Try clearing browser cache and retry

### Issue: Can't navigate back
**Solution:**
1. Use browser back button
2. Click "Back to Rule" button
3. Navigate via sidebar to hub

## Final Checklist

Before marking as complete, verify:
- [ ] No modal appears when clicking "Edit Logic"
- [ ] New page opens with full-screen form
- [ ] All data persists after save
- [ ] Browser navigation works correctly
- [ ] No console errors
- [ ] Database shows new versions
- [ ] Performance is acceptable
- [ ] Mobile experience is good
- [ ] Accessibility requirements met
- [ ] All edge cases handled
