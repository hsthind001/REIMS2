/**
 * API Type Definitions
 * 
 * TypeScript interfaces for API requests and responses
 */

// ===== User & Authentication =====

export interface Organization {
  id: number;
  name: string;
  slug: string;
  stripe_customer_id?: string;
  subscription_status?: string;
}

export interface OrganizationMember {
  id: number;
  organization_id: number;
  role: string;
  organization: Organization;
}

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  organization_memberships: OrganizationMember[];
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
  organization_name?: string;
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
  /**
   * Convenience display name for UI components (alias of property_name or property_code)
   */
  name?: string;
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
  property_code?: string; // Property code from joined Property table
  period_id: number;
  period_year?: number; // Period year from joined FinancialPeriod table
  period_month?: number; // Period month from joined FinancialPeriod table
  document_type: 'balance_sheet' | 'income_statement' | 'cash_flow' | 'rent_roll' | 'mortgage_statement';
  file_name: string;
  file_path: string;
  file_size_bytes: number;
  extraction_status: 'pending' | 'processing' | 'completed' | 'failed' | 'validating' | 'extracting';
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
  document_type: 'balance_sheet' | 'income_statement' | 'cash_flow' | 'rent_roll' | 'mortgage_statement';
  file: File;
}

export interface DocumentUploadResponse {
  upload_id: number;
  task_id: string;
  message: string;
  file_path: string;
  extraction_status: string;
  file_exists?: boolean;
  existing_file?: {
    path: string;
    size: number;
    last_modified: string;
  };
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
  record_id: number;
  table_name: string;
  property_code: string;
  property_name: string;
  period_year: number;
  period_month: number;
  file_name?: string;
  account_code?: string;
  account_name?: string;
  amount?: number;
  period_amount?: number;
  monthly_rent?: number;
  extraction_confidence: number;
  match_confidence?: number;
  needs_review: boolean;
  reviewed: boolean;
  needs_review_reason?: string;
  created_at: string;
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

// ===== Anomaly Thresholds =====

export interface AnomalyThreshold {
  id: number;
  account_code: string;
  account_name: string;
  threshold_value: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface AccountWithThreshold {
  account_code: string;
  account_name: string;
  account_type: string;
  threshold_value: number | null;
  is_custom: boolean;
  default_threshold: number;
}

export interface DefaultThreshold {
  default_threshold: number;
  description?: string;
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

// ===== Validation Rules =====

export interface RuleStatisticsItem {
  rule_id: number;
  rule_name: string;
  rule_description?: string;
  document_type: string;
  rule_type: string;
  severity: string;
  is_active: boolean;
  total_tests: number;
  passed_count: number;
  failed_count: number;
  pass_rate: number;
  last_executed_at?: string;
  created_at: string;
}

export interface RuleStatisticsSummary {
  total_rules: number;
  active_rules: number;
  total_checks: number;
  overall_pass_rate: number;
  critical_failures: number;
  warnings: number;
  errors: number;
}

export interface RuleStatisticsResponse {
  rules: RuleStatisticsItem[];
  summary: RuleStatisticsSummary;
}

export interface RuleResultItem {
  id: number;
  rule_id: number;
  rule_name?: string;
  rule_description?: string;
  passed: boolean;
  expected_value?: number;
  actual_value?: number;
  difference?: number;
  difference_percentage?: number;
  error_message?: string;
  severity: string;
}

// Validation Analytics Types (Phase 2)
export interface PassRateTrend {
  date: string;
  pass_rate: number;
  total_tests: number;
}

export interface FailureDistribution {
  severity?: string;
  document_type?: string;
  count: number;
  percentage: number;
}

export interface TopFailingRule {
  rule_id: number;
  rule_name: string;
  document_type: string;
  failure_count: number;
  failure_rate: number;
  total_tests: number;
}

export interface DocumentTypePerformance {
  document_type: string;
  total_rules: number;
  total_tests: number;
  pass_rate: number;
  failure_count: number;
}

export interface ValidationAnalyticsResponse {
  pass_rate_trends: {
    '7d': PassRateTrend[];
    '30d': PassRateTrend[];
    '90d': PassRateTrend[];
  };
  failure_distribution: FailureDistribution[];
  top_failing_rules: TopFailingRule[];
  document_type_performance: DocumentTypePerformance[];
}
