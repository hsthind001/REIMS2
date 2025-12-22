# Sprint Plan: REIMS2 Frontend to 100% Completion
**Start Date:** November 15, 2025
**Target Completion:** December 6, 2025 (3 weeks)
**Current Status:** 88% Complete
**Goal:** 100% Complete, Production Ready

---

## 🎯 SPRINT OBJECTIVES

### Week 1: Priority 1 APIs (88% → 95%)
**Goal:** Replace high-impact mock metrics with real calculations

### Week 2: Priority 2 APIs (95% → 98%)
**Goal:** Implement AI/ML features

### Week 3: Polish & Testing (98% → 100%)
**Goal:** Final enhancements, testing, deployment

---

## 📅 WEEK 1: PRIORITY 1 APIS (Nov 15-22)

### Day 1-2: Portfolio & Property Metrics

**1. Portfolio IRR Endpoint** ⭐ HIGH IMPACT
- **File:** `backend/app/routers/exit_strategy.py` (enhance existing)
- **Endpoint:** `GET /api/v1/exit-strategy/portfolio-irr`
- **Returns:**
  ```json
  {
    "irr": 14.2,
    "yoy_change": 2.1,
    "properties": [
      {"property_id": 1, "irr": 15.3, "weight": 0.25},
      {"property_id": 2, "irr": 13.8, "weight": 0.30}
    ],
    "calculation_date": "2025-11-15"
  }
  ```
- **Logic:** Weighted average based on property values
- **Replaces:** Mock 14.2% in CommandCenter.tsx

**2. Property LTV Calculation**
- **File:** `backend/app/routers/metrics.py` (new endpoint)
- **Endpoint:** `GET /api/v1/metrics/{property_id}/ltv`
- **Returns:**
  ```json
  {
    "ltv": 52.8,
    "loan_amount": 9500000,
    "property_value": 18000000,
    "debt_to_equity": 1.12,
    "calculation_date": "2025-11-15"
  }
  ```
- **Logic:** loan_amount / property_value * 100
- **Replaces:** Mock 52.8% in PortfolioHub.tsx

**3. Cap Rate Calculation**
- **File:** `backend/app/routers/metrics.py` (new endpoint)
- **Endpoint:** `GET /api/v1/metrics/{property_id}/cap-rate`
- **Returns:**
  ```json
  {
    "cap_rate": 4.22,
    "noi": 760000,
    "property_value": 18000000,
    "market_cap_rate": 4.5,
    "calculation_date": "2025-11-15"
  }
  ```
- **Logic:** (NOI / property_value) * 100
- **Replaces:** Mock 4.22% in PortfolioHub.tsx

### Day 3-5: Historical Data for Sparklines

**4. Historical Metrics API** ⭐ HIGH VISUAL IMPACT
- **File:** `backend/app/routers/metrics.py` (new endpoint)
- **Endpoint:** `GET /api/v1/metrics/historical?property_id={id}&months=12`
- **Returns:**
  ```json
  {
    "property_id": 1,
    "months": 12,
    "data": {
      "noi": [720000, 735000, 748000, ..., 760000],
      "value": [17500000, 17600000, ..., 18000000],
      "occupancy": [89.5, 90.2, 91.0, ..., 91.5],
      "revenue": [1200000, 1225000, ..., 1280000],
      "expenses": [480000, 490000, ..., 520000]
    },
    "periods": [
      {"year": 2024, "month": 12},
      {"year": 2025, "month": 1},
      ...
      {"year": 2025, "month": 11}
    ]
  }
  ```
- **Logic:** Query financial_metrics table for last 12 months
- **Replaces:** Mock trend arrays in CommandCenter.tsx and PortfolioHub.tsx

**Frontend Updates (Week 1):**
- Update CommandCenter.tsx to fetch real IRR
- Update PortfolioHub.tsx to fetch real LTV, Cap Rate
- Update MetricCard component to use real historical data
- Test all sparkline visualizations

**Success Criteria Week 1:**
- ✅ All 4 Priority 1 APIs deployed
- ✅ Frontend connected to real metrics
- ✅ Sparklines showing real trends
- ✅ 95% completion achieved

---

## 📅 WEEK 2: PRIORITY 2 APIS (Nov 22-29)

### Day 6-7: AI Insights

**5. NLQ Portfolio Insights API** ⭐ AI FEATURE
- **File:** `backend/app/routers/nlq.py` (enhance existing)
- **Endpoint:** `GET /api/v1/nlq/insights/portfolio`
- **Returns:**
  ```json
  {
    "insights": [
      {
        "id": "insight-1",
        "type": "risk",
        "title": "3 properties showing DSCR stress",
        "description": "Refinancing window optimal for Downtown Office Tower, Lakeside Retail, Sunset Plaza",
        "confidence": 0.92,
        "priority": "high",
        "action_items": [
          "Contact lenders for rate quotes",
          "Prepare refinancing packages",
          "Schedule appraisals"
        ]
      },
      {
        "id": "insight-2",
        "type": "opportunity",
        "title": "Market cap rates trending up 0.3%",
        "description": "Favorable for sales - consider exit strategy for Harbor View Apartments",
        "confidence": 0.88,
        "priority": "medium"
      }
    ],
    "generated_at": "2025-11-22T10:00:00Z",
    "model": "claude-3-5-sonnet-20241022"
  }
  ```
- **Logic:** Analyze risk alerts, market data, financial trends with Claude AI
- **Replaces:** 3 mock insights in CommandCenter.tsx

### Day 8-10: Market Intelligence

**6. Market Intelligence API** ⭐ AI FEATURE
- **File:** `backend/app/routers/property_research.py` (enhance existing)
- **Endpoint:** `GET /api/v1/property-research/{property_id}/market`
- **Returns:**
  ```json
  {
    "location_score": 8.5,
    "market_data": {
      "market_cap_rate": 4.5,
      "property_cap_rate": 4.22,
      "market_rent_growth": 3.2,
      "property_rent_growth": 2.8
    },
    "demographics": {
      "population": 125000,
      "median_income": 75000,
      "employment_rate": 96.5,
      "growth_rate": 1.8
    },
    "comparable_properties": [
      {
        "name": "City Center Plaza",
        "distance_miles": 0.8,
        "cap_rate": 4.3,
        "price_per_sqft": 285,
        "occupancy": 93.0
      }
    ],
    "ai_insights": [
      "Strong demographics with above-average income",
      "Location score driven by proximity to transit",
      "Market rent growth outpacing property - opportunity to raise rents"
    ]
  }
  ```
- **Logic:**
  - Call census API for demographics
  - Query CoStar/RealtyMogul APIs for comps (or use mock if unavailable)
  - AI analysis of location factors
- **Replaces:** Mock market data in PortfolioHub.tsx Tab 3

**7. Tenant Matching ML API** ⭐ ML FEATURE
- **File:** `backend/app/routers/tenant_recommendations.py` (enhance existing)
- **Endpoint:** `GET /api/v1/tenant-recommendations/{property_id}/matches`
- **Returns:**
  ```json
  {
    "tenant_mix_summary": [
      {"category": "Retail", "units": 8, "sqft": 12000, "rent": 240000},
      {"category": "Office", "units": 4, "sqft": 8000, "rent": 160000}
    ],
    "recommendations": [
      {
        "id": "tenant-1",
        "name": "TechStart Inc.",
        "match_score": 92,
        "credit_score": 720,
        "industry": "Technology",
        "desired_sqft": 2500,
        "estimated_rent": 5000,
        "lease_term_months": 36,
        "match_reasons": [
          "Strong credit profile (720)",
          "Desired space aligns with Unit 204 availability",
          "Industry mix diversification opportunity",
          "Rent estimate 15% above current tenant"
        ],
        "compatibility_factors": {
          "financial": 0.95,
          "space_fit": 0.88,
          "industry_mix": 0.92,
          "lease_term": 0.90
        }
      }
    ],
    "algorithm_version": "v2.1",
    "generated_at": "2025-11-23"
  }
  ```
- **Logic:**
  - Query rent_roll_data for current tenant mix
  - ML scoring algorithm (weighted factors)
  - AI-generated match reasons
- **Replaces:** Mock tenant data in PortfolioHub.tsx Tab 4

**Frontend Updates (Week 2):**
- Update CommandCenter.tsx to fetch real AI insights
- Update PortfolioHub.tsx Tab 3 (Market Intelligence)
- Update PortfolioHub.tsx Tab 4 (Tenant Matching)
- Test AI features end-to-end

**Success Criteria Week 2:**
- ✅ All 3 Priority 2 APIs deployed
- ✅ AI insights showing real analysis
- ✅ Market intelligence with real data
- ✅ Tenant matching with ML scores
- ✅ 98% completion achieved

---

## 📅 WEEK 3: POLISH & TESTING (Nov 29-Dec 6)

### Day 11-12: Detailed Data APIs

**8. Property Costs API**
- **File:** `backend/app/routers/properties.py` (enhance)
- **Endpoint:** `GET /api/v1/properties/{property_id}/costs`
- **Returns:** Real cost breakdown from financial data

**9. Unit Details API**
- **File:** `backend/app/routers/properties.py` (enhance)
- **Endpoint:** `GET /api/v1/properties/{property_id}/units`
- **Returns:** Unit-level details from rent roll

**10. Current Rent Roll API**
- **File:** `backend/app/routers/rent_rolls.py` (enhance)
- **Endpoint:** `GET /api/v1/rent-roll/{property_id}/current`
- **Returns:** Current tenant list

### Day 13-14: Frontend Polish

**Error Handling UI**
- Create ErrorBoundary component
- Add user-facing error messages
- Toast notifications for API errors

**Accessibility Enhancements**
- Add ARIA labels to all interactive elements
- Keyboard navigation support
- Focus management in modals
- Screen reader testing

**Loading States**
- Skeleton screens for data loading
- Improved spinner UX
- Progressive data loading

### Day 15: Comprehensive Testing

**Manual Testing Checklist:**
- [ ] Command Center - all metrics, alerts, insights
- [ ] Portfolio Hub - all 5 tabs, property CRUD
- [ ] Financial Command - all 6 tabs, NLQ, statements
- [ ] Data Control Center - all 6 tabs, quality monitoring
- [ ] Admin Hub - all 4 tabs, RBAC, audit log
- [ ] Mobile responsiveness (320px, 768px, 1024px, 1440px)
- [ ] Cross-browser (Chrome, Firefox, Safari, Edge)
- [ ] API error handling (disconnect backend, test error states)
- [ ] Performance (Lighthouse score target: 90+)

**Automated Testing:**
- Unit tests for critical components
- Integration tests for API services
- E2E tests for key user flows

---

## 📊 SUCCESS METRICS

| Metric | Current | Week 1 | Week 2 | Week 3 | Target |
|--------|---------|--------|--------|--------|--------|
| **Completion %** | 88% | 95% | 98% | 100% | 100% |
| **Mock Data %** | 12% | 5% | 2% | 0% | 0% |
| **Real APIs** | 23 | 27 | 30 | 33 | 33 |
| **Test Coverage** | 0% | 10% | 30% | 70% | 70% |
| **Lighthouse Score** | 85 | 87 | 90 | 92 | 90+ |
| **Accessibility** | 60% | 70% | 85% | 95% | 95% |

---

## 🚀 DEPLOYMENT TIMELINE

### Week 1 End (Nov 22)
- **Deploy to Staging:** Priority 1 APIs
- **Status:** 95% Complete
- **User Testing:** Core metrics and sparklines

### Week 2 End (Nov 29)
- **Deploy to Staging:** Priority 2 APIs
- **Status:** 98% Complete
- **User Testing:** AI features

### Week 3 End (Dec 6)
- **Deploy to Production:** Full application
- **Status:** 100% Complete
- **Announcement:** Production launch

---

## 📋 DELIVERABLES

### Week 1 Deliverables
1. ✅ 4 new backend API endpoints (IRR, LTV, Cap Rate, Historical)
2. ✅ Frontend integration for Priority 1 APIs
3. ✅ Sparkline visualizations with real data
4. ✅ Staging deployment
5. ✅ Week 1 test report

### Week 2 Deliverables
1. ✅ 3 new AI/ML API endpoints (Insights, Market, Tenant)
2. ✅ Frontend integration for Priority 2 APIs
3. ✅ AI features fully functional
4. ✅ Staging deployment update
5. ✅ Week 2 test report

### Week 3 Deliverables
1. ✅ 3 detailed data API endpoints (Costs, Units, Rent Roll)
2. ✅ Error handling UI components
3. ✅ Accessibility enhancements
4. ✅ Comprehensive test suite
5. ✅ Production deployment
6. ✅ Final documentation
7. ✅ User guide

---

## 🎯 RISK MITIGATION

### Risk 1: Backend API Complexity
- **Mitigation:** Start with simple calculations, enhance iteratively
- **Fallback:** Keep mock data as fallback if API fails

### Risk 2: External API Dependencies (Demographics, Comps)
- **Mitigation:** Use cached/mock data if external APIs unavailable
- **Fallback:** Manual data entry for critical properties

### Risk 3: Time Constraints
- **Mitigation:** Focus on Priority 1 first (highest impact)
- **Fallback:** Deploy at 95% if needed, complete Priority 2 post-launch

---

## 📞 SUPPORT & RESOURCES

### Documentation
- API specifications in `/backend/docs/`
- Frontend code in `/src/pages/`
- This sprint plan as living document

### Tools
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React, TypeScript, Vite
- AI: Claude API for insights
- Testing: pytest, Jest, Playwright

---

**Status:** ✅ Ready to Execute
**Confidence:** High (95%)
**Risk:** Low
**Next Action:** Begin Week 1 Day 1 - Portfolio IRR API

---

**Last Updated:** November 15, 2025
**Sprint Master:** Claude Code Assistant
**Next Review:** November 22, 2025 (End of Week 1)
