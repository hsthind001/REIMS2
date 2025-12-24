import { useCallback, useMemo } from 'react';
import { propertyService } from '../lib/property';
import { useMutation, useQuery, useQueryClient } from '../lib/queryClient';
import type { Property } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : 'http://localhost:8000/api/v1';

export interface PortfolioHealth {
  score: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
  totalValue: number;
  totalNOI: number;
  avgOccupancy: number;
  portfolioDSCR: number;
  percentageChanges?: {
    total_value_change: number;
    noi_change: number;
    occupancy_change: number;
    dscr_change: number;
  };
  alertCount: {
    critical: number;
    warning: number;
    info: number;
  };
  lastUpdated: Date;
}

export interface CriticalAlert {
  id: number;
  property: {
    id: number;
    name: string;
    code: string;
  };
  type: string;
  severity: 'critical' | 'high' | 'medium';
  metric: {
    name: string;
    current: number;
    threshold: number;
    impact: string;
  };
  recommendation: string;
  createdAt: Date;
  period?: {
    id: number;
    year: number;
    month: number;
  };
  financial_period_id?: number;
}

export interface PropertyPerformance {
  id: number;
  name: string;
  code: string;
  value: number;
  noi: number;
  dscr: number | null;
  ltv: number | null;
  occupancy: number;
  status: 'critical' | 'warning' | 'good';
  trends: {
    noi: number[];
  };
}

export interface AIInsight {
  id: string;
  type: 'risk' | 'opportunity' | 'market' | 'operational';
  title: string;
  description: string;
  confidence: number;
}

const fetchPortfolioHealth = async (
  selectedPropertyFilter: string,
  properties: Property[]
): Promise<PortfolioHealth | null> => {
  try {
    let metricsSummary = await fetch(`${API_BASE_URL}/metrics/summary`, {
      credentials: 'include'
    }).then((r) => (r.ok ? r.json() : []));

    if (selectedPropertyFilter !== 'all') {
      metricsSummary = metricsSummary.filter(
        (m: any) => m.property_code === selectedPropertyFilter
      );
    }

    let totalValue = 0;
    let totalNOI = 0;
    let totalOccupancy = 0;
    let occupancyCount = 0;
    let criticalAlerts = 0;
    let warningAlerts = 0;

    const propertyMap = new Map<string, any>();
    metricsSummary.forEach((m: any) => {
      const existing = propertyMap.get(m.property_code);
      if (!existing) {
        propertyMap.set(m.property_code, m);
      } else if (
        m.period_year > existing.period_year ||
        (m.period_year === existing.period_year && m.period_month > existing.period_month)
      ) {
        propertyMap.set(m.property_code, m);
      }
    });

    propertyMap.forEach((m: any) => {
      if (m.total_assets) totalValue += m.total_assets;
      if (m.net_operating_income !== null && m.net_operating_income !== undefined) {
        totalNOI += m.net_operating_income;
      } else if (m.net_income !== null && m.net_income !== undefined) {
        totalNOI += m.net_income;
      }
      if (m.occupancy_rate !== null && m.occupancy_rate !== undefined) {
        totalOccupancy += m.occupancy_rate;
        occupancyCount++;
      }
    });

    const avgOccupancy = occupancyCount > 0 ? totalOccupancy / occupancyCount : 0;
    let portfolioDSCR = 0;

    const selectedProp = properties.find((p) => p.property_code === selectedPropertyFilter);
    if (selectedPropertyFilter !== 'all' && selectedProp) {
      const periodIdParam =
        selectedProp.latest_financial_period_id || selectedProp.period_id
          ? `?financial_period_id=${selectedProp.latest_financial_period_id || selectedProp.period_id}`
          : '';
      const dscrResponse = await fetch(
        `${API_BASE_URL}/risk-alerts/properties/${selectedProp.id}/dscr/calculate${periodIdParam}`,
        {
          method: 'POST',
          credentials: 'include'
        }
      );
      if (dscrResponse.ok) {
        const dscrData = await dscrResponse.json();
        if (dscrData.success && dscrData.dscr !== null && dscrData.dscr !== undefined) {
          portfolioDSCR = dscrData.dscr;
        } else if (dscrData.dscr && typeof dscrData.dscr === 'number') {
          portfolioDSCR = dscrData.dscr;
        }
      }
    } else {
      const dscrResponse = await fetch(`${API_BASE_URL}/exit-strategy/portfolio-dscr`, {
        method: 'POST',
        credentials: 'include'
      });
      if (dscrResponse.ok) {
        const dscrData = await dscrResponse.json();
        portfolioDSCR = dscrData.portfolio_dscr || 0;
      }
    }

    let percentageChanges: PortfolioHealth['percentageChanges'] = undefined;
    if (selectedPropertyFilter === 'all') {
      const changesResponse = await fetch(`${API_BASE_URL}/metrics/portfolio-changes`, {
        credentials: 'include'
      });
      if (changesResponse.ok) {
        const changesData = await changesResponse.json();
        percentageChanges = {
          total_value_change: changesData.total_value_change ?? 0,
          noi_change: changesData.noi_change ?? 0,
          occupancy_change: changesData.occupancy_change ?? 0,
          dscr_change: changesData.dscr_change ?? 0
        };
      }
    }

    try {
      const alertCountsRes = await fetch(`${API_BASE_URL}/risk-alerts/summary`, {
        credentials: 'include'
      });
      if (alertCountsRes.ok) {
        const alertSummary = await alertCountsRes.json();
        criticalAlerts = alertSummary.critical_count || 0;
        warningAlerts = alertSummary.warning_count || 0;
      }
    } catch (err) {
      console.warn('Failed to load alert summary:', err);
    }

    let score = 85;
    if (avgOccupancy < 85) score -= 15;
    if (avgOccupancy < 80) score -= 10;
    if (criticalAlerts > 0) score -= criticalAlerts * 5;
    if (warningAlerts > 0) score -= warningAlerts * 2;
    score = Math.max(0, Math.min(100, score));

    const status =
      score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : 'poor';

    return {
      score,
      status,
      totalValue,
      totalNOI,
      avgOccupancy,
      portfolioDSCR,
      percentageChanges,
      alertCount: {
        critical: criticalAlerts,
        warning: warningAlerts,
        info: 0
      },
      lastUpdated: new Date()
    };
  } catch (error) {
    console.error('Failed to load portfolio health:', error);
    return null;
  }
};

const fetchCriticalAlerts = async (): Promise<CriticalAlert[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/risk-alerts?priority=critical&status=ACTIVE`, {
      credentials: 'include'
    });
    if (response.ok) {
      const data = await response.json();
      let alerts = data.alerts || data;
      const alertsByProperty = new Map<number, any>();
      alerts.forEach((a: any) => {
        const propertyId = a.property_id;
        const existing = alertsByProperty.get(propertyId);

        if (!existing) {
          alertsByProperty.set(propertyId, a);
        } else {
          const existingDate = new Date(existing.triggered_at || existing.created_at || 0);
          const currentDate = new Date(a.triggered_at || a.created_at || 0);

          if (a.financial_period_id && existing.financial_period_id) {
            if (currentDate > existingDate) {
              alertsByProperty.set(propertyId, a);
            }
          } else if (currentDate > existingDate) {
            alertsByProperty.set(propertyId, a);
          }
        }
      });

      alerts = Array.from(alertsByProperty.values())
        .sort((a: any, b: any) => {
          const dateA = new Date(a.triggered_at || a.created_at || 0).getTime();
          const dateB = new Date(b.triggered_at || b.created_at || 0).getTime();
          return dateB - dateA;
        })
        .slice(0, 5);

      return alerts.map((a: any) => ({
        id: a.id,
        property: {
          id: a.property_id,
          name: a.property_name || 'Unknown',
          code: a.property_code || ''
        },
        type: a.alert_type || 'risk',
        severity: a.severity || 'critical',
        metric: {
          name: a.metric_name || a.related_metric || 'DSCR',
          current: a.actual_value || 0,
          threshold: a.threshold_value || 1.25,
          impact: a.impact || 'Risk identified'
        },
        recommendation: a.recommendation || a.description || 'Review immediately',
        createdAt: new Date(a.triggered_at || a.created_at || Date.now()),
        financial_period_id: a.financial_period_id,
        period: a.period
          ? {
              id: a.period.id,
              year: a.period.year,
              month: a.period.month
            }
          : undefined
      }));
    }
  } catch (err) {
    console.error('Failed to load critical alerts:', err);
  }
  return [];
};

const fetchPropertyPerformance = async (properties: Property[]): Promise<PropertyPerformance[]> => {
  try {
    const performance: PropertyPerformance[] = [];
    const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
      credentials: 'include'
    });
    const allMetrics = metricsRes.ok ? await metricsRes.json() : [];

    const metricsMap = new Map<string, any>();
    allMetrics.forEach((m: any) => {
      const existing = metricsMap.get(m.property_code);
      const hasData =
        (m.total_assets !== null && m.total_assets !== undefined) ||
        (m.net_income !== null && m.net_income !== undefined);
      const existingHasData =
        existing &&
        ((existing.total_assets !== null && existing.total_assets !== undefined) ||
          (existing.net_income !== null && existing.net_income !== undefined));

      if (!existing) {
        metricsMap.set(m.property_code, m);
      } else if (hasData && !existingHasData) {
        metricsMap.set(m.property_code, m);
      } else if (!hasData && existingHasData) {
        // keep existing
      } else {
        if (m.period_year && existing.period_year && m.period_year > existing.period_year) {
          metricsMap.set(m.property_code, m);
        } else if (
          m.period_year === existing.period_year &&
          m.period_month &&
          existing.period_month &&
          m.period_month > existing.period_month
        ) {
          metricsMap.set(m.property_code, m);
        }
      }
    });

    const propertyPromises = properties.slice(0, 10).map(async (property) => {
      try {
        const metric = metricsMap.get(property.property_code);

        if (metric) {
          const noi =
            metric.net_operating_income !== null && metric.net_operating_income !== undefined
              ? metric.net_operating_income
              : metric.net_income !== null && metric.net_income !== undefined
                ? metric.net_income
                : 0;

          const dec2024PeriodIdMap: Record<string, number> = {
            ESP001: 2,
            HMND001: 4,
            TCSH001: 9,
            WEND001: 6
          };
          const periodIdToUse = dec2024PeriodIdMap[property.property_code] || metric.period_id;
          const periodIdParam = periodIdToUse ? `?financial_period_id=${periodIdToUse}` : '';

          const [histRes, dscrRes, ltvRes] = await Promise.all([
            fetch(`${API_BASE_URL}/metrics/historical?property_id=${property.id}&months=12`, {
              credentials: 'include'
            }).catch(() => ({ ok: false } as Response)),
            fetch(
              `${API_BASE_URL}/risk-alerts/properties/${property.id}/dscr/calculate${periodIdParam}`,
              {
                method: 'POST',
                credentials: 'include'
              }
            ).catch(() => ({ ok: false } as Response)),
            fetch(`${API_BASE_URL}/metrics/${property.id}/ltv`, {
              credentials: 'include'
            }).catch(() => ({ ok: false } as Response))
          ]);

          let noiTrend: number[] = [];
          if (histRes.ok) {
            try {
              const histData = await histRes.json();
              noiTrend = histData.data?.noi?.map((n: number) => n / 1000000) || [];
            } catch (histErr) {
              console.error('Failed to parse historical data:', histErr);
            }
          }

          let dscr: number | null = null;
          let status: 'critical' | 'warning' | 'good' = 'good';
          if (dscrRes.ok) {
            try {
              const dscrData = await dscrRes.json();
              if (dscrData.success && dscrData.dscr !== null && dscrData.dscr !== undefined) {
                dscr = dscrData.dscr;
                status =
                  dscrData.status === 'healthy'
                    ? 'good'
                    : dscrData.status === 'warning'
                      ? 'warning'
                      : 'critical';
              }
            } catch (dscrErr) {
              console.error(`Failed to parse DSCR for ${property.property_code}:`, dscrErr);
            }
          }

          if (dscr === null && ltvRes.ok) {
            try {
              const ltvData = await ltvRes.json();
              const loanAmount = ltvData.loan_amount || 0;
              const annualDebtService = loanAmount * 0.08;
              if (annualDebtService > 0 && noi > 0) {
                dscr = noi / annualDebtService;
                status = dscr < 1.25 ? 'critical' : dscr < 1.35 ? 'warning' : 'good';
              }
            } catch (fallbackErr) {
              console.error('Failed to calculate DSCR fallback:', fallbackErr);
            }
          }

          let ltv: number | null = null;
          if (ltvRes.ok) {
            try {
              const ltvData = await ltvRes.json();
              ltv = ltvData.ltv || null;
            } catch (ltvErr) {
              console.error(`Failed to parse LTV for ${property.property_code}:`, ltvErr);
            }
          }

          return {
            id: property.id,
            name: property.property_name,
            code: property.property_code,
            value: metric.total_assets || 0,
            noi,
            dscr,
            ltv,
            occupancy: metric.occupancy_rate || 0,
            status,
            trends: { noi: noiTrend }
          };
        }

        return {
          id: property.id,
          name: property.property_name,
          code: property.property_code,
          value: 0,
          noi: 0,
          dscr: 0,
          ltv: 0,
          occupancy: 0,
          status: 'warning' as const,
          trends: { noi: [] }
        };
      } catch (err) {
        console.error(`Failed to load metrics for ${property.property_code}:`, err);
        return {
          id: property.id,
          name: property.property_name,
          code: property.property_code,
          value: 0,
          noi: 0,
          dscr: 0,
          ltv: 0,
          occupancy: 0,
          status: 'warning' as const,
          trends: { noi: [] }
        };
      }
    });

    const results = await Promise.all(propertyPromises);
    performance.push(...results);
    return performance;
  } catch (err) {
    console.error('Failed to load property performance:', err);
    return [];
  }
};

const fetchSparklineData = async (
  selectedPropertyFilter: string,
  properties: Property[]
): Promise<{ value: number[]; noi: number[]; occupancy: number[]; dscr: number[] }> => {
  try {
    let url = `${API_BASE_URL}/metrics/historical?months=12`;
    if (selectedPropertyFilter !== 'all') {
      const selectedProp = properties.find((p) => p.property_code === selectedPropertyFilter);
      if (selectedProp) {
        url += `&property_id=${selectedProp.id}`;
      }
    }

    const response = await fetch(url, {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();

      const valueSparkline = data.data.value.map((v: number) => v / 1000000);
      const noiSparkline = data.data.noi.map((n: number) => n / 1000000);
      const occupancySparkline = data.data.occupancy;

      let dscrSparkline: number[] = [];
      if (selectedPropertyFilter !== 'all') {
        const selectedProp = properties.find((p) => p.property_code === selectedPropertyFilter);
        if (selectedProp) {
          const dscrResponse = await fetch(
            `${API_BASE_URL}/metrics/${selectedProp.id}/dscr/historical?months=12`,
            { credentials: 'include' }
          );
          if (dscrResponse.ok) {
            const dscrData = await dscrResponse.json();
            dscrSparkline = dscrData.dscr_values || [];
          }
        }
      }

      return {
        value: valueSparkline,
        noi: noiSparkline,
        occupancy: occupancySparkline,
        dscr: dscrSparkline
      };
    }
  } catch (err) {
    console.error('Failed to load sparkline data:', err);
  }

  return {
    value: [],
    noi: [],
    occupancy: [],
    dscr: []
  };
};

const fetchAIInsights = async (): Promise<AIInsight[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/nlq/insights/portfolio`, {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      return data.insights || [];
    }
  } catch (err) {
    console.error('Failed to load AI insights:', err);
  }
  return [];
};

const fetchPortfolioAnalysis = async () => {
  const response = await fetch(`${API_BASE_URL}/nlq/insights/portfolio?detailed=true`, {
    credentials: 'include'
  });
  if (!response.ok) {
    throw new Error('Failed to load portfolio analysis');
  }
  return response.json();
};

const fetchInsightAnalysis = async (insightId: string) => {
  const response = await fetch(`${API_BASE_URL}/nlq/insights/${insightId}`, {
    credentials: 'include'
  });
  if (!response.ok) {
    throw new Error('Failed to load insight analysis');
  }
  return response.json();
};

export function useCommandCenterData(selectedPropertyFilter: string) {
  const queryClient = useQueryClient();

  const propertiesQuery = useQuery<Property[]>({
    queryKey: ['command-center', 'properties'],
    queryFn: () => propertyService.getAllProperties(),
    staleTime: 5 * 60 * 1000
  });

  const portfolioHealthQuery = useQuery<PortfolioHealth | null>({
    queryKey: ['command-center', 'portfolio-health', selectedPropertyFilter],
    enabled: Boolean(propertiesQuery.data),
    queryFn: () => fetchPortfolioHealth(selectedPropertyFilter, propertiesQuery.data ?? []),
    staleTime: 2 * 60 * 1000
  });

  const criticalAlertsQuery = useQuery<CriticalAlert[]>({
    queryKey: ['command-center', 'critical-alerts'],
    queryFn: fetchCriticalAlerts,
    staleTime: 60 * 1000
  });

  const propertyPerformanceQuery = useQuery<PropertyPerformance[]>({
    queryKey: ['command-center', 'property-performance', selectedPropertyFilter],
    enabled: Boolean(propertiesQuery.data),
    queryFn: () => fetchPropertyPerformance(propertiesQuery.data ?? []),
    staleTime: 2 * 60 * 1000
  });

  const sparklineQuery = useQuery<{ value: number[]; noi: number[]; occupancy: number[]; dscr: number[] }>({
    queryKey: ['command-center', 'sparkline', selectedPropertyFilter],
    enabled: Boolean(propertiesQuery.data),
    queryFn: () => fetchSparklineData(selectedPropertyFilter, propertiesQuery.data ?? []),
    staleTime: 60 * 1000
  });

  const aiInsightsQuery = useQuery<AIInsight[]>({
    queryKey: ['command-center', 'ai-insights'],
    queryFn: fetchAIInsights,
    staleTime: 3 * 60 * 1000
  });

  const acknowledgeAlert = useMutation<{ success: boolean }, { alert: CriticalAlert; acknowledgedBy: number }>({
    mutationFn: async ({ alert, acknowledgedBy }) => {
      const response = await fetch(`${API_BASE_URL}/risk-alerts/alerts/${alert.id}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          acknowledged_by: acknowledgedBy,
          notes: `Acknowledged from Command Center dashboard`
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to acknowledge alert');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['command-center', 'critical-alerts'] });
    }
  });

  const refreshDashboard = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ['command-center'] }),
    [queryClient]
  );

  const isLoading =
    propertiesQuery.isLoading ||
    portfolioHealthQuery.isLoading ||
    criticalAlertsQuery.isLoading ||
    propertyPerformanceQuery.isLoading ||
    sparklineQuery.isLoading ||
    aiInsightsQuery.isLoading;

  const isFetching =
    propertiesQuery.isFetching ||
    portfolioHealthQuery.isFetching ||
    criticalAlertsQuery.isFetching ||
    propertyPerformanceQuery.isFetching ||
    sparklineQuery.isFetching ||
    aiInsightsQuery.isFetching;

  return {
    properties: propertiesQuery.data ?? [],
    portfolioHealth: portfolioHealthQuery.data,
    criticalAlerts: criticalAlertsQuery.data ?? [],
    propertyPerformance: propertyPerformanceQuery.data ?? [],
    sparklineData: sparklineQuery.data ?? { value: [], noi: [], occupancy: [], dscr: [] },
    aiInsights: aiInsightsQuery.data ?? [],
    isLoading,
    isFetching,
    refreshDashboard,
    acknowledgeAlert,
    fetchPortfolioAnalysis,
    fetchInsightAnalysis
  };
}
