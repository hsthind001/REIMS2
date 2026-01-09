import { useState, useEffect } from 'react';
import { 
  MessageSquare, 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  BarChart3,
  PieChart,
  FileText,
  Calculator,
  Sparkles,
  Send,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { Card, Button, ProgressBar } from '../components/design-system';
import { propertyService } from '../lib/property';
import { reportsService } from '../lib/reports';
import { documentService } from '../lib/document';
import { financialDataService } from '../lib/financial_data';
import { reconciliationService, type ReconciliationSession, type ComparisonData } from '../lib/reconciliation';
import { chartOfAccountsService, type ChartOfAccount, type ChartOfAccountsSummary } from '../lib/chart_of_accounts';
import { varianceAnalysisService, type PeriodOverPeriodVarianceResponse, type VarianceItem } from '../lib/variance_analysis';
import { financialPeriodsService } from '../lib/financial_periods';
import { MortgageDataTable } from '../components/mortgage/MortgageDataTable';
import { MortgageDetail } from '../components/mortgage/MortgageDetail';
import { MortgageMetrics } from '../components/mortgage/MortgageMetrics';
import { api } from '../lib/api';
import type { Property, DocumentUpload as DocumentUploadType, FinancialPeriod } from '../types/api';
import type { FinancialDataItem, FinancialDataResponse } from '../lib/financial_data';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

type FinancialTab = 'ai' | 'statements' | 'variance' | 'exit' | 'chart' | 'reconciliation';

interface NLQResponse {
  answer: string;
  data: any;
  sql?: string;
  visualizations?: Array<{ type: string; data: any }>;
  confidence: number;
  suggestedFollowUps: string[];
}

interface VarianceData {
  period: string;
  portfolio: {
    revenue: { budget: number; actual: number; variance: number };
    expenses: { budget: number; actual: number; variance: number };
    noi: { budget: number; actual: number; variance: number };
  };
  byProperty: Array<{
    propertyId: number;
    name: string;
    revenue: { budget: number; actual: number; variance: number };
    expenses: { budget: number; actual: number; variance: number };
    noi: { budget: number; actual: number; variance: number };
  }>;
}

interface ExitScenario {
  name: string;
  irr: number;
  npv: number;
  totalReturn: number;
  pros: string[];
  cons: string[];
  risk: 'low' | 'medium' | 'high';
  recommended: boolean;
}

export default function FinancialCommand() {
  const [activeTab, setActiveTab] = useState<FinancialTab>('ai');
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [nlqQuery, setNlqQuery] = useState('');
  const [nlqHistory, setNlqHistory] = useState<Array<{ query: string; response: NLQResponse; timestamp: Date }>>([]);
  const [nlqLoading, setNlqLoading] = useState(false);
  const [varianceData, setVarianceData] = useState<VarianceData | null>(null);
  const [exitScenarios, setExitScenarios] = useState<ExitScenario[]>([]);
  const [financialMetrics, setFinancialMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showFullFinancialData, setShowFullFinancialData] = useState(false);
  const [financialData, setFinancialData] = useState<FinancialDataResponse | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentUploadType[]>([]);
  const [loadingFinancialData, setLoadingFinancialData] = useState(false);
  const [selectedStatementType, setSelectedStatementType] = useState<'income_statement' | 'balance_sheet' | 'cash_flow' | 'mortgage_statement' | null>(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [kpiDscr, setKpiDscr] = useState<number | null>(null);
  const [kpiLtv, setKpiLtv] = useState<number | null>(null);
  const [kpiCapRate, setKpiCapRate] = useState<number | null>(null);
  const [kpiIrr, setKpiIrr] = useState<number | null>(null);
  
  // Reconciliation state
  const [reconciliationSessions, setReconciliationSessions] = useState<ReconciliationSession[]>([]);
  const [reconciliationLoading, setReconciliationLoading] = useState(false);
  const [reconciliationYear, setReconciliationYear] = useState<number>(new Date().getFullYear());
  const [reconciliationMonth, setReconciliationMonth] = useState<number>(new Date().getMonth() + 1);
  const [reconciliationDocType, setReconciliationDocType] = useState<string>('balance_sheet');
  const [activeReconciliation, setActiveReconciliation] = useState<ComparisonData | null>(null);
  
  // Mortgage statement state
  const [selectedMortgageId, setSelectedMortgageId] = useState<number | null>(null);
  const [currentPeriodId, setCurrentPeriodId] = useState<number | null>(null);

  // Chart of Accounts state
  const [showChartOfAccounts, setShowChartOfAccounts] = useState(false);
  const [chartOfAccounts, setChartOfAccounts] = useState<ChartOfAccount[]>([]);
  const [chartSummary, setChartSummary] = useState<ChartOfAccountsSummary | null>(null);
  const [loadingChart, setLoadingChart] = useState(false);
  const [chartSearchQuery, setChartSearchQuery] = useState('');
  const [chartFilterType, setChartFilterType] = useState<string>('');
  const [chartFilterCategory, setChartFilterCategory] = useState<string>('');

  // Variance Analysis state
  const [showVarianceAnalysis, setShowVarianceAnalysis] = useState(false);
  const [periodVariance, setPeriodVariance] = useState<PeriodOverPeriodVarianceResponse | null>(null);
  const [loadingVariance, setLoadingVariance] = useState(false);
  const [varianceFilterSeverity, setVarianceFilterSeverity] = useState<string>('');
  const [varianceSearchQuery, setVarianceSearchQuery] = useState('');
  const [availablePeriods, setAvailablePeriods] = useState<FinancialPeriod[]>([]);
  const [selectedVariancePeriod, setSelectedVariancePeriod] = useState<number | null>(null);

  useEffect(() => {
    loadInitialData();
    
    // Check URL hash for property parameter
    const hash = window.location.hash;
    if (hash.includes('property=')) {
      const params = new URLSearchParams(hash.split('?')[1] || '');
      const propertyCode = params.get('property');
      if (propertyCode) {
        // Property will be set after properties load
        setTimeout(() => {
          const property = properties.find(p => p.property_code === propertyCode);
          if (property) {
            setSelectedProperty(property);
          }
        }, 100);
      }
    }
  }, []);

  useEffect(() => {
    // Re-check hash when properties are loaded
    if (properties.length > 0) {
      const hash = window.location.hash;
      if (hash.includes('property=')) {
        const params = new URLSearchParams(hash.split('?')[1] || '');
        const propertyCode = params.get('property');
        if (propertyCode && (!selectedProperty || selectedProperty.property_code !== propertyCode)) {
          const property = properties.find(p => p.property_code === propertyCode);
          if (property) {
            setSelectedProperty(property);
          }
        }
      }
    }
  }, [properties]);

  useEffect(() => {
    if (selectedProperty) {
      loadFinancialData(selectedProperty.id);
      loadAvailableDocuments(selectedProperty.property_code);
      loadReconciliationSessions(selectedProperty.property_code);
      loadCurrentPeriod();
      loadAvailablePeriods();
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0) {
        setSelectedProperty(data[0]);
      }
    } catch (err) {
      console.error('Failed to load properties:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadFinancialData = async (propertyId: number) => {
    try {
      // Load variance data
      const varianceRes = await fetch(`${API_BASE_URL}/variance-analysis?property_id=${propertyId}`, {
        credentials: 'include'
      });
      if (varianceRes.ok) {
        const variance = await varianceRes.json();
        setVarianceData(variance);
      }

      // Load exit scenarios
      const exitRes = await fetch(`${API_BASE_URL}/risk-alerts/exit-strategy/${propertyId}`, {
        credentials: 'include'
      });
      if (exitRes.ok) {
        const exit = await exitRes.json();
        setExitScenarios(exit.scenarios || []);
      }

      // Load financial metrics
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
        credentials: 'include'
      });
      if (metricsRes.ok) {
        const metrics = await metricsRes.json();
        const propertyMetric = metrics.find((m: any) => m.property_id === propertyId);
        setFinancialMetrics(propertyMetric);

        // Fetch KPI metrics for the selected property
        try {
          const [ltvRes, capRateRes, irrRes] = await Promise.all([
            fetch(`${API_BASE_URL}/metrics/${propertyId}/ltv`, { credentials: 'include' }),
            fetch(`${API_BASE_URL}/metrics/${propertyId}/cap-rate`, { credentials: 'include' }),
            fetch(`${API_BASE_URL}/exit-strategy/portfolio-irr`, { credentials: 'include' })
          ]);

          if (ltvRes.ok) {
            const ltvData = await ltvRes.json();
            setKpiLtv(ltvData.ltv || null);

            // Calculate DSCR from LTV data
            // Use net_operating_income (NOI) for DSCR calculation, not net_income
            const loanAmount = ltvData.loan_amount || 0;
            const annualDebtService = loanAmount * 0.08;
            const noiForDscr = propertyMetric?.net_operating_income || propertyMetric?.net_income || 0;
            if (annualDebtService > 0 && noiForDscr > 0) {
              setKpiDscr(noiForDscr / annualDebtService);
            } else {
              setKpiDscr(null);
            }
          } else {
            setKpiLtv(null);
          }

          if (capRateRes.ok) {
            const capRateData = await capRateRes.json();
            setKpiCapRate(capRateData.cap_rate || null);
          } else {
            setKpiCapRate(null);
          }

          if (irrRes.ok) {
            const irrData = await irrRes.json();
            setKpiIrr(irrData.irr || null);
          } else {
            setKpiIrr(null);
          }
        } catch (kpiErr) {
          console.error('Failed to fetch KPI metrics:', kpiErr);
        }
      }
    } catch (err) {
      console.error('Failed to load financial data:', err);
    }
  };

  const handleNLQSubmit = async () => {
    if (!nlqQuery.trim()) return;

    setNlqLoading(true);
    try {
      // Include property context if a property is selected
      const requestBody: any = { question: nlqQuery };
      if (selectedProperty) {
        requestBody.context = {
          property_id: selectedProperty.id,
          property_code: selectedProperty.property_code,
          property_name: selectedProperty.property_name
        };
      }

      console.log('🚀 Sending NLQ request to:', `${API_BASE_URL}/nlq/query`);
      console.log('📦 Request body:', requestBody);
      
      let response: Response;
      try {
        response = await fetch(`${API_BASE_URL}/nlq/query`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify(requestBody)
        });
        console.log('✅ Response received:', response.status, response.statusText);
        console.log('📋 Response headers:', Object.fromEntries(response.headers.entries()));
      } catch (fetchError: any) {
        // Catch network errors and provide better error message
        console.error('❌ Fetch error details:', fetchError);
        console.error('❌ Error type:', fetchError.constructor.name);
        console.error('❌ Error message:', fetchError.message);
        console.error('❌ Error stack:', fetchError.stack);
        
        const errorResponse: NLQResponse = {
          answer: `❌ Network Error: ${fetchError.message || 'Failed to connect to server'}\n\nPlease check:\n1. Backend is running at ${API_BASE_URL}\n2. Open browser console (F12) and check for CORS errors\n3. Try refreshing the page and logging in again\n4. Check Network tab to see if request was sent`,
          data: {},
          confidence: 0,
          suggestedFollowUps: []
        };
        setNlqHistory(prev => [...prev, {
          query: nlqQuery,
          response: errorResponse,
          timestamp: new Date()
        }]);
        setNlqQuery('');
        setNlqLoading(false);
        return;
      }

      if (response.ok) {
        const data = await response.json();
        
        // Check if response indicates failure
        if (!data.success) {
          const errorResponse: NLQResponse = {
            answer: `❌ Error: ${data.error || 'Unable to process your query. Please try rephrasing or check if the required data is available.'}`,
            data: data.data || {},
            sql: data.sql_query,
            visualizations: data.visualizations,
            confidence: data.confidence || 0,
            suggestedFollowUps: data.suggested_follow_ups || []
          };
          setNlqHistory(prev => [...prev, {
            query: nlqQuery,
            response: errorResponse,
            timestamp: new Date()
          }]);
          setNlqQuery('');
          return;
        }
        
        const nlqResponse: NLQResponse = {
          answer: data.answer || 'Analysis complete',
          data: data.data,
          sql: data.sql_query,
          visualizations: data.visualizations,
          confidence: data.confidence || 85,
          suggestedFollowUps: data.suggested_follow_ups || []
        };

        setNlqHistory(prev => [...prev, {
          query: nlqQuery,
          response: nlqResponse,
          timestamp: new Date()
        }]);
        setNlqQuery('');
      } else {
        // Handle HTTP error responses
        let errorMessage = 'Unable to process your query.';
        
        if (response.status === 401) {
          errorMessage = 'Authentication required. Please refresh the page and log in again.';
        } else if (response.status === 403) {
          errorMessage = 'You do not have permission to perform this action.';
        } else if (response.status === 500) {
          errorMessage = 'Server error. Please try again later or contact support.';
        } else if (response.status === 404) {
          errorMessage = 'Endpoint not found. Please check if the backend is running correctly.';
        }
        
        const errorData = await response.json().catch(() => ({ 
          error: errorMessage,
          detail: `HTTP ${response.status}: ${response.statusText}`
        }));
        
        const errorResponse: NLQResponse = {
          answer: `❌ Error (HTTP ${response.status}): ${errorData.error || errorData.detail || errorMessage}`,
          data: {},
          confidence: 0,
          suggestedFollowUps: []
        };

        setNlqHistory(prev => [...prev, {
          query: nlqQuery,
          response: errorResponse,
          timestamp: new Date()
        }]);
        setNlqQuery('');
      }
    } catch (err) {
      console.error('NLQ query failed:', err);
      let errorMessage = 'Network error. Please check your connection and try again.';
      
      if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        errorMessage = 'Failed to connect to the server. Please check if the backend is running and try again.';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      const errorResponse: NLQResponse = {
        answer: `❌ Error: ${errorMessage}`,
        data: {},
        confidence: 0,
        suggestedFollowUps: []
      };
      setNlqHistory(prev => [...prev, {
        query: nlqQuery,
        response: errorResponse,
        timestamp: new Date()
      }]);
      setNlqQuery('');
    } finally {
      setNlqLoading(false);
    }
  };

  const getVarianceColor = (variance: number) => {
    if (variance > 10) return 'bg-danger-light';
    if (variance > 5) return 'bg-warning-light';
    if (variance < -5) return 'bg-success-light';
    return 'bg-background';
  };

  const getVarianceIcon = (variance: number) => {
    if (variance > 10) return '🔴';
    if (variance > 5) return '🟡';
    if (variance < -5) return '🟢';
    return '⚪';
  };

  const loadReconciliationSessions = async (propertyCode: string) => {
    try {
      setReconciliationLoading(true);
      const result = await reconciliationService.getSessions(propertyCode, 20);
      setReconciliationSessions(result.sessions || []);
    } catch (err) {
      console.error('Failed to load reconciliation sessions:', err);
      setReconciliationSessions([]);
    } finally {
      setReconciliationLoading(false);
    }
  };

  const handleStartReconciliation = async () => {
    if (!selectedProperty) return;

    try {
      setReconciliationLoading(true);
      const comparisonData = await reconciliationService.getComparison(
        selectedProperty.property_code,
        reconciliationYear,
        reconciliationMonth,
        reconciliationDocType
      );
      setActiveReconciliation(comparisonData);
    } catch (err: any) {
      console.error('Failed to start reconciliation:', err);
      // ApiClient error structure: { message, status, detail, category, retryable }
      const errorMessage = err.message || err.detail?.detail || 'Unable to start reconciliation';

      // Check if it's a document not found error
      if (errorMessage.toLowerCase().includes('not found') ||
          errorMessage.toLowerCase().includes('document') ||
          errorMessage.toLowerCase().includes('period not found')) {
        alert(`📄 Document Not Available\n\nThe document for ${selectedProperty?.property_name} (${reconciliationDocType.replace('_', ' ').toUpperCase()}) for ${new Date(2000, reconciliationMonth - 1).toLocaleString('default', { month: 'long' })} ${reconciliationYear} has not been uploaded yet.\n\nPlease upload the document first to proceed with reconciliation.`);
      } else {
        alert(`⚠️ ${errorMessage}\n\nPlease try again or contact support if the issue persists.`);
      }
    } finally {
      setReconciliationLoading(false);
    }
  };

  const loadAvailableDocuments = async (propertyCode: string) => {
    if (!propertyCode) return;
    
    try {
      // Load all documents for the property (without period filter) to show what's available
      const docs = await documentService.getDocuments({
        property_code: propertyCode,
        limit: 100  // Get more documents to show all available periods
      });
      setAvailableDocuments(docs.items || []);
      
      // If we have documents, try to find one matching the selected period
      // If found, use it; otherwise, use the most recent document's period
      if (docs.items && docs.items.length > 0) {
        const periodMatch = docs.items.find(d => {
          // We need to check the period from the document's period_id
          // For now, just use the first available document's period
          return true;
        });
        
        // If no documents match the selected period, suggest the most recent period
        const periodDocs = docs.items.filter(d => 
          d.document_type === 'income_statement' || 
          d.document_type === 'balance_sheet' || 
          d.document_type === 'cash_flow'
        );
        
        if (periodDocs.length > 0 && !periodDocs.some(d => {
          // We can't check period directly, so we'll just use what we have
          return true;
        })) {
          // Documents exist but may be for different period - that's OK, we'll show them
        }
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadFullFinancialData = async (documentType: 'income_statement' | 'balance_sheet' | 'cash_flow') => {
    if (!selectedProperty) return;
    
    setLoadingFinancialData(true);
    setFinancialData(null);
    
    try {
      console.log('Loading financial data for:', {
        documentType,
        propertyCode: selectedProperty.property_code,
        availableDocumentsCount: availableDocuments.length,
        availableDocs: availableDocuments.map(d => ({
          id: d.id,
          type: d.document_type,
          status: d.extraction_status
        }))
      });

      // First, try to find in availableDocuments - use the most recent completed one
      const matchingDocs = availableDocuments.filter(d => d.document_type === documentType);
      console.log('Matching documents for', documentType, ':', matchingDocs.map(d => ({ id: d.id, status: d.extraction_status })));
      
      let doc: DocumentUploadType | undefined;
      
      // Prioritize completed documents, use most recent (highest ID)
      const completed = matchingDocs.filter(d => d.extraction_status === 'completed');
      if (completed.length > 0) {
        doc = completed.sort((a, b) => (b.id || 0) - (a.id || 0))[0]; // Most recent first
      } else if (matchingDocs.length > 0) {
        // Fall back to any matching document, most recent first
        doc = matchingDocs.sort((a, b) => (b.id || 0) - (a.id || 0))[0];
      }
      
      // If still no doc in availableDocuments, reload from API
      if (!doc) {
        console.log('Document not found in availableDocuments, querying API...');
        const allDocs = await documentService.getDocuments({
          property_code: selectedProperty.property_code,
          document_type: documentType,
          limit: 10
        });
        console.log('API returned documents:', allDocs.items?.map(d => ({
          id: d.id,
          type: d.document_type,
          status: d.extraction_status
        })));
        doc = allDocs.items?.find(d => d.extraction_status === 'completed') || allDocs.items?.[0];
        
        // Update availableDocuments if we found something
        if (doc && allDocs.items) {
          setAvailableDocuments(prev => {
            const existing = prev.map(d => d.id);
            const newDocs = allDocs.items.filter(d => !existing.includes(d.id));
            return [...prev, ...newDocs];
          });
        }
      }
      
      console.log('Selected document:', doc ? {
        id: doc.id,
        type: doc.document_type,
        status: doc.extraction_status
      } : 'NONE FOUND');

      if (doc && doc.id) {
        console.log('Loading financial data for document ID:', doc.id);

        // Get summary to know total count
        const summary = await financialDataService.getSummary(doc.id);
        console.log('Summary loaded:', summary);

        // Respect API limit=1000; fetch in pages and aggregate
        const totalItems = summary.total_items || 0;
        const pageSize = Math.min(1000, Math.max(totalItems, 100));

        const firstPage = await financialDataService.getFinancialData(doc.id, {
          limit: pageSize,
          skip: 0
        });

        const allItems: FinancialDataItem[] = [...(firstPage.items || [])];
        let skip = allItems.length;

        while (allItems.length < (firstPage.total_items || 0)) {
          const nextPage = await financialDataService.getFinancialData(doc.id, {
            limit: Math.min(1000, (firstPage.total_items || 0) - allItems.length),
            skip
          });

          if (!nextPage.items || nextPage.items.length === 0) break;
          allItems.push(...nextPage.items);
          skip += nextPage.items.length;
        }

        console.log('Aggregated financial data items:', allItems.length, 'of', firstPage.total_items);

        setFinancialData({
          ...firstPage,
          items: allItems,
          limit: allItems.length
        });
      } else {
        console.warn('No valid document found, setting financialData to null');
        setFinancialData(null);
      }
    } catch (err) {
      console.error('Failed to load full financial data:', err);
      setFinancialData(null);
    } finally {
      setLoadingFinancialData(false);
    }
  };

  const loadChartOfAccounts = async () => {
    try {
      setLoadingChart(true);
      console.log('Loading chart of accounts with filters:', {
        search: chartSearchQuery,
        account_type: chartFilterType,
        category: chartFilterCategory
      });

      // Load summary
      const summary = await chartOfAccountsService.getSummary();
      setChartSummary(summary);
      console.log('Chart summary:', summary);

      // Load all accounts with filters
      const accounts = await chartOfAccountsService.getAccounts({
        limit: 500,
        search: chartSearchQuery || undefined,
        account_type: chartFilterType || undefined,
        category: chartFilterCategory || undefined,
        is_active: true
      });

      setChartOfAccounts(accounts);
      console.log('Loaded accounts:', accounts.length);
    } catch (err) {
      console.error('Failed to load chart of accounts:', err);
      alert('Failed to load chart of accounts. Please try again.');
    } finally {
      setLoadingChart(false);
    }
  };

  const handleViewChartOfAccounts = async () => {
    try {
      console.log('View Chart of Accounts clicked');
      setShowChartOfAccounts(true);
      await loadChartOfAccounts();
    } catch (err) {
      console.error('Error in handleViewChartOfAccounts:', err);
      alert('Failed to load chart of accounts. Please try again.');
    }
  };

  const loadCurrentPeriod = async (): Promise<number | null> => {
    if (!selectedProperty) {
      console.warn('Cannot load period: no property selected');
      setCurrentPeriodId(null);
      return null;
    }

    try {
      console.log('Loading financial period for:', {
        propertyId: selectedProperty.id,
        year: selectedYear,
        month: selectedMonth
      });

      const period = await financialPeriodsService.getOrCreatePeriod(
        selectedProperty.id,
        selectedYear,
        selectedMonth
      );

      setCurrentPeriodId(period.id);
      console.log('Financial period loaded:', period);
      return period.id;
    } catch (err) {
      console.error('Failed to load financial period:', err);
      setCurrentPeriodId(null);
      return null;
    }
  };

  const loadAvailablePeriods = async () => {
    if (!selectedProperty) {
      console.log('loadAvailablePeriods: No property selected');
      setAvailablePeriods([]);
      return;
    }

    try {
      console.log('loadAvailablePeriods: Fetching periods for property:', selectedProperty.id);
      const response = await fetch(`${API_BASE_URL}/financial-periods?property_id=${selectedProperty.id}`, {
        credentials: 'include'
      });

      console.log('loadAvailablePeriods: Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('loadAvailablePeriods: Received data:', data);
        // The API returns the array directly, not wrapped in an object
        const periods = Array.isArray(data) ? data : (data.periods || []);
        console.log('loadAvailablePeriods: Periods array:', periods);
        setAvailablePeriods(periods);

        // Auto-select the most recent period if none selected
        if (periods.length > 0 && !selectedVariancePeriod) {
          // Sort by year/month descending
          const sortedPeriods = [...periods].sort((a, b) => {
            if (a.period_year !== b.period_year) return b.period_year - a.period_year;
            return b.period_month - a.period_month;
          });
          console.log('loadAvailablePeriods: Auto-selecting period:', sortedPeriods[0]);
          setSelectedVariancePeriod(sortedPeriods[0].id);
        }
      } else {
        console.error('loadAvailablePeriods: Response not OK:', response.status, response.statusText);
      }
    } catch (err) {
      console.error('Failed to load available periods:', err);
      setAvailablePeriods([]);
    }
  };

  const loadVarianceAnalysis = async (periodId?: number) => {
    const usePeriodId = periodId || currentPeriodId;

    if (!selectedProperty || !usePeriodId) {
      console.warn('Cannot load variance: property or period not selected');
      return;
    }

    try {
      setLoadingVariance(true);
      console.log('Loading period-over-period variance analysis for:', {
        propertyId: selectedProperty.id,
        periodId: usePeriodId
      });

      const result = await varianceAnalysisService.getPeriodOverPeriodVariance(
        selectedProperty.id,
        usePeriodId
      );

      setPeriodVariance(result);
      console.log('Period-over-period variance loaded:', result);
    } catch (err) {
      console.error('Failed to load variance analysis:', err);
      alert('Failed to load period-over-period variance analysis. Please try again.');
    } finally {
      setLoadingVariance(false);
    }
  };

  const handleRunVarianceAnalysis = async () => {
    try {
      if (!selectedProperty) {
        alert('Please select a property first');
        return;
      }

      if (!selectedVariancePeriod) {
        alert('Please select a period for variance analysis');
        return;
      }

      console.log('Run Variance Analysis clicked for period:', selectedVariancePeriod);
      setShowVarianceAnalysis(true);

      // Load variance with the selected period ID
      await loadVarianceAnalysis(selectedVariancePeriod);
    } catch (err) {
      console.error('Error in handleRunVarianceAnalysis:', err);
      alert('Failed to run variance analysis. Please try again.');
    }
  };

  const handleViewFullFinancialData = async () => {
    // Navigate to dedicated full-financial-data page with context in hash params
    if (!selectedProperty) {
      alert('Please select a property first');
      return;
    }

    const params = new URLSearchParams({
      property: selectedProperty.property_code,
      year: String(selectedYear),
      month: String(selectedMonth),
    });

    if (selectedStatementType) {
      params.set('doc', selectedStatementType);
    }

    window.location.hash = `financial-data?${params.toString()}`;
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Financial Command</h1>
            <p className="text-text-secondary mt-1">Complete financial analysis, reporting, and AI intelligence</p>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedProperty?.id || ''}
              onChange={(e) => {
                const prop = properties.find(p => p.id === Number(e.target.value));
                setSelectedProperty(prop || null);
              }}
              className="px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            >
              {properties.map(p => (
                <option key={p.id} value={p.id}>{p.property_name}</option>
              ))}
            </select>
            <Button variant="primary" icon={<Download className="w-4 h-4" />}>
              Export Report
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border mb-6 items-center">
          {(['ai', 'statements', 'variance', 'exit', 'chart', 'reconciliation'] as FinancialTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium text-sm transition-colors capitalize ${
                activeTab === tab
                  ? 'text-info border-b-2 border-info'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab === 'ai' ? 'AI Assistant' : tab === 'chart' ? 'Chart of Accounts' : tab}
            </button>
          ))}
          {/* Quick Access Links */}
          <button
            onClick={() => {
              window.location.hash = 'chart-of-accounts';
            }}
            className="ml-auto px-4 py-2 font-medium text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            title="View and manage chart of accounts"
          >
            📊 Chart of Accounts
          </button>
          <button
            onClick={() => {
              window.location.hash = 'reconciliation';
            }}
            className="px-4 py-2 font-medium text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
            title="Period reconciliation dashboard"
          >
            🔄 Reconciliation
          </button>
          <button
            onClick={() => {
              window.location.hash = 'forensic-reconciliation';
            }}
            className="px-4 py-2 font-medium text-sm border-2 border-purple-600 text-purple-600 rounded-lg hover:bg-purple-50 transition-colors flex items-center gap-2"
            title="Open Forensic Reconciliation Elite System - Advanced matching, materiality-based thresholds, tiered exception management"
          >
            🔍 Forensic Reconciliation
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'ai' && (
          <div className="space-y-6">
            {/* AI Financial Assistant */}
            <Card variant="premium" className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-6 h-6 text-premium" />
                <h2 className="text-2xl font-bold">💬 Ask REIMS AI - Financial Intelligence Assistant</h2>
              </div>
              
              <div className="bg-premium-light/20 p-4 rounded-lg mb-4">
                <div className="text-sm text-text-secondary mb-2">Example queries:</div>
                <div className="text-sm space-y-1">
                  <div>• "Which properties have DSCR below 1.25?"</div>
                  <div>• "Show me NOI trends for last 12 months"</div>
                  <div>• "Compare Q3 vs Q2 performance"</div>
                  <div>• "What's my total portfolio value?"</div>
                </div>
              </div>

              <div className="flex gap-2 mb-6">
                <input
                  type="text"
                  value={nlqQuery}
                  onChange={(e) => setNlqQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleNLQSubmit()}
                  placeholder="Type your question in plain English..."
                  className="flex-1 px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-premium"
                />
                <Button
                  variant="premium"
                  icon={<Send className="w-4 h-4" />}
                  onClick={handleNLQSubmit}
                  isLoading={nlqLoading}
                >
                  Ask
                </Button>
              </div>

              {/* Conversation History */}
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {nlqHistory.map((item, i) => (
                  <div key={i} className="space-y-2">
                    <div className="text-sm font-medium text-text-primary">
                      You: {item.query}
                    </div>
                    <Card variant="premium" className="p-4 border-l-4 border-premium">
                      <div className="flex items-start gap-2 mb-2">
                        <Sparkles className="w-5 h-5 text-premium" />
                        <div className="flex-1">
                          <div className="font-semibold mb-2">🤖 REIMS AI:</div>
                          <div className="whitespace-pre-line text-sm">{item.response.answer}</div>
                          {item.response.suggestedFollowUps.length > 0 && (
                            <div className="mt-4">
                              <div className="text-sm font-medium mb-2">Suggested follow-ups:</div>
                              <div className="space-y-1">
                                {item.response.suggestedFollowUps.map((followUp, j) => (
                                  <button
                                    key={j}
                                    onClick={() => {
                                      setNlqQuery(followUp);
                                      handleNLQSubmit();
                                    }}
                                    className="text-sm text-premium hover:underline block"
                                  >
                                    • {followUp}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'statements' && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-2xl font-bold mb-4">Financial Statements</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <Card variant="success" className="p-4 cursor-pointer hover:scale-105 transition-transform">
                  <div className="text-sm text-text-secondary mb-1">Income Statement</div>
                  <div className="text-2xl font-bold">
                    Q{Math.floor((selectedMonth - 1) / 3) + 1} {selectedYear}
                  </div>
                  <div className="text-sm text-text-secondary mt-2">
                    Revenue: ${((financialMetrics?.total_revenue || 0) / 1000000).toFixed(1)}M
                  </div>
                </Card>
                <Card variant="info" className="p-4 cursor-pointer hover:scale-105 transition-transform">
                  <div className="text-sm text-text-secondary mb-1">Balance Sheet</div>
                  <div className="text-2xl font-bold">
                    Q{Math.floor((selectedMonth - 1) / 3) + 1} {selectedYear}
                  </div>
                  <div className="text-sm text-text-secondary mt-2">
                    Assets: ${((financialMetrics?.total_assets || 0) / 1000000).toFixed(1)}M
                  </div>
                </Card>
                <Card variant="primary" className="p-4 cursor-pointer hover:scale-105 transition-transform">
                  <div className="text-sm text-text-secondary mb-1">Cash Flow</div>
                  <div className="text-2xl font-bold">
                    Q{Math.floor((selectedMonth - 1) / 3) + 1} {selectedYear}
                  </div>
                  <div className="text-sm text-text-secondary mt-2">
                    Net CF: ${((financialMetrics?.net_cash_flow || 0) / 1000000).toFixed(2)}M
                  </div>
                </Card>
              </div>
              <div className="flex gap-4 items-center">
                <div className="flex gap-2">
                  <select
                    value={selectedYear}
                    onChange={(e) => {
                      setSelectedYear(Number(e.target.value));
                      if (selectedProperty) {
                        loadAvailableDocuments(selectedProperty.property_code);
                      }
                    }}
                    className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  >
                    {[2023, 2024, 2025, 2026].map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                  <select
                    value={selectedMonth}
                    onChange={(e) => {
                      setSelectedMonth(Number(e.target.value));
                      if (selectedProperty) {
                        loadAvailableDocuments(selectedProperty.property_code);
                      }
                    }}
                    className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  >
                    {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
                      <option key={month} value={month}>
                        {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                      </option>
                    ))}
                  </select>
                </div>
                <Button variant="primary" onClick={handleViewFullFinancialData}>
                  View Full Financial Data
                </Button>
              </div>
            </Card>

            {/* Full Financial Data Modal */}
            {showFullFinancialData && (
              <div
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                onClick={() => setShowFullFinancialData(false)}
              >
                <div
                  className="bg-surface rounded-2xl shadow-2xl w-full max-w-7xl mx-4 max-h-[90vh] overflow-hidden border border-border flex flex-col"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background sticky top-0 z-10">
                    <div>
                      <h2 className="text-2xl font-bold">Complete Financial Data</h2>
                      <p className="text-sm text-text-secondary mt-1">
                        {selectedProperty?.property_name || 'Select a property'} • {selectedYear}/{String(selectedMonth).padStart(2, '0')} • {availableDocuments.length} document{availableDocuments.length === 1 ? '' : 's'} available
                      </p>
                    </div>
                    <button
                      className="text-text-secondary hover:text-text-primary text-2xl"
                      onClick={() => setShowFullFinancialData(false)}
                    >
                      ×
                    </button>
                  </div>

                  <div className="grid lg:grid-cols-[320px_1fr] gap-4 p-6 h-full overflow-hidden">
                    {/* Left rail: statement selector + docs */}
                    <div className="h-full flex flex-col gap-4 overflow-hidden">
                      <Card className="p-4 h-min">
                        <div className="text-sm font-semibold mb-3 text-text-secondary">Statement Type</div>
                        <div className="grid grid-cols-2 gap-2">
                          {(['income_statement', 'balance_sheet', 'cash_flow', 'mortgage_statement'] as const).map((type) => {
                            const docs = availableDocuments.filter(d => d.document_type === type);
                            const doc = docs.find(d => d.extraction_status === 'completed') || docs[0];
                            return (
                              <button
                                key={type}
                                onClick={() => {
                                  setSelectedStatementType(type);
                                  if (type !== 'mortgage_statement') {
                                    loadFullFinancialData(type);
                                  }
                                }}
                                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors border ${
                                  selectedStatementType === type
                                    ? 'bg-info text-white border-info'
                                    : doc
                                    ? 'bg-background border-border hover:bg-background'
                                    : 'bg-background border-border opacity-50 cursor-not-allowed'
                                }`}
                                disabled={!doc}
                                title={doc ? `${doc.extraction_status} - Upload ID: ${doc.id}` : 'No document available'}
                              >
                                <div className="flex items-center justify-between">
                                  <span>{type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                                  {doc && (
                                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface border border-border">
                                      {doc.extraction_status}
                                    </span>
                                  )}
                                </div>
                                {docs.length > 1 && (
                                  <div className="text-[11px] text-text-secondary mt-1">
                                    {docs.length} versions available
                                  </div>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      </Card>

                      <Card className="p-4 flex-1 overflow-hidden">
                        <div className="flex items-center justify-between mb-3">
                          <div className="text-sm font-semibold text-text-secondary">Available Documents</div>
                          <div className="text-xs text-text-tertiary">{availableDocuments.length} total</div>
                        </div>
                        <div className="space-y-2 overflow-y-auto pr-1 max-h-[60vh] custom-scrollbar">
                          {availableDocuments.length === 0 ? (
                            <div className="text-sm text-text-tertiary">
                              No documents uploaded for this property yet.
                            </div>
                          ) : (
                            availableDocuments
                              .filter(d => ['income_statement', 'balance_sheet', 'cash_flow', 'mortgage_statement'].includes(d.document_type))
                              .map((doc) => (
                                <div
                                  key={doc.id}
                                  className={`p-3 rounded-lg border ${
                                    selectedStatementType === doc.document_type ? 'border-info bg-info-light/15' : 'border-border bg-background'
                                  }`}
                                >
                                  <div className="flex items-center justify-between text-sm font-medium">
                                    <span className="capitalize">{doc.document_type.replace('_', ' ')}</span>
                                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface border border-border">
                                      {doc.extraction_status}
                                    </span>
                                  </div>
                                  <div className="text-xs text-text-secondary mt-1">
                                    Upload #{doc.id} • Period {doc.period_year || '—'}/{String(doc.period_month || 0).padStart(2, '0')}
                                  </div>
                                </div>
                              ))
                          )}
                        </div>
                        <div className="text-[11px] text-text-tertiary mt-2">
                          Scroll to see all uploads. Documents may belong to different periods.
                        </div>
                      </Card>
                    </div>

                    {/* Right rail: data display */}
                    <div className="h-full overflow-hidden flex flex-col gap-4">
                      {selectedStatementType === 'mortgage_statement' ? (
                        selectedProperty && currentPeriodId ? (
                          <div className="space-y-4 overflow-y-auto pr-1 custom-scrollbar">
                            <Card className="p-6">
                              <h3 className="text-lg font-semibold mb-4">Mortgage Statements</h3>
                              <MortgageDataTable
                                propertyId={selectedProperty.id}
                                periodId={currentPeriodId}
                                onViewDetail={(mortgageId) => setSelectedMortgageId(mortgageId)}
                              />
                            </Card>
                            <Card className="p-6">
                              <h3 className="text-lg font-semibold mb-4">Mortgage Metrics</h3>
                              <MortgageMetrics
                                propertyId={selectedProperty.id}
                                periodId={currentPeriodId}
                              />
                            </Card>
                          </div>
                        ) : (
                          <Card className="p-8 text-center flex-1 flex items-center justify-center">
                            <div className="text-text-secondary">
                              Please select a property and period to view mortgage statements.
                            </div>
                          </Card>
                        )
                      ) : loadingFinancialData ? (
                        <Card className="p-8 text-center flex-1 flex flex-col items-center justify-center">
                          <div className="text-text-secondary">Loading complete financial document data...</div>
                          <div className="text-xs text-text-tertiary mt-2">Fetching all line items with zero data loss</div>
                        </Card>
                      ) : financialData && financialData.items && financialData.items.length > 0 ? (
                        <Card className="p-6 flex-1 flex flex-col overflow-hidden">
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <h3 className="text-lg font-semibold">
                                {financialData.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} - Complete Line Items
                              </h3>
                              <p className="text-sm text-text-secondary mt-1">
                                Showing all {financialData.items.length} of {financialData.total_items} extracted line items
                              </p>
                            </div>
                            <div className="text-sm text-text-secondary text-right">
                              {financialData.property_code}<br />
                              {financialData.period_year}/{String(financialData.period_month).padStart(2, '0')}
                            </div>
                          </div>
                          
                          <div className="overflow-x-auto overflow-y-auto max-h-[60vh] border border-border rounded-lg custom-scrollbar">
                            <table className="w-full">
                              <thead className="sticky top-0 bg-surface z-10 border-b-2 border-border">
                                <tr>
                                  <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Line</th>
                                  <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Code</th>
                                  <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Name</th>
                                  <th className="text-right py-3 px-4 text-sm font-semibold bg-surface">Amount</th>
                                  <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Confidence</th>
                                  <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Status</th>
                                </tr>
                              </thead>
                              <tbody>
                                {financialData.items.map((item: FinancialDataItem) => (
                                  <tr 
                                    key={item.id} 
                                    className={`border-b border-border hover:bg-background ${
                                      item.is_total ? 'font-bold bg-info-light/10' : 
                                      item.is_subtotal ? 'font-semibold bg-background' : ''
                                    }`}
                                  >
                                    <td className="py-2 px-4 text-sm text-text-secondary">
                                      {item.line_number || '-'}
                                    </td>
                                    <td className="py-2 px-4">
                                      <span className="font-mono font-medium">{item.account_code}</span>
                                    </td>
                                    <td className="py-2 px-4">
                                      <div className="flex items-center gap-2">
                                        {item.account_name}
                                        {item.is_total && (
                                          <span className="px-2 py-0.5 bg-info text-white rounded text-xs">
                                            TOTAL
                                          </span>
                                        )}
                                        {item.is_subtotal && (
                                          <span className="px-2 py-0.5 bg-premium text-white rounded text-xs">
                                            SUBTOTAL
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                    <td className="py-2 px-4 text-right font-mono">
                                      {item.amounts.amount !== undefined && item.amounts.amount !== null
                                        ? `$${item.amounts.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                        : item.amounts.period_amount !== undefined && item.amounts.period_amount !== null
                                        ? `$${item.amounts.period_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                        : item.amounts.ytd_amount !== undefined && item.amounts.ytd_amount !== null
                                        ? `YTD: $${item.amounts.ytd_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                        : '-'}
                                    </td>
                                    <td className="py-2 px-4 text-center">
                                      <div className="text-xs">
                                        <div className="font-medium">
                                          E: {item.extraction_confidence.toFixed(0)}%
                                        </div>
                                        <div className="text-text-secondary">
                                          M: {item.match_confidence?.toFixed(0) || 0}%
                                        </div>
                                      </div>
                                    </td>
                                    <td className="py-2 px-4 text-center">
                                      {item.severity === 'critical' && <span className="text-danger">🔴</span>}
                                      {item.severity === 'warning' && <span className="text-warning">🟡</span>}
                                      {item.severity === 'excellent' && <span className="text-success">🟢</span>}
                                      {item.needs_review && (
                                        <span className="ml-2 text-xs text-warning">Review</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </Card>
                      ) : (
                        <Card className="p-8 text-center flex-1 flex flex-col items-center justify-center">
                          <div className="text-text-secondary mb-3">
                            {selectedStatementType 
                              ? `No ${selectedStatementType.replace('_', ' ')} document found.`
                              : 'Please select a statement type on the left.'
                            }
                          </div>
                          {availableDocuments.length > 0 && (
                            <div className="text-xs text-text-tertiary max-w-md">
                              Use the left rail to pick the statement type. Documents may be for different periods.
                            </div>
                          )}
                        </Card>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* All 31 Financial KPIs */}
            {financialMetrics && (
              <Card className="p-6">
                <h2 className="text-2xl font-bold mb-4">All Financial KPIs</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-text-secondary">NOI</div>
                    {/* Use net_operating_income (NOI) instead of net_income for consistency */}
                    <div className="text-lg font-bold">${((financialMetrics.net_operating_income || financialMetrics.net_income || 0) / 1000).toFixed(0)}K</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">DSCR</div>
                    <div className="text-lg font-bold">{kpiDscr !== null ? kpiDscr.toFixed(2) : 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">LTV</div>
                    <div className="text-lg font-bold">{kpiLtv !== null ? `${kpiLtv.toFixed(1)}%` : 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Cap Rate</div>
                    <div className="text-lg font-bold">{kpiCapRate !== null ? `${kpiCapRate.toFixed(2)}%` : 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Occupancy</div>
                    <div className="text-lg font-bold">{(financialMetrics.occupancy_rate || 0).toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Total Assets</div>
                    <div className="text-lg font-bold">${(financialMetrics.total_assets || 0) / 1000000}M</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Total Revenue</div>
                    <div className="text-lg font-bold">${(financialMetrics.total_revenue || 0) / 1000}K</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">IRR</div>
                    <div className="text-lg font-bold">{kpiIrr !== null ? `${kpiIrr.toFixed(1)}%` : 'N/A'}</div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'variance' && (
          <div className="space-y-6">
            {/* Header Card */}
            <Card className="p-6">
              <div className="mb-4">
                <h2 className="text-2xl font-bold mb-2">📈 Variance Analysis</h2>
                <p className="text-text-secondary">
                  Compare actual performance between current and previous periods to identify significant variances.
                </p>
              </div>

              {/* Period Selection */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Select Period for Analysis (Available: {availablePeriods.length})
                </label>
                <select
                  value={selectedVariancePeriod || ''}
                  onChange={(e) => setSelectedVariancePeriod(Number(e.target.value))}
                  className="w-full md:w-auto px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                >
                  <option value="">Choose a period...</option>
                  {availablePeriods
                    .sort((a, b) => {
                      if (a.period_year !== b.period_year) return b.period_year - a.period_year;
                      return b.period_month - a.period_month;
                    })
                    .map(period => (
                      <option key={period.id} value={period.id}>
                        {period.period_year}-{String(period.period_month).padStart(2, '0')}
                      </option>
                    ))}
                </select>
              </div>

              <Button
                variant="primary"
                onClick={handleRunVarianceAnalysis}
                disabled={!selectedVariancePeriod}
              >
                Run Variance Analysis
              </Button>
            </Card>

            {/* Variance Results - Displayed Inline */}
            {showVarianceAnalysis && (
              <>
                {/* Summary Card */}
                {periodVariance && periodVariance.summary && (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Variance Summary</h3>
                    <div className="mb-4 text-sm text-text-secondary">
                      {periodVariance.property_name} • {periodVariance.current_period_year}/{String(periodVariance.current_period_month).padStart(2, '0')}
                      <span className="mx-2">vs</span>
                      {periodVariance.previous_period_year}/{String(periodVariance.previous_period_month).padStart(2, '0')}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="p-4 bg-background rounded-lg border border-border">
                        <div className="text-sm text-text-secondary mb-1">Total Accounts</div>
                        <div className="text-2xl font-bold">{periodVariance.summary.total_accounts}</div>
                      </div>
                      <div className="p-4 bg-warning-light/20 rounded-lg border border-warning">
                        <div className="text-sm text-text-secondary mb-1">Flagged</div>
                        <div className="text-2xl font-bold text-warning">{periodVariance.summary.flagged_accounts}</div>
                      </div>
                      <div className="p-4 bg-background rounded-lg border border-border">
                        <div className="text-sm text-text-secondary mb-1">Previous Period ({periodVariance.previous_period_year}/{periodVariance.previous_period_month})</div>
                        <div className="text-xl font-bold">${((periodVariance.summary.total_previous_period || 0) / 1000).toFixed(0)}K</div>
                      </div>
                      <div className="p-4 bg-background rounded-lg border border-border">
                        <div className="text-sm text-text-secondary mb-1">Current Period ({periodVariance.current_period_year}/{periodVariance.current_period_month})</div>
                        <div className="text-xl font-bold">${((periodVariance.summary.total_current_period || 0) / 1000).toFixed(0)}K</div>
                      </div>
                    </div>

                    <div className="mb-4">
                      <div className="text-sm text-text-secondary mb-2">Severity Breakdown:</div>
                      <div className="grid grid-cols-4 gap-4">
                        <div className="flex items-center gap-2">
                          <span className="w-3 h-3 bg-success rounded-full"></span>
                          <span className="text-sm">Normal: {periodVariance.summary.severity_breakdown.NORMAL}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-3 h-3 bg-warning rounded-full"></span>
                          <span className="text-sm">Warning: {periodVariance.summary.severity_breakdown.WARNING}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-3 h-3 bg-danger rounded-full"></span>
                          <span className="text-sm">Critical: {periodVariance.summary.severity_breakdown.CRITICAL}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-3 h-3 bg-purple-600 rounded-full"></span>
                          <span className="text-sm">Urgent: {periodVariance.summary.severity_breakdown.URGENT}</span>
                        </div>
                      </div>
                    </div>

                    {periodVariance.alerts_created > 0 && (
                      <div className="mt-4 p-3 bg-info-light/20 rounded-lg border border-info">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-info" />
                          <span className="text-sm font-medium">
                            {periodVariance.alerts_created} alert{periodVariance.alerts_created > 1 ? 's' : ''} created for critical variances
                          </span>
                        </div>
                      </div>
                    )}
                  </Card>
                )}

                {/* Filter Card */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Filter Results</h3>
                  <div className="flex gap-4">
                    <input
                      type="text"
                      placeholder="Search by account code or name..."
                      value={varianceSearchQuery}
                      onChange={(e) => setVarianceSearchQuery(e.target.value)}
                      className="flex-1 px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                    />
                    <select
                      value={varianceFilterSeverity}
                      onChange={(e) => setVarianceFilterSeverity(e.target.value)}
                      className="px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                    >
                      <option value="">All Severity Levels</option>
                      <option value="URGENT">Urgent (&gt;50%)</option>
                      <option value="CRITICAL">Critical (25-50%)</option>
                      <option value="WARNING">Warning (10-25%)</option>
                      <option value="NORMAL">Normal (&lt;10%)</option>
                    </select>
                  </div>
                </Card>

                {/* Variance Details Table */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Account-Level Variance</h3>
                  {loadingVariance ? (
                    <div className="text-center py-8">
                      <div className="text-text-secondary">Loading variance analysis...</div>
                    </div>
                  ) : periodVariance && periodVariance.variance_items && periodVariance.variance_items.length > 0 ? (
                    <div>
                      <div className="overflow-x-auto border border-border rounded-lg">
                        <table className="w-full">
                          <thead className="bg-background border-b-2 border-border">
                            <tr>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Code</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Account Name</th>
                              <th className="text-right py-3 px-4 text-sm font-semibold">Previous Period</th>
                              <th className="text-right py-3 px-4 text-sm font-semibold">Current Period</th>
                              <th className="text-right py-3 px-4 text-sm font-semibold">Variance $</th>
                              <th className="text-right py-3 px-4 text-sm font-semibold">Variance %</th>
                              <th className="text-center py-3 px-4 text-sm font-semibold">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {periodVariance.variance_items
                              .filter(item => {
                                const matchesSearch = !varianceSearchQuery ||
                                  item.account_code.toLowerCase().includes(varianceSearchQuery.toLowerCase()) ||
                                  item.account_name.toLowerCase().includes(varianceSearchQuery.toLowerCase());
                                const matchesSeverity = !varianceFilterSeverity || item.severity === varianceFilterSeverity;
                                return matchesSearch && matchesSeverity;
                              })
                              .map((item) => (
                                <tr
                                  key={item.account_code}
                                  className={`border-b border-border hover:bg-background transition-colors ${
                                    item.severity === 'URGENT' ? 'bg-purple-50' :
                                    item.severity === 'CRITICAL' ? 'bg-danger-light/10' :
                                    item.severity === 'WARNING' ? 'bg-warning-light/10' : ''
                                  }`}
                                >
                                  <td className="py-3 px-4">
                                    <span className="font-mono font-medium text-sm">{item.account_code}</span>
                                  </td>
                                  <td className="py-3 px-4">
                                    <span className="font-medium">{item.account_name}</span>
                                  </td>
                                  <td className="text-right py-3 px-4 font-mono text-sm">
                                    ${(item.previous_period_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </td>
                                  <td className="text-right py-3 px-4 font-mono text-sm">
                                    ${(item.current_period_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </td>
                                  <td className={`text-right py-3 px-4 font-mono text-sm font-semibold ${
                                    item.is_favorable ? 'text-success' : 'text-danger'
                                  }`}>
                                    {item.variance_amount >= 0 ? '+' : ''}{item.variance_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </td>
                                  <td className={`text-right py-3 px-4 font-mono text-sm font-semibold ${
                                    item.is_favorable ? 'text-success' : 'text-danger'
                                  }`}>
                                    {item.variance_percentage >= 0 ? '+' : ''}{item.variance_percentage.toFixed(1)}%
                                  </td>
                                  <td className="py-3 px-4 text-center">
                                    <div className="flex items-center justify-center gap-2">
                                      {item.severity === 'URGENT' && <span className="text-purple-600">🚨</span>}
                                      {item.severity === 'CRITICAL' && <span className="text-danger">🔴</span>}
                                      {item.severity === 'WARNING' && <span className="text-warning">🟡</span>}
                                      {(item.severity === 'NORMAL' || item.severity === 'INFO') && <span className="text-success">🟢</span>}
                                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                                        item.is_favorable ? 'bg-success-light text-success' : 'bg-danger-light text-danger'
                                      }`}>
                                        {item.is_favorable ? 'Favorable' : 'Unfavorable'}
                                      </span>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="mt-4 text-sm text-text-secondary text-center">
                        Showing {periodVariance.variance_items.filter(item => {
                          const matchesSearch = !varianceSearchQuery ||
                            item.account_code.toLowerCase().includes(varianceSearchQuery.toLowerCase()) ||
                            item.account_name.toLowerCase().includes(varianceSearchQuery.toLowerCase());
                          const matchesSeverity = !varianceFilterSeverity || item.severity === varianceFilterSeverity;
                          return matchesSearch && matchesSeverity;
                        }).length} of {periodVariance.variance_items.length} accounts
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="text-text-secondary">
                        No variance data available. Run the analysis to see results.
                      </div>
                    </div>
                  )}
                </Card>
              </>
            )}
          </div>
        )}

        {activeTab === 'exit' && exitScenarios.length > 0 && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-2xl font-bold mb-4">Exit Strategy Analysis</h2>
              
              {exitScenarios.find(s => s.recommended) && (
                <Card variant="premium" className="p-6 mb-6 border-2 border-premium">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-6 h-6 text-premium" />
                    <h3 className="text-xl font-bold">⭐ RECOMMENDED STRATEGY</h3>
                  </div>
                  {(() => {
                    const recommended = exitScenarios.find(s => s.recommended)!;
                    return (
                      <div>
                        <div className="text-2xl font-bold mb-2">{recommended.name}</div>
                        <div className="grid grid-cols-3 gap-4 mb-4">
                          <div>
                            <div className="text-sm text-text-secondary">IRR</div>
                            <div className="text-xl font-bold">{recommended.irr}%</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">NPV</div>
                            <div className="text-xl font-bold">${(recommended.npv / 1000000).toFixed(2)}M</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total Return</div>
                            <div className="text-xl font-bold">${(recommended.totalReturn / 1000000).toFixed(2)}M</div>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="premium">Generate Executive Summary</Button>
                          <Button variant="primary">Schedule CFO Review</Button>
                        </div>
                      </div>
                    );
                  })()}
                </Card>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {exitScenarios.map((scenario, i) => (
                  <Card
                    key={i}
                    variant={scenario.recommended ? 'premium' : 'default'}
                    className={`p-4 ${scenario.recommended ? 'border-2 border-premium' : ''}`}
                  >
                    <div className="text-lg font-bold mb-3">{i + 1}️⃣ {scenario.name}</div>
                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between">
                        <span className="text-sm text-text-secondary">IRR:</span>
                        <span className="font-semibold">{scenario.irr}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-text-secondary">NPV:</span>
                        <span className="font-semibold">${(scenario.npv / 1000000).toFixed(2)}M</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-text-secondary">Total Return:</span>
                        <span className="font-semibold">${(scenario.totalReturn / 1000000).toFixed(2)}M</span>
                      </div>
                    </div>
                    <div className="text-sm">
                      <div className="font-medium mb-1">PROS:</div>
                      <ul className="space-y-1 text-text-secondary">
                        {scenario.pros.map((pro, j) => (
                          <li key={j}>✅ {pro}</li>
                        ))}
                      </ul>
                      <div className="font-medium mb-1 mt-2">CONS:</div>
                      <ul className="space-y-1 text-text-secondary">
                        {scenario.cons.map((con, j) => (
                          <li key={j}>⚠️ {con}</li>
                        ))}
                      </ul>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'chart' && (
          <div className="space-y-6">
            {/* Header Card */}
            <Card className="p-6">
              <div className="mb-4">
                <h2 className="text-2xl font-bold mb-2">📊 Chart of Accounts</h2>
                <p className="text-text-secondary">
                  View and manage your complete chart of accounts with all account codes, categories, and types.
                </p>
              </div>
              <Button variant="primary" onClick={handleViewChartOfAccounts}>
                View Full Chart of Accounts
              </Button>
            </Card>

            {/* Chart of Accounts Content - Displayed Inline */}
            {showChartOfAccounts && (
              <>
                {/* Summary Cards */}
                {chartSummary && (
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Account Summary</h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      {Object.entries(chartSummary.by_type).map(([type, count]) => (
                        <div key={type} className="p-4 bg-background rounded-lg border border-border">
                          <div className="text-sm text-text-secondary mb-1 capitalize">{type}</div>
                          <div className="text-2xl font-bold">{count}</div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 pt-4 border-t border-border">
                      <div className="flex gap-6 text-sm">
                        <div>
                          <span className="text-text-secondary">Total Accounts:</span>
                          <span className="ml-2 font-semibold">{chartSummary.total_accounts}</span>
                        </div>
                        <div>
                          <span className="text-text-secondary">Active:</span>
                          <span className="ml-2 font-semibold text-success">{chartSummary.active_accounts}</span>
                        </div>
                        <div>
                          <span className="text-text-secondary">Calculated:</span>
                          <span className="ml-2 font-semibold text-info">{chartSummary.calculated_accounts}</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Search and Filter Card */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Search & Filter</h3>
                  <div className="flex gap-4">
                    <input
                      type="text"
                      placeholder="Search by account code or name..."
                      value={chartSearchQuery}
                      onChange={(e) => setChartSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && loadChartOfAccounts()}
                      className="flex-1 px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                    />
                    <select
                      value={chartFilterType}
                      onChange={(e) => setChartFilterType(e.target.value)}
                      className="px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                    >
                      <option value="">All Types</option>
                      <option value="asset">Asset</option>
                      <option value="liability">Liability</option>
                      <option value="equity">Equity</option>
                      <option value="income">Income</option>
                      <option value="expense">Expense</option>
                    </select>
                    <Button variant="info" onClick={loadChartOfAccounts}>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Refresh
                    </Button>
                  </div>
                </Card>

                {/* Accounts Table Card */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">All Accounts</h3>
                  {loadingChart ? (
                    <div className="text-center py-8">
                      <div className="text-text-secondary">Loading chart of accounts...</div>
                    </div>
                  ) : chartOfAccounts.length > 0 ? (
                    <div>
                      <div className="overflow-x-auto border border-border rounded-lg">
                        <table className="w-full">
                          <thead className="bg-background border-b-2 border-border">
                            <tr>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Code</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Account Name</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Type</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Category</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Subcategory</th>
                              <th className="text-left py-3 px-4 text-sm font-semibold">Document Types</th>
                              <th className="text-center py-3 px-4 text-sm font-semibold">Calculated</th>
                            </tr>
                          </thead>
                          <tbody>
                            {chartOfAccounts.map((account) => (
                              <tr
                                key={account.id}
                                className={`border-b border-border hover:bg-background transition-colors ${
                                  account.is_calculated ? 'bg-info-light/10' : ''
                                }`}
                              >
                                <td className="py-3 px-4">
                                  <span className="font-mono font-medium text-sm">{account.account_code}</span>
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex flex-col">
                                    <span className="font-medium">{account.account_name}</span>
                                    {account.parent_account_code && (
                                      <span className="text-xs text-text-tertiary">
                                        Parent: {account.parent_account_code}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="py-3 px-4">
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                                    account.account_type === 'asset' ? 'bg-success-light text-success' :
                                    account.account_type === 'liability' ? 'bg-danger-light text-danger' :
                                    account.account_type === 'equity' ? 'bg-info-light text-info' :
                                    account.account_type === 'income' ? 'bg-premium-light text-premium' :
                                    account.account_type === 'expense' ? 'bg-warning-light text-warning' :
                                    'bg-background text-text-secondary'
                                  }`}>
                                    {account.account_type}
                                  </span>
                                </td>
                                <td className="py-3 px-4 text-sm text-text-secondary">
                                  {account.category || '-'}
                                </td>
                                <td className="py-3 px-4 text-sm text-text-secondary">
                                  {account.subcategory || '-'}
                                </td>
                                <td className="py-3 px-4 text-xs text-text-secondary">
                                  {account.document_types && Array.isArray(account.document_types)
                                    ? account.document_types.map(dt => dt.replace('_', ' ')).join(', ')
                                    : '-'
                                  }
                                </td>
                                <td className="py-3 px-4 text-center">
                                  {account.is_calculated ? (
                                    <span className="text-info" title={account.calculation_formula || ''}>
                                      <Calculator className="w-4 h-4 inline" />
                                    </span>
                                  ) : (
                                    <span className="text-text-tertiary">-</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="mt-4 text-sm text-text-secondary text-center">
                        Showing {chartOfAccounts.length} of {chartSummary?.total_accounts || chartOfAccounts.length} accounts
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="text-text-secondary">
                        No accounts found. Try adjusting your search or filters.
                      </div>
                    </div>
                  )}
                </Card>
              </>
            )}
          </div>
        )}

        {activeTab === 'reconciliation' && (
          <div className="space-y-6">
            {/* Header */}
            <Card className="p-6">
              <div className="mb-4">
                <h2 className="text-2xl font-bold mb-2">📊 Financial Reconciliation</h2>
              </div>
            </Card>

            {/* Selection Panel */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Select Document to Reconcile</h3>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Property</label>
                  <select
                    value={selectedProperty?.property_code || ''}
                    onChange={(e) => {
                      const prop = properties.find(p => p.property_code === e.target.value);
                      setSelectedProperty(prop || null);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    disabled={reconciliationLoading}
                  >
                    <option value="">Select property...</option>
                    {properties.map((p) => (
                      <option key={p.id} value={p.property_code}>
                        {p.property_code} - {p.property_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
                  <input
                    type="number"
                    value={reconciliationYear}
                    onChange={(e) => setReconciliationYear(parseInt(e.target.value))}
                    min="2020"
                    max="2030"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    disabled={reconciliationLoading}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Month</label>
                  <select
                    value={reconciliationMonth}
                    onChange={(e) => setReconciliationMonth(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    disabled={reconciliationLoading}
                  >
                    {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                      <option key={month} value={month}>
                        {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
                  <select
                    value={reconciliationDocType}
                    onChange={(e) => setReconciliationDocType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    disabled={reconciliationLoading}
                  >
                    <option value="balance_sheet">📊 Balance Sheet</option>
                    <option value="income_statement">💰 Income Statement</option>
                    <option value="cash_flow">💵 Cash Flow</option>
                    <option value="rent_roll">🏠 Rent Roll</option>
                    <option value="mortgage_statement">🏦 Mortgage Statement</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <Button
                    variant="primary"
                    onClick={handleStartReconciliation}
                    disabled={reconciliationLoading || !selectedProperty}
                    className="w-full"
                  >
                    {reconciliationLoading ? 'Loading...' : 'Start Reconciliation'}
                  </Button>
                </div>
              </div>
            </Card>

            {/* Active Reconciliation Display */}
            {activeReconciliation && (
              <div className="space-y-6">
                {/* Header and Summary */}
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold mb-2">🔄 Reconciliation Results</h3>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>
                          <strong>Property:</strong> {activeReconciliation.property.name} ({activeReconciliation.property.code})
                        </div>
                        <div>
                          <strong>Period:</strong> {new Date(2000, activeReconciliation.period.month - 1).toLocaleString('default', { month: 'long' })} {activeReconciliation.period.year}
                        </div>
                        <div>
                          <strong>Document:</strong> {activeReconciliation.document_type.replace('_', ' ').toUpperCase()}
                        </div>
                        <div>
                          <strong>PDF File:</strong> {availableDocuments.find(d => 
                            d.property_id === activeReconciliation.property.id &&
                            d.document_type === activeReconciliation.document_type &&
                            d.period_year === activeReconciliation.period.year &&
                            d.period_month === activeReconciliation.period.month
                          )?.file_name || 'Original PDF Document'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold">{activeReconciliation.comparison.total_records}</div>
                      <div className="text-sm text-gray-600">Total Records</div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-green-700">{activeReconciliation.comparison.matches}</div>
                      <div className="text-sm text-gray-600">Matches</div>
                    </div>
                    <div className="bg-red-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-red-700">{activeReconciliation.comparison.differences}</div>
                      <div className="text-sm text-gray-600">Differences</div>
                    </div>
                    <div className="bg-yellow-50 p-4 rounded-lg">
                      <div className="text-2xl font-bold text-yellow-700">
                        {activeReconciliation.comparison.total_records > 0
                          ? Math.round((activeReconciliation.comparison.matches / activeReconciliation.comparison.total_records) * 100)
                          : 0}%
                      </div>
                      <div className="text-sm text-gray-600">Match Rate</div>
                    </div>
                  </div>
                </Card>

                {/* Comparison Table */}
                {activeReconciliation.comparison.records && activeReconciliation.comparison.records.length > 0 && (
                  <Card className="p-6">
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold mb-2">📊 Detailed Comparison Table</h3>
                      <p className="text-sm text-gray-600">
                        Compare the values from the PDF file with the data stored in the database. 
                        <span className="inline-block ml-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Green rows</span> indicate exact matches, 
                        <span className="inline-block ml-2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded">Red rows</span> indicate differences.
                      </p>
                    </div>
                    <div className="overflow-x-auto border border-gray-200 rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                          <tr>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Account Code</th>
                            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Account Name</th>
                            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">PDF Value</th>
                            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Database Value</th>
                            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Difference</th>
                            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Difference %</th>
                            <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200">Status</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {activeReconciliation.comparison.records.map((record, index) => {
                            const isMatch = record.match_status === 'exact' || record.match_status === 'tolerance';
                            const hasDifference = record.match_status === 'mismatch' || (record.difference !== null && record.difference !== 0 && record.match_status !== 'exact');
                            
                            return (
                              <tr 
                                key={index} 
                                className={`transition-colors duration-150 ${
                                  hasDifference ? 'bg-red-50 hover:bg-red-100' : 
                                  isMatch ? 'bg-green-50 hover:bg-green-100' : 
                                  'hover:bg-gray-50'
                                }`}
                              >
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 border-r border-gray-100">
                                  {record.account_code || 'N/A'}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-700 border-r border-gray-100">
                                  {record.account_name || 'N/A'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-gray-900 border-r border-gray-100">
                                  {record.pdf_value !== null && record.pdf_value !== undefined 
                                    ? new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD',
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                      }).format(record.pdf_value)
                                    : <span className="text-gray-400 italic">N/A</span>}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-semibold text-gray-900 border-r border-gray-100">
                                  {record.db_value !== null && record.db_value !== undefined 
                                    ? new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD',
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                      }).format(record.db_value)
                                    : <span className="text-gray-400 italic">N/A</span>}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-semibold border-r border-gray-100 ${
                                  hasDifference ? 'text-red-700' : 'text-gray-700'
                                }`}>
                                  {record.difference !== null && record.difference !== undefined && record.difference !== 0
                                    ? new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD',
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                      }).format(Math.abs(record.difference))
                                    : <span className="text-gray-400">—</span>}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm text-right border-r border-gray-100 ${
                                  hasDifference ? 'text-red-700 font-semibold' : 'text-gray-600'
                                }`}>
                                  {record.difference_percent !== null && record.difference_percent !== undefined && record.difference_percent !== 0
                                    ? `${record.difference_percent.toFixed(2)}%`
                                    : <span className="text-gray-400">—</span>}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                                    record.match_status === 'exact' ? 'bg-green-100 text-green-800 border border-green-200' :
                                    record.match_status === 'tolerance' ? 'bg-yellow-100 text-yellow-800 border border-yellow-200' :
                                    record.match_status === 'mismatch' ? 'bg-red-100 text-red-800 border border-red-200' :
                                    record.match_status === 'missing_pdf' ? 'bg-orange-100 text-orange-800 border border-orange-200' :
                                    record.match_status === 'missing_db' ? 'bg-purple-100 text-purple-800 border border-purple-200' :
                                    'bg-gray-100 text-gray-800 border border-gray-200'
                                  }`}>
                                    {record.match_status === 'exact' ? '✅ Exact Match' :
                                     record.match_status === 'tolerance' ? '⚠️ Within Tolerance' :
                                     record.match_status === 'mismatch' ? '❌ Mismatch' :
                                     record.match_status === 'missing_pdf' ? '📄 Missing in PDF' :
                                     record.match_status === 'missing_db' ? '💾 Missing in DB' :
                                     record.match_status || 'Unknown'}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                )}
              </div>
            )}



            {/* Empty State */}
            {!activeReconciliation && reconciliationSessions.length === 0 && !reconciliationLoading && (
              <Card className="p-6">
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">
                    No reconciliation sessions found. Start a new reconciliation by selecting a property, period, and document type above.
                  </p>
                  <div className="flex gap-4 justify-center mb-4">
                    <Button
                      variant="primary"
                      onClick={() => window.location.hash = 'reconciliation'}
                    >
                      Open Full Reconciliation Page
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => window.location.hash = 'forensic-reconciliation'}
                      className="bg-purple-600 text-white hover:bg-purple-700 border-purple-600"
                    >
                      🔍 Open Forensic Reconciliation (Elite)
                    </Button>
                  </div>
                  <div className="mt-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <p className="text-sm font-semibold text-purple-900 mb-2">✨ Forensic Reconciliation Elite Features:</p>
                    <ul className="text-xs text-purple-700 text-left max-w-2xl mx-auto space-y-1">
                      <li>• Materiality-based reconciliation with dynamic thresholds</li>
                      <li>• Tiered exception management (Auto-close, Auto-suggest, Route, Escalate)</li>
                      <li>• Enhanced matching with Chart of Accounts semantic mapping</li>
                      <li>• Configurable health scores per persona (Controller, Auditor, Analyst, Investor)</li>
                      <li>• Real estate domain-specific anomaly detection</li>
                      <li>• Comprehensive explainability (Why Flagged, What Would Resolve, What Changed)</li>
                    </ul>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
      
      {/* Mortgage Detail Modal */}
      {selectedMortgageId && (
        <MortgageDetail
          mortgageId={selectedMortgageId}
          onClose={() => setSelectedMortgageId(null)}
        />
      )}
    </div>
  );
}
