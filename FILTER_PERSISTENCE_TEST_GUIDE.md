# Filter Persistence Testing Guide

**Quick 3-Minute Test**

---

## ✅ **Test 1: Navigation Persistence**

1. **Go to Forensic Audit Dashboard** (`localhost:5173/#forensic-audit-dashboard`)
2. **Select Filters**:
   - Property: **Eastern Shore Plaza**
   - Period: **2025-10**
3. **Click these tabs in order** (verify same filters on each):
   - ✅ Math Integrity
   - ✅ Performance
   - ✅ Fraud Detection
   - ✅ Covenants
   - ✅ Tenant Risk
   - ✅ Collections
   - ✅ Documents
   - ✅ Reconciliation
   - ✅ History (property only)

**Expected**: Each page shows **Eastern Shore Plaza + 2025-10**

---

## ✅ **Test 2: Filter Change Persistence**

1. **On Performance page**, change to:
   - Property: **Different property**
   - Period: **2025-11**
2. **Click "Math Integrity" tab**
3. **Verify**: Shows new property + **2025-11**

---

## ✅ **Test 3: Browser Refresh**

1. **On any forensic audit page** with filters selected
2. **Press F5** (refresh browser)
3. **Verify**: Filters are restored after refresh

---

## ✅ **Test 4: Back/Forward Navigation**

1. **Navigate**: Forensic Audit → Math Integrity → Performance
2. **Click browser back button**
3. **Verify**: Returns to Math Integrity with same filters
4. **Click forward button**
5. **Verify**: Returns to Performance with same filters

---

## 🎯 **Success Criteria**

All tests should show:
- ✅ Filters persist across tab navigation
- ✅ Filter changes sync immediately
- ✅ Refresh maintains selections
- ✅ Browser history navigation works correctly

---

## 🐛 **If Something Doesn't Work**

1. **Clear localStorage**: Open DevTools Console, run `localStorage.clear()`
2. **Hard refresh**: `Ctrl + Shift + R`
3. **Check console**: Look for errors in browser DevTools
4. **Verify keys**: Run `localStorage.getItem('reims_forensic_property_id')` in console

---

**Expected Test Duration**: 3 minutes  
**Status**: Ready for testing
