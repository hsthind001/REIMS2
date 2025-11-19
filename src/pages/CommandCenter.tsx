import { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  Plus, 
  Upload, 
  MessageSquare,
  FileText,
  Building2,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { MetricCard, Card, Button, ProgressBar } from '../components/design-system';
import { propertyService } from '../lib/property';
import { DocumentUpload } from '../components/DocumentUpload';
import type { Property } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface PortfolioHealth {
  score: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
  totalValue: number;
  totalNOI: number;
  avgOccupancy: number;
  portfolioIRR: number;
  alertCount: {
    critical: number;
    warning: number;
    info: number;
  };
  lastUpdated: Date;
}

interface CriticalAlert {
  id: number;
  property: {
    id: number;
    name: string;
    code: string;
  };
  type: string;
  severity: 'critical' | 'high' | 'medium';
  metric: {
    name: string;
    current: number;
    threshold: number;
    impact: string;
  };
  recommendation: string;
  createdAt: Date;
}

interface PropertyPerformance {
  id: number;
  name: string;
  code: string;
  value: number;
  noi: number;
  dscr: number;
  ltv: number;
  occupancy: number;
  status: 'critical' | 'warning' | 'good';
  trends: {
    noi: number[];
  };
}

interface AIInsight {
  id: string;
  type: 'risk' | 'opportunity' | 'market' | 'operational';
  title: string;
  description: string;
  confidence: number;
}

export default function CommandCenter() {
  const [portfolioHealth, setPortfolioHealth] = useState<PortfolioHealth | null>(null);
  const [criticalAlerts, setCriticalAlerts] = useState<CriticalAlert[]>([]);
  const [propertyPerformance, setPropertyPerformance] = useState<PropertyPerformance[]>([]);
  const [aiInsights, setAIInsights] = useState<AIInsight[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showPropertyModal, setShowPropertyModal] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);

  useEffect(() => {
    loadDashboardData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadDashboardData, 300000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load properties
      const propertiesData = await propertyService.getAllProperties();
      setProperties(propertiesData);

      // Load portfolio health
      await loadPortfolioHealth(propertiesData);
      
      // Load critical alerts
      await loadCriticalAlerts();
      
      // Load property performance
      await loadPropertyPerformance(propertiesData);
      
      // Load AI insights
      await loadAIInsights();
      
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioHealth = async (_properties: Property[]) => {
    try {
      // Calculate portfolio health from properties and metrics
      const metricsSummary = await fetch(`${API_BASE_URL}/metrics/summary`, {
        credentials: 'include'
      }).then(r => r.ok ? r.json() : []);

      let totalValue = 0;
      let totalNOI = 0;
      let totalOccupancy = 0;
      let occupancyCount = 0;
      let criticalAlerts = 0;
      let warningAlerts = 0;

      metricsSummary.forEach((m: any) => {
        if (m.total_assets) totalValue += m.total_assets;
        if (m.net_income) totalNOI += m.net_income;
        if (m.occupancy_rate) {
          totalOccupancy += m.occupancy_rate;
          occupancyCount++;
        }
      });

      const avgOccupancy = occupancyCount > 0 ? totalOccupancy / occupancyCount : 0;
      
      // Calculate health score (0-100)
      let score = 85; // Base score
      if (avgOccupancy < 85) score -= 15;
      if (avgOccupancy < 80) score -= 10;
      if (criticalAlerts > 0) score -= criticalAlerts * 5;
      if (warningAlerts > 0) score -= warningAlerts * 2;
      score = Math.max(0, Math.min(100, score));

      const status = score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'poor';

      setPortfolioHealth({
        score,
        status,
        totalValue,
        totalNOI,
        avgOccupancy,
        portfolioIRR: 14.2, // Would come from exit strategy analysis
        alertCount: {
          critical: criticalAlerts,
          warning: warningAlerts,
          info: 0
        },
        lastUpdated: new Date()
      });
    } catch (err) {
      console.error('Failed to load portfolio health:', err);
    }
  };

  const loadCriticalAlerts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts?priority=critical`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        const alerts = (data.alerts || data).slice(0, 5); // Top 5 critical
        setCriticalAlerts(alerts.map((a: any) => ({
          id: a.id,
          property: {
            id: a.property_id,
            name: a.property_name || 'Unknown',
            code: a.property_code || ''
          },
          type: a.alert_type || 'risk',
          severity: a.severity || 'critical',
          metric: {
            name: a.metric_name || 'DSCR',
            current: a.actual_value || 0,
            threshold: a.threshold_value || 1.25,
            impact: a.impact || 'Risk identified'
          },
          recommendation: a.recommendation || 'Review immediately',
          createdAt: new Date(a.created_at || Date.now())
        })));
      }
    } catch (err) {
      console.error('Failed to load critical alerts:', err);
    }
  };

  const loadPropertyPerformance = async (properties: Property[]) => {
    try {
      const performance: PropertyPerformance[] = [];
      
      for (const property of properties.slice(0, 10)) {
        try {
          const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=1`, {
            credentials: 'include'
          });
          const metrics = metricsRes.ok ? await metricsRes.json() : [];
          const metric = metrics.find((m: any) => m.property_code === property.property_code);
          
          if (metric) {
            // Generate mock trend data (12 months)
            const noiTrend = Array.from({ length: 12 }, () => 
              (metric.net_income || 0) * (0.9 + Math.random() * 0.2)
            );

            const dscr = 1.0 + Math.random() * 0.3; // Mock DSCR
            const status = dscr < 1.25 ? 'critical' : dscr < 1.35 ? 'warning' : 'good';

            performance.push({
              id: property.id,
              name: property.property_name,
              code: property.property_code,
              value: metric.total_assets || 0,
              noi: metric.net_income || 0,
              dscr,
              ltv: 52.8, // Mock
              occupancy: metric.occupancy_rate || 0,
              status,
              trends: { noi: noiTrend }
            });
          }
        } catch (err) {
          console.error(`Failed to load metrics for ${property.property_code}:`, err);
        }
      }
      
      setPropertyPerformance(performance);
    } catch (err) {
      console.error('Failed to load property performance:', err);
    }
  };

  const loadAIInsights = async () => {
    try {
      // Mock AI insights - would come from NLQ API
      setAIInsights([
        {
          id: '1',
          type: 'risk',
          title: 'DSCR Stress Pattern Detected',
          description: '3 properties showing DSCR stress - refinancing window optimal',
          confidence: 0.85
        },
        {
          id: '2',
          type: 'market',
          title: 'Market Cap Rates Trending Up',
          description: 'Market cap rates trending up 0.3% - favorable for sales',
          confidence: 0.78
        },
        {
          id: '3',
          type: 'operational',
          title: 'Q1 2026 Lease Expirations',
          description: '45 lease expirations Q1 2026 - start negotiations NOW',
          confidence: 0.92
        }
      ]);
    } catch (err) {
      console.error('Failed to load AI insights:', err);
    }
  };


  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <CheckCircle className="w-5 h-5 text-success" />;
      case 'good': return <CheckCircle className="w-5 h-5 text-info" />;
      case 'fair': return <AlertTriangle className="w-5 h-5 text-warning" />;
      case 'poor': return <AlertTriangle className="w-5 h-5 text-danger" />;
      default: return null;
    }
  };

  if (loading && !portfolioHealth) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-info" />
          <p className="text-text-secondary">Loading Command Center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section - Portfolio Health Score */}
      <div className="bg-hero-gradient text-white py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold mb-2">🏢 Portfolio Health Score</h1>
              <p className="text-white/80">Last Updated: {portfolioHealth?.lastUpdated.toLocaleTimeString() || 'Just now'}</p>
            </div>
            <div className="text-right">
              <div className="text-6xl font-bold mb-2">
                {portfolioHealth?.score || 0}/100
              </div>
              <div className="flex items-center gap-2 text-xl">
                {getStatusIcon(portfolioHealth?.status || 'fair')}
                <span className="uppercase font-semibold">{portfolioHealth?.status || 'FAIR'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Portfolio Value"
            value={portfolioHealth?.totalValue || 0}
            change={5.2}
            trend="up"
            icon="💰"
            variant="success"
            sparkline={[65, 68, 70, 69, 72, 71, 73, 75, 74, 76, 75, 77]}
          />
          <MetricCard
            title="Portfolio NOI"
            value={portfolioHealth?.totalNOI || 0}
            change={3.8}
            trend="up"
            icon="📊"
            variant="info"
            sparkline={[2.8, 2.9, 2.85, 2.9, 2.95, 2.92, 2.98, 3.0, 2.98, 3.02, 3.0, 3.05]}
          />
          <MetricCard
            title="Average Occupancy"
            value={`${(portfolioHealth?.avgOccupancy || 0).toFixed(1)}%`}
            change={-1.2}
            trend="down"
            icon="🏘️"
            variant="warning"
            sparkline={[92, 91.5, 91.8, 91.2, 91.0, 90.8, 91.0, 90.5, 90.8, 91.0, 90.5, 91.0]}
          />
          <MetricCard
            title="Portfolio IRR"
            value={`${portfolioHealth?.portfolioIRR || 0}%`}
            change={2.1}
            trend="up"
            icon="📈"
            variant="success"
            sparkline={[12, 12.5, 13, 12.8, 13.2, 13.5, 13.8, 14, 13.9, 14.1, 14.0, 14.2]}
          />
        </div>

        {/* Critical Alerts Section */}
        {criticalAlerts.length > 0 && (
          <Card variant="danger" className="mb-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <AlertTriangle className="w-6 h-6 text-danger" />
                Critical Alerts ({criticalAlerts.length} Require Immediate Action)
              </h2>
            </div>
            <div className="space-y-4">
              {criticalAlerts.map((alert) => (
                <Card key={alert.id} variant="danger" className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-danger font-bold">🔴</span>
                        <span className="font-semibold text-lg">
                          {alert.property.name} - {alert.metric.name} {alert.metric.current}
                        </span>
                        <span className="text-sm text-text-secondary">
                          (Below {alert.metric.threshold})
                        </span>
                      </div>
                      <p className="text-text-secondary mb-2">
                        <strong>Impact:</strong> {alert.metric.impact}
                      </p>
                      <p className="text-text-secondary mb-3">
                        <strong>Action:</strong> {alert.recommendation}
                      </p>
                      <ProgressBar
                        value={((alert.metric.current / alert.metric.threshold) * 100)}
                        max={100}
                        variant="danger"
                        showLabel
                        label={`${Math.round((alert.metric.current / alert.metric.threshold) * 100)}% to compliance`}
                      />
                    </div>
                    <div className="ml-4 flex gap-2">
                      <Button variant="info" size="sm">View Financials</Button>
                      <Button variant="premium" size="sm">AI Recommendations</Button>
                      <Button variant="success" size="sm">Acknowledge</Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Portfolio Performance Grid */}
          <div className="lg:col-span-2">
            <Card className="p-6">
              <h2 className="text-2xl font-bold mb-4">Portfolio Performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-semibold">Property</th>
                      <th className="text-right py-3 px-4 font-semibold">Value</th>
                      <th className="text-right py-3 px-4 font-semibold">NOI</th>
                      <th className="text-right py-3 px-4 font-semibold">DSCR</th>
                      <th className="text-right py-3 px-4 font-semibold">LTV</th>
                      <th className="text-right py-3 px-4 font-semibold">Trend</th>
                      <th className="text-center py-3 px-4 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {propertyPerformance.map((prop) => (
                      <tr
                        key={prop.id}
                        className={`border-b border-border hover:bg-background cursor-pointer ${
                          prop.status === 'critical' ? 'bg-danger-light/10' :
                          prop.status === 'warning' ? 'bg-warning-light/10' :
                          'bg-success-light/10'
                        }`}
                      >
                        <td className="py-3 px-4 font-medium">{prop.name}</td>
                        <td className="py-3 px-4 text-right">
                          ${(prop.value / 1000000).toFixed(1)}M
                        </td>
                        <td className="py-3 px-4 text-right">
                          ${(prop.noi / 1000).toFixed(0)}K
                        </td>
                        <td className="py-3 px-4 text-right">{prop.dscr.toFixed(2)}</td>
                        <td className="py-3 px-4 text-right">{prop.ltv.toFixed(1)}%</td>
                        <td className="py-3 px-4">
                          <div className="h-6 w-24 flex items-end gap-0.5">
                            {prop.trends.noi.slice(-12).map((val, i) => {
                              const max = Math.max(...prop.trends.noi);
                              const height = (val / max) * 100;
                              return (
                                <div
                                  key={i}
                                  className="flex-1 bg-info rounded-t"
                                  style={{ height: `${Math.max(height, 10)}%` }}
                                />
                              );
                            })}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {prop.status === 'critical' ? '🔴' :
                           prop.status === 'warning' ? '🟡' : '🟢'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* AI Insights Widget */}
          <div>
            <Card variant="premium" className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-6 h-6 text-premium" />
                <h2 className="text-2xl font-bold">AI Portfolio Insights</h2>
              </div>
              <p className="text-sm text-text-secondary mb-4">Powered by Claude AI</p>
              <div className="space-y-4">
                {aiInsights.map((insight) => (
                  <div key={insight.id} className="bg-premium-light/20 p-3 rounded-lg border border-premium/30">
                    <div className="flex items-start gap-2">
                      <span className="text-premium">🟣</span>
                      <div className="flex-1">
                        <p className="font-medium text-sm mb-1">{insight.title}</p>
                        <p className="text-xs text-text-secondary">{insight.description}</p>
                        <div className="mt-2 flex gap-2">
                          <Button variant="premium" size="sm">View Analysis</Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Floating Action Button */}
      <div className="fixed bottom-8 right-8 z-50">
        <div className="relative">
          <Button
            variant="premium"
            size="lg"
            className="rounded-full w-14 h-14 shadow-lg"
            onClick={() => setShowQuickActions(!showQuickActions)}
          >
            <Plus className="w-6 h-6" />
          </Button>
          
          {showQuickActions && (
            <div className="absolute bottom-16 right-0 space-y-2">
              <Button
                variant="primary"
                size="md"
                icon={<Upload className="w-4 h-4" />}
                onClick={() => {
                  setShowUploadModal(true);
                  setShowQuickActions(false);
                }}
              >
                Upload Document
              </Button>
              <Button
                variant="success"
                size="md"
                icon={<Building2 className="w-4 h-4" />}
                onClick={() => {
                  setShowPropertyModal(true);
                  setShowQuickActions(false);
                }}
              >
                Add Property
              </Button>
              <Button
                variant="premium"
                size="md"
                icon={<MessageSquare className="w-4 h-4" />}
                onClick={() => {
                  setShowQuickActions(false);
                  alert('Navigate to "Ask AI" from the sidebar menu');
                }}
              >
                Ask AI
              </Button>
              <Button
                variant="primary"
                size="md"
                icon={<FileText className="w-4 h-4" />}
                onClick={() => {
                  setShowQuickActions(false);
                  alert('Navigate to "Reports" from the sidebar menu');
                }}
              >
                Generate Report
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowUploadModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Upload Document</h2>
            <DocumentUpload onUploadSuccess={() => {
              setShowUploadModal(false);
              loadDashboardData();
            }} />
          </div>
        </div>
      )}

      {showPropertyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowPropertyModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Add Property</h2>
            <p className="text-text-secondary mb-4">Navigate to Properties page to add a new property</p>
            <div className="flex gap-3">
              <Button variant="primary" onClick={() => {
                setShowPropertyModal(false);
                alert('Navigate to "Properties" from the sidebar menu to add a new property');
              }}>
                Go to Properties Page
              </Button>
              <Button variant="danger" onClick={() => setShowPropertyModal(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

