# 🚀 NLQ Quick Access Guide

## Instant Access to NLQ System

Your NLQ system is now integrated into REIMS at `http://localhost:5173`

---

## ⚡ Quick Start (30 seconds)

### Step 1: Start Backend
```bash
cd /home/hsthind/Documents/GitHub/REIMS2/backend
uvicorn app.main:app --reload
```

### Step 2: Access NLQ Page
Navigate to: **`http://localhost:5173/#nlq-search`**

Done! 🎉

---

## 💬 Start Asking Questions

Try these immediately:

```
✅ What was the cash position in November 2025?
✅ How is DSCR calculated?
✅ Show me total revenue for Q4 2025
✅ Calculate current ratio for property ESP
✅ Who changed the balance sheet last week?
✅ Compare net income YTD vs last year
```

---

## 🎯 3 Ways to Use NLQ

### 1. Dedicated NLQ Page ✅ **READY NOW**
**URL:** `http://localhost:5173/#nlq-search`

Full-featured page with:
- Property selector
- Example queries
- Formula browser
- Health status

### 2. Add Search Bar to Any Page
```tsx
import NLQSearchBar from '../components/NLQSearchBar';

<NLQSearchBar
  propertyCode="ESP"
  propertyId={1}
  userId={user?.id}
/>
```

### 3. Add to Sidebar Navigation
Edit `src/App.tsx` at line ~265:

```tsx
<button
  className={`nav-item ${hashRoute === 'nlq-search' ? 'active' : ''}`}
  onClick={() => window.location.hash = 'nlq-search'}
>
  <span className="nav-icon">💬</span>
  {sidebarOpen && <span className="nav-text">NLQ Search</span>}
</button>
```

---

## 📍 Files Created

```
✅ src/services/nlqService.ts              - API client
✅ src/components/NLQSearchBar.tsx         - Reusable component
✅ src/pages/NaturalLanguageQueryNew.tsx   - Full page
✅ src/App.tsx                             - Updated with route
```

---

## 🔗 Direct Links

- **NLQ Page:** http://localhost:5173/#nlq-search
- **Backend API:** http://localhost:8000/api/v1/nlq/health
- **API Docs:** http://localhost:8000/docs

---

## 🎨 Recommended Next Steps

### Add to Command Center (High Priority)

Edit `src/pages/CommandCenter.tsx` around line 500-600:

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

// Add this card after the critical alerts section:
<div className="card" style={{ marginBottom: '20px' }}>
  <h3 className="card-title">💬 Ask Questions About Your Portfolio</h3>
  <NLQSearchBar userId={user?.id} compact={true} />
</div>
```

This adds NLQ search directly to your main dashboard!

---

## ✨ Features

### Temporal Queries
- "last 3 months"
- "Q4 2025"
- "November 2025"
- "YTD", "MTD", "QTD"
- "between August and December 2025"

### Formula Questions
- "How is DSCR calculated?"
- "What is Current Ratio?"
- "Explain NOI"
- "Calculate DSCR for ESP"

### Data Queries
- "What was cash position?"
- "Show revenue for Q4"
- "Total assets for ESP"
- "Operating expenses last month"

### Audit Questions
- "Who changed cash position?"
- "Show audit history for ESP"
- "What was modified last week?"

---

## 🎯 Your System Status

✅ **Backend:** NLQ API running on port 8000
✅ **Frontend:** React app on port 5173
✅ **Integration:** Complete with TypeScript
✅ **Route:** `#nlq-search` hash route added
✅ **Components:** Ready to use anywhere
✅ **Service:** API client with full types

---

## 🚀 **YOU'RE READY TO GO!**

Navigate to: **http://localhost:5173/#nlq-search**

Start asking questions now! 💬

---

For detailed documentation, see:
- [FRONTEND_NLQ_INTEGRATED.md](FRONTEND_NLQ_INTEGRATED.md) - Complete integration guide
- [NLQ_IMPLEMENTATION_COMPLETE.md](NLQ_IMPLEMENTATION_COMPLETE.md) - Full system overview
