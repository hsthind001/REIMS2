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
import type { Property, DocumentUpload as DocumentUploadType } from '../types/api';
import type { FinancialDataItem, FinancialDataResponse } from '../lib/financial_data';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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
  const [selectedStatementType, setSelectedStatementType] = useState<'income_statement' | 'balance_sheet' | 'cash_flow' | null>(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [kpiDscr, setKpiDscr] = useState<number>(1.25);
  const [kpiLtv, setKpiLtv] = useState<number>(52.8);
  const [kpiCapRate, setKpiCapRate] = useState<number>(4.22);
  const [kpiIrr, setKpiIrr] = useState<number>(14.2);
  
  // Reconciliation state
  const [reconciliationSessions, setReconciliationSessions] = useState<ReconciliationSession[]>([]);
  const [reconciliationLoading, setReconciliationLoading] = useState(false);
  const [reconciliationYear, setReconciliationYear] = useState<number>(new Date().getFullYear());
  const [reconciliationMonth, setReconciliationMonth] = useState<number>(new Date().getMonth() + 1);
  const [reconciliationDocType, setReconciliationDocType] = useState<string>('balance_sheet');
  const [activeReconciliation, setActiveReconciliation] = useState<ComparisonData | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadFinancialData(selectedProperty.id);
      loadAvailableDocuments(selectedProperty.property_code);
      loadReconciliationSessions(selectedProperty.property_code);
    }
  }, [selectedProperty]); // Removed period dependencies - load all documents

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
      const varianceRes = await fetch(`${API_BASE_URL}/variance_analysis?property_id=${propertyId}`, {
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
            setKpiLtv(ltvData.ltv || 52.8);

            // Calculate DSCR from LTV data
            const loanAmount = ltvData.loan_amount || 0;
            const annualDebtService = loanAmount * 0.08;
            if (annualDebtService > 0 && propertyMetric?.net_income) {
              setKpiDscr(propertyMetric.net_income / annualDebtService);
            }
          }

          if (capRateRes.ok) {
            const capRateData = await capRateRes.json();
            setKpiCapRate(capRateData.cap_rate || 4.22);
          }

          if (irrRes.ok) {
            const irrData = await irrRes.json();
            setKpiIrr(irrData.irr || 14.2);
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
      const response = await fetch(`${API_BASE_URL}/nlq/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ question: nlqQuery })
      });

      if (response.ok) {
        const data = await response.json();
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
        // Show error instead of dummy data
        const errorData = await response.json().catch(() => ({ error: 'Failed to process query' }));
        const errorResponse: NLQResponse = {
          answer: `❌ Error: ${errorData.error || 'Unable to process your query. Please try rephrasing or check if the required data is available.'}`,
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
      const errorMessage = err.response?.data?.detail || err.message || 'Unable to start reconciliation';
      
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
        // Get summary to know total count
        const summary = await financialDataService.getSummary(doc.id);
        
        // Load ALL items
        const data = await financialDataService.getFinancialData(doc.id, {
          limit: Math.max(summary.total_items || 10000, 10000),
          skip: 0
        });
        
        // If paginated, load remaining pages
        if (data.total_items > data.items.length) {
          const allItems = [...data.items];
          let skip = data.items.length;
          
          while (allItems.length < data.total_items) {
            const nextPage = await financialDataService.getFinancialData(doc.id, {
              limit: 1000,
              skip: skip
            });
            
            allItems.push(...nextPage.items);
            skip += nextPage.items.length;
            
            if (nextPage.items.length === 0) break;
          }
          
          setFinancialData({
            ...data,
            items: allItems,
            limit: allItems.length
          });
        } else {
          setFinancialData(data);
        }
      } else {
        setFinancialData(null);
      }
    } catch (err) {
      console.error('Failed to load full financial data:', err);
      setFinancialData(null);
    } finally {
      setLoadingFinancialData(false);
    }
  };

  const handleViewFullFinancialData = async () => {
    setShowFullFinancialData(true);
    
    // Ensure documents are loaded
    if (selectedProperty && availableDocuments.length === 0) {
      await loadAvailableDocuments(selectedProperty.property_code);
    }
    
    // Auto-select first available document type
    if (availableDocuments.length > 0) {
      const firstDoc = availableDocuments.find(d => 
        (d.document_type === 'income_statement' || d.document_type === 'balance_sheet' || d.document_type === 'cash_flow') &&
        d.extraction_status === 'completed'
      ) || availableDocuments.find(d => 
        d.document_type === 'income_statement' || d.document_type === 'balance_sheet' || d.document_type === 'cash_flow'
      );
      
      if (firstDoc && (firstDoc.document_type === 'income_statement' || firstDoc.document_type === 'balance_sheet' || firstDoc.document_type === 'cash_flow')) {
        setSelectedStatementType(firstDoc.document_type);
        loadFullFinancialData(firstDoc.document_type);
      }
    }
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
        <div className="flex gap-1 border-b border-border mb-6">
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
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowFullFinancialData(false)}>
                <div className="bg-surface rounded-xl p-6 max-w-7xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold">Complete Financial Data</h2>
                    <button className="text-text-secondary hover:text-text-primary text-2xl" onClick={() => setShowFullFinancialData(false)}>×</button>
                  </div>

                  {/* Statement Type Selector */}
                  <div className="flex gap-2 mb-4 flex-wrap">
                    {(['income_statement', 'balance_sheet', 'cash_flow'] as const).map((type) => {
                      const docs = availableDocuments.filter(d => d.document_type === type);
                      const doc = docs.find(d => d.extraction_status === 'completed') || docs[0];
                      return (
                        <button
                          key={type}
                          onClick={() => {
                            setSelectedStatementType(type);
                            loadFullFinancialData(type);
                          }}
                          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                            selectedStatementType === type
                              ? 'bg-info text-white'
                              : doc
                              ? 'bg-background border border-border hover:bg-background'
                              : 'bg-background border border-border opacity-50 cursor-not-allowed'
                          }`}
                          disabled={!doc}
                          title={doc ? `${doc.extraction_status} - Upload ID: ${doc.id}` : 'No document available'}
                        >
                          {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          {doc && (
                            <span className="ml-2 text-xs">
                              ({doc.extraction_status})
                              {docs.length > 1 && ` - ${docs.length} available`}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                  
                  {/* Available Documents Info */}
                  {availableDocuments.length > 0 && (
                    <div className="mb-4 p-3 bg-info-light/20 rounded-lg">
                      <div className="text-sm font-medium mb-2">Available Documents:</div>
                      <div className="text-xs text-text-secondary space-y-1">
                        {availableDocuments
                          .filter(d => d.document_type === 'income_statement' || d.document_type === 'balance_sheet' || d.document_type === 'cash_flow')
                          .map((doc, i) => (
                            <div key={i}>
                              {doc.document_type.replace('_', ' ')} - {doc.extraction_status} (ID: {doc.id})
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Financial Data Display */}
                  {loadingFinancialData ? (
                    <div className="text-center py-8">
                      <div className="text-text-secondary">Loading complete financial document data...</div>
                      <div className="text-xs text-text-tertiary mt-2">Fetching all line items with zero data loss</div>
                    </div>
                  ) : financialData && financialData.items && financialData.items.length > 0 ? (
                    <Card className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-semibold">
                            {financialData.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} - Complete Line Items
                          </h3>
                          <p className="text-sm text-text-secondary mt-1">
                            Showing all {financialData.items.length} of {financialData.total_items} extracted line items
                          </p>
                        </div>
                        <div className="text-sm text-text-secondary">
                          {financialData.property_code} • {financialData.period_year}/{String(financialData.period_month).padStart(2, '0')}
                        </div>
                      </div>
                      
                      <div className="overflow-x-auto max-h-[500px] overflow-y-auto border border-border rounded-lg">
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
                    <Card className="p-8 text-center">
                      <div className="text-text-secondary mb-4">
                        {selectedStatementType 
                          ? `No ${selectedStatementType.replace('_', ' ')} document found.`
                          : 'Please select a statement type above.'
                        }
                      </div>
                      {availableDocuments.length > 0 && (
                        <div className="text-xs text-text-tertiary mb-4">
                          <div className="font-medium mb-2">Available documents for this property:</div>
                          <div className="space-y-1">
                            {availableDocuments
                              .filter(d => d.document_type === 'income_statement' || d.document_type === 'balance_sheet' || d.document_type === 'cash_flow')
                              .map((doc, i) => (
                                <div key={i} className="text-left">
                                  • {doc.document_type.replace('_', ' ')} - Status: {doc.extraction_status} (ID: {doc.id})
                                </div>
                              ))}
                          </div>
                          <div className="mt-3 text-text-secondary">
                            Note: Documents may be for different periods. The year/month selector is for reference only.
                          </div>
                        </div>
                      )}
                    </Card>
                  )}
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
                    <div className="text-lg font-bold">${(financialMetrics.net_income || 0) / 1000}K</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">DSCR</div>
                    <div className="text-lg font-bold">{kpiDscr.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">LTV</div>
                    <div className="text-lg font-bold">{kpiLtv.toFixed(1)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Cap Rate</div>
                    <div className="text-lg font-bold">{kpiCapRate.toFixed(2)}%</div>
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
                    <div className="text-lg font-bold">{kpiIrr.toFixed(1)}%</div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'variance' && varianceData && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-2xl font-bold mb-4">Variance Analysis - {varianceData.period}</h2>
              
              {/* Portfolio Summary */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Portfolio Summary</h3>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-4">Metric</th>
                      <th className="text-right py-2 px-4">Budget</th>
                      <th className="text-right py-2 px-4">Actual</th>
                      <th className="text-right py-2 px-4">Variance</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className={getVarianceColor(varianceData.portfolio.revenue.variance)}>
                      <td className="py-2 px-4">Total Revenue</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.revenue.budget / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.revenue.actual / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">
                        {getVarianceIcon(varianceData.portfolio.revenue.variance)} {varianceData.portfolio.revenue.variance.toFixed(1)}%
                      </td>
                    </tr>
                    <tr className={getVarianceColor(varianceData.portfolio.expenses.variance)}>
                      <td className="py-2 px-4">Total OpEx</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.expenses.budget / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.expenses.actual / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">
                        {getVarianceIcon(varianceData.portfolio.expenses.variance)} {varianceData.portfolio.expenses.variance.toFixed(1)}%
                      </td>
                    </tr>
                    <tr className={getVarianceColor(varianceData.portfolio.noi.variance)}>
                      <td className="py-2 px-4">Net Operating Income</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.noi.budget / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">${(varianceData.portfolio.noi.actual / 1000000).toFixed(2)}M</td>
                      <td className="text-right py-2 px-4">
                        {getVarianceIcon(varianceData.portfolio.noi.variance)} {varianceData.portfolio.noi.variance.toFixed(1)}%
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Property-Level Heatmap */}
              <div>
                <h3 className="text-lg font-semibold mb-3">Property-Level Variance</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 px-4">Property</th>
                        <th className="text-right py-2 px-4">Revenue Var</th>
                        <th className="text-right py-2 px-4">Expense Var</th>
                        <th className="text-right py-2 px-4">NOI Var</th>
                        <th className="text-center py-2 px-4">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {varianceData.byProperty.map((prop) => (
                        <tr key={prop.propertyId} className={getVarianceColor(prop.noi.variance)}>
                          <td className="py-2 px-4 font-medium">{prop.name}</td>
                          <td className="text-right py-2 px-4">
                            {getVarianceIcon(prop.revenue.variance)} {prop.revenue.variance.toFixed(1)}%
                          </td>
                          <td className="text-right py-2 px-4">
                            {getVarianceIcon(prop.expenses.variance)} {prop.expenses.variance.toFixed(1)}%
                          </td>
                          <td className="text-right py-2 px-4">
                            {getVarianceIcon(prop.noi.variance)} {prop.noi.variance.toFixed(1)}%
                          </td>
                          <td className="text-center py-2 px-4">
                            {prop.noi.variance > 10 ? '🔴 Monitor' : prop.noi.variance > 5 ? '🟡 Watch' : '🟢 OK'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </Card>
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
          <Card className="p-6">
            <h2 className="text-2xl font-bold mb-4">Chart of Accounts</h2>
            <Button variant="primary" onClick={() => window.location.hash = 'chart-of-accounts'}>
              View Full Chart of Accounts
            </Button>
          </Card>
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
                  <Button
                    variant="primary"
                    onClick={() => window.location.hash = 'reconciliation'}
                  >
                    Open Full Reconciliation Page
                  </Button>
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

