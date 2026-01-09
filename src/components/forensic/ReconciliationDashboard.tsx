/**
 * Reconciliation Dashboard Component
 * 
 * Best-in-class summary header for reconciliation: KPI tiles + tight action bar.
 */

import { Card, Button } from '../design-system';
import {
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Play,
  Download,
  RefreshCw,
  ArrowUpRight,
  ArrowRight
} from 'lucide-react';
import type { ReconciliationDashboard } from '../../lib/forensic_reconciliation';

interface ReconciliationDashboardProps {
  dashboardData: ReconciliationDashboard;
  healthScore: number | null;
  onRunReconciliation?: () => void;
  onCompleteSession?: () => void;
  onRefresh?: () => void;
}

export default function ReconciliationDashboardComponent({
  dashboardData,
  healthScore,
  onRunReconciliation,
  onCompleteSession,
  onRefresh
}: ReconciliationDashboardProps) {
  const matches = dashboardData.matches || { total: 0, by_status: {}, by_type: {} };
  const discrepancies = dashboardData.discrepancies || { total: 0, by_severity: {}, by_status: {} };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card variant="success" className="p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Matches</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{matches.total || 0}</p>
              <div className="mt-3 flex gap-4 text-sm text-gray-700">
                <span className="flex items-center gap-1">
                  Exact <ArrowRight className="w-3 h-3" /> <strong>{matches.by_type?.exact || 0}</strong>
                </span>
                <span className="flex items-center gap-1">
                  Fuzzy <ArrowRight className="w-3 h-3" /> <strong>{matches.by_type?.fuzzy || 0}</strong>
                </span>
              </div>
            </div>
            <CheckCircle className="w-10 h-10 text-green-500" />
          </div>
        </Card>

        <Card variant="info" className="p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Approvals</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{matches.by_status?.approved || 0}</p>
              <p className="mt-2 text-sm text-gray-700 flex items-center gap-1">
                Pending <ArrowRight className="w-3 h-3" /> <strong>{matches.by_status?.pending || 0}</strong>
              </p>
            </div>
            <CheckCircle className="w-10 h-10 text-blue-500" />
          </div>
        </Card>

        <Card variant="warning" className="p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Discrepancies</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{discrepancies.total || 0}</p>
              <div className="mt-3 flex gap-4 text-sm text-gray-700">
                <span className="flex items-center gap-1 text-red-600">
                  Critical <ArrowUpRight className="w-3 h-3" /> <strong>{discrepancies.by_severity?.critical || 0}</strong>
                </span>
                <span className="flex items-center gap-1 text-amber-600">
                  High <ArrowUpRight className="w-3 h-3" /> <strong>{discrepancies.by_severity?.high || 0}</strong>
                </span>
              </div>
            </div>
            <AlertTriangle className="w-10 h-10 text-amber-500" />
          </div>
        </Card>

        <Card
          variant={
            healthScore && healthScore >= 80
              ? 'success'
              : healthScore && healthScore >= 60
              ? 'warning'
              : 'danger'
          }
          className="p-6 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Health Score</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {healthScore !== null ? `${healthScore.toFixed(1)}%` : 'N/A'}
              </p>
              <p className="mt-2 text-sm text-gray-700 flex items-center gap-1">
                {healthScore !== null
                  ? healthScore >= 80
                    ? 'Excellent'
                    : healthScore >= 60
                    ? 'Stable'
                    : 'Needs attention'
                  : 'Not available'}
              </p>
            </div>
            <TrendingUp className="w-10 h-10 text-green-500" />
          </div>
        </Card>
      </div>

      {/* Action Buttons */}
      <Card className="p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-2">
            {onRunReconciliation && (
              <Button
                onClick={onRunReconciliation}
                variant="primary"
                icon={<Play className="w-4 h-4" />}
              >
                Run Reconciliation
              </Button>
            )}
            <Button
              variant="info"
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={onRefresh || (() => window.location.reload())}
            >
              Refresh
            </Button>
          </div>

          <div className="flex gap-2">
            <Button variant="info" icon={<Download className="w-4 h-4" />}>
              Export Report
            </Button>
            {onCompleteSession && (
              <Button
                onClick={onCompleteSession}
                variant="success"
                icon={<CheckCircle className="w-4 h-4" />}
              >
                Complete Session
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
