/**
 * Audit History Dashboard
 *
 * Executive trend view for forensic audit scorecards.
 */

import { useEffect, useMemo, useState } from 'react';
import { RefreshCw, AlertTriangle, TrendingUp } from 'lucide-react';
import { Card, Button } from '../components/design-system';
import TrendAnalysisChart from '../components/charts/TrendAnalysisChart';
import { forensicAuditService, type AuditHistoryItem } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import type { Property } from '../types/api';

export default function AuditHistoryDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [history, setHistory] = useState<AuditHistoryItem[]>([]);
  const [limit, setLimit] = useState<number>(12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedPropertyId) {
      loadHistory();
    }
  }, [selectedPropertyId, limit]);

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

  const loadHistory = async () => {
    if (!selectedPropertyId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await forensicAuditService.getAuditHistory(selectedPropertyId, limit);
      setHistory(data);
    } catch (err: any) {
      console.error('Error loading audit history:', err);
      setError(err.message || 'Failed to load audit history. Run audits to generate history.');
    } finally {
      setLoading(false);
    }
  };

  const historyAscending = useMemo(() => {
    return [...history].sort((a, b) => a.period_label.localeCompare(b.period_label));
  }, [history]);

  const latest = history[0];

  const scoreTrendData = useMemo(() => (
    historyAscending.map((item) => ({
      date: item.period_label,
      value: item.overall_health_score,
      label: item.period_label
    }))
  ), [historyAscending]);

  const dscrTrendData = useMemo(() => (
    historyAscending
      .filter((item) => item.dscr != null)
      .map((item) => ({
        date: item.period_label,
        value: item.dscr ?? 0,
        label: item.period_label
      }))
  ), [historyAscending]);

  const occupancyTrendData = useMemo(() => (
    historyAscending
      .filter((item) => item.occupancy_rate != null)
      .map((item) => ({
        date: item.period_label,
        value: item.occupancy_rate ?? 0,
        label: item.period_label
      }))
  ), [historyAscending]);

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusColor = (status: string) => {
    if (status === 'GREEN') return 'text-green-600';
    if (status === 'YELLOW') return 'text-yellow-600';
    return 'text-red-600';
  };

  const propertyLabel = (property: Property) => (
    property.property_name || property.property_code || `Property ${property.id}`
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Audit History</h1>
          <p className="text-gray-600 mt-1">Trend analysis of forensic audit scorecards</p>
        </div>

        <div className="flex items-center gap-4">
          <select
            value={selectedPropertyId}
            onChange={(e) => setSelectedPropertyId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select Property</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {propertyLabel(property)}
              </option>
            ))}
          </select>

          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {[6, 12, 18, 24, 36].map((value) => (
              <option key={value} value={value}>{value} periods</option>
            ))}
          </select>

          <Button onClick={loadHistory} disabled={loading || !selectedPropertyId}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {!loading && history.length === 0 && selectedPropertyId && !error && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
          No audit history found for this property. Run audits to populate history.
        </div>
      )}

      {latest && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="text-sm text-gray-600">Latest Health Score</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{latest.overall_health_score}</div>
            <div className="text-xs text-gray-500 mt-1">{latest.period_label}</div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-600">Latest Status</div>
            <div className={`text-2xl font-bold mt-1 ${getStatusColor(latest.traffic_light_status)}`}>
              {latest.traffic_light_status}
            </div>
            <div className="text-xs text-gray-500 mt-1">{latest.audit_opinion}</div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-600">Critical Issues</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{latest.critical_issues}</div>
            <div className="text-xs text-gray-500 mt-1">Last audited {formatDate(latest.audit_date)}</div>
          </Card>
        </div>
      )}

      {history.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <TrendAnalysisChart
            title="Overall Health Score"
            data={scoreTrendData}
            metric="Health Score"
            chartType="area"
            showExport={false}
            yAxisFormatter={(value) => value.toFixed(0)}
            color="#2563eb"
            height={240}
          />
          <TrendAnalysisChart
            title="DSCR Trend"
            data={dscrTrendData}
            metric="DSCR"
            chartType="line"
            showExport={false}
            yAxisFormatter={(value) => value.toFixed(2)}
            color="#10b981"
            referenceLine={1.25}
            referenceLineLabel="Covenant"
            height={240}
          />
          <TrendAnalysisChart
            title="Occupancy Trend"
            data={occupancyTrendData}
            metric="Occupancy"
            chartType="line"
            showExport={false}
            yAxisFormatter={(value) => `${value.toFixed(1)}%`}
            tooltipFormatter={(value) => `${value.toFixed(1)}%`}
            color="#f97316"
            height={240}
          />
        </div>
      )}

      {history.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">Audit History Details</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-gray-600">
                <tr className="border-b">
                  <th className="text-left py-2">Period</th>
                  <th className="text-left py-2">Audit Date</th>
                  <th className="text-right py-2">Health</th>
                  <th className="text-right py-2">DSCR</th>
                  <th className="text-right py-2">Occupancy</th>
                  <th className="text-right py-2">Critical Issues</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Opinion</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={`${item.period_id}-${item.period_label}`} className="border-b last:border-b-0">
                    <td className="py-2 text-gray-800">{item.period_label}</td>
                    <td className="py-2 text-gray-600">{formatDate(item.audit_date)}</td>
                    <td className="py-2 text-right text-gray-800 font-medium">{item.overall_health_score}</td>
                    <td className="py-2 text-right text-gray-600">{item.dscr != null ? item.dscr.toFixed(2) : 'N/A'}</td>
                    <td className="py-2 text-right text-gray-600">{item.occupancy_rate != null ? `${item.occupancy_rate.toFixed(1)}%` : 'N/A'}</td>
                    <td className="py-2 text-right text-gray-800">{item.critical_issues}</td>
                    <td className={`py-2 font-medium ${getStatusColor(item.traffic_light_status)}`}>
                      {item.traffic_light_status}
                    </td>
                    <td className="py-2 text-gray-600">{item.audit_opinion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
