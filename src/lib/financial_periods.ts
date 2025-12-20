/**
 * Financial Periods Service
 *
 * API calls for managing financial periods
 */

import { api } from './api';

export interface FinancialPeriod {
  id: number;
  property_id: number;
  period_year: number;
  period_month: number;
  is_closed: boolean;
}

export interface FinancialPeriodParams {
  property_id?: number;
  period_year?: number;
  period_month?: number;
}

export interface CreateFinancialPeriodRequest {
  property_id: number;
  period_year: number;
  period_month: number;
}

export class FinancialPeriodsService {
  /**
   * List financial periods with optional filters
   */
  async listPeriods(params?: FinancialPeriodParams): Promise<FinancialPeriod[]> {
    return api.get<FinancialPeriod[]>('/financial-periods', params);
  }

  /**
   * Get a specific financial period by ID
   */
  async getPeriod(periodId: number): Promise<FinancialPeriod> {
    return api.get<FinancialPeriod>(`/financial-periods/${periodId}`);
  }

  /**
   * Create a new financial period (or return existing one)
   */
  async createPeriod(request: CreateFinancialPeriodRequest): Promise<FinancialPeriod> {
    return api.post<FinancialPeriod>('/financial-periods', request);
  }

  /**
   * Get or create a financial period for a property and date
   */
  async getOrCreatePeriod(
    propertyId: number,
    year: number,
    month: number
  ): Promise<FinancialPeriod> {
    // First try to find existing period
    const periods = await this.listPeriods({
      property_id: propertyId,
      period_year: year,
      period_month: month
    });

    if (periods && periods.length > 0) {
      return periods[0];
    }

    // If not found, create it
    return this.createPeriod({
      property_id: propertyId,
      period_year: year,
      period_month: month
    });
  }
}

// Export singleton
export const financialPeriodsService = new FinancialPeriodsService();
