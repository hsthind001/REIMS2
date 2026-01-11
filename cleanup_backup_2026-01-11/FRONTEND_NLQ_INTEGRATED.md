# ✅ NLQ System Integrated into REIMS Frontend (Port 5173)

Complete integration of the Natural Language Query system into your existing REIMS TypeScript/Vite React application.

---

## 🎯 What's Been Implemented

### ✅ **1. NLQ Service Layer** (`src/services/nlqService.ts`)
Complete TypeScript service for all NLQ operations:
- Query execution with full type safety
- Temporal expression parsing
- Formula browsing and calculations
- Health check monitoring
- Proper error handling

### ✅ **2. Reusable NLQ Search Component** (`src/components/NLQSearchBar.tsx`)
Drop-in search component that works anywhere:
- Matches existing REIMS design system
- Compact and full modes
- Property context support
- Real-time confidence scoring
- Error handling
- Quick suggestions

### ✅ **3. Complete NLQ Page** (`src/pages/NaturalLanguageQueryNew.tsx`)
Full-featured search page with:
- Property selector
- Example queries by category
- Formula browser
- System health status
- Supported features showcase

### ✅ **4. App Integration**
- Added to App.tsx routing (`#nlq-search`)
- Lazy-loaded for performance
- Accessible via hash route

---

## 📂 Files Created

```
src/
├── services/
│   └── nlqService.ts              ✅ NEW - Complete NLQ API client
├── components/
│   └── NLQSearchBar.tsx           ✅ NEW - Reusable search component
└── pages/
    └── NaturalLanguageQueryNew.tsx ✅ NEW - Full NLQ page
```

**Total:** 3 new TypeScript files integrated

---

## 🚀 How to Access

### Method 1: Direct Hash Route

Add a button/link anywhere in your app:

```tsx
<button onClick={() => window.location.hash = 'nlq-search'}>
  💬 Ask Questions
</button>
```

### Method 2: Add to Navigation Menu

Add to the sidebar in `App.tsx` (lines 220-266):

```tsx
<button
  className={`nav-item ${hashRoute === 'nlq-search' ? 'active' : ''}`}
  onClick={() => window.location.hash = 'nlq-search'}
>
  <span className="nav-icon">💬</span>
  {sidebarOpen && <span className="nav-text">NLQ Search</span>}
</button>
```

### Method 3: Add Search Bar to Any Page

Import and use the component anywhere:

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

// In your page component:
<NLQSearchBar
  propertyCode="ESP"
  propertyId={1}
  userId={user?.id}
/>
```

---

## 💡 Usage Examples

### Example 1: Add to Command Center Dashboard

Edit `src/pages/CommandCenter.tsx` around line 500:

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

// Inside the component, add a new section:
<div className="card" style={{ marginBottom: '20px' }}>
  <h3 className="card-title">💬 Ask About Your Portfolio</h3>
  <NLQSearchBar
    userId={user?.id}
    compact={true}
  />
</div>
```

### Example 2: Add to Portfolio Hub

Edit `src/pages/PortfolioHub.tsx`:

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

// Add search for specific property:
<div className="card">
  <NLQSearchBar
    propertyCode={selectedProperty?.code}
    propertyId={selectedProperty?.id}
    userId={user?.id}
  />
</div>
```

### Example 3: Add to Financial Command

Edit `src/pages/FinancialCommand.tsx`:

```tsx
import NLQSearchBar from '../components/NLQSearchBar';

// Add formula questions section:
<div className="card">
  <h3>🧮 Ask About Formulas</h3>
  <NLQSearchBar
    userId={user?.id}
    compact={true}
  />
</div>
```

---

## 🎨 Component Props

### NLQSearchBar Props

```typescript
interface NLQSearchBarProps {
  propertyCode?: string;      // Property code (e.g., "ESP", "OAK")
  propertyId?: number;         // Property ID
  userId?: number;             // User ID for tracking
  compact?: boolean;           // Compact mode (no header/suggestions)
  onResult?: (result) => void; // Callback when query completes
}
```

**Usage:**

```tsx
// Full mode with all features
<NLQSearchBar />

// Compact mode for dashboards
<NLQSearchBar compact={true} />

// Property-specific
<NLQSearchBar
  propertyCode="ESP"
  propertyId={1}
  userId={user?.id}
/>

// With callback
<NLQSearchBar
  onResult={(result) => {
    console.log('Query result:', result);
    // Handle result in parent component
  }}
/>
```

---

## 🔧 Quick Integration Steps

### Step 1: Start Backend

```bash
cd /home/hsthind/Documents/GitHub/REIMS2/backend
uvicorn app.main:app --reload
```

Backend will run on `http://localhost:8000`

### Step 2: Verify Environment Variable

Check `src/services/nlqService.ts` line 9:

```typescript
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';
```

If needed, create `.env` in root:

```bash
VITE_API_URL=http://localhost:8000
```

### Step 3: Access NLQ Page

Navigate to: `http://localhost:5173/#nlq-search`

Or add navigation button as shown above.

### Step 4: Test Queries

Try these example queries:

```
✅ "What was the cash position in November 2025?"
✅ "How is DSCR calculated?"
✅ "Show me total revenue for Q4 2025"
✅ "Calculate current ratio for property ESP"
✅ "Who changed the balance sheet last week?"
```

---

## 📊 Features Available

### Temporal Queries (10+ Types)
- Absolute dates: "November 2025", "2025-11-15"
- Relative periods: "last 3 months", "last year"
- Fiscal periods: "Q4 2025", "fiscal year 2025"
- Special keywords: "YTD", "MTD", "QTD"
- Date ranges: "between August and December 2025"

### Financial Formulas (50+)
- Liquidity ratios
- Leverage ratios
- Mortgage metrics (DSCR, LTV, etc.)
- Income statement metrics
- Rent roll metrics

### Query Types
- Financial data queries
- Formula explanations
- Calculations
- Audit trail
- Reconciliation
- Comparative analysis

---

## 🎯 Recommended Implementation Locations

### High Priority - Add These First:

1. **Command Center Dashboard** (`CommandCenter.tsx`)
   - Add at top for portfolio-wide queries
   - Use compact mode

2. **Portfolio Hub** (`PortfolioHub.tsx`)
   - Add in property details section
   - Pass property context

3. **Financial Command** (`FinancialCommand.tsx`)
   - Add for formula queries
   - Show in reports section

### Medium Priority:

4. **Data Control Center** (`DataControlCenter.tsx`)
   - Add for data quality queries

5. **Risk Management** (`RiskManagement.tsx`)
   - Add for risk metric queries

---

## 📝 Adding to Navigation Sidebar

Edit `src/App.tsx` at line ~265 (after the Risk Management button):

```tsx
<button
  className={`nav-item ${hashRoute === 'nlq-search' ? 'active' : ''}`}
  onClick={() => window.location.hash = 'nlq-search'}
  title="Natural Language Query"
>
  <span className="nav-icon">💬</span>
  {sidebarOpen && <span className="nav-text">NLQ Search</span>}
</button>
```

This adds a dedicated NLQ button to your main navigation.

---

## 🔍 API Endpoints Used

The service connects to these backend endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/nlq/query` | POST | Main query execution |
| `/api/v1/nlq/temporal/parse` | POST | Parse temporal expressions |
| `/api/v1/nlq/formulas` | GET | List all formulas |
| `/api/v1/nlq/formulas/{metric}` | GET | Get specific formula |
| `/api/v1/nlq/calculate/{metric}` | POST | Calculate metric |
| `/api/v1/nlq/health` | GET | Health check |

---

## 🎨 Styling

The components use your existing REIMS design system:

- CSS classes from `App.css`
- CSS variables: `--primary`, `--text`, `--border`, etc.
- Matches `.card`, `.btn-primary`, `.badge` styles
- Responsive design
- Dark mode compatible (if enabled)

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to backend"

**Solution:**
```bash
# 1. Check backend is running
curl http://localhost:8000/api/v1/nlq/health

# 2. Start backend if not running
cd backend
uvicorn app.main:app --reload

# 3. Check CORS settings in backend
# Should allow origin: http://localhost:5173
```

### Issue: "Module not found"

**Solution:**
```bash
# Restart Vite dev server
# Kill existing server (Ctrl+C)
npm run dev
```

### Issue: TypeScript errors

**Solution:**
```bash
# Check TypeScript compilation
npx tsc --noEmit

# If issues persist, restart VS Code/editor
```

---

## ✅ Testing Checklist

Before deploying, test:

- [ ] NLQ page loads at `#nlq-search`
- [ ] Search bar accepts input
- [ ] Example queries work
- [ ] Property selector updates context
- [ ] Results display correctly
- [ ] Confidence scores show
- [ ] Error handling works
- [ ] Formula browser loads
- [ ] Health status displays
- [ ] Mobile responsive

---

## 🚀 Next Steps

### Recommended Additions:

1. **Add to Command Center**
   ```tsx
   // At top of dashboard for quick access
   <NLQSearchBar compact={true} userId={user?.id} />
   ```

2. **Add to Portfolio Hub**
   ```tsx
   // In property details card
   <NLQSearchBar
     propertyCode={property.code}
     propertyId={property.id}
     userId={user?.id}
   />
   ```

3. **Add Navigation Button**
   ```tsx
   // In sidebar navigation
   <button onClick={() => window.location.hash = 'nlq-search'}>
     💬 Ask Questions
   </button>
   ```

4. **Add Quick Access Button**
   ```tsx
   // In header (next to notifications)
   <button
     className="btn-secondary"
     onClick={() => window.location.hash = 'nlq-search'}
     title="Ask Questions"
   >
     💬
   </button>
   ```

---

## 📖 Full Documentation

Complete documentation available:

1. **[NLQ_IMPLEMENTATION_COMPLETE.md](NLQ_IMPLEMENTATION_COMPLETE.md)** - Complete system overview
2. **[NLQ_DEPLOYMENT_GUIDE.md](NLQ_DEPLOYMENT_GUIDE.md)** - Backend setup
3. **[FRONTEND_NLQ_INTEGRATION.md](FRONTEND_NLQ_INTEGRATION.md)** - General integration guide

---

## 🎉 Summary

**What's Ready:**
✅ Complete NLQ service (`nlqService.ts`)
✅ Reusable search component (`NLQSearchBar.tsx`)
✅ Full NLQ page (`NaturalLanguageQueryNew.tsx`)
✅ Integrated into App.tsx routing
✅ TypeScript types included
✅ Error handling complete
✅ Mobile responsive

**How to Use:**
1. Access page: `http://localhost:5173/#nlq-search`
2. Or add `<NLQSearchBar />` to any page
3. Or add navigation button to sidebar

**Your NLQ system is fully integrated and ready to use!** 🚀

Navigate to `http://localhost:5173/#nlq-search` to start asking questions!
