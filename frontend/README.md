# REIMS Frontend - NLQ Integration

Complete React frontend with Natural Language Query integration.

## 🎯 Implemented Features

### ✅ Option 1: Simple Search Integration
- **Location:** Dashboard page (`/`)
- **Component:** `<NLQSearchBar />` integrated directly
- **Features:** Property selector, real-time search, confidence scoring

### ✅ Option 2: Card Integration
- **Location:** Property Details page (`/property/:propertyCode`)
- **Component:** `<NLQSearchBar />` wrapped in Card
- **Features:** Property-specific queries, contextual search

### 🎁 Bonus: Dedicated NLQ Page
- **Location:** NLQ page (`/nlq`)
- **Features:** Full-featured search interface with examples and history

## 📂 Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── NLQSearchBar.jsx      # Main NLQ search component
│   │   └── NLQSearchBar.css      # Component styles
│   ├── hooks/
│   │   └── useNLQ.js             # React hook for NLQ state
│   ├── pages/
│   │   ├── Dashboard.jsx         # Option 1: Simple integration
│   │   ├── Dashboard.css
│   │   ├── PropertyDetails.jsx   # Option 2: Card integration
│   │   ├── PropertyDetails.css
│   │   ├── NLQPage.jsx          # Bonus: Dedicated page
│   │   └── NLQPage.css
│   ├── services/
│   │   └── nlqService.js         # API client
│   ├── App.jsx                   # Main app with routing
│   ├── App.css
│   ├── index.js                  # Entry point
│   └── index.css
├── .env                          # Environment variables
├── package.json
└── README.md
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Backend URL

File `.env` is already created with:
```bash
REACT_APP_API_URL=http://localhost:8000
```

### 3. Start Backend (In separate terminal)

```bash
cd backend
uvicorn app.main:app --reload
```

### 4. Start Frontend

```bash
npm start
```

The app will open at `http://localhost:3000`

## 📱 Pages & Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | **Option 1** - Simple NLQ search with property selector |
| `/property/ESP` | Property Details | **Option 2** - NLQ in Card for specific property |
| `/property/OAK` | Property Details | Property-specific queries for Oakland |
| `/property/PIN` | Property Details | Property-specific queries for Pinecrest |
| `/nlq` | NLQ Search | Dedicated full-featured search page |

## 🎨 Components

### NLQSearchBar

Main search component with all features:

```jsx
import NLQSearchBar from './components/NLQSearchBar';

// Basic usage
<NLQSearchBar />

// With property context
<NLQSearchBar propertyCode="ESP" propertyId={1} />

// In a Card (Option 2)
<Card title="Ask Questions">
  <NLQSearchBar propertyCode={property.code} propertyId={property.id} />
</Card>
```

**Features:**
- Natural language input
- Real-time search
- Loading states
- Confidence scoring (color-coded)
- Execution time display
- Expandable data viewer
- Quick suggestions
- Error handling

### useNLQ Hook

React hook for NLQ state management:

```jsx
import { useNLQ } from './hooks/useNLQ';

const { query, loading, error, result, reset } = useNLQ();

// Execute query
const handleSearch = async () => {
  const response = await query("What was cash position?", { property_code: "ESP" });
  console.log(response);
};
```

### nlqService

API client for backend communication:

```javascript
import nlqService from './services/nlqService';

// Send query
const result = await nlqService.query("What was revenue in Q4?");

// Parse temporal
const temporal = await nlqService.parseTemporal("last 3 months");

// Get formulas
const formulas = await nlqService.getFormulas("mortgage");

// Calculate metric
const dscr = await nlqService.calculateMetric("dscr", {
  property_id: 1,
  year: 2025,
  month: 11
});

// Health check
const health = await nlqService.healthCheck();
```

## 💡 Example Queries

Users can ask questions like:

```
✅ "What was the cash position in November 2025?"
✅ "Show me total revenue for Q4 2025"
✅ "How is DSCR calculated?"
✅ "Calculate current ratio for property ESP"
✅ "Who changed the balance sheet last week?"
✅ "Compare net income YTD vs last year"
✅ "Show operating expenses for last month"
✅ "What are total assets for property OAK?"
```

## 🎯 Implementation Details

### Option 1: Dashboard Integration

**File:** `src/pages/Dashboard.jsx`

```jsx
<NLQSearchBar
  propertyCode={selectedProperty !== 'ALL' ? selectedProperty : null}
  propertyId={
    selectedProperty !== 'ALL'
      ? properties.find(p => p.code === selectedProperty)?.id
      : null
  }
/>
```

**Features:**
- Property selector at top
- Dynamic property context
- Shows metrics above search
- Recent activity below

### Option 2: Property Details Integration

**File:** `src/pages/PropertyDetails.jsx`

```jsx
<Card
  title={
    <span>
      <CalculatorOutlined /> Ask Questions About {property.name}
    </span>
  }
  bordered={false}
  style={{ background: '#f9f9f9' }}
>
  <NLQSearchBar
    propertyCode={property.code}
    propertyId={property.id}
  />
</Card>
```

**Features:**
- Property-specific context automatically applied
- Integrated with property information
- Shows property details above
- Financial metrics visible

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Backend API URL
REACT_APP_API_URL=http://localhost:8000

# App Configuration
REACT_APP_NAME=REIMS
REACT_APP_VERSION=1.0.0
```

### Production Build

```bash
# Build for production
npm run build

# Serve build folder
npm install -g serve
serve -s build
```

## 🎨 Customization

### Modify Styles

Edit component CSS files:
- `src/components/NLQSearchBar.css` - Search component
- `src/pages/Dashboard.css` - Dashboard page
- `src/pages/PropertyDetails.css` - Property page
- `src/App.css` - Global app styles

### Add More Properties

Edit `Dashboard.jsx` and `PropertyDetails.jsx`:

```javascript
const properties = [
  { code: 'ESP', name: 'Esperanza', id: 1 },
  { code: 'OAK', name: 'Oakland Plaza', id: 2 },
  { code: 'PIN', name: 'Pinecrest', id: 3 },
  { code: 'MAP', name: 'Maple Grove', id: 4 },
  // Add more properties here
];
```

### Customize Search Suggestions

Edit `NLQSearchBar.jsx`:

```javascript
<button onClick={() => setQuestion("Your custom question")}>
  Custom suggestion
</button>
```

## 📊 API Integration

The frontend communicates with the NLQ backend via these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/nlq/query` | POST | Main query endpoint |
| `/api/v1/nlq/temporal/parse` | POST | Parse temporal expressions |
| `/api/v1/nlq/formulas` | GET | List all formulas |
| `/api/v1/nlq/formulas/{metric}` | GET | Get specific formula |
| `/api/v1/nlq/calculate/{metric}` | POST | Calculate metric |
| `/api/v1/nlq/health` | GET | Health check |

## 🐛 Troubleshooting

### "Cannot connect to backend"

1. Check backend is running: `http://localhost:8000/api/v1/nlq/health`
2. Verify `REACT_APP_API_URL` in `.env`
3. Check CORS settings in backend

### "Module not found" errors

```bash
npm install
```

### Styling issues

Clear cache and rebuild:
```bash
rm -rf node_modules package-lock.json
npm install
npm start
```

## 📖 Documentation

- [NLQ System Implementation](../COMPLETE_IMPLEMENTATION_STATUS.md)
- [Backend Integration Guide](../FRONTEND_NLQ_INTEGRATION.md)
- [Deployment Guide](../NLQ_DEPLOYMENT_GUIDE.md)

## ✅ Features Summary

- ✅ Option 1: Simple search on Dashboard
- ✅ Option 2: Card integration on Property Details
- ✅ Bonus: Dedicated NLQ search page
- ✅ Property-specific context
- ✅ Real-time search with loading states
- ✅ Confidence scoring
- ✅ Error handling
- ✅ Quick suggestions
- ✅ Query history (on NLQ page)
- ✅ Example queries
- ✅ Responsive design
- ✅ Ant Design UI components
- ✅ React Router navigation

## 🚀 Production Ready

The frontend is complete and production-ready with:
- Clean, modular code
- Proper error handling
- Loading states
- Responsive design
- Performance optimized
- Well documented

**Start using it now!** 🎉
