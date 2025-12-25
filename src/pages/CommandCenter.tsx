import { useState } from 'react';
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
import { MetricCard, Card, Button, ProgressBar, Skeleton } from '../components/design-system';
import { PDFViewer } from '../components/PDFViewer';
import { DocumentUpload } from '../components/DocumentUpload';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { exportPortfolioHealthToPDF, exportToCSV, exportToExcel } from '../lib/exportUtils';
import { getMetricSource, getPDFViewerData } from '../lib/metrics_source';
import { useAuth } from '../components/AuthContext';
import {
  useCommandCenterData,
  type AIInsight,
  type PortfolioHealth,
  type PropertyPerformance,
  type CriticalAlert
} from '../hooks/useCommandCenterData';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export default function CommandCenter() {
  const { user } = useAuth();
  const [selectedPropertyFilter, setSelectedPropertyFilter] = useState<string>('all'); // 'all' or property_code
  const {
    properties,
    portfolioHealth,
    criticalAlerts,
    propertyPerformance,
    aiInsights,
    sparklineData,
    isLoading,
    isFetching,
    refreshDashboard,
    acknowledgeAlert,
    fetchPortfolioAnalysis,
    fetchInsightAnalysis
  } = useCommandCenterData(selectedPropertyFilter);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showPropertyModal, setShowPropertyModal] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [selectedInsight, setSelectedInsight] = useState<AIInsight | null>(null);
  const [analysisDetails, setAnalysisDetails] = useState<any>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showPDFViewer, setShowPDFViewer] = useState(false);
  const [pdfViewerData, setPdfViewerData] = useState<{
    pdfUrl: string;
    highlightPage?: number;
    highlightCoords?: { x0: number; y0: number; x1: number; y1: number };
  } | null>(null);
  const [loadingPDFSource, setLoadingPDFSource] = useState(false);
  const heroLoading = isLoading && !portfolioHealth;
  const metricsLoading = isLoading && propertyPerformance.length === 0;

  const { isRefreshing, isPaused, lastRefresh, pause, resume, toggle, refresh } = useAutoRefresh({
    interval: 300000, // 5 minutes
    enabled: true,
    onRefresh: refreshDashboard,
    dependencies: [refreshDashboard]
  });

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

  const loadPortfolioAnalysis = async () => {
    try {
      setLoadingAnalysis(true);
      const data = await fetchPortfolioAnalysis();
      setAnalysisDetails(data);
    } catch (err) {
      console.error('Failed to load portfolio analysis:', err);
      setAnalysisDetails({
        title: 'Portfolio Health Analysis',
        summary: portfolioHealth
          ? `Portfolio Health Score: ${portfolioHealth.score}/100 (${portfolioHealth.status.toUpperCase()})`
          : 'Unable to load detailed analysis',
        details: portfolioHealth
          ? [
              `Total Portfolio Value: $${((portfolioHealth.totalValue || 0) / 1000000).toFixed(1)}M`,
              `Total NOI: $${((portfolioHealth.totalNOI || 0) / 1000).toFixed(1)}K`,
              `Average Occupancy: ${(portfolioHealth.avgOccupancy || 0).toFixed(1)}%`,
              `Portfolio DSCR: ${(portfolioHealth.portfolioDSCR || 0).toFixed(2)}`,
              `Critical Alerts: ${portfolioHealth.alertCount.critical}`,
              `Warning Alerts: ${portfolioHealth.alertCount.warning}`
            ]
          : [],
        recommendations: ['Please try again later']
      });
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const loadInsightAnalysis = async (insight: AIInsight) => {
    try {
      setLoadingAnalysis(true);
      const data = await fetchInsightAnalysis(insight.id);
      setAnalysisDetails(data);
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
      await acknowledgeAlert.mutateAsync({ alert, acknowledgedBy: currentUserId });
      alert('Alert acknowledged successfully');
      await refreshDashboard();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      alert(
        `Failed to acknowledge alert: ${
          err instanceof Error ? err.message : 'Unknown error'
        }`
      );
    }
  };

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
                {heroLoading ? (
                  <Skeleton className="h-4 w-48 bg-white/20 border-white/20" />
                ) : (
                  <p className="text-white/80">
                    Last Updated: {lastRefresh.toLocaleTimeString()}
                  </p>
                )}
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
              {heroLoading ? (
                <div className="flex flex-col items-end gap-2">
                  <Skeleton className="h-12 w-40 bg-white/20 border-white/20" />
                  <Skeleton className="h-5 w-32 bg-white/20 border-white/20" />
                </div>
              ) : (
                <>
                  <div className="text-6xl font-bold mb-2">
                    {portfolioHealth?.score || 0}/100
                  </div>
                  <div className="flex items-center gap-2 text-xl">
                    {getStatusIcon(portfolioHealth?.status || 'fair')}
                    <span className="uppercase font-semibold">{portfolioHealth?.status || 'FAIR'}</span>
                  </div>
                </>
              )}
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
        {metricsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {[1, 2, 3, 4].map((key) => (
              <Skeleton key={key} className="h-32 w-full" />
            ))}
          </div>
        ) : (
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
              value={portfolioHealth?.portfolioDSCR ? portfolioHealth.portfolioDSCR.toFixed(2) : "0.00"}
              change={portfolioHealth?.percentageChanges?.dscr_change || 0}
              trend={portfolioHealth?.percentageChanges?.dscr_change >= 0 ? "up" : "down"}
              icon="📈"
              variant="success"
              sparkline={sparklineData.dscr.length > 0 ? sparklineData.dscr : undefined}
              onClick={selectedPropertyFilter !== 'all' ? () => handleMetricClick('dscr') : undefined}
            />
          </div>
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
                        <td className="py-3 px-4 text-right">{prop.ltv ? prop.ltv.toFixed(1) : 'N/A'}%</td>
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
              refreshDashboard();
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
