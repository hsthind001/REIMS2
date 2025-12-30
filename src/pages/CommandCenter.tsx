import { useState, useEffect, useCallback, useRef } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Plus,
  Upload,
  MessageSquare,
  FileText,
  Building2,
  Sparkles,
  RefreshCw,
  Pause,
  Play,
  Download
} from 'lucide-react';
import { MetricCard, Card, Button, ProgressBar } from '../components/design-system';
import { PDFViewer } from '../components/PDFViewer';
import { propertyService } from '../lib/property';
import { DocumentUpload } from '../components/DocumentUpload';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { exportPortfolioHealthToPDF, exportToCSV, exportToExcel } from '../lib/exportUtils';
import { getMetricSource, getPDFViewerData } from '../lib/metrics_source';
import { useAuth } from '../components/AuthContext';
import type { Property } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface PortfolioHealth {
  score: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
  totalValue: number;
  totalNOI: number;
  avgOccupancy: number;
  portfolioDSCR: number;
  percentageChanges?: {
    total_value_change: number;
    noi_change: number;
    occupancy_change: number;
    dscr_change: number;
  };
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
  period?: {
    id: number;
    year: number;
    month: number;
  };
  financial_period_id?: number;
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
  const { user } = useAuth();
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
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear()); // Default to current year
  const [documentMatrix, setDocumentMatrix] = useState<any>(null);
  const [loadingDocMatrix, setLoadingDocMatrix] = useState(false);
  const [latestCompleteDSCR, setLatestCompleteDSCR] = useState<any>(null);
  const [sparklineData, setSparklineData] = useState<{
    value: number[];
    noi: number[];
    occupancy: number[];
    dscr: number[];
  }>({
    value: [],
    noi: [],
    occupancy: [],
    dscr: []
  });
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [pdfViewerData, setPdfViewerData] = useState<{
    pdfUrl: string;
    highlightPage?: number;
    highlightCoords?: { x0: number; y0: number; x1: number; y1: number };
  } | null>(null);
  const [loadingPDFSource, setLoadingPDFSource] = useState(false);

  // Auto-refresh hook - we'll define loadDashboardData after helper functions
  // For now, use a placeholder that will be updated
  const loadDashboardDataRef = useRef<(() => Promise<void>) | undefined>(undefined);
  
  const { isRefreshing, isPaused, lastRefresh, pause, resume, toggle, refresh } = useAutoRefresh({
    interval: 300000, // 5 minutes
    enabled: true,
    onRefresh: () => loadDashboardDataRef.current?.() || Promise.resolve(),
    dependencies: []
  });

  // Initial load effect - will be updated after loadDashboardData is defined
  const initialLoadRef = useRef(false);

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

      // Fetch DSCR - property-specific if single property selected, portfolio if "all"
      let portfolioDSCR = 0;
      let dscrChange = 0;
      
      if (selectedPropertyFilter === 'all') {
        // Fetch Portfolio DSCR from API
        try {
          const dscrResponse = await fetch(`${API_BASE_URL}/exit-strategy/portfolio-dscr`, {
            credentials: 'include'
          });
          if (dscrResponse.ok) {
            const dscrData = await dscrResponse.json();
            portfolioDSCR = dscrData.dscr || 0;
            dscrChange = dscrData.yoy_change || 0;
          }
        } catch (dscrErr) {
          console.error('Failed to fetch portfolio DSCR:', dscrErr);
        }
      } else {
        // Get property-specific DSCR from metrics summary (already calculated)
        const metric = propertyMap.get(selectedPropertyFilter);
        if (metric) {
          // Use DSCR from metrics summary
          portfolioDSCR = metric.dscr !== null && metric.dscr !== undefined ? metric.dscr : 0;

          // TODO: Calculate dscrChange by comparing with previous period's metrics
          // For now, we'll leave dscrChange as 0 until we implement historical DSCR comparison
          dscrChange = 0;
        }
      }

      // Fetch percentage changes from API
      let percentageChanges = {
        total_value_change: 0,
        noi_change: 0,
        occupancy_change: 0,
        dscr_change: 0
      };
      
      if (selectedPropertyFilter === 'all') {
        try {
          const changesResponse = await fetch(`${API_BASE_URL}/metrics/portfolio-changes`, {
            credentials: 'include'
          });
          if (changesResponse.ok) {
            const changesData = await changesResponse.json();
            percentageChanges = {
              total_value_change: changesData.total_value_change || 0,
              noi_change: changesData.noi_change || 0,
              occupancy_change: changesData.occupancy_change || 0,
              dscr_change: changesData.dscr_change || dscrChange
            };
          }
        } catch (changesErr) {
          console.error('Failed to fetch percentage changes:', changesErr);
        }
      } else {
        // Calculate property-specific percentage changes
        const metric = propertyMap.get(selectedPropertyFilter);
        if (metric) {
          // Get previous period data for comparison
          const prevYear = metric.period_year;
          const prevMonth = metric.period_month - 1;
          const prevYearFinal = prevMonth < 1 ? prevYear - 1 : prevYear;
          const prevMonthFinal = prevMonth < 1 ? 12 : prevMonth;
          
          // Fetch previous period metrics
          try {
            const prevMetricsResponse = await fetch(`${API_BASE_URL}/metrics/summary`, {
              credentials: 'include'
            });
            if (prevMetricsResponse.ok) {
              const prevMetrics = await prevMetricsResponse.json();
              const prevMetric = prevMetrics.find((m: any) => 
                m.property_code === selectedPropertyFilter && 
                m.period_year === prevYearFinal && 
                m.period_month === prevMonthFinal
              );
              
              if (prevMetric) {
                const calcChange = (current: number, previous: number) => {
                  if (!previous || previous === 0) return 0;
                  return ((current - previous) / previous) * 100;
                };
                
                percentageChanges = {
                  total_value_change: calcChange(metric.total_assets || 0, prevMetric.total_assets || 0),
                  noi_change: calcChange(metric.net_operating_income || 0, prevMetric.net_operating_income || 0),
                  occupancy_change: calcChange(metric.occupancy_rate || 0, prevMetric.occupancy_rate || 0),
                  dscr_change: dscrChange
                };
              }
            }
          } catch (prevErr) {
            console.warn('Failed to fetch previous period metrics for comparison:', prevErr);
          }
        }
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
        portfolioDSCR,
        percentageChanges, // Store percentage changes
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
      const response = await fetch(`${API_BASE_URL}/risk-alerts?priority=critical&status=ACTIVE`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        let alerts = data.alerts || data;
        
        // Filter to show only latest period's alert per property
        // Group by property_id and keep only the most recent alert per property
        const alertsByProperty = new Map<number, any>();
        alerts.forEach((a: any) => {
          const propertyId = a.property_id;
          const existing = alertsByProperty.get(propertyId);
          
          if (!existing) {
            alertsByProperty.set(propertyId, a);
          } else {
            // Compare by period (year/month) or triggered_at
            const existingDate = new Date(existing.triggered_at || existing.created_at || 0);
            const currentDate = new Date(a.triggered_at || a.created_at || 0);
            
            // Prefer alert with more recent period or triggered_at
            if (a.financial_period_id && existing.financial_period_id) {
              // If both have period_id, prefer the one with later period
              // For now, use triggered_at as proxy (will be improved with period info)
              if (currentDate > existingDate) {
                alertsByProperty.set(propertyId, a);
              }
            } else if (currentDate > existingDate) {
              alertsByProperty.set(propertyId, a);
            }
          }
        });
        
        // Convert map back to array and take top 5
        alerts = Array.from(alertsByProperty.values())
          .sort((a: any, b: any) => {
            const dateA = new Date(a.triggered_at || a.created_at || 0).getTime();
            const dateB = new Date(b.triggered_at || b.created_at || 0).getTime();
            return dateB - dateA; // Most recent first
          })
          .slice(0, 5);
        
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
            name: a.metric_name || a.related_metric || 'DSCR',
            current: a.actual_value || 0,
            threshold: a.threshold_value || 1.25,
            impact: a.impact || 'Risk identified'
          },
          recommendation: a.recommendation || a.description || 'Review immediately',
          createdAt: new Date(a.triggered_at || a.created_at || Date.now()),
          financial_period_id: a.financial_period_id,
          period: a.period ? {
            id: a.period.id,
            year: a.period.year,
            month: a.period.month
          } : undefined
        })));
      } else if (response.status === 404) {
        // Endpoint doesn't exist yet - set empty alerts
        setCriticalAlerts([]);
      }
    } catch (err) {
      console.error('Failed to load critical alerts:', err);
      // Set empty alerts on error to prevent blocking
      setCriticalAlerts([]);
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
      
      // Process properties in parallel for better performance
      const propertyPromises = properties.slice(0, 10).map(async (property) => {
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

            // Fetch historical data for trends
            const histRes = await fetch(`${API_BASE_URL}/metrics/historical?property_id=${property.id}&months=12`, {
              credentials: 'include'
            }).catch(() => ({ ok: false }));

            // Process historical data
            let noiTrend: number[] = [];
            if (histRes.ok) {
              try {
                const histData = await histRes.json();
                noiTrend = histData.data?.noi?.map((n: number) => n / 1000000) || [];
              } catch (histErr) {
                console.error('Failed to parse historical data:', histErr);
              }
            }

            // Get DSCR from latest complete period (not just latest period)
            // This ensures we use DSCR only when all required documents are available
            let dscr: number | null = null;
            let ltv: number | null = null;
            let status: 'critical' | 'warning' | 'good' = 'good';

            try {
              const dscrResponse = await fetch(
                `${API_BASE_URL}/dscr/latest-complete/${property.id}?year=${new Date().getFullYear()}`,
                { credentials: 'include' }
              );

              if (dscrResponse.ok) {
                const dscrData = await dscrResponse.json();
                if (dscrData.dscr !== null && dscrData.dscr !== undefined) {
                  dscr = dscrData.dscr;
                }
                // Also get LTV from the same latest complete period
                if (dscrData.period && dscrData.period.id) {
                  try {
                    const ltvResponse = await fetch(
                      `${API_BASE_URL}/metrics/${property.property_code}/${dscrData.period.year}/${dscrData.period.month}`,
                      { credentials: 'include' }
                    );
                    if (ltvResponse.ok) {
                      const ltvData = await ltvResponse.json();
                      if (ltvData.ltv_ratio !== null && ltvData.ltv_ratio !== undefined) {
                        ltv = ltvData.ltv_ratio;
                      }
                    }
                  } catch (ltvErr) {
                    console.warn(`Failed to fetch LTV for ${property.property_code}`, ltvErr);
                  }
                }
              }
            } catch (dscrErr) {
              console.warn(`Failed to fetch DSCR for ${property.property_code}, falling back to metrics summary`, dscrErr);
              // Fallback to metrics summary DSCR if available
              dscr = metric.dscr !== null && metric.dscr !== undefined ? metric.dscr : null;
            }

            // Determine status based on DSCR thresholds
            if (dscr !== null) {
              status = dscr < 1.25 ? 'critical' : dscr < 1.35 ? 'warning' : 'good';
            }

            // Fallback to metrics summary LTV if not fetched from latest complete period
            if (ltv === null) {
              ltv = metric.ltv_ratio !== null && metric.ltv_ratio !== undefined ? metric.ltv_ratio : null;
            }

            return {
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
            };
          } else {
            // Property exists but no metrics yet - show with zeros
            return {
              id: property.id,
              name: property.property_name,
              code: property.property_code,
              value: 0,
              noi: 0,
              dscr: 0,
              ltv: 0,
              occupancy: 0,
              status: 'warning' as const,
              trends: { noi: [] }
            };
          }
        } catch (err) {
          console.error(`Failed to load metrics for ${property.property_code}:`, err);
          // Return property with zeros if there's an error
          return {
            id: property.id,
            name: property.property_name,
            code: property.property_code,
            value: 0,
            noi: 0,
            dscr: 0,
            ltv: 0,
            occupancy: 0,
            status: 'warning' as const,
            trends: { noi: [] }
          };
        }
      });

      // Wait for all properties to load in parallel
      const results = await Promise.all(propertyPromises);
      performance.push(...results);
      
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
        setAIInsights(data.insights || []);
      } else {
        // No fallback - show empty state if API fails
        setAIInsights([]);
      }
    } catch (err) {
      console.error('Failed to load AI insights:', err);
      // No fallback - show empty state on error
      setAIInsights([]);
    }
  };

  const handleMetricClick = async (metricType: string) => {
    // Only work for single property, not portfolio view
    if (selectedPropertyFilter === 'all') {
      return; // Don't show source for portfolio aggregates
    }

    const selectedProperty = properties.find(p => p.property_code === selectedPropertyFilter);
    if (!selectedProperty) {
      return;
    }

    setLoadingPDFSource(true);
    try {
      // Get the latest period for this property
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary`, {
        credentials: 'include'
      });
      const allMetrics = metricsRes.ok ? await metricsRes.json() : [];
      const propertyMetric = allMetrics.find((m: any) => m.property_code === selectedPropertyFilter);
      
      if (!propertyMetric || !propertyMetric.period_id) {
        alert('No financial data available for this property');
        return;
      }

      // Get source document info
      const sourceData = await getMetricSource(selectedProperty.id, metricType, propertyMetric.period_id);
      
      if (!sourceData) {
        // Try to get any document for this property/period as fallback
        const fallbackUrl = `${API_BASE_URL}/metrics/${selectedProperty.id}/source?period_id=${propertyMetric.period_id}`;
        try {
          const fallbackRes = await fetch(fallbackUrl, { credentials: 'include' });
          if (fallbackRes.ok) {
            const fallbackData = await fallbackRes.json();
            if (fallbackData.pdf_url) {
              setPdfViewerData({
                pdfUrl: fallbackData.pdf_url,
                highlightPage: undefined,
                highlightCoords: undefined
              });
              setShowPDFViewer(true);
              return;
            }
          }
        } catch (e) {
          console.error('Fallback failed:', e);
        }
        
        alert(`Source document not found for ${metricType}. This metric may be calculated from multiple sources or the data may not have been extracted yet.`);
        return;
      }

      // Show PDF even if coordinates don't exist
      if (!sourceData.pdf_url) {
        alert(`PDF document not available for ${metricType}. This metric may be calculated from multiple sources or the document may not have been uploaded yet for this property.`);
        return;
      }
      
      // Validate PDF URL format
      if (!sourceData.pdf_url.includes('/pdf-viewer/') || !sourceData.pdf_url.includes('/stream')) {
        console.error('Invalid PDF URL format:', sourceData.pdf_url);
        alert('Invalid PDF URL format. Please contact support.');
        return;
      }

      // Get PDF viewer data with highlight coordinates (if available)
      const highlightCoords = sourceData.has_coordinates && 
        sourceData.extraction_x0 !== null && 
        sourceData.extraction_y0 !== null &&
        sourceData.extraction_x1 !== null &&
        sourceData.extraction_y1 !== null
        ? {
            x0: sourceData.extraction_x0,
            y0: sourceData.extraction_y0,
            x1: sourceData.extraction_x1,
            y1: sourceData.extraction_y1
          }
        : undefined;

      // Build PDF URL with highlight coordinates as query params for backend annotation
      let pdfUrlWithHighlight = sourceData.pdf_url;
      if (highlightCoords && sourceData.page_number) {
        const params = new URLSearchParams({
          page: sourceData.page_number.toString(),
          x0: highlightCoords.x0.toString(),
          y0: highlightCoords.y0.toString(),
          x1: highlightCoords.x1.toString(),
          y1: highlightCoords.y1.toString(),
        });
        pdfUrlWithHighlight = `${sourceData.pdf_url}?${params.toString()}`;
      }
      
      // Use the PDF URL with highlight coordinates
      setPdfViewerData({
        pdfUrl: pdfUrlWithHighlight,
        highlightPage: sourceData.page_number || undefined,
        highlightCoords: highlightCoords
      });
      setShowPDFViewer(true);
      
      // Show info message if coordinates are not available
      if (!sourceData.has_coordinates) {
        console.info('PDF opened without highlight coordinates. This is normal for existing data that was extracted before coordinate tracking was added.');
        // Note: Highlighting will not work for this document, but the PDF will still display
      }
    } catch (error) {
      console.error('Error loading PDF source:', error);
      alert(`Failed to load source document: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`);
    } finally {
      setLoadingPDFSource(false);
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

        // Fetch DSCR historical data if a specific property is selected
        let dscrSparkline: number[] = [];
        if (selectedPropertyFilter !== 'all') {
          const selectedProp = properties.find(p => p.property_code === selectedPropertyFilter);
          if (selectedProp) {
            try {
              const dscrResponse = await fetch(
                `${API_BASE_URL}/metrics/${selectedProp.id}/dscr/historical?months=12`,
                { credentials: 'include' }
              );
              if (dscrResponse.ok) {
                const dscrData = await dscrResponse.json();
                dscrSparkline = dscrData.dscr_values || [];
              }
            } catch (dscrErr) {
              console.warn('Failed to load DSCR historical data:', dscrErr);
              // Continue with empty DSCR array - sparkline will handle gracefully
            }
          }
        }

        setSparklineData({
          value: valueSparkline,
          noi: noiSparkline,
          occupancy: occupancySparkline,
          dscr: dscrSparkline
        });
      }
    } catch (err) {
      console.error('Failed to load sparkline data:', err);
      // Keep empty arrays as fallback - component will handle gracefully
    }
  };

  // Load document availability matrix and DSCR for latest complete period
  const loadDocumentMatrixAndDSCR = async (propertyId: number, year: number) => {
    try {
      setLoadingDocMatrix(true);

      // Fetch document matrix
      const matrixResponse = await fetch(
        `${API_BASE_URL}/documents/availability-matrix?property_id=${propertyId}&year=${year}`,
        { credentials: 'include' }
      );

      if (matrixResponse.ok) {
        const matrixData = await matrixResponse.json();
        setDocumentMatrix(matrixData);

        // If there's a latest complete period, fetch DSCR for it
        if (matrixData.latest_complete_period) {
          const dscrResponse = await fetch(
            `${API_BASE_URL}/dscr/latest-complete/${propertyId}?year=${year}`,
            { credentials: 'include' }
          );

          if (dscrResponse.ok) {
            const dscrData = await dscrResponse.json();
            setLatestCompleteDSCR(dscrData);
          }
        } else {
          setLatestCompleteDSCR(null);
        }
      }
    } catch (err) {
      console.error('Failed to load document matrix and DSCR:', err);
    } finally {
      setLoadingDocMatrix(false);
    }
  };

  // Define loadDashboardData after all helper functions are defined
  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Load properties first (needed for other calls)
      const propertiesData = await propertyService.getAllProperties();
      setProperties(propertiesData);

      // Parallelize independent API calls for better performance
      await Promise.all([
        loadPortfolioHealth(propertiesData),
        loadCriticalAlerts(),
        loadAIInsights(),
        loadSparklineData() // Only call once
      ]);

      // Load property performance (depends on properties being loaded)
      await loadPropertyPerformance(propertiesData);

    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Assign to ref for useAutoRefresh
  loadDashboardDataRef.current = loadDashboardData;

  // Initial load
  useEffect(() => {
    if (!initialLoadRef.current) {
      initialLoadRef.current = true;
      loadDashboardData();
    }
  }, []);

  useEffect(() => {
    // Reload portfolio health and sparklines when property filter changes
    if (properties.length > 0) {
      loadPortfolioHealth(properties);
      loadSparklineData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPropertyFilter]);

  useEffect(() => {
    // Load document matrix and DSCR when property filter or year changes
    if (selectedPropertyFilter !== 'all' && properties.length > 0) {
      const selectedProperty = properties.find(p => p.property_code === selectedPropertyFilter);
      if (selectedProperty) {
        loadDocumentMatrixAndDSCR(selectedProperty.id, selectedYear);
      }
    } else {
      // Reset when showing all properties
      setDocumentMatrix(null);
      setLatestCompleteDSCR(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPropertyFilter, selectedYear, properties]);

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
            `Total NOI: $${((portfolioHealth.totalNOI || 0) / 1000).toFixed(1)}K`,
            `Average Occupancy: ${(portfolioHealth.avgOccupancy || 0).toFixed(1)}%`,
            `Portfolio DSCR: ${(portfolioHealth.portfolioDSCR || 0).toFixed(2)}`,
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
        let recommendations: string[] = [];
        
        // Enhanced recommendations based on insight type
        if (insight.id === 'market_cap_rates') {
          recommendations = [
            'Consider selling properties when market cap rates are favorable',
            'Monitor market trends to identify optimal exit timing',
            'Compare portfolio cap rates to market averages',
            'Review property valuations in light of current market conditions',
            'Evaluate refinancing vs. sale options based on cap rate trends'
          ];
        } else {
          recommendations = [
            'Review related financial metrics',
            'Monitor trends over next quarter',
            'Consider implementing suggested actions'
          ];
        }
        
        setAnalysisDetails({
          title: insight.title,
          summary: insight.description,
          details: [
            `Type: ${insight.type}`,
            `Confidence: ${(insight.confidence * 100).toFixed(0)}%`,
            insight.id === 'market_cap_rates' ? 'Market Analysis: Cap rates indicate market conditions favorable for property sales' : ''
          ].filter(Boolean),
          recommendations: recommendations
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

  // Export functions
  const handleExportPDF = () => {
    if (!portfolioHealth) {
      alert('No data to export');
      return;
    }

    exportPortfolioHealthToPDF(portfolioHealth, propertyPerformance, 'portfolio-health-report');
    setShowExportMenu(false);
  };

  const handleExportExcel = () => {
    if (propertyPerformance.length === 0) {
      alert('No property data to export');
      return;
    }

    const data = propertyPerformance.map(p => ({
      'Property': p.name,
      'Property Code': p.code,
      'Value': p.value,
      'NOI': p.noi,
      'DSCR': p.dscr,
      'LTV': p.ltv,
      'Occupancy': p.occupancy,
      'Status': p.status
    }));

    exportToExcel(data, 'portfolio-performance', 'Properties');
    setShowExportMenu(false);
  };

  const handleExportCSV = () => {
    if (propertyPerformance.length === 0) {
      alert('No property data to export');
      return;
    }

    const data = propertyPerformance.map(p => ({
      'Property': p.name,
      'Property Code': p.code,
      'Value': p.value,
      'NOI': p.noi,
      'DSCR': p.dscr,
      'LTV': p.ltv,
      'Occupancy': p.occupancy,
      'Status': p.status
    }));

    exportToCSV(data, 'portfolio-performance');
    setShowExportMenu(false);
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

  // Button handlers for critical alerts
  const handleViewFinancials = (alert: CriticalAlert) => {
    // Navigate to Financial Command page (reports page) with property filter
    // The FinancialCommand page will read the property code from URL hash
    window.location.hash = `reports?property=${alert.property.code}`;
  };

  const handleAIRecommendations = async (alert: CriticalAlert) => {
    setLoadingAnalysis(true);
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          question: `What are the recommendations for ${alert.property.name} with ${alert.metric.name} of ${alert.metric.current} (threshold: ${alert.metric.threshold})?`,
          context: {
            property_id: alert.property.id,
            alert_id: alert.id,
            metric: alert.metric.name,
            current_value: alert.metric.current,
            threshold: alert.metric.threshold
          }
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Check if query was successful
        if (!data.success) {
          // Display error in modal for better UX
          setAnalysisDetails({
            title: `AI Recommendations for ${alert.property.name}`,
            summary: data.answer || data.error || 'Unable to generate recommendations at this time.',
            details: [
              `Property: ${alert.property.name} (${alert.property.code})`,
              `Metric: ${alert.metric.name}`,
              `Current Value: ${alert.metric.current}`,
              `Threshold: ${alert.metric.threshold}`,
              `Impact: ${alert.metric.impact}`
            ],
            recommendations: [
              'The AI recommendation service is currently unavailable.',
              'Please try again later or contact support if the issue persists.'
            ]
          });
          setShowAnalysisModal(true);
          return;
        }
        
        // Successful query - display results
        setAnalysisDetails({
          title: `AI Recommendations for ${alert.property.name}`,
          summary: data.answer || data.response || data.message || 'AI analysis unavailable',
          details: [
            `Property: ${alert.property.name} (${alert.property.code})`,
            `Metric: ${alert.metric.name}`,
            `Current Value: ${alert.metric.current}`,
            `Threshold: ${alert.metric.threshold}`,
            `Impact: ${alert.metric.impact}`
          ],
          recommendations: data.recommendations || (data.answer ? [data.answer] : ['No specific recommendations available at this time.'])
        });
        setShowAnalysisModal(true);
      } else {
        const error = await response.json();
        alert(`Failed to load AI recommendations: ${error.detail || error.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to get AI recommendations:', err);
      alert('Failed to load AI recommendations. Please try again.');
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleAcknowledgeAlert = async (alert: CriticalAlert) => {
    // Get current user ID from auth context
    const currentUserId = user?.id || 1; // Fallback to 1 if not available
    
    if (!currentUserId) {
      alert('Please log in to acknowledge alerts');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${alert.id}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          acknowledged_by: currentUserId,
          notes: `Acknowledged from Command Center dashboard`
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Remove alert from list
          setCriticalAlerts(prev => prev.filter(a => a.id !== alert.id));
          // Show success message
          alert('Alert acknowledged successfully');
          // Refresh alerts to get updated list
          await loadCriticalAlerts();
        } else {
          alert(`Failed to acknowledge alert: ${data.message || 'Unknown error'}`);
        }
      } else {
        const error = await response.json();
        alert(`Failed to acknowledge alert: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      alert('Failed to acknowledge alert. Please try again.');
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
              <div className="flex items-center gap-4">
                <p className="text-white/80">
                  Last Updated: {lastRefresh.toLocaleTimeString()}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={toggle}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm"
                    title={isPaused ? 'Resume auto-refresh' : 'Pause auto-refresh'}
                  >
                    {isPaused ? (
                      <>
                        <Play className="w-4 h-4" />
                        <span>Resume</span>
                      </>
                    ) : (
                      <>
                        <Pause className="w-4 h-4" />
                        <span>Pause</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={refresh}
                    disabled={isRefreshing}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm disabled:opacity-50"
                    title="Refresh now"
                  >
                    <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
                  </button>
                  <div className="relative">
                    <button
                      onClick={() => setShowExportMenu(!showExportMenu)}
                      className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm"
                      title="Export data"
                    >
                      <Download className="w-4 h-4" />
                      <span>Export</span>
                    </button>
                    {showExportMenu && (
                      <div className="absolute top-full right-0 mt-2 bg-white text-gray-900 rounded-lg shadow-xl border border-gray-200 min-w-[160px] z-50">
                        <button
                          onClick={handleExportPDF}
                          className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 text-sm transition-colors rounded-t-lg"
                        >
                          <FileText className="w-4 h-4" />
                          Export PDF
                        </button>
                        <button
                          onClick={handleExportExcel}
                          className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 text-sm transition-colors"
                        >
                          <FileText className="w-4 h-4" />
                          Export Excel
                        </button>
                        <button
                          onClick={handleExportCSV}
                          className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2 text-sm transition-colors rounded-b-lg"
                        >
                          <FileText className="w-4 h-4" />
                          Export CSV
                        </button>
                      </div>
                    )}
                  </div>
                  {!isPaused && (
                    <span className="text-xs text-white/60">Auto-refresh: Every 5 min</span>
                  )}
                </div>
              </div>
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
        {/* Property and Year Filter */}
        <Card className="p-4 mb-6">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-4 flex-1 min-w-[300px]">
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
            </div>

            {selectedPropertyFilter !== 'all' && (
              <div className="flex items-center gap-4">
                <label className="text-sm font-semibold text-gray-700 whitespace-nowrap">
                  Year:
                </label>
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                  className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {Array.from({length: 5}, (_, i) => new Date().getFullYear() - i).map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="text-sm text-gray-600">
              {selectedPropertyFilter === 'all'
                ? `Showing metrics for ${properties.length} properties`
                : `Showing ${selectedYear} data for selected property`
              }
            </div>
          </div>
        </Card>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Total Portfolio Value" : "Property Value"}
            value={portfolioHealth?.totalValue || 0}
            change={portfolioHealth?.percentageChanges?.total_value_change || 0}
            trend={portfolioHealth?.percentageChanges?.total_value_change >= 0 ? "up" : "down"}
            icon="💰"
            variant="success"
            sparkline={sparklineData.value.length > 0 ? sparklineData.value : undefined}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('property_value') : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio NOI" : "Property NOI"}
            value={portfolioHealth?.totalNOI || 0}
            change={portfolioHealth?.percentageChanges?.noi_change || 0}
            trend={portfolioHealth?.percentageChanges?.noi_change >= 0 ? "up" : "down"}
            icon="📊"
            variant="info"
            sparkline={sparklineData.noi.length > 0 ? sparklineData.noi : undefined}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('net_operating_income') : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Average Occupancy" : "Occupancy Rate"}
            value={`${(portfolioHealth?.avgOccupancy || 0).toFixed(1)}%`}
            change={portfolioHealth?.percentageChanges?.occupancy_change || 0}
            trend={portfolioHealth?.percentageChanges?.occupancy_change >= 0 ? "up" : "down"}
            icon="🏘️"
            variant="warning"
            sparkline={sparklineData.occupancy.length > 0 ? sparklineData.occupancy : undefined}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('occupancy_rate') : undefined}
          />
          <MetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio DSCR" : "Property DSCR"}
            value={selectedPropertyFilter !== 'all' && latestCompleteDSCR?.dscr
              ? latestCompleteDSCR.dscr.toFixed(2)
              : portfolioHealth?.portfolioDSCR ? portfolioHealth.portfolioDSCR.toFixed(2) : "N/A"}
            change={portfolioHealth?.percentageChanges?.dscr_change || 0}
            trend={portfolioHealth?.percentageChanges?.dscr_change >= 0 ? "up" : "down"}
            icon="📈"
            variant="success"
            sparkline={sparklineData.dscr.length > 0 ? sparklineData.dscr : undefined}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('dscr') : undefined}
          />
        </div>

        {/* Document Availability Matrix - Only show for individual property */}
        {selectedPropertyFilter !== 'all' && documentMatrix && (
          <Card className="mb-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                📄 Document Availability Matrix - {selectedYear}
              </h2>
              {latestCompleteDSCR && latestCompleteDSCR.period && (
                <div className="flex items-center gap-4 bg-blue-50 px-4 py-2 rounded-lg">
                  <span className="text-sm font-semibold text-gray-700">
                    Latest Complete Period: {latestCompleteDSCR.period.year}-{String(latestCompleteDSCR.period.month).padStart(2, '0')}
                  </span>
                  <div className="h-6 w-px bg-gray-300"></div>
                  <div className="text-sm">
                    <span className="text-gray-600">DSCR: </span>
                    <span className={`font-bold ${
                      latestCompleteDSCR.dscr >= 1.25 ? 'text-green-600' :
                      latestCompleteDSCR.dscr >= 1.10 ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {latestCompleteDSCR.dscr ? latestCompleteDSCR.dscr.toFixed(4) : 'N/A'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {loadingDocMatrix ? (
              <div className="text-center py-8 text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
                Loading document matrix...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="border border-gray-300 px-4 py-2 text-left font-semibold">Month</th>
                      {documentMatrix.required_documents?.map((doc: string) => (
                        <th key={doc} className="border border-gray-300 px-4 py-2 text-center font-semibold text-sm">
                          {doc.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </th>
                      ))}
                      <th className="border border-gray-300 px-4 py-2 text-center font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documentMatrix.months?.map((month: any) => (
                      <tr
                        key={month.period_id}
                        className={`
                          ${month.all_available ? 'bg-green-50' : 'bg-white'}
                          ${documentMatrix.latest_complete_period?.period_id === month.period_id ? 'ring-2 ring-blue-500' : ''}
                          hover:bg-gray-50
                        `}
                      >
                        <td className="border border-gray-300 px-4 py-2 font-medium">
                          {month.month_name}
                          {documentMatrix.latest_complete_period?.period_id === month.period_id && (
                            <span className="ml-2 text-xs bg-blue-500 text-white px-2 py-0.5 rounded">
                              Latest Complete
                            </span>
                          )}
                        </td>
                        {documentMatrix.required_documents?.map((doc: string) => (
                          <td key={doc} className="border border-gray-300 px-4 py-2 text-center">
                            {month.documents[doc] ? (
                              <CheckCircle className="w-5 h-5 text-green-600 mx-auto" />
                            ) : (
                              <span className="text-gray-300 text-2xl">✗</span>
                            )}
                          </td>
                        ))}
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          {month.all_available ? (
                            <span className="inline-block px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
                              Complete
                            </span>
                          ) : (
                            <span className="inline-block px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
                              Incomplete
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {!documentMatrix.latest_complete_period && (
                  <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-yellow-800 text-sm">
                      <AlertTriangle className="w-4 h-4 inline mr-2" />
                      No complete period found for {selectedYear}. DSCR cannot be calculated until all required documents are uploaded for at least one month.
                    </p>
                  </div>
                )}

                {latestCompleteDSCR && !latestCompleteDSCR.dscr && latestCompleteDSCR.error && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-800 text-sm">
                      <AlertTriangle className="w-4 h-4 inline mr-2" />
                      DSCR Calculation Error: {latestCompleteDSCR.error}
                    </p>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}

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
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className="text-danger font-bold">🔴</span>
                        <span className="font-semibold text-lg">
                          {alert.property.name} - {alert.metric.name} {alert.metric.current}
                        </span>
                        <span className="text-sm text-text-secondary">
                          (Below {alert.metric.threshold})
                        </span>
                        {alert.period && (
                          <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded font-medium">
                            {new Date(alert.period.year, alert.period.month - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                          </span>
                        )}
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
                        label={`${Math.round((alert.metric.current / alert.metric.threshold) * 100)}% of threshold (${Math.round(((alert.metric.threshold - alert.metric.current) / alert.metric.threshold) * 100)}% below compliance)`}
                      />
                    </div>
                    <div className="ml-4 flex gap-2">
                      <Button 
                        variant="info" 
                        size="sm"
                        onClick={() => handleViewFinancials(alert)}
                      >
                        View Financials
                      </Button>
                      <Button 
                        variant="premium" 
                        size="sm"
                        onClick={() => handleAIRecommendations(alert)}
                      >
                        AI Recommendations
                      </Button>
                      <Button 
                        variant="success" 
                        size="sm"
                        onClick={() => handleAcknowledgeAlert(alert)}
                      >
                        Acknowledge
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </Card>
        )}

        {/* Portfolio Performance Section - Added spacing from KPI cards */}
        <div className="mt-10">
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
                          ${prop.value ? (prop.value / 1000000).toFixed(1) : '0.0'}M
                        </td>
                        <td className="py-3 px-4 text-right">
                          ${prop.noi ? (prop.noi / 1000).toFixed(1) : '0.0'}K
                        </td>
                        <td className="py-3 px-4 text-right">{prop.dscr ? prop.dscr.toFixed(2) : 'N/A'}</td>
                        <td className="py-3 px-4 text-right">{prop.ltv ? (prop.ltv * 100).toFixed(1) : 'N/A'}%</td>
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

              {/* AI Insights */}
              <div className="space-y-4">
                {aiInsights.length === 0 ? (
                  <div className="bg-premium-light/20 p-4 rounded-lg border border-premium/30 text-center">
                    <p className="text-sm text-text-secondary">Loading AI insights...</p>
                  </div>
                ) : (
                  aiInsights.map((insight) => (
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
                  ))
                )}
              </div>
            </Card>
          </div>
          </div>
        </div>

        {/* PDF Viewer - Inline at bottom after AI Portfolio Insights */}
        {showPDFViewer && pdfViewerData && (
          <div className="mt-8">
            <PDFViewer
              pdfUrl={pdfViewerData.pdfUrl}
              highlightPage={pdfViewerData.highlightPage}
              highlightCoords={pdfViewerData.highlightCoords}
              inline={true}
              onClose={() => {
                setShowPDFViewer(false);
                setPdfViewerData(null);
              }}
            />
          </div>
        )}
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

