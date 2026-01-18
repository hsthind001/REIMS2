/**
 * Portfolio Metrics Hook Types
 * 
 * TypeScript interfaces for centralized metrics management
 */

// Property-level metrics
export interface PropertyMetrics {
  property_code: string;
  property_name: string;
  property_value: number;
  noi: number;
  occupancy_rate: number;
  dscr: number | null;
  ltv: number | null;
  cap_rate: number | null;
  period: {
    year: number;
    month: number;
    is_complete: boolean;
  };
}

// Portfolio-level aggregated metrics
export interface PortfolioMetrics {
  total_value: number;
  total_noi: number;
  avg_occupancy: number;
  portfolio_dscr: number;
  percentage_changes: {
    total_value_change: number;
    noi_change: number;
    occupancy_change: number;
    dscr_change: number;
  };
  calculation_method: string;
  properties_included: number;
  properties_excluded: number;
}

// Combined response from metrics endpoints
export interface MetricsSummaryResponse {
  portfolio: PortfolioMetrics;
  properties: PropertyMetrics[];
  calculation_date: string;
  note: string;
}

// Metrics summary item from existing API
export interface MetricsSummaryItem {
  property_code: string;
  property_name: string;
  period_id: number | null;
  period_year: number;
  period_month: number;
  total_assets: number | null;
  total_revenue: number | null;
  net_income: number | null;
  net_operating_income: number | null;
  occupancy_rate: number | null;
  dscr: number | null;
  ltv_ratio: number | null;
  is_complete: boolean;
}
