/**
 * Mortgage Metrics Widget
 * 
 * Wrapper component that gets period ID and displays mortgage metrics
 */
import { useState, useEffect } from 'react';
import { MortgageMetrics } from './MortgageMetrics';
import { api } from '../../lib/api';
import type { FinancialPeriod } from '../../types/api';

interface MortgageMetricsWidgetProps {
  propertyId: number;
  periodYear: number;
  periodMonth: number;
}

export function MortgageMetricsWidget({
  propertyId,
  periodYear,
  periodMonth
}: MortgageMetricsWidgetProps) {
  const [periodId, setPeriodId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPeriodId();
  }, [propertyId, periodYear, periodMonth]);

  const loadPeriodId = async () => {
    setLoading(true);
    try {
      // Get periods for this property
      const periods = await api.get<{ periods: FinancialPeriod[] }>(
        `/financial-periods?property_id=${propertyId}`
      );
      const period = periods.periods?.find(
        (p: FinancialPeriod) => p.period_year === periodYear && p.period_month === periodMonth
      );
      if (period) {
        setPeriodId(period.id);
      }
    } catch (err) {
      console.error('Failed to load period ID:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !periodId) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-4 text-center">
        <p className="text-gray-600 text-sm">Loading mortgage metrics...</p>
      </div>
    );
  }

  return <MortgageMetrics propertyId={propertyId} periodId={periodId} />;
}

