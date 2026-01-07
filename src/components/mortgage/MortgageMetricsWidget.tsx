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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPeriodId();
  }, [propertyId, periodYear, periodMonth]);

  const loadPeriodId = async () => {
    setLoading(true);
    setError(null);
    setPeriodId(null);
    try {
      // Get periods for this property - API returns array directly, not wrapped
      const periods = await api.get<FinancialPeriod[]>(
        `/financial-periods?property_id=${propertyId}`
      );
      console.log('Loaded periods:', periods);
      const period = periods.find(
        (p: FinancialPeriod) => p.period_year === periodYear && p.period_month === periodMonth
      );
      console.log('Found period for', periodYear, periodMonth, ':', period);
      if (period) {
        setPeriodId(period.id);
      } else {
        console.warn('No period found for:', { propertyId, periodYear, periodMonth });
        setError(`No financial period found for ${periodYear}/${periodMonth}. Please ensure data has been uploaded for this period.`);
      }
    } catch (err: any) {
      console.error('Failed to load period ID:', err);
      setError(err?.message || 'Failed to load financial period');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-4 text-center">
        <p className="text-gray-600 text-sm">Loading mortgage metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded p-4 text-center">
        <p className="text-yellow-800 text-sm">⚠️ {error}</p>
      </div>
    );
  }

  if (!periodId) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-4 text-center">
        <p className="text-gray-600 text-sm">No financial period found for this property and date.</p>
      </div>
    );
  }

  return <MortgageMetrics propertyId={propertyId} periodId={periodId} />;
}

