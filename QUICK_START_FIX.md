# 🚀 QUICK START - Fix Display Issue

## Problem You're Seeing

**By Document Tab showing:**
- ❌ Rent Roll: Only 2 rules (should be 9)
- ❌ Three Statement Integration: MISSING (should show 23 rules)

---

## ⚡ Quick Fix (3 Minutes)

### Step 1: Run Seed Script
```bash
cd /home/hsthind/Documents/GitHub/REIMS2
./backend/scripts/apply_all_seed_files.sh
```

**This will:**
- Apply all 6 seed files to database
- Insert 135 validation rules
- Show verification results

**Expected Output:**
```
✅ All seed files applied successfully!

Verification:
balance_sheet               | 35 rules
income_statement            | 31 rules
three_statement_integration | 23 rules  ⭐
cash_flow                   | 23 rules
mortgage_statement          | 14 rules
rent_roll                   |  9 rules  ⭐
--------------------------------
TOTAL                       | 135 rules
```

### Step 2: Restart Backend
```bash
docker-compose restart backend
```

### Step 3: Refresh Browser
- Open Financial Integrity Hub
- Hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
- Select property and period
- Click **"Validate"**

---

## ✅ Expected Result

**By Document Tab should show:**
```
Balance Sheet                  35 Active Rules
Income Statement               31 Active Rules
Cash Flow                      23 Active Rules
Rent Roll                       9 Active Rules  ⭐
Mortgage Statement             14 Active Rules
Three Statement Integration    23 Active Rules  ⭐ NEW!
```

**Total: 135 rules across 6 categories**

---

## 🚨 If Something Goes Wrong

### Issue: "Database container not running"
```bash
docker-compose up -d
sleep 10
./backend/scripts/apply_all_seed_files.sh
```

### Issue: "Permission denied"
```bash
chmod +x backend/scripts/apply_all_seed_files.sh
./backend/scripts/apply_all_seed_files.sh
```

### Issue: Still showing old counts
1. Clear browser cache completely
2. `docker-compose restart backend`
3. Close and reopen browser
4. Try again

---

## 📚 For More Details

See: `DISPLAY_FIX_AND_SEED_APPLICATION.md` for:
- Detailed explanations
- What each seed file does
- Verification queries
- Troubleshooting guide
- Before/after comparisons

---

**That's it! Should take less than 3 minutes total.**

🎉 **You'll then have all 135 rules across 6 categories working perfectly!**
