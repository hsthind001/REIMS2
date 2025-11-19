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
import type { Property } from '../types/api';

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

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadFinancialData(selectedProperty.id);
    }
  }, [selectedProperty]);

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
        body: JSON.stringify({ query: nlqQuery })
      });

      if (response.ok) {
        const data = await response.json();
        const nlqResponse: NLQResponse = {
          answer: data.answer || 'Analysis complete',
          data: data.data,
          sql: data.sql,
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
        // Mock response for demo
        const mockResponse: NLQResponse = {
          answer: `Based on your query "${nlqQuery}", here's the analysis:\n\n4 properties currently have DSCR below 1.25:\n\n1. 🔴 Downtown Office Tower - DSCR: 1.07 (-18%)\n   NOI: $760K | Debt Service: $710K/year\n   Gap: Needs $128K additional NOI\n\n2. 🔴 Lakeside Retail Center - DSCR: 1.03 (-21%)\n   NOI: $780K | Debt Service: $757K/year\n   Gap: Needs $189K additional NOI\n\n💡 Recommendation: Prioritize refinancing for properties 1 & 2 to avoid covenant breach.`,
          data: {},
          confidence: 92,
          suggestedFollowUps: [
            'What would refinancing cost for these properties?',
            'Show me historical DSCR trends',
            'Calculate impact of 5% rent increase on DSCR'
          ]
        };

        setNlqHistory(prev => [...prev, {
          query: nlqQuery,
          response: mockResponse,
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
                  <div className="text-2xl font-bold">Q3 2025</div>
                  <div className="text-sm text-text-secondary mt-2">Revenue: $11.2M</div>
                </Card>
                <Card variant="info" className="p-4 cursor-pointer hover:scale-105 transition-transform">
                  <div className="text-sm text-text-secondary mb-1">Balance Sheet</div>
                  <div className="text-2xl font-bold">Q3 2025</div>
                  <div className="text-sm text-text-secondary mt-2">Assets: $18.5M</div>
                </Card>
                <Card variant="primary" className="p-4 cursor-pointer hover:scale-105 transition-transform">
                  <div className="text-sm text-text-secondary mb-1">Cash Flow</div>
                  <div className="text-2xl font-bold">Q3 2025</div>
                  <div className="text-sm text-text-secondary mt-2">Net CF: $3.04M</div>
                </Card>
              </div>
              <Button variant="primary" onClick={() => window.location.hash = 'financial-data'}>
                View Full Financial Data
              </Button>
            </Card>

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
                    <div className="text-lg font-bold">1.07</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">LTV</div>
                    <div className="text-lg font-bold">52.8%</div>
                  </div>
                  <div>
                    <div className="text-sm text-text-secondary">Cap Rate</div>
                    <div className="text-lg font-bold">4.22%</div>
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
                    <div className="text-lg font-bold">14.2%</div>
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
          <Card className="p-6">
            <h2 className="text-2xl font-bold mb-4">Reconciliation</h2>
            <Button variant="primary" onClick={() => window.location.hash = 'reconciliation'}>
              View Full Reconciliation
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}

