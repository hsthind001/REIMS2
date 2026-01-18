/**
 * Portfolio Metrics Hook
 * 
 * Centralized hook for fetching and managing portfolio metrics.
 * Ensures consistency across all UI components by providing a single source of truth.
 * 
 * Usage:
 * ```tsx
 * const { metrics, loading, error } = usePortfolioMetrics('all', 2023);
 * ```
 */

import { useState, useEffect } from 'react';
import type { MetricsSummaryItem } from '../types/metrics';


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface PortfolioMetrics {
  // Portfolio-level aggregated metrics
  totalValue: number;
  totalNOI: number;
  avgOccupancy: number;
  portfolioDSCR: number;
  avgLTV: number;
  percentageChanges: {
    total_value_change: number;
    noi_change: number;
    occupancy_change: number;
    dscr_change: number;
  };
  
  // Property-level metrics (for detailed views)
  properties: MetricsSummaryItem[];
  
  // Metadata
  calculationDate: Date;
  propertiesIncluded: number;
  note?: string;
}

export interface UsePortfolioMetricsResult {
  metrics: PortfolioMetrics | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Custom hook to fetch portfolio metrics
 * 
 * @param propertyFilter - 'all' for portfolio view, or specific property_code
 * @param year - Optional year filter for metrics
 * @returns Portfolio metrics, loading state, and error state
 */
export function usePortfolioMetrics(
  propertyFilter: string = 'all',
  year?: number
): UsePortfolioMetricsResult {
  const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch metrics summary (already filters by completeness)
      const summaryUrl = `${API_BASE_URL}/metrics/summary${year ? `?year=${year}` : ''}`;
      const summaryResponse = await fetch(summaryUrl, {
        credentials: 'include'
      });

      if (!summaryResponse.ok) {
        throw new Error(`Failed to fetch metrics: ${summaryResponse.statusText}`);
      }

      let metricsSummary: MetricsSummaryItem[] = await summaryResponse.json();

      // Filter by selected property if not "all"
      if (propertyFilter !== 'all') {
        metricsSummary = metricsSummary.filter((m) => m.property_code === propertyFilter);
      }

      // Calculate portfolio aggregates
      let totalValue = 0;
      let totalNOI = 0;
      let totalOccupancy = 0;
      let occupancyCount = 0;
      let totalLTV = 0;
      let ltvCount = 0;

      // Create property map (latest period per property)
      const propertyMap = new Map<string, MetricsSummaryItem>();
      metricsSummary.forEach((m) => {
        const existing = propertyMap.get(m.property_code);
        if (!existing) {
          propertyMap.set(m.property_code, m);
        } else {
          // Prefer later period if duplicate
          if (
            m.period_year > existing.period_year ||
            (m.period_year === existing.period_year && m.period_month > existing.period_month)
          ) {
            propertyMap.set(m.property_code, m);
          }
        }
      });

      // Sum values from unique properties
      propertyMap.forEach((m) => {
        if (m.total_assets) totalValue += m.total_assets;
        if (m.net_operating_income != null) {
          totalNOI += m.net_operating_income;
        } else if (m.net_income != null) {
          // Fallback to net_income if NOI not available
          totalNOI += m.net_income;
        }
        if (m.occupancy_rate != null) {
          totalOccupancy += m.occupancy_rate;
          occupancyCount++;
        }
        if (m.ltv_ratio != null) {
          totalLTV += m.ltv_ratio;
          ltvCount++;
        }
      });

      const avgOccupancy = occupancyCount > 0 ? totalOccupancy / occupancyCount : 0;
      const avgLTV = ltvCount > 0 ? totalLTV / ltvCount : 0;

      // Calculate DSCR
      let portfolioDSCR = 0;
      let dscrChange = 0;
      const propertyArray = Array.from(propertyMap.values());

      if (propertyFilter === 'all') {
        if (propertyArray.length === 1) {
          // Single property: use its DSCR directly
          const metric = propertyArray[0];
          portfolioDSCR = metric.dscr ?? 0;
        } else if (propertyArray.length > 1) {
          // Multi-property: fetch from portfolio endpoint with year filter
          try {
            const dscrUrl = `${API_BASE_URL}/exit-strategy/portfolio-dscr${year ? `?year=${year}` : ''}`;
            const dscrResponse = await fetch(dscrUrl, {
              credentials: 'include'
            });
            if (dscrResponse.ok) {
              const dscrData = await dscrResponse.json();
              portfolioDSCR = dscrData.dscr || 0;
              dscrChange = dscrData.yoy_change || 0;
            }
          } catch (dscrErr) {
            console.error('Failed to fetch portfolio DSCR:', dscrErr);
          }
        }
      } else {
        // Property-specific DSCR
        const metric = propertyMap.get(propertyFilter);
        if (metric) {
          portfolioDSCR = metric.dscr ?? 0;
        }
      }

      // Fetch percentage changes
      let percentageChanges = {
        total_value_change: 0,
        noi_change: 0,
        occupancy_change: 0,
        dscr_change: dscrChange
      };

      if (propertyFilter === 'all') {
        try {
          const changesResponse = await fetch(`${API_BASE_URL}/metrics/portfolio-changes`, {
            credentials: 'include'
          });
          if (changesResponse.ok) {
            const changesData = await changesResponse.json();
            percentageChanges = {
              total_value_change: changesData.total_value_change || 0,
              noi_change: changesData.noi_change || 0,
              occupancy_change: changesData.occupancy_change || 0,
              dscr_change: changesData.dscr_change || dscrChange
            };
          }
        } catch (changesErr) {
          console.error('Failed to fetch percentage changes:', changesErr);
        }
      } else {
        // Calculate property-specific percentage changes
        const metric = propertyMap.get(propertyFilter);
        if (metric && year) {
          try {
            const prevYear = year - 1;
            const prevMetricsResponse = await fetch(
              `${API_BASE_URL}/metrics/summary?year=${prevYear}`,
              { credentials: 'include' }
            );
            if (prevMetricsResponse.ok) {
              const prevMetrics = await prevMetricsResponse.json();
              const prevMetric = prevMetrics.find(
                (m: MetricsSummaryItem) =>
                  m.property_code === propertyFilter &&
                  m.period_year === prevYear
              );

              if (prevMetric) {
                const calcChange = (current: number, previous: number) => {
                  if (!previous || previous === 0) return 0;
                  return ((current - previous) / previous) * 100;
                };

                percentageChanges = {
                  total_value_change: calcChange(
                    metric.total_assets || 0,
                    prevMetric.total_assets || 0
                  ),
                  noi_change: calcChange(
                    metric.net_operating_income || 0,
                    prevMetric.net_operating_income || 0
                  ),
                  occupancy_change: calcChange(
                    metric.occupancy_rate || 0,
                    prevMetric.occupancy_rate || 0
                  ),
                  dscr_change: dscrChange
                };
              }
            }
          } catch (prevErr) {
            console.warn('Failed to fetch previous period metrics:', prevErr);
          }
        }
      }

      setMetrics({
        totalValue,
        totalNOI,
        avgOccupancy,
        portfolioDSCR,
        avgLTV,
        percentageChanges,
        properties: Array.from(propertyMap.values()),
        calculationDate: new Date(),
        propertiesIncluded: propertyMap.size,
        note: `Metrics from complete periods only (all 3 documents required)`
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching portfolio metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propertyFilter, year]);

  return {
    metrics,
    loading,
    error,
    refetch: fetchMetrics
  };
}
