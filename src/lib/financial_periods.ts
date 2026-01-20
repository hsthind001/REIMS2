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
  is_complete?: boolean;
  /**
   * Convenience display name for UI components (e.g., "2024-03")
   */
  name?: string;
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
  private formatPeriodName(period: FinancialPeriod): string {
    if (period.period_year && period.period_month) {
      return `${period.period_year}-${String(period.period_month).padStart(2, '0')}`;
    }
    return `Period ${period.id}`;
  }

  private withDisplayName(period: FinancialPeriod): FinancialPeriod {
    return {
      ...period,
      name: this.formatPeriodName(period),
    };
  }

  /**
   * List financial periods with optional filters
   */
  async listPeriods(params?: FinancialPeriodParams): Promise<FinancialPeriod[]> {
    const periods = await api.get<FinancialPeriod[]>('/financial-periods', params);
    return periods.map((period) => this.withDisplayName(period));
  }

  /**
   * Get a specific financial period by ID
   */
  async getPeriod(periodId: number): Promise<FinancialPeriod> {
    const period = await api.get<FinancialPeriod>(`/financial-periods/${periodId}`);
    return this.withDisplayName(period);
  }

  /**
   * Create a new financial period (or return existing one)
   */
  async createPeriod(request: CreateFinancialPeriodRequest): Promise<FinancialPeriod> {
    const period = await api.post<FinancialPeriod>('/financial-periods', request);
    return this.withDisplayName(period);
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
      return this.withDisplayName(periods[0]);
    }

    // If not found, create it
    return this.createPeriod({
      property_id: propertyId,
      period_year: year,
      period_month: month
    });
  }

  /**
   * Legacy helper used by several dashboards to fetch periods by property
   * Kept for backwards compatibility with earlier component implementations.
   */
  async getPeriods(propertyId: number): Promise<FinancialPeriod[]> {
    return this.listPeriods({ property_id: propertyId });
  }
}

// Export singleton
export const financialPeriodsService = new FinancialPeriodsService();
