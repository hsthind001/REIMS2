/**
 * Forensic Audit Dashboard (CEO View)
 *
 * Main executive dashboard showing overall health score, audit opinion,
 * priority risks, and action items.
 */

import { useState, useEffect } from 'react';
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
import { forensicAuditService, type AuditScorecard } from '../lib/forensic_audit';
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
    }
  }, [selectedPropertyId, selectedPeriodId]);

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

  const handleRunAudit = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setRunningAudit(true);
    setError(null);

    try {
      const response = await forensicAuditService.runAudit({
        property_id: selectedPropertyId,
        period_id: selectedPeriodId,
      });

      // Poll for task completion
      const taskId = response.task_id;
      const pollInterval = setInterval(async () => {
        try {
          const status = await forensicAuditService.getAuditTaskStatus(taskId);

          if (status.status === 'SUCCESS') {
            clearInterval(pollInterval);
            setRunningAudit(false);
            loadScorecard(); // Reload the scorecard
          } else if (status.status === 'FAILURE') {
            clearInterval(pollInterval);
            setRunningAudit(false);
            setError('Audit failed: ' + status.message);
          }
        } catch (err) {
          console.error('Error checking task status:', err);
        }
      }, 2000);

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (runningAudit) {
          setRunningAudit(false);
          setError('Audit timed out');
        }
      }, 300000);
    } catch (err: any) {
      console.error('Error running audit:', err);
      setError(err.response?.data?.detail || 'Failed to start audit');
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
            onClick={loadScorecard}
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
                value={`${scorecard.covenant_summary.dscr.toFixed(2)}x`}
                subtitle="Debt Service Coverage"
                status={scorecard.covenant_summary.dscr_status as any}
                target={`${scorecard.covenant_summary.dscr_covenant.toFixed(2)}x`}
                targetLabel="Covenant"
                icon={TrendingUp}
                iconColor="text-blue-600"
              />

              <MetricCard
                title="LTV Ratio"
                value={`${scorecard.covenant_summary.ltv.toFixed(1)}%`}
                subtitle="Loan-to-Value"
                status={scorecard.covenant_summary.ltv_status as any}
                target={`${scorecard.covenant_summary.ltv_covenant.toFixed(0)}%`}
                targetLabel="Covenant"
                icon={DollarSign}
                iconColor="text-green-600"
              />

              <MetricCard
                title="Fraud Risk"
                value={scorecard.fraud_summary.fraud_risk_level}
                subtitle="Overall Assessment"
                status={scorecard.fraud_summary.overall_status}
                icon={Shield}
                iconColor="text-purple-600"
              />

              <MetricCard
                title="Reconciliation Pass Rate"
                value={`${scorecard.reconciliation_summary.pass_rate_pct.toFixed(1)}%`}
                subtitle={`${scorecard.reconciliation_summary.passed}/${scorecard.reconciliation_summary.total_reconciliations} passed`}
                status={scorecard.reconciliation_summary.pass_rate_pct >= 90 ? 'GREEN' : scorecard.reconciliation_summary.pass_rate_pct >= 75 ? 'YELLOW' : 'RED'}
                icon={CheckCircle2}
                iconColor="text-teal-600"
              />
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
                  {formatCurrency(scorecard.financial_summary.total_revenue)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">Net Income</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(scorecard.financial_summary.net_income)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">NOI</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(scorecard.financial_summary.noi)}
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-sm text-gray-600">Cash Balance</div>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(scorecard.financial_summary.cash_balance)}
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
