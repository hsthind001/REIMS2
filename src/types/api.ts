/**
 * API Type Definitions
 * 
 * TypeScript interfaces for API requests and responses
 */

// ===== User & Authentication =====

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

// ===== Property =====

export interface Property {
  id: number;
  property_code: string;
  property_name: string;
  property_type?: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  country?: string;
  total_area_sqft?: number;
  acquisition_date?: string;
  ownership_structure?: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface PropertyCreate {
  property_code: string;
  property_name: string;
  property_type?: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  country?: string;
  total_area_sqft?: number;
  acquisition_date?: string;
  ownership_structure?: string;
  status?: string;
  notes?: string;
}

// ===== Financial Period =====

export interface FinancialPeriod {
  id: number;
  property_id: number;
  period_year: number;
  period_month: number;
  period_start_date: string;
  period_end_date: string;
  fiscal_year?: number;
  fiscal_quarter?: number;
  is_closed: boolean;
  created_at: string;
}

// ===== Document Upload =====

export interface DocumentUpload {
  id: number;
  property_id: number;
  period_id: number;
  document_type: 'balance_sheet' | 'income_statement' | 'cash_flow' | 'rent_roll';
  file_name: string;
  file_path: string;
  file_size_bytes: number;
  extraction_status: 'pending' | 'processing' | 'completed' | 'failed';
  extraction_started_at?: string;
  extraction_completed_at?: string;
  upload_date: string;
  version: number;
  notes?: string;
}

export interface DocumentUploadRequest {
  property_code: string;
  period_year: number;
  period_month: number;
  document_type: 'balance_sheet' | 'income_statement' | 'cash_flow' | 'rent_roll';
  file: File;
}

export interface DocumentUploadResponse {
  upload_id: number;
  task_id: string;
  message: string;
  file_path: string;
  extraction_status: string;
}

// ===== Financial Data =====

export interface BalanceSheetData {
  id: number;
  property_id: number;
  period_id: number;
  account_code: string;
  account_name: string;
  amount: number;
  is_debit?: boolean;
  is_calculated: boolean;
  extraction_confidence: number;
  needs_review: boolean;
  reviewed: boolean;
  reviewed_by?: number;
  reviewed_at?: string;
  review_notes?: string;
}

export interface IncomeStatementData {
  id: number;
  property_id: number;
  period_id: number;
  account_code: string;
  account_name: string;
  period_amount: number;
  ytd_amount?: number;
  period_percentage?: number;
  ytd_percentage?: number;
  is_income: boolean;
  is_calculated: boolean;
  extraction_confidence: number;
  needs_review: boolean;
  reviewed: boolean;
}

export interface CashFlowData {
  id: number;
  property_id: number;
  period_id: number;
  account_code: string;
  account_name: string;
  period_amount: number;
  ytd_amount?: number;
  cash_flow_category: 'operating' | 'investing' | 'financing';
  is_inflow: boolean;
  extraction_confidence: number;
  needs_review: boolean;
}

export interface RentRollData {
  id: number;
  property_id: number;
  period_id: number;
  unit_number: string;
  tenant_name: string;
  lease_start_date?: string;
  lease_end_date?: string;
  unit_area_sqft?: number;
  monthly_rent: number;
  annual_rent: number;
  occupancy_status: 'occupied' | 'vacant' | 'notice';
  needs_review: boolean;
}

// ===== Financial Metrics =====

export interface FinancialMetrics {
  id: number;
  property_id: number;
  period_id: number;
  total_assets?: number;
  total_liabilities?: number;
  total_equity?: number;
  total_revenue?: number;
  total_expenses?: number;
  net_operating_income?: number;
  net_income?: number;
  operating_margin?: number;
  profit_margin?: number;
  occupancy_rate?: number;
  calculated_at: string;
}

// ===== Review Queue =====

export interface ReviewQueueItem {
  id: number;
  table_name: string;
  property_code: string;
  property_name: string;
  period_year: number;
  period_month: number;
  account_code?: string;
  account_name?: string;
  extraction_confidence: number;
  needs_review_reason?: string;
}

// ===== Chart of Accounts =====

export interface ChartOfAccount {
  id: number;
  account_code: string;
  account_name: string;
  account_type: 'asset' | 'liability' | 'equity' | 'income' | 'expense';
  category?: string;
  subcategory?: string;
  parent_account_code?: string;
  document_types: string[];
  is_calculated: boolean;
  is_active: boolean;
}

// ===== Pagination =====

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

// ===== Reports =====

export interface PropertySummary {
  property: Property;
  period: FinancialPeriod;
  balance_sheet: BalanceSheetData[];
  income_statement: IncomeStatementData[];
  cash_flow: CashFlowData[];
  rent_roll: RentRollData[];
  metrics: FinancialMetrics;
}

