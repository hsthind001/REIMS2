# Frontend Mock Data Comprehensive Audit
**Date:** November 15, 2025
**Status:** Critical Issues Identified
**Frontend Completion:** Currently ~98%, Target 100%

---

## 🔴 CRITICAL ISSUES - Mock Data Still Displayed

### **Priority 1: Financial Metrics (CRITICAL)**

#### **1. DSCR (Debt Service Coverage Ratio) - RANDOM MOCK**
**Location:**
- `CommandCenter.tsx:254` - `const dscr = 1.0 + Math.random() * 0.3;`
- `PortfolioHub.tsx:151` - `const dscr = 1.0 + Math.random() * 0.3;`

**Impact:** 🔴 CRITICAL
- Property status indicators (red/yellow/green) based on fake DSCR
- Dashboard shows random financial health
- Triggers incorrect risk alerts

**Current Behavior:**
```typescript
const dscr = 1.0 + Math.random() * 0.3; // Returns 1.0 to 1.3
const status = dscr < 1.2 ? 'red' : dscr < 1.35 ? 'yellow' : 'green';
```

**Solution:**
1. **Option A (Quick):** Calculate DSCR proxy from existing data
   ```
   DSCR = NOI / (Total_Liabilities * 0.08)
   ```
   Where 0.08 = assumed 8% annual debt service rate

2. **Option B (Proper):** Add debt_service field to database
   - Requires migration
   - Store actual annual debt service payments
   - Calculate: `DSCR = NOI / Annual_Debt_Service`

**API Endpoint Needed:**
```
GET /api/v1/metrics/summary
Response: Add "dscr" field
```

---

#### **2. LTV (Loan-to-Value) - HARDCODED 52.8%**
**Location:**
- `CommandCenter.tsx:264` - `ltv: 52.8` (hardcoded)

**Impact:** 🔴 CRITICAL
- Always shows 52.8% regardless of property
- Lending risk assessment is fake

**Current Status:**
- ✅ API EXISTS: `GET /api/v1/metrics/{id}/ltv`
- ❌ NOT USED in CommandCenter property performance

**Solution:**
- Replace line 264 with API call to `/metrics/{propertyId}/ltv`
- Already working in PortfolioHub, just needs same integration in CommandCenter

---

#### **3. NOI/Occupancy Trends - RANDOM SPARKLINES**
**Location:**
- `CommandCenter.tsx:249-252` - NOI trend generation
  ```typescript
  const noiTrend = Array.from({ length: 12 }, () =>
    (metric.net_income || 0) * (0.9 + Math.random() * 0.2)
  );
  ```
- `PortfolioHub.tsx:186-188` - NOI and Occupancy trends
  ```typescript
  trends: {
    noi: Array.from({ length: 12 }, () => (propertyMetric.net_income || 0) * (0.9 + Math.random() * 0.2)),
    occupancy: Array.from({ length: 12 }, () => (propertyMetric.occupancy_rate || 0) * (0.95 + Math.random() * 0.1))
  }
  ```

**Impact:** 🔴 CRITICAL
- Trend charts show fake data
- Cannot identify actual performance trends
- Misleading visualizations

**Current Status:**
- ✅ API EXISTS: `GET /api/v1/metrics/historical?months=12`
- ✅ Used for portfolio-level sparklines in CommandCenter
- ❌ NOT USED for property-level sparklines

**Solution:**
- Update to use `/metrics/historical?property_id={id}&months=12`
- Extract NOI and occupancy from response

---

### **Priority 2: Data Display Issues (HIGH)**

#### **4. Property Sorting - NON-FUNCTIONAL**
**Location:**
- `PortfolioHub.tsx:580-583`
  ```typescript
  const sortedProperties = [...filteredProperties].sort(() => {
    // Mock sorting - would use actual metrics
    return sortBy === 'noi' ? 0 : 0;
  });
  ```

**Impact:** 🟡 HIGH
- Sort dropdown doesn't work
- Always returns 0 (no sorting applied)
- Poor UX

**Solution:**
```typescript
const sortedProperties = [...filteredProperties].sort((a, b) => {
  if (sortBy === 'noi') {
    const aNoi = propertyMetrics.find(m => m.property_id === a.id)?.net_income || 0;
    const bNoi = propertyMetrics.find(m => m.property_id === b.id)?.net_income || 0;
    return bNoi - aNoi; // Descending
  }
  if (sortBy === 'risk') {
    const aRisk = getRiskScore(a.id);
    const bRisk = getRiskScore(b.id);
    return bRisk - aRisk;
  }
  // ... etc
});
```

---

#### **5. Tenant Mix Table - STATIC HTML**
**Location:**
- `PortfolioHub.tsx:1323-1344`
  ```tsx
  <tr><td>Office (A)</td><td>80</td><td>120,000</td><td>$96,000</td>...</tr>
  <tr><td>Office (B)</td><td>50</td><td>62,500</td><td>$50,000</td>...</tr>
  <tr><td>Retail</td><td>20</td><td>30,000</td><td>$30,000</td>...</tr>
  ```

**Impact:** 🟡 HIGH
- Always shows same 3 tenant types
- Doesn't reflect actual rent roll

**Solution:**
- Create API: `GET /api/v1/metrics/{property_id}/tenant-mix`
- Calculate from RentRollData grouped by lease_type
- Return: tenant type, count, sqft, revenue, occupancy%

---

#### **6. Documents List - STATIC HTML**
**Location:**
- `PortfolioHub.tsx:1416-1430`
  ```tsx
  <div>Q3 2025 Income Statement</div>
  <div>Q3 2025 Balance Sheet</div>
  <div>Q3 2025 Cash Flow</div>
  <div className="text-sm text-text-secondary">28 Documents</div>
  ```

**Impact:** 🟡 HIGH
- Always shows 3 fake documents
- Doesn't show actual uploaded files

**Solution:**
- ✅ API EXISTS: `GET /api/v1/documents?property_id={id}`
- Replace static HTML with API integration
- Show actual DocumentUpload records

---

#### **7. Hold Period - HARDCODED "34 mo"**
**Location:**
- `PortfolioHub.tsx:755` - `<div>34 mo</div>`

**Impact:** 🟡 MEDIUM
- Always shows "34 mo" for all properties

**Solution:**
- Calculate from property acquisition_date: `now - acquisition_date`
- Or add hold_period field to Property model

---

#### **8. Financial Statement Cards - STATIC**
**Location:**
- `FinancialCommand.tsx:520-532`
  ```tsx
  <div>Q3 2025</div>
  <div>Revenue: $11.2M</div>
  <div>Assets: $18.5M</div>
  <div>Net CF: $3.04M</div>
  ```

**Impact:** 🟡 HIGH
- Always shows Q3 2025 data
- Doesn't update when selecting different periods

**Solution:**
- Use selectedPeriod state (already exists)
- Fetch metrics for selected period
- Update cards dynamically

---

#### **9. Financial KPIs - 4 HARDCODED METRICS**
**Location:**
- `FinancialCommand.tsx:771-797`
  ```tsx
  <div>DSCR</div><div>1.07</div>  // ❌ Hardcoded
  <div>LTV</div><div>52.8%</div>   // ❌ Hardcoded
  <div>Cap Rate</div><div>4.22%</div>  // ❌ Hardcoded
  <div>IRR</div><div>14.2%</div>   // ❌ Hardcoded
  ```

**Impact:** 🟡 HIGH
- 4 out of 8 KPIs always static
- Other 4 (NOI, Occupancy, Assets) come from API

**Solution:**
- DSCR: Use calculated value from metrics
- LTV: Call `/metrics/{id}/ltv`
- Cap Rate: Call `/metrics/{id}/cap-rate`
- IRR: Call `/exit-strategy/portfolio-irr` (for portfolio) or property-level IRR

---

### **Priority 3: Minor Issues (MEDIUM)**

#### **10. Documents Processed Count - HARDCODED**
**Location:**
- `DataControlCenter.tsx:100` - `documentsProcessed: 1247`

**Impact:** 🟢 MEDIUM
- Always shows 1247 documents processed

**Solution:**
- Add to `GET /api/v1/quality/score` response
- Count total DocumentUpload records

---

#### **11. Tenant Match Fields - PARTIAL MOCK**
**Location:**
- `PortfolioHub.tsx:377-403` - Tenant recommendations

**Impact:** 🟢 MEDIUM
- API returns tenant matches
- But hardcodes: credit_score, industry, desired_sqft, estimated_rent, reasons

**Solution:**
- Enhance `/tenant-recommendations` API to include these fields
- Or remove if not critical to MVP

---

## ✅ ACCEPTABLE FALLBACKS

These are correctly implemented with API-first, mock-second pattern:

1. **Portfolio IRR** - `CommandCenter.tsx:162`
2. **AI Insights** - `CommandCenter.tsx:293-342`
3. **Property Costs** - `PortfolioHub.tsx:211-230`
4. **Unit Info** - `PortfolioHub.tsx:248-277`
5. **Market Intelligence** - `PortfolioHub.tsx:336-371`
6. **NLQ Responses** - `FinancialCommand.tsx:175-194`
7. **Quality Scores** - `DataControlCenter.tsx:93-112`

---

## 📊 IMPACT SUMMARY

| Issue | Priority | Frontend Files | API Needed | Lines of Code |
|-------|----------|----------------|------------|---------------|
| DSCR Mock | 🔴 CRITICAL | CommandCenter, PortfolioHub | Enhance /metrics/summary | 2 |
| LTV Hardcoded | 🔴 CRITICAL | CommandCenter | Use existing API | 1 |
| NOI/Occ Trends | 🔴 CRITICAL | CommandCenter, PortfolioHub | Use existing API | 6 |
| Property Sorting | 🟡 HIGH | PortfolioHub | None (frontend only) | 4 |
| Tenant Mix Table | 🟡 HIGH | PortfolioHub | New API needed | 20 |
| Documents List | 🟡 HIGH | PortfolioHub | Use existing API | 15 |
| Hold Period | 🟡 MEDIUM | PortfolioHub | Calculate frontend | 1 |
| Statement Cards | 🟡 HIGH | FinancialCommand | Use existing API | 20 |
| Financial KPIs | 🟡 HIGH | FinancialCommand | Use existing APIs | 8 |
| Docs Processed | 🟢 MEDIUM | DataControlCenter | Enhance API | 1 |
| Tenant Fields | 🟢 MEDIUM | PortfolioHub | Enhance API | 10 |

**Total Mock Data Points:** 11
**Estimated Fix Time:** 4-6 hours
**Completion Impact:** 98% → 100%

---

## 🎯 RECOMMENDED FIX ORDER

### **Phase 1: Quick Wins (2 hours)**
1. ✅ Fix LTV in CommandCenter (use existing API)
2. ✅ Fix NOI/Occupancy trends (use existing API)
3. ✅ Fix property sorting (frontend logic only)
4. ✅ Fix hold period (calculate from acquisition_date)
5. ✅ Fix documents list (use existing API)
6. ✅ Fix statement cards (use selected period)

### **Phase 2: API Enhancements (2 hours)**
1. ✅ Add DSCR to metrics summary endpoint
2. ✅ Create tenant-mix endpoint
3. ✅ Add documents_processed to quality API
4. ✅ Add KPI values to metrics response

### **Phase 3: Integration (2 hours)**
1. ✅ Integrate all new APIs into frontend
2. ✅ Test end-to-end
3. ✅ Verify no mock data displayed
4. ✅ Check component styling/alignment

---

## 🚀 EXPECTED OUTCOME

**After Fixes:**
- ✅ 100% real data (no mock values displayed)
- ✅ All components functional (sorting, filtering work)
- ✅ Accurate financial metrics (DSCR, LTV, trends)
- ✅ Real document lists and tenant mix
- ✅ Production-ready frontend

---

## 📝 TESTING CHECKLIST

After fixes, verify:

### **CommandCenter Page:**
- [ ] Portfolio IRR shows real value
- [ ] All sparklines show historical data (not random)
- [ ] AI insights are data-driven
- [ ] Property performance cards show real DSCR/LTV
- [ ] Critical alerts based on real metrics

### **PortfolioHub Page:**
- [ ] Property selection works
- [ ] Sorting by NOI/Risk/Value works correctly
- [ ] Overview tab shows real metrics (no hardcoded values)
- [ ] Tenant mix table shows actual lease types
- [ ] Documents tab shows uploaded files
- [ ] Hold period calculated from acquisition date
- [ ] Sparklines show real trends

### **FinancialCommand Page:**
- [ ] Statement cards update with period selection
- [ ] All 8 KPIs show real values
- [ ] NLQ queries return intelligent responses
- [ ] Charts reflect actual financial data

### **DataControlCenter Page:**
- [ ] Documents processed count is accurate
- [ ] Quality scores from API
- [ ] Validation rules displayed

### **AdminHub Page:**
- [ ] Users list from API
- [ ] Roles management functional
- [ ] Audit logs displayed

---

**Status:** Ready for implementation
**Estimated Completion:** 6 hours
**Target Completion:** 100% real data, 0% mock data
