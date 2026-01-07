/**
 * Mortgage API Service
 * 
 * Handles all mortgage-related API calls
 */
import { api } from './api';
import type {
  MortgageStatement,
  MortgageStatementDetailResponse,
  DSCRHistory,
  LTVHistory,
  DebtSummary,
  CovenantMonitoring,
  MaturityCalendar,
  LatestCompleteDSCR
} from '../types/mortgage';

export const mortgageService = {
  /**
   * Get all mortgage statements for a property and period
   */
  async getMortgagesByPropertyPeriod(
    propertyId: number,
    periodId: number
  ): Promise<MortgageStatement[]> {
    try {
      return await api.get<MortgageStatement[]>(
        `/mortgage/properties/${propertyId}/periods/${periodId}`
      );
    } catch (error: any) {
      console.error('Failed to fetch mortgages:', error);
      throw new Error(error.message || 'Failed to fetch mortgage statements');
    }
  },

  /**
   * Get detailed mortgage statement with payment history
   */
  async getMortgageDetail(mortgageId: number): Promise<MortgageStatementDetailResponse> {
    try {
      return await api.get<MortgageStatementDetailResponse>(`/mortgage/${mortgageId}`);
    } catch (error: any) {
      console.error('Failed to fetch mortgage detail:', error);
      throw new Error(error.message || 'Failed to fetch mortgage details');
    }
  },

  /**
   * Update mortgage statement
   */
  async updateMortgage(mortgageId: number, updates: Partial<MortgageStatement>): Promise<MortgageStatement> {
    try {
      return await api.put<MortgageStatement>(`/mortgage/${mortgageId}`, updates);
    } catch (error: any) {
      console.error('Failed to update mortgage:', error);
      throw new Error(error.message || 'Failed to update mortgage statement');
    }
  },

  /**
   * Delete mortgage statement
   */
  async deleteMortgage(mortgageId: number): Promise<void> {
    try {
      await api.delete(`/mortgage/${mortgageId}`);
    } catch (error: any) {
      console.error('Failed to delete mortgage:', error);
      throw new Error(error.message || 'Failed to delete mortgage statement');
    }
  },

  /**
   * Get DSCR history for a property
   */
  async getDSCRHistory(
    propertyId: number,
    limit: number = 12
  ): Promise<DSCRHistory> {
    try {
      return await api.get<DSCRHistory>(
        `/mortgage/properties/${propertyId}/dscr-history?limit=${limit}`
      );
    } catch (error: any) {
      console.error('Failed to fetch DSCR history:', error);
      throw new Error(error.message || 'Failed to fetch DSCR history');
    }
  },

  /**
   * Get LTV history for a property
   */
  async getLTVHistory(
    propertyId: number,
    limit: number = 12
  ): Promise<LTVHistory> {
    try {
      return await api.get<LTVHistory>(
        `/mortgage/properties/${propertyId}/ltv-history?limit=${limit}`
      );
    } catch (error: any) {
      console.error('Failed to fetch LTV history:', error);
      throw new Error(error.message || 'Failed to fetch LTV history');
    }
  },

  /**
   * Get comprehensive debt summary for a property/period
   */
  async getDebtSummary(
    propertyId: number,
    periodId: number
  ): Promise<DebtSummary> {
    try {
      return await api.get<DebtSummary>(
        `/mortgage/properties/${propertyId}/periods/${periodId}/debt-summary`
      );
    } catch (error: any) {
      console.error('Failed to fetch debt summary:', error);
      throw new Error(error.message || 'Failed to fetch debt summary');
    }
  },

  /**
   * Get covenant monitoring dashboard
   */
  async getCovenantMonitoring(propertyId?: number): Promise<CovenantMonitoring[]> {
    try {
      const url = propertyId
        ? `/mortgage/covenant-monitoring?property_id=${propertyId}`
        : '/mortgage/covenant-monitoring';
      return await api.get<CovenantMonitoring[]>(url);
    } catch (error: any) {
      console.error('Failed to fetch covenant monitoring:', error);
      throw new Error(error.message || 'Failed to fetch covenant monitoring');
    }
  },

  /**
   * Get loan maturity calendar
   */
  async getMaturityCalendar(monthsAhead: number = 24): Promise<MaturityCalendar> {
    try {
      return await api.get<MaturityCalendar>(
        `/mortgage/maturity-calendar?months_ahead=${monthsAhead}`
      );
    } catch (error: any) {
      console.error('Failed to fetch maturity calendar:', error);
      throw new Error(error.message || 'Failed to fetch maturity calendar');
    }
  },

  /**
   * Get DSCR for the latest COMPLETE period (has both income and mortgage data)
   *
   * This method ensures DSCR is calculated only when complete data is available,
   * preventing N/A or NULL values when the latest period by date is incomplete.
   */
  async getLatestCompleteDSCR(
    propertyId: number,
    year?: number
  ): Promise<LatestCompleteDSCR> {
    try {
      const url = year
        ? `/mortgage/properties/${propertyId}/dscr/latest-complete?year=${year}`
        : `/mortgage/properties/${propertyId}/dscr/latest-complete`;
      return await api.get<LatestCompleteDSCR>(url);
    } catch (error: any) {
      console.error('Failed to fetch latest complete DSCR:', error);
      throw new Error(error.message || 'Failed to fetch latest complete DSCR');
    }
  }
};


