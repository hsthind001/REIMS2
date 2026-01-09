/**
 * Tenant Risk Dashboard
 *
 * Displays tenant concentration, lease rollover, occupancy, and credit quality
 */

import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Users,
  Calendar,
  Home,
  CreditCard,
  DollarSign,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { forensicAuditService, type TenantRiskResults } from '../lib/forensic_audit';
import { propertyService } from '../lib/property';
import { financialPeriodsService } from '../lib/financial_periods';
import type { Property } from '../types/api';
import TrafficLightIndicator from '../components/forensic-audit/TrafficLightIndicator';
import MetricCard from '../components/forensic-audit/MetricCard';

export default function TenantRiskDashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>('');
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [periods, setPeriods] = useState<any[]>([]);
  const [results, setResults] = useState<TenantRiskResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      loadResults();
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
    }
  };

  const loadPeriods = async (propertyId: string) => {
    try {
      const data = await financialPeriodsService.getPeriods(Number(propertyId));
      setPeriods(data);
      if (data.length > 0) {
        setSelectedPeriodId(String(data[0].id));
      }
    } catch (err) {
      console.error('Error loading periods:', err);
    }
  };

  const loadResults = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await forensicAuditService.getTenantRisk(selectedPropertyId, selectedPeriodId);
      setResults(data);
    } catch (err: any) {
      console.error('Error loading tenant risk:', err);
      setError(err.response?.data?.detail || 'Failed to load tenant risk analysis. Run audit first.');
    } finally {
      setLoading(false);
    }
  };

  const formatPeriodLabel = (period: any): string => {
    if (period.period_year && period.period_month) {
      return `${period.period_year}-${String(period.period_month).padStart(2, '0')}`;
    }
    return period.name || `Period ${period.id}`;
  };

  const getPropertyLabel = (property: Property): string => {
    return property.property_name || property.property_code || property.name || `Property ${property.id}`;
  };

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.hash = 'forensic-audit-dashboard';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" icon={<ArrowLeft className="w-4 h-4" />} onClick={handleBack}>
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Tenant Risk Analysis</h1>
            <p className="text-gray-600 mt-1">Concentration, rollover, and credit quality assessment</p>
          </div>
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
                {getPropertyLabel(property)}
              </option>
            ))}
          </select>

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

          <Button onClick={loadResults} disabled={loading || !selectedPropertyId || !selectedPeriodId}>
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

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      )}

      {!loading && results && (
        <>
          {/* Overall Status */}
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Users className="w-12 h-12 text-purple-600" />
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Overall Tenant Risk</h2>
                  <p className="text-gray-600">Composite tenant and lease risk assessment</p>
                </div>
              </div>
              <TrafficLightIndicator status={results.overall_status} size="lg" showLabel />
            </div>
          </Card>

          {/* Tenant Concentration */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Users className="w-6 h-6 text-purple-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Tenant Concentration Risk</h3>
                <p className="text-sm text-gray-600">Percentage of rent from top tenants</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <MetricCard
                title="Top 1 Tenant"
                value={`${results.concentration.top_1_pct.toFixed(1)}%`}
                status={results.concentration.top_1_pct > 20 ? 'RED' : results.concentration.top_1_pct > 15 ? 'YELLOW' : 'GREEN'}
                target="<20%"
                icon={Users}
              />
              <MetricCard
                title="Top 3 Tenants"
                value={`${results.concentration.top_3_pct.toFixed(1)}%`}
                status={results.concentration.top_3_pct > 50 ? 'RED' : results.concentration.top_3_pct > 40 ? 'YELLOW' : 'GREEN'}
                target="<50%"
                icon={Users}
              />
              <MetricCard
                title="Top 5 Tenants"
                value={`${results.concentration.top_5_pct.toFixed(1)}%`}
                target="Monitor"
                icon={Users}
              />
              <MetricCard
                title="Top 10 Tenants"
                value={`${results.concentration.top_10_pct.toFixed(1)}%`}
                target="Monitor"
                icon={Users}
              />
            </div>

            {results.concentration.top_tenants.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-3">Top Tenants:</div>
                <div className="space-y-2">
                  {results.concentration.top_tenants.map((tenant, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="font-medium text-gray-900">{tenant.tenant_name}</div>
                      <div className="text-right">
                        <div className="font-bold text-gray-900">{formatCurrency(tenant.monthly_rent)}/mo</div>
                        <div className="text-sm text-gray-600">{tenant.pct_of_total.toFixed(1)}% of total</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Lease Rollover */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Calendar className="w-6 h-6 text-orange-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Lease Rollover Risk</h3>
                <p className="text-sm text-gray-600">Percentage of rent expiring by period</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="12-Month Rollover"
                value={`${results.rollover.rollover_12mo_pct.toFixed(1)}%`}
                status={results.rollover.rollover_12mo_pct > 25 ? 'RED' : results.rollover.rollover_12mo_pct > 15 ? 'YELLOW' : 'GREEN'}
                target="<25%"
                icon={Calendar}
                iconColor="text-red-600"
              />
              <MetricCard
                title="24-Month Rollover"
                value={`${results.rollover.rollover_24mo_pct.toFixed(1)}%`}
                status={results.rollover.rollover_24mo_pct > 50 ? 'YELLOW' : 'GREEN'}
                target="<50%"
                icon={Calendar}
                iconColor="text-yellow-600"
              />
              <MetricCard
                title="36-Month Rollover"
                value={`${results.rollover.rollover_36mo_pct.toFixed(1)}%`}
                target="Monitor"
                icon={Calendar}
                iconColor="text-blue-600"
              />
            </div>
          </Card>

          {/* Occupancy Metrics */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Home className="w-6 h-6 text-green-600" />
              <div>
                <h3 className="text-xl font-bold text-gray-900">Occupancy Metrics</h3>
                <p className="text-sm text-gray-600">Physical and economic occupancy rates</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="text-sm text-gray-600 mb-2">Physical Occupancy</div>
                <div className="text-3xl font-bold text-gray-900 mb-3">
                  {results.occupancy.physical_occupancy_pct.toFixed(1)}%
                </div>
                <div className="bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-green-500 h-full transition-all duration-500"
                    style={{ width: `${results.occupancy.physical_occupancy_pct}%` }}
                  />
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  {results.occupancy.occupied_sf.toLocaleString()} / {results.occupancy.total_sf.toLocaleString()} SF
                </div>
              </div>

              <div>
                <div className="text-sm text-gray-600 mb-2">Economic Occupancy</div>
                <div className="text-3xl font-bold text-gray-900 mb-3">
                  {results.occupancy.economic_occupancy_pct.toFixed(1)}%
                </div>
                <div className="bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full transition-all duration-500"
                    style={{ width: `${results.occupancy.economic_occupancy_pct}%` }}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* Credit Quality & Rent/SF */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <CreditCard className="w-6 h-6 text-indigo-600" />
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Credit Quality</h3>
                  <p className="text-sm text-gray-600">Tenant creditworthiness</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">Investment Grade</span>
                    <span className="font-medium">{results.credit_quality.investment_grade_pct.toFixed(0)}%</span>
                  </div>
                  <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-green-500 h-full"
                      style={{ width: `${results.credit_quality.investment_grade_pct}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">Non-Investment Grade</span>
                    <span className="font-medium">{results.credit_quality.non_investment_grade_pct.toFixed(0)}%</span>
                  </div>
                  <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-yellow-500 h-full"
                      style={{ width: `${results.credit_quality.non_investment_grade_pct}%` }}
                    />
                  </div>
                </div>

                <div className="text-sm text-gray-600 mt-4">
                  Total Tenants: {results.credit_quality.tenant_count}
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <DollarSign className="w-6 h-6 text-teal-600" />
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Rent per SF</h3>
                  <p className="text-sm text-gray-600">Statistical distribution</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Average:</span>
                  <span className="font-bold">${results.rent_per_sf.average.toFixed(2)}/SF</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Median:</span>
                  <span className="font-bold">${results.rent_per_sf.median.toFixed(2)}/SF</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Range:</span>
                  <span className="font-bold">
                    ${results.rent_per_sf.min.toFixed(2)} - ${results.rent_per_sf.max.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Std Dev:</span>
                  <span className="font-bold">${results.rent_per_sf.std_dev.toFixed(2)}</span>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
