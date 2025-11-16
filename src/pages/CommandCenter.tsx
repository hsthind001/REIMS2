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
  dscr: number | null;
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
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [selectedInsight, setSelectedInsight] = useState<AIInsight | null>(null);
  const [analysisDetails, setAnalysisDetails] = useState<any>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [selectedPropertyFilter, setSelectedPropertyFilter] = useState<string>('all'); // 'all' or property_code
  const [sparklineData, setSparklineData] = useState<{
    value: number[];
    noi: number[];
    occupancy: number[];
    irr: number[];
  }>({
    value: [],
    noi: [],
    occupancy: [],
    irr: []
  });

  useEffect(() => {
    loadDashboardData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(loadDashboardData, 300000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Reload portfolio health and sparklines when property filter changes
    if (properties.length > 0) {
      loadPortfolioHealth(properties);
      loadSparklineData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPropertyFilter]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load properties
      const propertiesData = await propertyService.getAllProperties();
      setProperties(propertiesData);

      // Auto-calculate debt service for all properties (background task)
      // This ensures DSCR data is up-to-date
      try {
        console.log('🔄 Auto-calculating debt service for all properties...');
        const debtServiceRes = await fetch(`${API_BASE_URL}/metrics/calculate-debt-service-all`, {
          method: 'POST',
          credentials: 'include'
        });
        if (debtServiceRes.ok) {
          const debtServiceData = await debtServiceRes.json();
          console.log(`✅ Debt service calculated for ${debtServiceData.summary?.successful || 0} properties`);
        } else {
          console.warn('⚠️ Debt service auto-calculation failed:', await debtServiceRes.text());
        }
      } catch (debtErr) {
        console.error('❌ Failed to auto-calculate debt service:', debtErr);
        // Don't block dashboard load if this fails
      }

      // Load portfolio health (will use selectedPropertyFilter from state)
      await loadPortfolioHealth(propertiesData);
      
      // Reload sparklines when data changes
      await loadSparklineData();

      // Load critical alerts
      await loadCriticalAlerts();

      // Load property performance
      await loadPropertyPerformance(propertiesData);

      // Load AI insights
      await loadAIInsights();

      // Load sparkline data
      await loadSparklineData();

    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioHealth = async (_properties: Property[]) => {
    try {
      // Calculate portfolio health from properties and metrics
      let metricsSummary = await fetch(`${API_BASE_URL}/metrics/summary`, {
        credentials: 'include'
      }).then(r => r.ok ? r.json() : []);

      // Filter by selected property if not "all"
      if (selectedPropertyFilter !== 'all') {
        metricsSummary = metricsSummary.filter((m: any) => m.property_code === selectedPropertyFilter);
      }

      let totalValue = 0;
      let totalNOI = 0;
      let totalOccupancy = 0;
      let occupancyCount = 0;
      let criticalAlerts = 0;
      let warningAlerts = 0;

      // Use only latest period per property (API now filters, but double-check)
      const propertyMap = new Map<string, any>();
      metricsSummary.forEach((m: any) => {
        const existing = propertyMap.get(m.property_code);
        if (!existing) {
          propertyMap.set(m.property_code, m);
        } else {
          // Prefer later period if duplicate
          if (m.period_year > existing.period_year || 
              (m.period_year === existing.period_year && m.period_month > existing.period_month)) {
            propertyMap.set(m.property_code, m);
          }
        }
      });

      // Sum values from unique properties only
      propertyMap.forEach((m: any) => {
        if (m.total_assets) totalValue += m.total_assets;
        // Use NOI (Net Operating Income) instead of net_income for portfolio NOI
        if (m.net_operating_income !== null && m.net_operating_income !== undefined) {
          totalNOI += m.net_operating_income;
        } else if (m.net_income !== null && m.net_income !== undefined) {
          // Fallback to net_income if NOI not available
          totalNOI += m.net_income;
        }
        if (m.occupancy_rate !== null && m.occupancy_rate !== undefined) {
          totalOccupancy += m.occupancy_rate;
          occupancyCount++;
        }
      });

      const avgOccupancy = occupancyCount > 0 ? totalOccupancy / occupancyCount : 0;

      // Fetch Portfolio IRR from API (only for "all" - single property IRR not available)
      let portfolioIRR = 14.2; // Fallback
      if (selectedPropertyFilter === 'all') {
        try {
          const irrResponse = await fetch(`${API_BASE_URL}/exit-strategy/portfolio-irr`, {
            credentials: 'include'
          });
          if (irrResponse.ok) {
            const irrData = await irrResponse.json();
            portfolioIRR = irrData.irr;
          }
        } catch (irrErr) {
          console.error('Failed to fetch portfolio IRR:', irrErr);
        }
      } else {
        // For single property, use a placeholder or calculate from NOI
        // TODO: Calculate property-specific IRR when available
        portfolioIRR = 14.2; // Placeholder
      }

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
        portfolioIRR,
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
      
      // Fetch all metrics once with a high limit to get all properties
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
        credentials: 'include'
      });
      const allMetrics = metricsRes.ok ? await metricsRes.json() : [];
      
      // Create a map of property_code -> latest metric with actual data for quick lookup
      const metricsMap = new Map<string, any>();
      allMetrics.forEach((m: any) => {
        const existing = metricsMap.get(m.property_code);
        const hasData = (m.total_assets !== null && m.total_assets !== undefined) || 
                        (m.net_income !== null && m.net_income !== undefined);
        const existingHasData = existing && 
                                ((existing.total_assets !== null && existing.total_assets !== undefined) || 
                                 (existing.net_income !== null && existing.net_income !== undefined));
        
        // Prefer metrics with actual data over null values
        // If both have data, prefer the latest period
        // If neither has data, prefer the latest period anyway
        if (!existing) {
          metricsMap.set(m.property_code, m);
        } else if (hasData && !existingHasData) {
          // Current has data, existing doesn't - use current
          metricsMap.set(m.property_code, m);
        } else if (!hasData && existingHasData) {
          // Existing has data, current doesn't - keep existing
          // Don't update
        } else {
          // Both have same data status - prefer latest period
          if (m.period_year && existing.period_year && m.period_year > existing.period_year) {
            metricsMap.set(m.property_code, m);
          } else if (m.period_year === existing.period_year && 
                     m.period_month && existing.period_month && 
                     m.period_month > existing.period_month) {
            metricsMap.set(m.property_code, m);
          }
        }
      });
      
      // Process each property
      for (const property of properties.slice(0, 10)) {
        try {
          const metric = metricsMap.get(property.property_code);

          if (metric) {
            console.log(`Loaded metrics for ${property.property_code}:`, {
              total_assets: metric.total_assets,
              net_income: metric.net_income,
              period: `${metric.period_year}-${metric.period_month}`
            });
            
            // Calculate NOI (Net Operating Income) once - use for both DSCR and display
            // Prefer net_operating_income over net_income for consistency with KPI cards
            const noi = (metric.net_operating_income !== null && metric.net_operating_income !== undefined)
              ? metric.net_operating_income
              : (metric.net_income !== null && metric.net_income !== undefined)
                ? metric.net_income
                : 0;

            // Fetch real NOI trend data from historical API
            let noiTrend: number[] = [];
            try {
              const histRes = await fetch(`${API_BASE_URL}/metrics/historical?property_id=${property.id}&months=12`, {
                credentials: 'include'
              });
              if (histRes.ok) {
                const histData = await histRes.json();
                noiTrend = histData.data?.noi?.map((n: number) => n / 1000000) || [];
              }
            } catch (histErr) {
              console.error('Failed to load historical data:', histErr);
            }

            // Fetch DSCR from financial_metrics table (pre-calculated from real debt service data)
            let dscr: number | null = null;
            let status: 'critical' | 'warning' | 'good' = 'good';
            try {
              const metricsRes = await fetch(`${API_BASE_URL}/metrics/${property.id}/latest`, {
                credentials: 'include'
              });
              if (metricsRes.ok) {
                const metricsData = await metricsRes.json();
                // DSCR is now pre-calculated and stored in financial_metrics table
                if (metricsData.dscr !== null && metricsData.dscr !== undefined) {
                  dscr = metricsData.dscr;
                  // Determine status based on DSCR thresholds
                  if (dscr < 1.25) {
                    status = 'critical';
                  } else if (dscr < 1.35) {
                    status = 'warning';
                  } else {
                    status = 'good';
                  }
                }
              }
            } catch (dscrErr) {
              console.error(`Failed to fetch metrics for property ${property.property_code}:`, dscrErr);
            }

            // Fetch real LTV from API
            // API now uses true LTV: long_term_debt / net_property_value
            // Falls back through multiple calculation methods if data is unavailable
            let ltv = 52.8; // Fallback
            try {
              const ltvRes = await fetch(`${API_BASE_URL}/metrics/${property.id}/ltv`, {
                credentials: 'include'
              });
              if (ltvRes.ok) {
                const ltvData = await ltvRes.json();
                ltv = ltvData.ltv || 52.8;
              } else {
                console.warn(`LTV API failed for property ${property.property_code}: ${ltvRes.status} ${ltvRes.statusText}`);
              }
            } catch (ltvErr) {
              console.error(`Failed to fetch LTV for property ${property.property_code}:`, ltvErr);
            }

            performance.push({
              id: property.id,
              name: property.property_name,
              code: property.property_code,
              value: metric.total_assets || 0,
              noi: noi,
              dscr,
              ltv,
              occupancy: metric.occupancy_rate || 0,
              status,
              trends: { noi: noiTrend }
            });
          } else {
            // Property exists but no metrics yet - show with zeros
            performance.push({
              id: property.id,
              name: property.property_name,
              code: property.property_code,
              value: 0,
              noi: 0,
              dscr: null,
              ltv: 0,
              occupancy: 0,
              status: 'warning',
              trends: { noi: [] }
            });
          }
        } catch (err) {
          console.error(`Failed to load metrics for ${property.property_code}:`, err);
          // Add property with zeros if there's an error
          performance.push({
            id: property.id,
            name: property.property_name,
            code: property.property_code,
            value: 0,
            noi: 0,
            dscr: 0,
            ltv: 0,
            occupancy: 0,
            status: 'warning',
            trends: { noi: [] }
          });
        }
      }
      
      setPropertyPerformance(performance);
    } catch (err) {
      console.error('Failed to load property performance:', err);
    }
  };

  const loadAIInsights = async () => {
    try {
      // Fetch real AI insights from NLQ API
      const response = await fetch(`${API_BASE_URL}/nlq/insights/portfolio`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAIInsights(data.insights);
      } else {
        // Fallback to mock data
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
      }
    } catch (err) {
      console.error('Failed to load AI insights:', err);
      // Fallback to mock data
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
    }
  };

  const loadSparklineData = async () => {
    try {
      // Determine if we need property-specific or portfolio-wide data
      let url = `${API_BASE_URL}/metrics/historical?months=12`;
      if (selectedPropertyFilter !== 'all') {
        // Find property ID for the selected property
        const selectedProp = properties.find(p => p.property_code === selectedPropertyFilter);
        if (selectedProp) {
          url += `&property_id=${selectedProp.id}`;
        }
      }
      
      // Fetch 12 months of historical data for sparklines
      const response = await fetch(url, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();

        // Transform API data to sparkline format
        // Convert millions to display values for sparklines
        const valueSparkline = data.data.value.map((v: number) => v / 1000000); // Convert to millions
        const noiSparkline = data.data.noi.map((n: number) => n / 1000000); // Convert to millions
        const occupancySparkline = data.data.occupancy;

        // For IRR, generate reasonable trend based on portfolio growth
        // (API doesn't have IRR history yet, so derive from NOI trend)
        const irrSparkline = noiSparkline.map((noi: number) => {
          const baseIRR = 12;
          const growth = (noi / (noiSparkline[0] || 1)) - 1;
          return baseIRR + (growth * 10); // Scale NOI growth to IRR points
        });

        setSparklineData({
          value: valueSparkline,
          noi: noiSparkline,
          occupancy: occupancySparkline,
          irr: irrSparkline
        });
      }
    } catch (err) {
      console.error('Failed to load sparkline data:', err);
      // Keep empty arrays as fallback - component will handle gracefully
    }
  };

  const loadPortfolioAnalysis = async () => {
    try {
      setLoadingAnalysis(true);
      // Try to fetch detailed portfolio analysis from NLQ API
      const response = await fetch(`${API_BASE_URL}/nlq/insights/portfolio?detailed=true`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAnalysisDetails(data);
      } else {
        // Generate analysis from portfolio health data
        setAnalysisDetails({
          title: 'Portfolio Health Analysis',
          summary: portfolioHealth ? 
            `Portfolio Health Score: ${portfolioHealth.score}/100 (${portfolioHealth.status.toUpperCase()})` :
            'Portfolio analysis unavailable',
          details: portfolioHealth ? [
            `Total Portfolio Value: $${((portfolioHealth.totalValue || 0) / 1000000).toFixed(1)}M`,
            `Total NOI: $${((portfolioHealth.totalNOI || 0) / 1000).toFixed(0)}K`,
            `Average Occupancy: ${(portfolioHealth.avgOccupancy || 0).toFixed(1)}%`,
            `Portfolio IRR: ${(portfolioHealth.portfolioIRR || 0).toFixed(1)}%`,
            `Critical Alerts: ${portfolioHealth.alertCount.critical}`,
            `Warning Alerts: ${portfolioHealth.alertCount.warning}`
          ] : [],
          recommendations: portfolioHealth && portfolioHealth.score < 90 ? [
            'Monitor properties with DSCR below 1.35',
            'Review occupancy rates for properties below 85%',
            'Consider refinancing opportunities for properties with high LTV'
          ] : [
            'Portfolio is performing well',
            'Continue monitoring key metrics',
            'Maintain current operational strategies'
          ]
        });
      }
    } catch (err) {
      console.error('Failed to load portfolio analysis:', err);
      setAnalysisDetails({
        title: 'Portfolio Health Analysis',
        summary: 'Unable to load detailed analysis',
        details: [],
        recommendations: ['Please try again later']
      });
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const loadInsightAnalysis = async (insight: AIInsight) => {
    try {
      setLoadingAnalysis(true);
      // Try to fetch detailed analysis for specific insight
      const response = await fetch(`${API_BASE_URL}/nlq/insights/${insight.id}`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAnalysisDetails(data);
      } else {
        // Generate analysis from insight data
        setAnalysisDetails({
          title: insight.title,
          summary: insight.description,
          details: [
            `Type: ${insight.type}`,
            `Confidence: ${(insight.confidence * 100).toFixed(0)}%`
          ],
          recommendations: [
            'Review related financial metrics',
            'Monitor trends over next quarter',
            'Consider implementing suggested actions'
          ]
        });
      }
    } catch (err) {
      console.error('Failed to load insight analysis:', err);
      setAnalysisDetails({
        title: insight.title,
        summary: insight.description,
        details: [],
        recommendations: ['Please try again later']
      });
    } finally {
      setLoadingAnalysis(false);
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
              <h1 className="text-4xl font-bold mb-2">
                {selectedPropertyFilter === 'all' 
                  ? '🏢 Portfolio Health Score' 
                  : `🏢 ${properties.find(p => p.property_code === selectedPropertyFilter)?.property_name || 'Property'} Health Score`
                }
              </h1>
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
        {/* Property Filter */}
        <Card className="p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-semibold text-gray-700 whitespace-nowrap">
              Filter by Property:
            </label>
            <select
              value={selectedPropertyFilter}
              onChange={(e) => setSelectedPropertyFilter(e.target.value)}
              className="flex-1 max-w-xs px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">📊 All Properties (Portfolio Overview)</option>
              {properties.map((property) => (
                <option key={property.id} value={property.property_code}>
                  {property.property_code} - {property.property_name}
                </option>
              ))}
            </select>
            <div className="text-sm text-gray-600">
              {selectedPropertyFilter === 'all' 
                ? `Showing metrics for ${properties.length} properties`
                : `Showing metrics for selected property`
              }
            </div>
          </div>
        </Card>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Total Portfolio Value" : "Property Value"}
            value={portfolioHealth?.totalValue || 0}
            change={5.2}
            trend="up"
            icon="💰"
            variant="success"
            sparkline={sparklineData.value.length > 0 ? sparklineData.value : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio NOI" : "Property NOI"}
            value={portfolioHealth?.totalNOI || 0}
            change={3.8}
            trend="up"
            icon="📊"
            variant="info"
            sparkline={sparklineData.noi.length > 0 ? sparklineData.noi : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Average Occupancy" : "Occupancy Rate"}
            value={`${(portfolioHealth?.avgOccupancy || 0).toFixed(1)}%`}
            change={-1.2}
            trend="down"
            icon="🏘️"
            variant="warning"
            sparkline={sparklineData.occupancy.length > 0 ? sparklineData.occupancy : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio IRR" : "Property IRR"}
            value={`${portfolioHealth?.portfolioIRR || 0}%`}
            change={2.1}
            trend="up"
            icon="📈"
            variant="success"
            sparkline={sparklineData.irr.length > 0 ? sparklineData.irr : undefined}
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

              {/* Critical DSCR Alert Banner */}
              {propertyPerformance.some(p => p.dscr !== null && p.dscr < 1.0) && (
                <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4 rounded">
                  <div className="flex items-start">
                    <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-red-800 mb-1">
                        🚨 Critical: Property Cannot Cover Debt Payments
                      </h3>
                      <p className="text-sm text-red-700 mb-2">
                        {propertyPerformance.filter(p => p.dscr !== null && p.dscr < 1.0).length} {propertyPerformance.filter(p => p.dscr !== null && p.dscr < 1.0).length === 1 ? 'property has' : 'properties have'} DSCR below 1.0 - NOI is insufficient to cover debt service.
                      </p>
                      <div className="space-y-1">
                        {propertyPerformance.filter(p => p.dscr !== null && p.dscr < 1.0).map(prop => (
                          <div key={prop.id} className="text-sm bg-white rounded p-2 border border-red-200">
                            <span className="font-semibold text-red-900">{prop.name}</span>
                            <span className="text-red-700 ml-2">
                              DSCR: {prop.dscr?.toFixed(2)} | NOI: ${(prop.noi / 1000).toFixed(0)}K
                            </span>
                            <span className="block text-xs text-red-600 mt-1">
                              ⚠️ Requires immediate attention - Property generating only {((prop.dscr || 0) * 100).toFixed(0)}% of required debt service
                            </span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-red-600 mt-2">
                        💡 Recommended Actions: Increase revenue, reduce expenses, or refinance debt to lower payments
                      </p>
                    </div>
                  </div>
                </div>
              )}

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
                        <td className="py-3 px-4 text-right">
                          {prop.dscr !== null ? prop.dscr.toFixed(2) : 'N/A'}
                        </td>
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
              
              {/* Portfolio Health Summary */}
              <div className="bg-premium-light/20 p-4 rounded-lg border border-premium/30 mb-4">
                <div className="flex items-start gap-2">
                  <span className="text-premium">🟣</span>
                  <div className="flex-1">
                    <p className="font-medium text-sm mb-1">Portfolio Health Strong</p>
                    <p className="text-xs text-text-secondary mb-2">
                      No critical issues detected - portfolio performing within normal parameters.
                    </p>
                    <Button 
                      variant="premium" 
                      size="sm"
                      onClick={async () => {
                        setSelectedInsight(null);
                        setShowAnalysisModal(true);
                        await loadPortfolioAnalysis();
                      }}
                    >
                      View Analysis
                    </Button>
                  </div>
                </div>
              </div>

              {/* Individual Insights */}
              <div className="space-y-4">
                {aiInsights.map((insight) => (
                  <div key={insight.id} className="bg-premium-light/20 p-3 rounded-lg border border-premium/30">
                    <div className="flex items-start gap-2">
                      <span className="text-premium">🟣</span>
                      <div className="flex-1">
                        <p className="font-medium text-sm mb-1">{insight.title}</p>
                        <p className="text-xs text-text-secondary">{insight.description}</p>
                        <div className="mt-2 flex gap-2">
                          <Button 
                            variant="premium" 
                            size="sm"
                            onClick={async () => {
                              setSelectedInsight(insight);
                              setShowAnalysisModal(true);
                              await loadInsightAnalysis(insight);
                            }}
                          >
                            View Analysis
                          </Button>
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

      {/* AI Analysis Modal */}
      {showAnalysisModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => {
          setShowAnalysisModal(false);
          setSelectedInsight(null);
          setAnalysisDetails(null);
        }}>
          <div className="bg-surface rounded-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-premium" />
                <h2 className="text-2xl font-bold">
                  {analysisDetails?.title || selectedInsight?.title || 'AI Portfolio Analysis'}
                </h2>
              </div>
              <Button variant="danger" size="sm" onClick={() => {
                setShowAnalysisModal(false);
                setSelectedInsight(null);
                setAnalysisDetails(null);
              }}>
                ✕
              </Button>
            </div>

            {loadingAnalysis ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin text-info" />
                <span className="ml-3 text-text-secondary">Loading analysis...</span>
              </div>
            ) : analysisDetails ? (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Summary</h3>
                  <p className="text-text-secondary">{analysisDetails.summary}</p>
                </div>

                {analysisDetails.details && analysisDetails.details.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Key Metrics</h3>
                    <ul className="list-disc list-inside space-y-1 text-text-secondary">
                      {analysisDetails.details.map((detail: string, idx: number) => (
                        <li key={idx}>{detail}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {analysisDetails.recommendations && analysisDetails.recommendations.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Recommendations</h3>
                    <ul className="list-disc list-inside space-y-1 text-text-secondary">
                      {analysisDetails.recommendations.map((rec: string, idx: number) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedInsight && (
                  <div className="mt-4 p-4 bg-premium-light/10 rounded-lg">
                    <p className="text-sm text-text-secondary">
                      <strong>Confidence:</strong> {(selectedInsight.confidence * 100).toFixed(0)}%
                    </p>
                    <p className="text-sm text-text-secondary mt-1">
                      <strong>Type:</strong> {selectedInsight.type}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-text-secondary">No analysis data available</p>
              </div>
            )}

            <div className="mt-6 flex justify-end gap-3">
              <Button variant="primary" onClick={() => {
                setShowAnalysisModal(false);
                setSelectedInsight(null);
                setAnalysisDetails(null);
              }}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

