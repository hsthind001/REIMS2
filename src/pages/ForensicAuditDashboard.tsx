/**
 * Forensic Audit Dashboard (CEO View)
 *
 * Main executive dashboard showing overall health score, audit opinion,
 * priority risks, and action items.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  FileText,
  RefreshCw,
  Play,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import {
  forensicAuditService,
  type AuditScorecard,
  type CollectionsQualityResults,
  type CovenantComplianceResults,
  type CrossDocumentReconciliationResults,
  type FraudDetectionResults,
  type TenantRiskResults,
} from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService, type FinancialPeriod } from '../lib/financial_periods';
import type { Property } from '../types/api';
import HealthScoreGauge from '../components/forensic-audit/HealthScoreGauge';
import AuditOpinionBadge from '../components/forensic-audit/AuditOpinionBadge';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';
import RiskPriorityBadge from '../components/forensic-audit/RiskPriorityBadge';
import TrendIndicator from '../components/forensic-audit/TrendIndicator';

export default function ForensicAuditDashboard() {
  // Property and period selection
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);

  // Data
  const [scorecard, setScorecard] = useState<AuditScorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runningAudit, setRunningAudit] = useState(false);
  const [auditTaskId, setAuditTaskId] = useState<string | null>(null);
  const [auditPhase, setAuditPhase] = useState<string | null>(null);
  const [auditProgress, setAuditProgress] = useState<number | null>(null);
  const [auditStatusMessage, setAuditStatusMessage] = useState<string | null>(null);
  const auditPollerRef = useRef<number | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reconciliationResults, setReconciliationResults] =
    useState<CrossDocumentReconciliationResults | null>(null);
  const [fraudResults, setFraudResults] = useState<FraudDetectionResults | null>(null);
  const [covenantResults, setCovenantResults] = useState<CovenantComplianceResults | null>(null);
  const [tenantRiskResults, setTenantRiskResults] = useState<TenantRiskResults | null>(null);
  const [collectionsResults, setCollectionsResults] = useState<CollectionsQualityResults | null>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedPropertyId) {
      loadPeriods(selectedPropertyId);
    } else {
      setPeriods([]);
      setSelectedPeriodId('');
    }
  }, [selectedPropertyId]);

  useEffect(() => {
    if (selectedPropertyId && selectedPeriodId) {
      loadScorecard();
      loadDetailPanels();
    } else {
      setReconciliationResults(null);
      setFraudResults(null);
      setCovenantResults(null);
      setTenantRiskResults(null);
      setCollectionsResults(null);
    }
  }, [selectedPropertyId, selectedPeriodId]);

  useEffect(() => {
    if (!runningAudit || !auditTaskId) return;

    let cancelled = false;

    const pollStatus = async () => {
      try {
        const status = await forensicAuditService.getAuditStatus(auditTaskId);
        if (cancelled) return;

        const state = status.state || status.status;
        if (state === 'PENDING') {
          setAuditPhase('Queued');
          setAuditProgress(0);
          setAuditStatusMessage(status.message || 'Audit is queued and waiting to start.');
          return;
        }

        if (state === 'PROGRESS') {
          setAuditPhase(status.current_phase || 'In Progress');
          setAuditProgress(Number.isFinite(status.progress) ? status.progress : null);
          setAuditStatusMessage(status.message || 'Audit running.');
          return;
        }

        if (state === 'SUCCESS' || state === 'COMPLETED') {
          setRunningAudit(false);
          setAuditTaskId(null);
          setAuditPhase(null);
          setAuditProgress(null);
          setAuditStatusMessage(null);
          await loadScorecard();
          await loadDetailPanels();
          return;
        }

        if (state === 'FAILURE' || state === 'FAILED') {
          setRunningAudit(false);
          setAuditTaskId(null);
          setAuditPhase(null);
          setAuditProgress(null);
          setAuditStatusMessage(null);
          setError(status.message || 'Forensic audit failed. Check server logs for details.');
        }
      } catch (err: any) {
        if (cancelled) return;
        console.error('Error checking audit status:', err);
        setRunningAudit(false);
        setAuditTaskId(null);
        setAuditPhase(null);
        setAuditProgress(null);
        setAuditStatusMessage(null);
        setError(err.message || 'Failed to check audit status');
      }
    };

    pollStatus();
    auditPollerRef.current = window.setInterval(pollStatus, 5000);

    return () => {
      cancelled = true;
      if (auditPollerRef.current !== null) {
        window.clearInterval(auditPollerRef.current);
        auditPollerRef.current = null;
      }
    };
  }, [runningAudit, auditTaskId]);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0) {
        setSelectedPropertyId(String(data[0].id));
      }
    } catch (err) {
      console.error('Error loading properties:', err);
      setError('Failed to load properties');
    }
  };

  const loadPeriods = async (propertyId: string) => {
    try {
      const data = await financialPeriodsService.getPeriods(Number(propertyId));
      setPeriods(data);
      if (data.length > 0) {
        setSelectedPeriodId(String(data[0].id));
      } else {
        setSelectedPeriodId('');
      }
    } catch (err) {
      console.error('Error loading periods:', err);
      setError('Failed to load periods');
    }
  };

  const loadScorecard = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await forensicAuditService.getScorecard(
        selectedPropertyId,
        selectedPeriodId
      );
      setScorecard(data);
    } catch (err: any) {
      console.error('Error loading scorecard:', err);
      setError(err.response?.data?.detail || 'Failed to load forensic audit scorecard. Run audit first.');
    } finally {
      setLoading(false);
    }
  };

  const loadDetailPanels = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setDetailLoading(true);

    const requests = await Promise.allSettled([
      forensicAuditService.getReconciliations(selectedPropertyId, selectedPeriodId),
      forensicAuditService.getFraudDetection(selectedPropertyId, selectedPeriodId),
      forensicAuditService.getCovenantCompliance(selectedPropertyId, selectedPeriodId),
      forensicAuditService.getTenantRisk(selectedPropertyId, selectedPeriodId),
      forensicAuditService.getCollectionsQuality(selectedPropertyId, selectedPeriodId),
    ]);

    const [reconResult, fraudResult, covenantResult, tenantResult, collectionsResult] = requests;

    if (reconResult.status === 'fulfilled') {
      setReconciliationResults(reconResult.value);
    } else {
      setReconciliationResults(null);
      console.error('Error loading reconciliation results:', reconResult.reason);
    }

    if (fraudResult.status === 'fulfilled') {
      setFraudResults(fraudResult.value);
    } else {
      setFraudResults(null);
      console.error('Error loading fraud detection results:', fraudResult.reason);
    }

    if (covenantResult.status === 'fulfilled') {
      setCovenantResults(covenantResult.value);
    } else {
      setCovenantResults(null);
      console.error('Error loading covenant compliance results:', covenantResult.reason);
    }

    if (tenantResult.status === 'fulfilled') {
      setTenantRiskResults(tenantResult.value);
    } else {
      setTenantRiskResults(null);
      console.error('Error loading tenant risk results:', tenantResult.reason);
    }

    if (collectionsResult.status === 'fulfilled') {
      setCollectionsResults(collectionsResult.value);
    } else {
      setCollectionsResults(null);
      console.error('Error loading collections quality results:', collectionsResult.reason);
    }

    setDetailLoading(false);
  };

  const handleRunAudit = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setRunningAudit(true);
    setError(null);
    setAuditPhase('Queued');
    setAuditProgress(0);
    setAuditStatusMessage('Audit queued. Tracking progress...');

    try {
      const response = await forensicAuditService.runAudit({
        property_id: selectedPropertyId,
        period_id: selectedPeriodId,
      });

      const taskId = response.task_id;
      console.log('Audit task started with ID:', taskId);
      setAuditTaskId(taskId);

    } catch (err: any) {
      console.error('Error running audit:', err);
      // ApiClient error structure: { message, status, detail, category, retryable }
      setError(err.message || err.detail?.detail || 'Failed to start audit');
      setRunningAudit(false);
    }
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatPeriodLabel = (period: FinancialPeriod): string => {
    if (period.period_year && period.period_month) {
      return `${period.period_year}-${String(period.period_month).padStart(2, '0')}`;
    }
    return `Period ${period.id}`;
  };

  const getPropertyLabel = (property: Property): string => {
    return property.property_name || property.property_code || `Property ${property.id}`;
  };

  const handleRefresh = () => {
    loadScorecard();
    loadDetailPanels();
  };

  const goToRoute = (route: string) => {
    window.location.hash = route;
  };

  const getStatusFromCounts = (failed?: number, warnings?: number) => {
    if (failed && failed > 0) return 'RED';
    if (warnings && warnings > 0) return 'YELLOW';
    return 'GREEN';
  };

  const reconciliationPassRate = scorecard
    ? scorecard.reconciliation_summary.pass_rate_pct ?? scorecard.reconciliation_summary.pass_rate ?? 0
    : 0;

  const fraudSummary = scorecard
    ? scorecard.fraud_summary ?? {
        fraud_risk_level: scorecard.fraud_detection_summary?.overall_risk_level ?? 'Unknown',
        overall_status: scorecard.traffic_light_status,
      }
    : null;

  const financialTotals = scorecard
    ? {
        totalRevenue:
          scorecard.financial_summary.total_revenue ??
          scorecard.financial_summary.ytd_revenue ??
          0,
        netIncome:
          scorecard.financial_summary.net_income ??
          scorecard.financial_summary.ytd_net_income ??
          0,
        noi: scorecard.financial_summary.noi ?? scorecard.financial_summary.ytd_noi ?? 0,
        cashBalance: scorecard.financial_summary.cash_balance ?? 0,
      }
    : null;

  const ltvValue =
    scorecard?.covenant_summary.ltv ??
    scorecard?.covenant_summary.ltv_ratio ??
    null;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Forensic Audit Dashboard</h1>
          <p className="text-gray-600 mt-1">Big 5 Accounting Firm-Level Comprehensive Analysis</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Property Selector */}
          <select
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select Property</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {getPropertyLabel(property)}
              </option>
            ))}
          </select>

          {/* Period Selector */}
          <select
            value={selectedPeriodId}
            onChange={(e) => setSelectedPeriodId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            disabled={!selectedPropertyId}
          >
            <option value="">Select Period</option>
            {periods.map((period) => (
              <option key={period.id} value={period.id}>
                {formatPeriodLabel(period)}
              </option>
            ))}
          </select>

          {/* Actions */}
          <Button
            onClick={handleRefresh}
            disabled={loading || !selectedPropertyId || !selectedPeriodId}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            onClick={handleRunAudit}
            disabled={runningAudit || !selectedPropertyId || !selectedPeriodId}
            variant="primary"
          >
            <Play className={`w-4 h-4 ${runningAudit ? 'animate-pulse' : ''}`} />
            {runningAudit ? 'Running Audit...' : 'Run Audit'}
          </Button>
        </div>
      </div>

      {/* Empty data guidance */}
      {!loading && properties.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg">
          No properties found. Add a property to run the forensic audit dashboard.
        </div>
      )}

      {!loading && properties.length > 0 && periods.length === 0 && !error && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
          Select a period to view forensic audit results. If no periods exist for this property, create one or run an audit to generate the first scorecard.
        </div>
      )}

      {(runningAudit || auditTaskId) && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
          <div className="flex items-center gap-3">
            <RefreshCw className={`w-5 h-5 ${runningAudit ? 'animate-spin' : ''}`} />
            <div className="flex-1">
              <div className="font-medium">
                Audit status{auditPhase ? `: ${auditPhase}` : ''}
              </div>
              <div className="text-sm text-blue-700">
                {auditStatusMessage || 'Tracking audit progress...'}
              </div>
            </div>
            {auditProgress != null && (
              <div className="text-sm font-semibold text-blue-700">
                {auditProgress}%
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600">Loading scorecard...</p>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!loading && scorecard && (
        <>
          {/* Top Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Overall Health Score */}
            <Card className="p-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Health Score</h3>
                <HealthScoreGauge score={scorecard.overall_health_score} size="lg" />
                <div className="mt-4 text-sm text-gray-600">
                  Generated {formatDate(scorecard.generated_at)}
                </div>
              </div>
            </Card>

            {/* Audit Opinion */}
            <Card className="p-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Audit Opinion</h3>
                <div className="flex justify-center mb-4">
                  <AuditOpinionBadge opinion={scorecard.audit_opinion} size="lg" showDescription />
                </div>
                {scorecard.auditor_notes && (
                  <div className="text-sm text-gray-600 mt-4">
                    {scorecard.auditor_notes}
                  </div>
                )}
              </div>
            </Card>

            {/* Traffic Light Status */}
            <Card className="p-6">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Status</h3>
                <div className="flex justify-center mb-4">
                  <TrafficLightIndicator status={scorecard.traffic_light_status} size="lg" showLabel />
                </div>
                <div className="grid grid-cols-3 gap-2 mt-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-600">Pass</div>
                    <div className="text-lg font-bold text-green-600">
                      {scorecard.reconciliation_summary.passed}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-600">Warning</div>
                    <div className="text-lg font-bold text-yellow-600">
                      {scorecard.reconciliation_summary.warnings}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-600">Fail</div>
                    <div className="text-lg font-bold text-red-600">
                      {scorecard.reconciliation_summary.failed}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Key Financial Metrics */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Key Financial Metrics</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <MetricCard
                title="DSCR"
                value={scorecard.covenant_summary.dscr != null ? `${scorecard.covenant_summary.dscr.toFixed(2)}x` : 'N/A'}
                subtitle="Debt Service Coverage"
                status={scorecard.covenant_summary.dscr_status as any}
                target={scorecard.covenant_summary.dscr_covenant != null ? `${scorecard.covenant_summary.dscr_covenant.toFixed(2)}x` : 'N/A'}
                targetLabel="Covenant"
                icon={TrendingUp}
                iconColor="text-blue-600"
              />

              <MetricCard
                title="LTV Ratio"
                value={ltvValue != null ? `${ltvValue.toFixed(1)}%` : 'N/A'}
                subtitle="Loan-to-Value"
                status={scorecard.covenant_summary.ltv_status as any}
                target={scorecard.covenant_summary.ltv_covenant != null ? `${scorecard.covenant_summary.ltv_covenant.toFixed(0)}%` : 'N/A'}
                targetLabel="Covenant"
                icon={DollarSign}
                iconColor="text-green-600"
              />

              <MetricCard
                title="Fraud Risk"
                value={fraudSummary?.fraud_risk_level || 'Unknown'}
                subtitle="Overall Assessment"
                status={fraudSummary?.overall_status || scorecard.traffic_light_status}
                icon={Shield}
                iconColor="text-purple-600"
              />

              <MetricCard
                title="Reconciliation Pass Rate"
                value={`${reconciliationPassRate.toFixed(1)}%`}
                subtitle={`${scorecard.reconciliation_summary.passed}/${scorecard.reconciliation_summary.total_reconciliations} passed`}
                status={reconciliationPassRate >= 90 ? 'GREEN' : reconciliationPassRate >= 75 ? 'YELLOW' : 'RED'}
                icon={CheckCircle2}
                iconColor="text-teal-600"
              />
            </div>
          </div>

          {/* Traffic Light Metrics */}
          {scorecard.metrics.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Traffic Light Metrics</h2>
                {detailLoading && (
                  <span className="text-sm text-gray-500">Refreshing detail panels...</span>
                )}
              </div>
              <Card className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {scorecard.metrics.map((metric) => (
                    <div key={metric.metric_name} className="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{metric.metric_name}</div>
                        <div className="text-xs text-gray-500">
                          {metric.current_value != null ? metric.current_value.toFixed(2) : 'N/A'}
                          {metric.target_value != null ? ` / Target ${metric.target_value.toFixed(2)}` : ''}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <TrendIndicator trend={metric.trend as any} size="sm" />
                        <TrafficLightIndicator status={metric.status} size="sm" />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Audit Drilldowns */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Audit Drilldowns</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Reconciliations</div>
                    <div className="text-xs text-gray-500">9 cross-document tie-outs</div>
                  </div>
                  <TrafficLightIndicator
                    status={(reconciliationResults
                      ? getStatusFromCounts(reconciliationResults.failed, reconciliationResults.warnings)
                      : scorecard.traffic_light_status) as any}
                    size="sm"
                  />
                </div>
                <div className="text-sm text-gray-700">
                  {reconciliationResults
                    ? `${reconciliationResults.passed}/${reconciliationResults.total_reconciliations} passed`
                    : 'Run audit to generate reconciliation results.'}
                </div>
                <Button onClick={() => goToRoute('reconciliation-results')} variant="secondary">
                  View Reconciliation Results
                </Button>
              </Card>

              <Card className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Fraud Detection</div>
                    <div className="text-xs text-gray-500">Benford, round numbers, duplicates</div>
                  </div>
                  <TrafficLightIndicator
                    status={(fraudResults?.overall_status || fraudSummary?.overall_status || scorecard.traffic_light_status) as any}
                    size="sm"
                  />
                </div>
                <div className="text-sm text-gray-700">
                  {fraudResults
                    ? `Risk: ${fraudResults.fraud_risk_level}`
                    : `Risk: ${fraudSummary?.fraud_risk_level ?? 'Unknown'}`}
                </div>
                <Button onClick={() => goToRoute('fraud-detection')} variant="secondary">
                  View Fraud Detection
                </Button>
              </Card>

              <Card className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Covenant Compliance</div>
                    <div className="text-xs text-gray-500">DSCR, LTV, liquidity</div>
                  </div>
                  <TrafficLightIndicator
                    status={(covenantResults?.overall_status || scorecard.covenant_summary.dscr_status) as any}
                    size="sm"
                  />
                </div>
                <div className="text-sm text-gray-700">
                  {covenantResults
                    ? `DSCR ${covenantResults.tests.dscr.dscr.toFixed(2)}x • LTV ${covenantResults.tests.ltv.ltv.toFixed(1)}%`
                    : `DSCR ${scorecard.covenant_summary.dscr.toFixed(2)}x`}
                </div>
                <Button onClick={() => goToRoute('covenant-compliance')} variant="secondary">
                  View Covenant Compliance
                </Button>
              </Card>

              <Card className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Tenant Risk</div>
                    <div className="text-xs text-gray-500">Concentration and rollover</div>
                  </div>
                  <TrafficLightIndicator
                    status={(tenantRiskResults?.overall_status || scorecard.traffic_light_status) as any}
                    size="sm"
                  />
                </div>
                <div className="text-sm text-gray-700">
                  {tenantRiskResults
                    ? `Top 5 tenants ${tenantRiskResults.concentration.top_5_pct.toFixed(0)}% • 12mo rollover ${tenantRiskResults.rollover.rollover_12mo_pct.toFixed(0)}%`
                    : 'Run audit to generate tenant risk results.'}
                </div>
                <Button onClick={() => goToRoute('tenant-risk')} variant="secondary">
                  View Tenant Risk
                </Button>
              </Card>

              <Card className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">Collections Quality</div>
                    <div className="text-xs text-gray-500">DSO and revenue quality</div>
                  </div>
                  <TrafficLightIndicator
                    status={(collectionsResults?.overall_status || scorecard.traffic_light_status) as any}
                    size="sm"
                  />
                </div>
                <div className="text-sm text-gray-700">
                  {collectionsResults
                    ? `Quality ${collectionsResults.revenue_quality.quality_score}% • DSO ${collectionsResults.dso.current_dso.toFixed(0)}`
                    : 'Run audit to generate collections results.'}
                </div>
                <Button onClick={() => goToRoute('collections-quality')} variant="secondary">
                  View Collections Quality
                </Button>
              </Card>
            </div>
          </div>

          {/* Priority Risks */}
          {scorecard.priority_risks.length > 0 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4">Priority Risks ({scorecard.priority_risks.length})</h2>
              <Card>
                <div className="divide-y divide-gray-200">
                  {scorecard.priority_risks.map((risk) => (
                    <div key={risk.risk_id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <RiskPriorityBadge severity={risk.severity} />
                            <span className="text-sm font-medium text-gray-600">{risk.category}</span>
                          </div>
                          <h4 className="font-semibold text-gray-900 mb-1">{risk.description}</h4>
                          <p className="text-sm text-gray-600 mb-2">{risk.action_required}</p>
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <span>Owner: {risk.owner}</span>
                            {risk.due_date && <span>Due: {formatDate(risk.due_date)}</span>}
                            {risk.financial_impact && (
                              <span>Impact: {formatCurrency(risk.financial_impact)}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Action Items */}
          {scorecard.action_items.length > 0 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4">Action Items ({scorecard.action_items.length})</h2>
              <Card>
                <div className="divide-y divide-gray-200">
                  {scorecard.action_items.map((item) => (
                    <div key={item.action_id} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            item.priority === 'URGENT' ? 'bg-red-100 text-red-700' :
                            item.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                            item.priority === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {item.priority}
                          </span>
                          <span className="text-sm text-gray-500">{item.assigned_to}</span>
                        </div>
                        <p className="text-sm font-medium text-gray-900">{item.description}</p>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-xs text-gray-500">Due: {formatDate(item.due_date)}</div>
                        <div className={`text-xs font-medium mt-1 ${
                          item.status === 'COMPLETED' ? 'text-green-600' :
                          item.status === 'IN_PROGRESS' ? 'text-blue-600' :
                          'text-gray-600'
                        }`}>
                          {item.status}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Financial Summary */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Financial Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4">
                <div className="text-sm text-gray-600">Total Revenue</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(financialTotals?.totalRevenue ?? 0)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">Net Income</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(financialTotals?.netIncome ?? 0)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">NOI</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(financialTotals?.noi ?? 0)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">Cash Balance</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(financialTotals?.cashBalance ?? 0)}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}

      {/* No Data State */}
      {!loading && !scorecard && !error && selectedPropertyId && selectedPeriodId && (
        <div className="text-center py-12">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Audit Data Available</h3>
          <p className="text-gray-600 mb-4">
            Click "Run Audit" to generate a forensic audit scorecard for this property and period.
          </p>
          <Button onClick={handleRunAudit} disabled={runningAudit} variant="primary">
            <Play className="w-4 h-4" />
            Run Forensic Audit
          </Button>
        </div>
      )}
    </div>
  );
}
