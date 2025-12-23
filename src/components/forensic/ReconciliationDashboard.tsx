/**
 * Reconciliation Dashboard Component
 * 
 * Displays summary cards, filters, and action buttons for forensic reconciliation
 */

import { Card, Button } from '../design-system';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  TrendingUp,
  Play,
  Download,
  RefreshCw
} from 'lucide-react';
import type { ReconciliationDashboard } from '../../lib/forensic_reconciliation';

interface ReconciliationDashboardProps {
  dashboardData: ReconciliationDashboard;
  healthScore: number | null;
  onRunReconciliation?: () => void;
  onCompleteSession?: () => void;
}

export default function ReconciliationDashboardComponent({
  dashboardData,
  healthScore,
  onRunReconciliation,
  onCompleteSession
}: ReconciliationDashboardProps) {
  const summary = dashboardData.summary || {};
  const matches = dashboardData.matches || { total: 0, by_status: {}, by_type: {} };
  const discrepancies = dashboardData.discrepancies || { total: 0, by_severity: {}, by_status: {} };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card variant="success" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Matches</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{matches.total || 0}</p>
            </div>
            <CheckCircle className="w-12 h-12 text-green-500" />
          </div>
          <div className="mt-4 flex gap-4 text-sm">
            <div>
              <span className="text-gray-600">Exact:</span>
              <span className="ml-2 font-semibold">{matches.by_type?.exact || 0}</span>
            </div>
            <div>
              <span className="text-gray-600">Fuzzy:</span>
              <span className="ml-2 font-semibold">{matches.by_type?.fuzzy || 0}</span>
            </div>
          </div>
        </Card>

        <Card variant="info" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Approved</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{matches.by_status?.approved || 0}</p>
            </div>
            <CheckCircle className="w-12 h-12 text-blue-500" />
          </div>
          <div className="mt-4">
            <span className="text-sm text-gray-600">
              Pending: {matches.by_status?.pending || 0}
            </span>
          </div>
        </Card>

        <Card variant="warning" className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Discrepancies</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{discrepancies.total || 0}</p>
            </div>
            <AlertTriangle className="w-12 h-12 text-amber-500" />
          </div>
          <div className="mt-4 flex gap-4 text-sm">
            <div>
              <span className="text-gray-600">Critical:</span>
              <span className="ml-2 font-semibold text-red-600">{discrepancies.by_severity?.critical || 0}</span>
            </div>
            <div>
              <span className="text-gray-600">High:</span>
              <span className="ml-2 font-semibold text-orange-600">{discrepancies.by_severity?.high || 0}</span>
            </div>
          </div>
        </Card>

        <Card variant={healthScore && healthScore >= 80 ? 'success' : healthScore && healthScore >= 60 ? 'warning' : 'danger'} className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Health Score</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {healthScore !== null ? `${healthScore.toFixed(1)}%` : 'N/A'}
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-green-500" />
          </div>
        </Card>
      </div>

      {/* Action Buttons */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
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
              onClick={() => window.location.reload()}
            >
              Refresh
            </Button>
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="info"
              icon={<Download className="w-4 h-4" />}
            >
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

