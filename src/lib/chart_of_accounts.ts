/**
 * Chart of Accounts Service
 *
 * API calls for chart of accounts management
 */

import { api } from './api';

export interface ChartOfAccount {
  id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  category: string | null;
  subcategory: string | null;
  parent_account_code: string | null;
  document_types: string[] | null;
  is_calculated: boolean;
  calculation_formula: string | null;
  display_order: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ChartOfAccountsSummary {
  total_accounts: number;
  active_accounts: number;
  calculated_accounts: number;
  by_type: {
    [key: string]: number;
  };
}

export interface ChartOfAccountsParams {
  skip?: number;
  limit?: number;
  account_type?: string;
  category?: string;
  subcategory?: string;
  document_type?: string;
  is_calculated?: boolean;
  is_active?: boolean;
  search?: string;
}

export class ChartOfAccountsService {
  /**
   * Get list of chart of accounts with filters
   */
  async getAccounts(params?: ChartOfAccountsParams): Promise<ChartOfAccount[]> {
    return api.get<ChartOfAccount[]>('/chart-of-accounts', params);
  }

  /**
   * Get summary statistics
   */
  async getSummary(): Promise<ChartOfAccountsSummary> {
    return api.get<ChartOfAccountsSummary>('/chart-of-accounts/summary');
  }

  /**
   * Get account by code
   */
  async getAccountByCode(accountCode: string): Promise<ChartOfAccount> {
    return api.get<ChartOfAccount>(`/chart-of-accounts/${accountCode}`);
  }

  /**
   * Get child accounts of a parent
   */
  async getChildren(accountCode: string): Promise<ChartOfAccount[]> {
    return api.get<ChartOfAccount[]>(`/chart-of-accounts/${accountCode}/children`);
  }
}

// Export singleton
export const chartOfAccountsService = new ChartOfAccountsService();
