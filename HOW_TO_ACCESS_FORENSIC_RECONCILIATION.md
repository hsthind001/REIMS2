# How to Access Forensic Reconciliation on the Frontend

**Quick Guide:** Where to find the Forensic Reconciliation Elite System in the UI

---

## 🎯 Access Methods

### Method 1: From Financial Command Page (Recommended)

1. **Click on "Financial Command"** in the left sidebar (💰 icon)
2. **Look for the purple button** at the top right of the tabs section
3. **Click "🔍 Forensic Reconciliation"** button
4. You'll be taken to the Forensic Reconciliation page

**Visual Location:**
- In the Financial Command page, you'll see tabs: "AI Assistant", "Statements", "Variance", "Exit", "Chart of Accounts", "Reconciliation"
- On the right side of these tabs, there's a **purple button** labeled "🔍 Forensic Reconciliation"

### Method 2: From Financial Command > Reconciliation Tab

1. **Click on "Financial Command"** in the left sidebar
2. **Click on the "Reconciliation" tab**
3. If no reconciliation sessions exist, you'll see a card with two buttons:
   - "Open Full Reconciliation Page" (standard reconciliation)
   - **"🔍 Open Forensic Reconciliation (Elite)"** (purple button)
4. Click the purple button to access Forensic Reconciliation

### Method 3: From Data Control Center

1. **Click on "Data Control Center"** in the left sidebar (🔧 icon)
2. **Look for the purple button** at the top right of the tabs section
3. **Click "🔍 Forensic Reconciliation"** button

### Method 4: Direct URL

Type directly in your browser:
```
http://localhost:5173/#forensic-reconciliation
```

---

## 📍 Visual Indicators

### Purple Button
- **Color:** Purple border and text (`border-purple-600 text-purple-600`)
- **Icon:** 🔍 (magnifying glass)
- **Text:** "Forensic Reconciliation"
- **Location:** Top right of the tabs section

### What You'll See

When you access Forensic Reconciliation, you'll see:

1. **Page Header:** "Forensic Reconciliation"
2. **Subtitle:** "Automated matching and reconciliation across Balance Sheet, Income Statement, Cash Flow, Rent Roll, and Mortgage Statement"
3. **Property & Period Selection:** Dropdowns to select property and financial period
4. **Start Reconciliation Button:** To begin the reconciliation process
5. **Tabs:** Overview, Cockpit, Matches, Discrepancies

---

## 🎨 New Features You'll See

### Cockpit View (New Tab)
- **Three-panel layout:**
  - **Left:** Filters (property, period, severity, tier, SLA)
  - **Center:** Work Queue (exceptions grouped by severity)
  - **Right:** Evidence Panel (match details and explainability)

### Explainability Features
- **Why Flagged:** Top 3 reasons why a match was flagged
- **What Would Resolve:** Suggested actions to resolve
- **What Changed:** Period comparison with sparklines

### Enhanced Matching
- Materiality-based thresholds
- Tiered exception management (Tier 0-3)
- Bulk operations
- Health score with persona support

---

## 🔍 Troubleshooting

### Can't Find the Button?

1. **Check you're on the right page:**
   - Financial Command (💰 icon) OR
   - Data Control Center (🔧 icon)

2. **Look for purple button:**
   - It's on the right side of the tabs
   - Has a 🔍 icon
   - Says "Forensic Reconciliation"

3. **Try direct URL:**
   - `http://localhost:5173/#forensic-reconciliation`

### Button Not Working?

1. **Refresh the page** (F5 or Ctrl+R)
2. **Check browser console** for errors (F12)
3. **Verify frontend is running:**
   ```bash
   docker compose ps frontend
   ```

### Page Not Loading?

1. **Check backend is running:**
   ```bash
   docker compose ps backend
   ```

2. **Check browser console** for API errors

3. **Verify you're logged in** (should see "admin" in top right)

---

## 📸 Screenshot Locations

### Financial Command Page
- Navigate to: **Financial Command** (💰 in sidebar)
- Look for: Purple button on right side of tabs
- Button text: "🔍 Forensic Reconciliation"

### Reconciliation Tab
- Navigate to: **Financial Command > Reconciliation tab**
- Look for: Purple button in empty state card
- Button text: "🔍 Open Forensic Reconciliation (Elite)"

---

## ✅ Quick Test

1. Open your browser
2. Go to: `http://localhost:5173`
3. Log in (if not already)
4. Click **"Financial Command"** in sidebar
5. Look for **purple "🔍 Forensic Reconciliation"** button
6. Click it!
7. You should see the Forensic Reconciliation page

---

## 🎯 What to Expect

Once you're on the Forensic Reconciliation page:

1. **Select Property** from dropdown
2. **Select Period** from dropdown (after selecting property)
3. **Click "Start Reconciliation"** button
4. **Navigate to "Cockpit" tab** to see the new three-panel layout
5. **Select a match** to see explainability features in the Evidence Panel

---

**Need Help?** Check the browser console (F12) for any errors or see the troubleshooting section above.

