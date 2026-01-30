/**
 * Variance Analysis Service
 *
 * API calls for budget vs actual and forecast variance analysis
 */

import { api } from './api';

export interface VarianceItem {
  account_code: string;
  account_name: string;
  budget_amount?: number;
  actual_amount?: number;
  previous_period_amount?: number;
  current_period_amount?: number;
  variance_amount: number;
  variance_percentage: number;
  is_favorable: boolean;
  severity: 'NORMAL' | 'WARNING' | 'CRITICAL' | 'URGENT' | 'INFO';
  tolerance_percentage?: number;
  within_tolerance?: boolean;
  document_type?: string;
}

export interface VarianceSummary {
  total_accounts: number;
  flagged_accounts: number;
  total_budget?: number;
  total_actual?: number;
  total_previous_period?: number;
  total_current_period?: number;
  total_variance_amount: number;
  total_variance_percentage: number;
  severity_breakdown: {
    NORMAL: number;
    WARNING: number;
    CRITICAL: number;
    URGENT: number;
  };
}

export interface BudgetVarianceResponse {
  success: boolean;
  property_id: number;
  property_code: string;
  property_name: string;
  financial_period_id: number;
  period_year: number;
  period_month: number;
  budget_id?: number;
  variance_items: VarianceItem[];
  summary: VarianceSummary;
  alerts_created: number;
}

export interface ForecastVarianceResponse {
  success: boolean;
  property_id: number;
  property_code: string;
  property_name: string;
  financial_period_id: number;
  period_year: number;
  period_month: number;
  forecast_id?: number;
  variance_items: VarianceItem[];
  summary: VarianceSummary;
  alerts_created: number;
}

export interface ComprehensiveVarianceResponse {
  success: boolean;
  property_id: number;
  property_code: string;
  property_name: string;
  financial_period_id: number;
  period_year: number;
  period_month: number;
  budget_variance?: BudgetVarianceResponse;
  forecast_variance?: ForecastVarianceResponse;
}

export interface VarianceTrendData {
  period_year: number;
  period_month: number;
  variance_percentage: number;
  flagged_accounts: number;
}

export interface VarianceTrendResponse {
  success: boolean;
  property_id: number;
  variance_type: 'budget' | 'forecast';
  trend_data: VarianceTrendData[];
  trend_direction: 'improving' | 'stable' | 'deteriorating';
}

export interface PeriodOverPeriodVarianceResponse {
  success: boolean;
  property_id: number;
  property_code: string;
  property_name: string;
  current_period_id: number;
  current_period_year: number;
  current_period_month: number;
  previous_period_id: number;
  previous_period_year: number;
  previous_period_month: number;
  variance_type: 'period_over_period';
  analysis_date: string;
  variance_items: VarianceItem[];
  summary: VarianceSummary;
  alerts_created: number;
}

export interface DataStatusResponse {
  property_id: number;
  period_id: number;
  has_metrics: boolean;
  approved_budget_count: number;
  draft_budget_count: number;
  approved_forecast_count: number;
  draft_forecast_count: number;
}

export interface BudgetLineResponse {
  id: number;
  account_code: string;
  account_name: string | null;
  budgeted_amount: number;
  status: string;
}

export interface ForecastLineResponse {
  id: number;
  account_code: string;
  account_name: string | null;
  forecasted_amount: number;
  status: string;
}

export class VarianceAnalysisService {
  /**
   * Get budget variance for a property and period
   */
  async getBudgetVariance(
    propertyId: number,
    periodId: number,
    budgetId?: number
  ): Promise<BudgetVarianceResponse> {
    const params: any = {};
    if (budgetId) {
      params.budget_id = budgetId;
    }
    return api.get<BudgetVarianceResponse>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/budget`,
      params
    );
  }

  /**
   * Get forecast variance for a property and period
   */
  async getForecastVariance(
    propertyId: number,
    periodId: number,
    forecastId?: number
  ): Promise<ForecastVarianceResponse> {
    const params: any = {};
    if (forecastId) {
      params.forecast_id = forecastId;
    }
    return api.get<ForecastVarianceResponse>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/forecast`,
      params
    );
  }

  /**
   * Get comprehensive variance report (budget + forecast)
   */
  async getComprehensiveVariance(
    propertyId: number,
    periodId: number,
    includeBudget: boolean = true,
    includeForecast: boolean = true
  ): Promise<ComprehensiveVarianceResponse> {
    return api.get<ComprehensiveVarianceResponse>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/comprehensive`,
      {
        include_budget: includeBudget,
        include_forecast: includeForecast
      }
    );
  }

  /**
   * Get variance trend over time
   */
  async getVarianceTrend(
    propertyId: number,
    varianceType: 'budget' | 'forecast' = 'budget',
    lookbackPeriods: number = 6
  ): Promise<VarianceTrendResponse> {
    return api.get<VarianceTrendResponse>(
      `/variance-analysis/properties/${propertyId}/trend`,
      {
        variance_type: varianceType,
        lookback_periods: lookbackPeriods
      }
    );
  }

  /**
   * Get period-over-period variance for a property and period
   */
  async getPeriodOverPeriodVariance(
    propertyId: number,
    periodId: number
  ): Promise<PeriodOverPeriodVarianceResponse> {
    return api.get<PeriodOverPeriodVarianceResponse>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/period-over-period`
    );
  }

  /**
   * Get variance thresholds configuration
   */
  async getThresholds() {
    return api.get('/variance-analysis/thresholds');
  }

  /**
   * Get reconciliation data status (metrics, budget, forecast) for property/period
   */
  async getDataStatus(
    propertyId: number,
    periodId: number
  ): Promise<DataStatusResponse> {
    return api.get<DataStatusResponse>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/data-status`
    );
  }

  /**
   * List budget line items for property/period (for display and inline edit)
   */
  async listBudgetsForPeriod(
    propertyId: number,
    periodId: number
  ): Promise<BudgetLineResponse[]> {
    return api.get<BudgetLineResponse[]>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/budgets`
    );
  }

  /**
   * List forecast line items for property/period (for display and inline edit)
   */
  async listForecastsForPeriod(
    propertyId: number,
    periodId: number
  ): Promise<ForecastLineResponse[]> {
    return api.get<ForecastLineResponse[]>(
      `/variance-analysis/properties/${propertyId}/periods/${periodId}/forecasts`
    );
  }

  /**
   * Update a single budget line (budgeted_amount). Only DRAFT/REVISED.
   */
  async updateBudgetLine(
    budgetId: number,
    body: { budgeted_amount?: number }
  ): Promise<BudgetLineResponse> {
    return api.patch<BudgetLineResponse>(
      `/variance-analysis/budgets/${budgetId}`,
      body
    );
  }

  /**
   * Update a single forecast line (forecasted_amount). Only DRAFT/REVISED.
   */
  async updateForecastLine(
    forecastId: number,
    body: { forecasted_amount?: number }
  ): Promise<ForecastLineResponse> {
    return api.patch<ForecastLineResponse>(
      `/variance-analysis/forecasts/${forecastId}`,
      body
    );
  }
}

// Export singleton
export const varianceAnalysisService = new VarianceAnalysisService();
