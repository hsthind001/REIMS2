/**
 * Reports & Analytics Service
 */

import { api } from './api';
import type { PropertySummary, FinancialMetrics } from '../types/api';

export class ReportsService {
  /**
   * Get property summary for a specific period
   */
  async getPropertySummary(
    propertyCode: string,
    year: number,
    month: number
  ): Promise<PropertySummary> {
    return api.get<PropertySummary>(`/reports/summary/${propertyCode}/${year}/${month}`);
  }

  /**
   * Get portfolio dashboard data
   */
  async getPortfolioDashboard(): Promise<any> {
    return api.get<any>('/reports/portfolio-dashboard');
  }

  /**
   * Get period comparison
   */
  async getPeriodComparison(
    propertyCode: string,
    startYear: number,
    startMonth: number,
    endYear: number,
    endMonth: number
  ): Promise<any> {
    return api.get<any>('/reports/period-comparison', {
      property_code: propertyCode,
      start_year: startYear,
      start_month: startMonth,
      end_year: endYear,
      end_month: endMonth
    });
  }

  /**
   * Get annual trends
   */
  async getAnnualTrends(
    propertyCode: string,
    year: number,
    accountCodes?: string[]
  ): Promise<any> {
    const params = accountCodes ? `?account_codes=${accountCodes.join(',')}` : '';
    return api.get<any>(`/reports/trends/${propertyCode}/${year}${params}`);
  }

  /**
   * Get metrics for a property/period
   */
  async getMetrics(
    propertyCode: string,
    year: number,
    month: number
  ): Promise<FinancialMetrics> {
    return api.get<FinancialMetrics>('/metrics/property', {
      property_code: propertyCode,
      year,
      month
    });
  }
}

// Export singleton
export const reportsService = new ReportsService();

