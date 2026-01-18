import { useState, useEffect, useRef } from 'react';
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
  Download,
  Activity
} from 'lucide-react';
import { 
  ProgressBar,
  Card as UICard,
  MetricCard as UIMetricCard,
  Skeleton as UISkeleton,
  Button,
  Select
} from '../components/ui';
import { useToastContext } from '../hooks/ToastContext';
import { PDFViewer } from '../components/PDFViewer';
import { propertyService } from '../lib/property';
import { mortgageService } from '../lib/mortgage';
import { DocumentUpload } from '../components/DocumentUpload';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { usePortfolioMetrics } from '../hooks/usePortfolioMetrics';
import { exportPortfolioHealthToPDF, exportToCSV, exportToExcel } from '../lib/exportUtils';
import { getMetricSource } from '../lib/metrics_source';
import { useAuth } from '../components/AuthContext';
import type { Property } from '../types/api';
import './insightsHub.css';


const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface PortfolioHealth {
  score: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
  totalValue: number;
  totalNOI: number;
  avgOccupancy: number;
  portfolioDSCR: number;
  portfolioIRR?: number;
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
  dscr: number | null;
  ltv: number | null;
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
  updated_at?: string;
}

export default function InsightsHub() {
  const { user } = useAuth();
  const { success: toastSuccess, error: toastError, warning: toastWarning } = useToastContext();
  const [portfolioHealth, setPortfolioHealth] = useState<PortfolioHealth | null>(null);
  const [criticalAlerts, setCriticalAlerts] = useState<CriticalAlert[]>([]);
  const [propertyPerformance, setPropertyPerformance] = useState<PropertyPerformance[]>([]);
  const [aiInsights, setAIInsights] = useState<AIInsight[]>([]);
  const [loadingCriticalAlerts, setLoadingCriticalAlerts] = useState(false);
  const [loadingAIInsights, setLoadingAIInsights] = useState(false);
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
  // Default to 2023 (year with actual data)
  const [selectedYear, setSelectedYear] = useState<number>(2023);
  const [documentMatrix, setDocumentMatrix] = useState<any>(null);
  const [loadingDocMatrix, setLoadingDocMatrix] = useState(false);
  const [showHeroMenu, setShowHeroMenu] = useState(false);
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
  
  const { isRefreshing, isPaused, lastRefresh, toggle, refresh } = useAutoRefresh({
    interval: 300000, // 5 minutes
    enabled: true,
    onRefresh: () => loadDashboardDataRef.current?.() || Promise.resolve(),
    dependencies: []
  });

  // Initial load effect - will be updated after loadDashboardData is defined
  const initialLoadRef = useRef(false);

  // Use centralized metrics hook - replaces loadPortfolioHealth function
  const { metrics: portfolioMetrics, loading: loadingMetrics, error: metricsError } = usePortfolioMetrics(
    selectedPropertyFilter,
    selectedYear
  );

  // Transform centralized metrics to portfolioHealth state
  useEffect(() => {
    if (portfolioMetrics) {
      // Calculate health score based on metrics
      let score = 85; // Base score

      if (properties.length === 0) {
        score = 100; // Clean slate\n      } else {
        // Penalize for low occupancy
        if (portfolioMetrics.avgOccupancy < 85) score -= 15;
        if (portfolioMetrics.avgOccupancy < 80) score -= 10;
        
        // Penalize for critical alerts
        if (criticalAlerts.length > 0) score -= criticalAlerts.length * 5;
      }

      score = Math.max(0, Math.min(100, score));
      const status = score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'poor';

      setPortfolioHealth({
        score,
        status,
        totalValue: portfolioMetrics.totalValue,
        totalNOI: portfolioMetrics.totalNOI,
        avgOccupancy: portfolioMetrics.avgOccupancy,
        portfolioDSCR: portfolioMetrics.portfolioDSCR,
        percentageChanges: portfolioMetrics.percentageChanges,
        alertCount: {
          critical: criticalAlerts.length,
          warning: 0,
          info: 0
        },
        lastUpdated: new Date()
      });
    }
  }, [portfolioMetrics, properties.length, criticalAlerts.length]);

  // Display metrics error if present
  useEffect(() => {
    if (metricsError) {
      console.error('Failed to load portfolio metrics:', metricsError);
      toastError(`Failed to load metrics: ${metricsError}`);
    }
  }, [metricsError, toastError]);


  const loadCriticalAlerts = async () => {
    setLoadingCriticalAlerts(true);
    try {
      // Fetch critical alerts for the selected year
      // Use severity=CRITICAL (not priority) and optionally filter by year
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts?severity=CRITICAL&status=ACTIVE&limit=50`, {
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
        
        // Convert map back to array and show more alerts (increased from 5 to 20)
        // This allows users to see all critical issues requiring attention
        alerts = Array.from(alertsByProperty.values())
          .sort((a: any, b: any) => {
            const dateA = new Date(a.triggered_at || a.created_at || 0).getTime();
            const dateB = new Date(b.triggered_at || b.created_at || 0).getTime();
            return dateB - dateA; // Most recent first
          })
          .slice(0, 20);
        
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
    } finally {
      setLoadingCriticalAlerts(false);
    }
  };

  const loadPropertyPerformance = async (properties: Property[]) => {
    try {
      const performance: PropertyPerformance[] = [];

      // Fetch all metrics once with a high limit to get all properties
      // IMPORTANT: Include year parameter to filter metrics by selected year
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100&year=${selectedYear}`, {
        credentials: 'include'
      });
      const allMetrics = metricsRes.ok ? await metricsRes.json() : [];

      // Create a map of property_code -> metric
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
            // Prefer net_operating_income over net_income for consistency with Key Indicators
            const noi = (metric.net_operating_income !== null && metric.net_operating_income !== undefined)
              ? metric.net_operating_income
              : (metric.net_income !== null && metric.net_income !== undefined)
                ? metric.net_income
                : 0;

            // Fetch historical data for trends
            let noiTrend: number[] = [];
            try {
              const histRes = await fetch(
                `${API_BASE_URL}/metrics/historical?property_id=${property.id}&months=12`,
                { credentials: 'include' }
              );
              if (histRes.ok) {
                const histData = await histRes.json();
                noiTrend = histData.data?.noi?.map((n: number) => n / 1000000) || [];
              }
            } catch (histErr) {
              console.error('Failed to load historical data:', histErr);
            }

            // Get DSCR from latest complete period (not just latest period)
            // This ensures we use DSCR only when all required documents are available
            let dscr: number | null = null;
            let ltv: number | null = null;
            let status: 'critical' | 'warning' | 'good' = 'good';

            try {
              // Use the new mortgageService method to get latest complete DSCR
              const dscrData = await mortgageService.getLatestCompleteDSCR(property.id, selectedYear);

              if (dscrData && dscrData.dscr !== null && dscrData.dscr !== undefined) {
                dscr = dscrData.dscr;
              }

              // Also get LTV from the same latest complete period
              if (dscrData.period && dscrData.period.period_id) {
                try {
                  const ltvResponse = await fetch(
                    `${API_BASE_URL}/metrics/${property.property_code}/${dscrData.period.period_year}/${dscrData.period.period_month}`,
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
            } catch (dscrErr) {
              console.warn(`Failed to fetch DSCR for ${property.property_code}, falling back to metrics summary`, dscrErr);
            }

            // Always fall back to metrics summary if DSCR wasn't fetched from latest complete period
            if (dscr === null) {
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
      console.error('Failed to load property scorecard:', err);
    }
  };

  const loadAIInsights = async () => {
    setLoadingAIInsights(true);
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
    } finally {
      setLoadingAIInsights(false);
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
      // Get the latest period for this property (filtered by selected year)
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?year=${selectedYear}`, {
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
          try {
            const dscrData = await mortgageService.getLatestCompleteDSCR(propertyId, year);
            setLatestCompleteDSCR(dscrData);
          } catch (err) {
            console.warn('Failed to fetch latest complete DSCR:', err);
            setLatestCompleteDSCR(null);
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
        // Portfolio health is now managed by usePortfolioMetrics hook
        loadCriticalAlerts(),
        loadAIInsights(),
        loadSparklineData() // Only call once
      ]);

      // Load property scorecard (depends on properties being loaded)
      await loadPropertyPerformance(propertiesData);

      // Show success toast only on manual refresh (not on initial load)
      if (initialLoadRef.current) {
        toastSuccess('Dashboard data refreshed');
      }

    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      toastError('Failed to load dashboard data');
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
    // Reload property scorecard and sparklines when property or year filter changes
    // Portfolio health is now managed by usePortfolioMetrics hook
    if (properties.length > 0) {
      loadPropertyPerformance(properties);
      loadSparklineData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPropertyFilter, selectedYear]);

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
            `Portfolio Vitals: ${portfolioHealth.score}/100 (${portfolioHealth.status.toUpperCase()})` :
            'Portfolio analysis unavailable',
          details: portfolioHealth ? [
            `Total Portfolio Value: $${((portfolioHealth.totalValue || 0) / 1000000).toFixed(1)}M`,
            `Total NOI: $${((portfolioHealth.totalNOI || 0) / 1000).toFixed(1)}K`,
            `Average Occupancy: ${(portfolioHealth.avgOccupancy || 0).toFixed(1)}%`,
            `Portfolio DSCR: ${(portfolioHealth.portfolioDSCR || 0).toFixed(2)}`,
            `Priority Actions: ${portfolioHealth.alertCount.critical}`,
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
      toastWarning('No data to export');
      return;
    }

    try {
      exportPortfolioHealthToPDF(
        { ...portfolioHealth, portfolioIRR: portfolioHealth.portfolioIRR ?? 0 },
        propertyPerformance,
        'portfolio-health-report'
      );
      toastSuccess('PDF report exported successfully');
      setShowExportMenu(false);
    } catch (error) {
      toastError('Failed to export PDF report');
    }
  };

  const handleExportExcel = () => {
    if (propertyPerformance.length === 0) {
      toastWarning('No property data to export');
      return;
    }

    try {
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
      toastSuccess('Excel file exported successfully');
      setShowExportMenu(false);
    } catch (error) {
      toastError('Failed to export Excel file');
    }
  };

  const handleExportCSV = () => {
    if (propertyPerformance.length === 0) {
      toastWarning('No property data to export');
      return;
    }

    try {
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
      toastSuccess('CSV file exported successfully');
      setShowExportMenu(false);
    } catch (error) {
      toastError('Failed to export CSV file');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <CheckCircle className="w-5 h-5 text-success" />;
      case 'good': return <CheckCircle className="w-5 h-5 text-info" />;
      case 'fair': return <Activity className="w-5 h-5 text-white" />;
      case 'poor': return <AlertTriangle className="w-5 h-5 text-danger" />;
      default: return null;
    }
  };

  // Button handlers for critical alerts
  const handleViewFinancials = (criticalAlert: CriticalAlert) => {
    // Navigate to Financial Command page (reports page) with property filter
    // The FinancialCommand page will read the property code from URL hash
    window.location.hash = `reports?property=${criticalAlert.property.code}`;
  };

  const handleAIRecommendations = async (criticalAlert: CriticalAlert) => {
    setLoadingAnalysis(true);
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          question: `What are the recommendations for ${criticalAlert.property.name} with ${criticalAlert.metric.name} of ${criticalAlert.metric.current} (threshold: ${criticalAlert.metric.threshold})?`,
          context: {
            property_id: criticalAlert.property.id,
            alert_id: criticalAlert.id,
            metric: criticalAlert.metric.name,
            current_value: criticalAlert.metric.current,
            threshold: criticalAlert.metric.threshold
          }
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Check if query was successful
        if (!data.success) {
          // Display error in modal for better UX
          setAnalysisDetails({
            title: `AI Recommendations for ${criticalAlert.property.name}`,
            summary: data.answer || data.error || 'Unable to generate recommendations at this time.',
            details: [
              `Property: ${criticalAlert.property.name} (${criticalAlert.property.code})`,
              `Metric: ${criticalAlert.metric.name}`,
              `Current Value: ${criticalAlert.metric.current}`,
              `Threshold: ${criticalAlert.metric.threshold}`,
              `Impact: ${criticalAlert.metric.impact}`
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
          title: `AI Recommendations for ${criticalAlert.property.name}`,
          summary: data.answer || data.response || data.message || 'AI analysis unavailable',
          details: [
            `Property: ${criticalAlert.property.name} (${criticalAlert.property.code})`,
            `Metric: ${criticalAlert.metric.name}`,
            `Current Value: ${criticalAlert.metric.current}`,
            `Threshold: ${criticalAlert.metric.threshold}`,
            `Impact: ${criticalAlert.metric.impact}`
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

  const handleAcknowledgeAlert = async (criticalAlert: CriticalAlert) => {
    // Get current user ID from auth context
    const currentUserId = user?.id || 1; // Fallback to 1 if not available
    
    // Optimistic update - remove immediately
    const prevAlerts = [...criticalAlerts];
    setCriticalAlerts(prev => prev.filter(a => a.id !== criticalAlert.id));
    
    try {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${criticalAlert.id}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          acknowledged_by: currentUserId,
          notes: `Acknowledged from Command Center dashboard`
        })
      });
      
      if (response.ok) {
        toastSuccess('Alert acknowledged');
        // Refresh to ensure consistent state
        loadCriticalAlerts();
      } else {
        // Revert on failure
        setCriticalAlerts(prevAlerts);
        const error = await response.json();
        toastError(`Failed to acknowledge: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      // Revert on failure
      setCriticalAlerts(prevAlerts);
      toastError('Failed to acknowledge alert');
    }
  };

  const totalValueChange = portfolioHealth?.percentageChanges?.total_value_change ?? 0;
  const noiChange = portfolioHealth?.percentageChanges?.noi_change ?? 0;
  const occupancyChange = portfolioHealth?.percentageChanges?.occupancy_change ?? 0;
  const dscrChange = portfolioHealth?.percentageChanges?.dscr_change ?? 0;
  const criticalCount = portfolioHealth?.alertCount?.critical ?? 0;
  const warningCount = portfolioHealth?.alertCount?.warning ?? 0;
  const insightCount = portfolioHealth?.alertCount?.info ?? 0;

  if (loading && !portfolioHealth) {
    return (
      <div className="min-h-screen bg-background">
        <div className="bg-hero-gradient text-white py-12 px-6">
          <div className="max-w-7xl mx-auto space-y-4">
            <UISkeleton variant="text" style={{ width: '40%', height: '2rem' }} />
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <UISkeleton variant="text" style={{ width: '200px', height: '1rem' }} />
              <UISkeleton variant="text" style={{ width: '140px', height: '1rem' }} />
              <UISkeleton variant="text" style={{ width: '120px', height: '1rem' }} />
            </div>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[0, 1, 2, 3].map((i) => (
              <UICard key={i} variant="elevated" className="p-6">
                <UISkeleton variant="text" style={{ width: '55%', height: '1rem', marginBottom: '0.75rem' }} />
                <UISkeleton variant="text" style={{ width: '40%', height: '1.75rem', marginBottom: '0.5rem' }} />
                <UISkeleton style={{ width: '100%', height: '8px' }} />
              </UICard>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section - Portfolio Vitals */}
      <div className="bg-hero-gradient text-white px-6" style={{ paddingTop: '2.5rem', paddingBottom: '3rem' }}>
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h1 className="text-4xl font-bold">
                {selectedPropertyFilter === 'all'
                  ? '🏢 Portfolio Vitals'
                  : `🏢 ${properties.find(p => p.property_code === selectedPropertyFilter)?.property_name || 'Property'} Vitals`
                }
              </h1>
              <p className="text-white/80">
                Last updated: {lastRefresh.toLocaleTimeString()} • Auto-refresh {isPaused ? 'off' : 'on (5 min)'}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={toggle}
                  className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm"
                  title={isPaused ? 'Resume auto-refresh' : 'Pause auto-refresh'}
                >
                  {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  <span>{isPaused ? 'Resume' : 'Pause'}</span>
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
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white/10 text-sm">
                  🔴 Critical: {criticalCount}
                </span>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white/10 text-sm">
                  🟡 Warnings: {warningCount}
                </span>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white/10 text-sm">
                  🔵 Insights: {insightCount}
                </span>
              </div>
              <div className="mt-3 rounded-xl border border-white/20 bg-white/10 backdrop-blur-sm p-3 flex flex-wrap items-center gap-3 text-sm" aria-live="polite">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-danger/20 text-white font-semibold">{criticalCount}</span>
                  <div>
                    <div className="font-semibold text-white">Priority Actions</div>

                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => { window.location.hash = 'alert-rules'; }}
                    className="px-3 py-1.5 rounded-lg bg-white text-blue-600 hover:bg-blue-50 font-semibold transition-colors shadow-sm"
                  >
                    View Priority Actions
                  </button>
                  <div className="relative">
                    <button
                      onClick={() => setShowHeroMenu(!showHeroMenu)}
                      className="px-3 py-1.5 rounded-lg bg-white text-blue-600 hover:bg-blue-50 font-semibold transition-colors shadow-sm flex items-center gap-2"
                    >
                      Quick Actions
                    </button>
                    {showHeroMenu && (
                      <>
                        <div className="fixed inset-0 z-40" onClick={() => setShowHeroMenu(false)} />
                        <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-lg shadow-xl border border-gray-100 py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
                          <button
                            onClick={() => { setShowUploadModal(true); setShowHeroMenu(false); }}
                            className="w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm text-gray-700"
                          >
                            <Upload className="w-4 h-4 text-blue-500" />
                            Upload Document
                          </button>
                          <button
                            onClick={() => { setShowPropertyModal(true); setShowHeroMenu(false); }}
                            className="w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm text-gray-700"
                          >
                            <Building2 className="w-4 h-4 text-green-500" />
                            Add Property
                          </button>
                          <button
                            onClick={() => { setShowHeroMenu(false); alert('Navigate to "Ask AI" from the sidebar menu'); }}
                            className="w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm text-gray-700"
                          >
                            <MessageSquare className="w-4 h-4 text-purple-500" />
                            Ask AI
                          </button>
                          <button
                            onClick={() => { setShowHeroMenu(false); alert('Navigate to "Reports" from the sidebar menu'); }}
                            className="w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-2 text-sm text-gray-700"
                          >
                            <FileText className="w-4 h-4 text-orange-500" />
                            Generate Report
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex justify-center md:justify-end mt-6 md:mt-0 z-10 relative">
              <div className="relative w-32 h-32 shrink-0">
                <div
                  className="absolute inset-0 rounded-full"
                  style={{
                    background: `conic-gradient(#22c55e ${Math.min(portfolioHealth?.score || 0, 100)}%, rgba(255,255,255,0.1) ${Math.min(portfolioHealth?.score || 0, 100)}%)`
                  }}
                />
                <div className="absolute inset-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex flex-col items-center justify-center text-center">
                  <div className="text-xs uppercase tracking-wide text-white/70">Health</div>
                  <div className="text-3xl font-bold">{portfolioHealth?.score || 0}</div>
                  <div className="text-[10px] text-white/80">of 100</div>
                  <div className="mt-1 flex items-center gap-1 text-sm">
                    {getStatusIcon(portfolioHealth?.status || 'fair')}
                    <span className="uppercase font-semibold text-xs">{portfolioHealth?.status || 'FAIR'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Property and Year Filter */}
        <UICard variant="elevated" className="p-4 mb-6">
          <div className="flex items-center gap-6 flex-wrap w-full">
              <div className="flex-1 min-w-[300px]">
                <Select
                  label="Filter by Property"
                  value={selectedPropertyFilter}
                  onChange={(val) => setSelectedPropertyFilter(val)}
                  options={[
                    { value: 'all', label: '📊 All Properties (Portfolio Overview)' },
                    ...properties.map(p => ({
                      value: p.property_code,
                      label: `${p.property_code} - ${p.property_name}`
                    }))
                  ]}
                  searchable
                />
              </div>

              {selectedPropertyFilter !== 'all' && (
                <div className="w-48">
                  <Select
                    label="Year"
                    value={selectedYear.toString()}
                    onChange={(val) => setSelectedYear(parseInt(val))}
                    options={Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(year => ({
                      value: year.toString(),
                      label: year.toString()
                    }))}
                  />
                </div>
              )}

            <div className="text-sm text-gray-600">
              {selectedPropertyFilter === 'all'
                ? `Showing metrics for ${properties.length} properties`
                : `Showing ${selectedYear} data for selected property`
              }
            </div>
          </div>
        </UICard>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <UIMetricCard
            title={selectedPropertyFilter === 'all' ? "Total Portfolio Value" : "Property Value"}
            value={portfolioHealth?.totalValue ? `$${(portfolioHealth.totalValue / 1_000_000).toFixed(1)}M` : '$0'}
            delta={Number.isFinite(totalValueChange) ? Number(totalValueChange.toFixed(1)) : 0}
            trend={totalValueChange >= 0 ? "up" : "down"}
            status="success"
            target={portfolioHealth?.percentageChanges?.total_value_change ?? undefined}
            comparison={selectedPropertyFilter === 'all' ? 'vs last period' : 'vs prior period'}
            loading={loading}
            sparklineData={sparklineData.value}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('property_value') : undefined}
          />
          <UIMetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio NOI" : "Property NOI"}
            value={portfolioHealth?.totalNOI ? `$${(portfolioHealth.totalNOI / 1_000_000).toFixed(1)}M` : '$0'}
            delta={Number.isFinite(noiChange) ? Number(noiChange.toFixed(1)) : 0}
            trend={noiChange >= 0 ? "up" : "down"}
            status="info"
            target={portfolioHealth?.percentageChanges?.noi_change ?? undefined}
            comparison="vs last period"
            loading={loading}
            sparklineData={sparklineData.noi}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('net_operating_income') : undefined}
          />
          <UIMetricCard
            title={selectedPropertyFilter === 'all' ? "Average Occupancy" : "Occupancy Rate"}
            value={`${(portfolioHealth?.avgOccupancy || 0).toFixed(1)}%`}
            delta={Number.isFinite(occupancyChange) ? Number(occupancyChange.toFixed(1)) : 0}
            trend={occupancyChange >= 0 ? "up" : "down"}
            status="warning"
            target={portfolioHealth?.percentageChanges?.occupancy_change ?? undefined}
            comparison="vs last period"
            loading={loading}
            sparklineData={sparklineData.occupancy}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('occupancy_rate') : undefined}
          />
          <UIMetricCard
            title={selectedPropertyFilter === 'all' ? "Portfolio DSCR" : "Property DSCR"}
            value={selectedPropertyFilter !== 'all' && latestCompleteDSCR?.dscr
              ? latestCompleteDSCR.dscr.toFixed(2)
              : portfolioHealth?.portfolioDSCR ? portfolioHealth.portfolioDSCR.toFixed(2) : "N/A"}
            delta={Number.isFinite(dscrChange) ? Number(dscrChange.toFixed(2)) : 0}
            trend={dscrChange >= 0 ? "up" : "down"}
            status="success"
            target={portfolioHealth?.percentageChanges?.dscr_change ?? undefined}
            comparison="vs last period"
            loading={loading}
            sparklineData={sparklineData.dscr}
            onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('dscr') : undefined}
          />
        </div>

        {/* Document Availability Matrix - Only show for individual property */}
        {selectedPropertyFilter !== 'all' && documentMatrix && (
          <UICard variant="elevated" className="mb-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                📄 Document Availability Matrix - {selectedYear}
              </h2>
              <div className="flex items-center gap-3">
                {latestCompleteDSCR && latestCompleteDSCR.period && (
                  <div className="flex items-center gap-3 bg-blue-50 px-4 py-2 rounded-lg">
                    <span className="text-sm font-semibold text-gray-700">
                      Latest Complete: {latestCompleteDSCR.period.year}-{String(latestCompleteDSCR.period.month).padStart(2, '0')}
                    </span>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      All Docs
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
                <Button variant="primary" size="sm" icon={<Upload className="w-4 h-4" />} onClick={() => setShowUploadModal(true)}>
                  Upload Missing Docs
                </Button>
              </div>
            </div>

            {loadingDocMatrix ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(6)].map((_, idx) => (
                  <div key={idx} className="space-y-3">
                    <UISkeleton variant="text" style={{ width: '70%', height: '1rem' }} />
                    <UISkeleton style={{ width: '100%', height: '0.5rem' }} />
                    <UISkeleton style={{ width: '100%', height: '0.5rem' }} />
                    <UISkeleton style={{ width: '80%', height: '0.5rem' }} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {documentMatrix.months && (
                  <div className="flex flex-col gap-3">
                    {(() => {
                      const totalMonths = documentMatrix.months.length;
                      const completeMonths = documentMatrix.months.filter((m: any) => m.all_available).length;
                      const progress = totalMonths ? Math.round((completeMonths / totalMonths) * 100) : 0;
                      const missingDocs = documentMatrix.months.reduce((count: number, month: any) => {
                        const missing = documentMatrix.required_documents?.filter((doc: string) => !month.documents?.[doc])?.length || 0;
                        return count + missing;
                      }, 0);
                      return (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="p-4 rounded-xl border border-border bg-surface">
                            <div className="text-sm text-text-secondary mb-1">Completeness</div>
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xl font-semibold text-text-primary">{progress}%</span>
                              <span className="text-sm text-text-secondary">{completeMonths}/{totalMonths} months</span>
                            </div>
                            <ProgressBar value={progress} max={100} showLabel={false} />
                          </div>
                          <div className="p-4 rounded-xl border border-border bg-surface">
                            <div className="text-sm text-text-secondary mb-1">Missing Documents</div>
                            <div className="text-xl font-semibold text-text-primary">{missingDocs}</div>
                            <div className="text-sm text-text-secondary">Across all periods</div>
                          </div>
                          <div className="p-4 rounded-xl border border-border bg-surface">
                            <div className="text-sm text-text-secondary mb-1">Timeline</div>
                            <div className="flex flex-wrap gap-2">
                              {documentMatrix.months.map((month: any) => (
                                <span
                                  key={month.period_id}
                                  className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                                    month.all_available
                                      ? 'bg-green-50 text-green-700 border-green-200'
                                      : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                                  } ${documentMatrix.latest_complete_period?.period_id === month.period_id ? 'ring-2 ring-blue-400' : ''}`}
                                >
                                  {month.month_name}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
                <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm text-left">
                  <thead className="bg-muted/50 text-text-secondary">
                    <tr className="border-b border-border">
                      <th className="px-4 py-3 font-semibold">Month</th>
                      {documentMatrix.required_documents?.map((doc: string) => (
                        <th key={doc} className="px-4 py-3 text-center font-semibold text-xs uppercase tracking-wider">
                          {doc.replace(/_/g, ' ')}
                        </th>
                      ))}
                      <th className="px-4 py-3 text-center font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border bg-surface">
                    {documentMatrix.months?.map((month: any) => (
                      <tr
                        key={month.period_id}
                        className={`
                          transition-colors
                          ${month.all_available ? 'bg-success-light/5' : ''}
                          ${documentMatrix.latest_complete_period?.period_id === month.period_id ? 'bg-primary-light/5 ring-1 ring-inset ring-primary/30' : ''}
                          hover:bg-muted/30
                        `}
                      >
                        <td className="px-4 py-3 font-medium">
                          {month.month_name}
                          {documentMatrix.latest_complete_period?.period_id === month.period_id && (
                            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary text-white shadow-sm">
                              Latest Complete
                            </span>
                          )}
                        </td>
                        {documentMatrix.required_documents?.map((doc: string) => (
                          <td key={doc} className="px-4 py-3 text-center">
                            {month.documents?.[doc] ? (
                              <CheckCircle className="w-5 h-5 text-success mx-auto" />
                            ) : (
                              <span className="text-border text-lg">•</span>
                            )}
                          </td>
                        ))}
                        <td className="px-4 py-3 text-center">
                          {month.all_available ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-light text-success">
                              Complete
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-light text-warning">
                              Incomplete
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>

                <div className="mt-4">
                  <div className="text-sm font-semibold text-text-primary mb-2">Heatmap</div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {documentMatrix.months?.map((month: any) => (
                      <div key={month.period_id} className="flex items-center gap-1 px-2 py-1 rounded bg-gray-50 border border-border">
                        <span className={`inline-block h-3 w-3 rounded-full ${
                          month.all_available ? 'bg-success' : 'bg-warning'
                        }`} />
                        <span>{month.month_name}</span>
                      </div>
                    ))}
                  </div>
                </div>

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
          </UICard>
        )}

        {/* Priority Actions / Alerts */}
        <UICard variant="elevated" className="mb-8 p-6 border-l-4 border-l-red-500">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-6 h-6 text-danger" />
              <div>
                <h2 className="text-2xl font-bold">Priority Actions</h2>
                <p className="text-sm text-text-secondary">Live issues across the portfolio</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {(() => {
                const counts = criticalAlerts.reduce(
                  (acc, a) => {
                    acc[a.severity] = (acc[a.severity] || 0) + 1;
                    return acc;
                  },
                  { critical: 0, high: 0, medium: 0 } as Record<string, number>
                );
                const badge = (label: string, count: number, tone: 'danger' | 'warning' | 'info') => (
                  <span
                    key={label}
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${
                      tone === 'danger'
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : tone === 'warning'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-blue-50 text-blue-700 border-blue-200'
                    }`}
                  >
                    {label}: {count}
                  </span>
                );
                return (
                  <>
                    {badge('Critical', counts.critical, 'danger')}
                    {badge('High', counts.high, 'warning')}
                    {badge('Medium', counts.medium, 'info')}
                  </>
                );
              })()}
            </div>
          </div>
          <div className="space-y-4">
            {loadingCriticalAlerts ? (
              [...Array(3)].map((_, idx) => (
                <div key={idx} className="space-y-2">
                  <UISkeleton variant="text" style={{ width: '60%', height: '1.25rem' }} />
                  <UISkeleton style={{ width: '100%', height: '0.5rem' }} />
                  <UISkeleton style={{ width: '80%', height: '0.5rem' }} />
                </div>
              ))
            ) : criticalAlerts.length === 0 ? (
              <div className="space-y-2 bg-success-light/20 p-4 rounded-lg border border-success/30">
                <p className="font-medium text-success">No critical alerts</p>
                <p className="text-sm text-text-secondary">All systems are stable.</p>
              </div>
            ) : (
              criticalAlerts.map((alert) => {
                const tone =
                  alert.severity === 'critical'
                    ? { bg: 'bg-red-50 border-red-200', pill: 'bg-red-100 text-red-800', bar: 'danger', dot: '🔴' }
                    : alert.severity === 'high'
                    ? { bg: 'bg-amber-50 border-amber-200', pill: 'bg-amber-100 text-amber-800', bar: 'warning', dot: '🟠' }
                    : { bg: 'bg-blue-50 border-blue-200', pill: 'bg-blue-100 text-blue-800', bar: 'info', dot: '🔵' };

                return (
                  <UICard key={alert.id} variant="elevated" hoverable className={`p-4 border ${tone.bg}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold">{tone.dot}</span>
                          <span className="font-semibold text-lg">
                            {alert.property.name} • {alert.metric.name} {alert.metric.current}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full font-semibold ${tone.pill}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                          {alert.period && (
                            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded font-medium">
                              {new Date(alert.period.year, alert.period.month - 1).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-text-secondary flex flex-wrap items-center gap-2">
                          <span className="font-medium text-text-primary">{alert.property.code}</span>
                          <span className="text-text-secondary">Threshold {alert.metric.threshold}</span>
                          <span className="text-text-secondary">• Impact: {alert.metric.impact}</span>
                        </div>
                        <p className="text-text-secondary">
                          <strong>Action:</strong> {alert.recommendation}
                        </p>
                        <ProgressBar
                          value={(alert.metric.current / alert.metric.threshold) * 100}
                          max={100}
                          variant={tone.bar as any}
                          showLabel
                          label={`${Math.round((alert.metric.current / alert.metric.threshold) * 100)}% of threshold (${Math.round(((alert.metric.threshold - alert.metric.current) / alert.metric.threshold) * 100)}% below compliance)`}
                        />
                      </div>
                      <div className="ml-4 flex flex-col gap-2 shrink-0">
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
                  </UICard>
                );
              })
            )}
          </div>
        </UICard>

        {/* Portfolio Performance Section - Added spacing from Key Indicators */}
        <div className="mt-10">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
            {/* Portfolio Performance Grid */}
            <div className="lg:col-span-2">
              <UICard variant="elevated" className="p-0 overflow-hidden">
                <div className="p-6 border-b border-border">
                  <h2 className="text-2xl font-bold">Portfolio Performance</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-muted/50 text-text-secondary">
                      <tr className="border-b border-border">
                        <th className="py-3 px-4 font-semibold">Property</th>
                        <th className="text-right py-3 px-4 font-semibold">Value</th>
                        <th className="text-right py-3 px-4 font-semibold">NOI</th>
                        <th className="text-right py-3 px-4 font-semibold">DSCR</th>
                        <th className="text-right py-3 px-4 font-semibold">LTV</th>
                        <th className="text-right py-3 px-4 font-semibold">Trend (NOI)</th>
                        <th className="text-center py-3 px-4 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {propertyPerformance.map((prop) => (
                        <tr
                          key={prop.id}
                          className={`hover:bg-muted/30 transition-colors cursor-pointer ${
                            prop.status === 'critical' ? 'bg-danger-light/5' :
                            prop.status === 'warning' ? 'bg-warning-light/5' :
                            ''
                          }`}
                        >
                          <td className="py-3 px-4 font-medium">{prop.name}</td>
                          <td className="py-3 px-4 text-right">
                            ${prop.value ? (prop.value / 1000000).toFixed(1) : '0.0'}M
                          </td>
                          <td className="py-3 px-4 text-right">
                            ${prop.noi ? (prop.noi / 1000).toFixed(1) : '0.0'}K
                          </td>
                          <td className={`py-3 px-4 text-right font-medium ${
                            (prop.dscr || 0) < 1.25 ? 'text-danger' : 
                            (prop.dscr || 0) < 1.35 ? 'text-warning' : 'text-success'
                          }`}>
                            {prop.dscr ? prop.dscr.toFixed(2) : 'N/A'}
                          </td>
                          <td className="py-3 px-4 text-right">{prop.ltv ? (prop.ltv * 100).toFixed(1) : 'N/A'}%</td>
                          <td className="py-3 px-4">
                            <div className="h-8 w-24 flex items-end gap-0.5 ml-auto">
                              {prop.trends.noi.slice(-12).map((val, i) => {
                                const max = Math.max(...prop.trends.noi, 1);
                                const height = (val / max) * 100;
                                return (
                                  <div
                                    key={i}
                                    className="flex-1 bg-info rounded-t opacity-80 hover:opacity-100 transition-opacity"
                                    style={{ height: `${Math.max(height, 15)}%` }}
                                    title={`$${val.toFixed(1)}M`}
                                  />
                                );
                              })}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-center">
                            {prop.status === 'critical' ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-danger-light text-danger">Critical</span>
                            ) : prop.status === 'warning' ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-light text-warning">Warning</span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-light text-success">Good</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
            </UICard>
          </div>

          {/* AI Insights Widget */}
          <div>
            <UICard variant="glass" className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-6 h-6 text-premium" />
                <h2 className="text-2xl font-bold">AI Advisor</h2>
              </div>
              <p className="text-sm text-text-secondary mb-4">Powered by Claude AI</p>

              {/* AI Insights */}
              <div className="space-y-4">
                {loadingAIInsights ? (
                  [...Array(3)].map((_, idx) => (
                    <div key={idx} className="space-y-2">
                      <UISkeleton variant="text" style={{ width: '50%', height: '1rem' }} />
                      <UISkeleton style={{ width: '100%', height: '0.5rem' }} />
                      <UISkeleton style={{ width: '80%', height: '0.5rem' }} />
                    </div>
                  ))
                ) : aiInsights.length === 0 ? (
                  <div className="bg-success-light/20 p-4 rounded-lg border border-success/30">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-6 h-6 text-success" />
                      <div>
                        <p className="font-medium text-success">Portfolio Health Strong</p>
                        <p className="text-sm text-text-secondary mt-1">
                          No critical issues detected - portfolio performing within normal parameters
                        </p>
                        <p className="text-xs text-text-secondary mt-2">
                          AI monitors: DSCR stress, vacancy trends, lease expirations, NOI patterns
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  aiInsights.map((insight) => (
                  <div key={insight.id} className="bg-premium-light/20 p-3 rounded-lg border border-premium/30">
                    <div className="flex items-start gap-3">
                      <span className="text-premium">🟣</span>
                      <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-sm">{insight.title}</p>
                      <span className="text-xs px-2 py-1 rounded-full bg-white/30 text-white">
                        {Math.round(insight.confidence)}% confidence
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary">{insight.description}</p>
                    <div className="flex gap-2 flex-wrap text-xs">
                      <span className="px-2 py-1 rounded bg-white/10 text-white">
                        Impact: {insight.type === 'risk' ? 'High' : insight.type === 'opportunity' ? 'Medium' : 'Low'}
                      </span>
                      <span className="px-2 py-1 rounded bg-white/10 text-white">
                        Updated: {insight.updated_at ? new Date(insight.updated_at).toLocaleTimeString() : 'just now'}
                      </span>
                    </div>
                    <div className="mt-1 flex gap-2 flex-wrap">
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
                          <Button variant="ghost" size="sm">Acknowledge</Button>
                        </div>
                      </div>
                    </div>
                  </div>
                  ))
                )}
              </div>
            </UICard>
          </div>
          </div>
        </div>

        {/* PDF Viewer - Inline at bottom after AI Advisor */}
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
