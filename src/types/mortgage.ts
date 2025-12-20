/**
 * Mortgage Statement Types
 */

export interface MortgageStatement {
  id: number;
  property_id: number;
  period_id: number;
  upload_id?: number;
  lender_id?: number;
  loan_number: string;
  loan_type?: string;
  property_address?: string;
  borrower_name?: string;
  statement_date: string;
  payment_due_date?: string;
  statement_period_start?: string;
  statement_period_end?: string;
  principal_balance: number;
  tax_escrow_balance?: number;
  insurance_escrow_balance?: number;
  reserve_balance?: number;
  other_escrow_balance?: number;
  suspense_balance?: number;
  total_loan_balance?: number;
  principal_due?: number;
  interest_due?: number;
  tax_escrow_due?: number;
  insurance_escrow_due?: number;
  reserve_due?: number;
  late_fees?: number;
  other_fees?: number;
  total_payment_due?: number;
  ytd_principal_paid?: number;
  ytd_interest_paid?: number;
  ytd_taxes_disbursed?: number;
  ytd_insurance_disbursed?: number;
  ytd_reserve_disbursed?: number;
  ytd_total_paid?: number;
  original_loan_amount?: number;
  interest_rate?: number;
  loan_term_months?: number;
  maturity_date?: string;
  origination_date?: string;
  payment_frequency?: string;
  amortization_type?: string;
  remaining_term_months?: number;
  ltv_ratio?: number;
  annual_debt_service?: number;
  monthly_debt_service?: number;
  extraction_confidence?: number;
  extraction_method?: string;
  needs_review?: boolean;
  reviewed?: boolean;
  reviewed_by?: number;
  reviewed_at?: string;
  review_notes?: string;
  validation_score?: number;
  has_errors?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface MortgagePayment {
  id: number;
  mortgage_id: number;
  property_id: number;
  payment_date: string;
  payment_number?: number;
  principal_paid: number;
  interest_paid: number;
  escrow_paid?: number;
  fees_paid?: number;
  total_payment: number;
  principal_balance_after?: number;
  escrow_balance_after?: number;
  payment_status?: string;
  days_late?: number;
  created_at?: string;
}

export interface MortgageStatementDetailResponse extends MortgageStatement {
  payment_history?: MortgagePayment[];
  lender?: {
    id: number;
    name: string;
    lender_type?: string;
  };
}

export interface DSCRDataPoint {
  period: string;
  dscr: number;
  status: 'healthy' | 'warning' | 'critical';
  noi: number;
  total_debt_service: number;
}

export interface DSCRHistory {
  property_id: number;
  property_code: string;
  history: DSCRDataPoint[];
  current_dscr?: number;
  average_dscr?: number;
  trend?: 'improving' | 'declining' | 'stable';
}

export interface LTVDataPoint {
  period: string;
  ltv?: number;
  mortgage_debt: number;
  property_value: number;
}

export interface LTVHistory {
  property_id: number;
  property_code: string;
  history: LTVDataPoint[];
  current_ltv?: number;
  average_ltv?: number;
  trend?: 'improving' | 'declining' | 'stable';
}

export interface DebtSummary {
  property_id: number;
  period_id: number;
  total_mortgage_debt: number;
  weighted_avg_interest_rate?: number;
  total_monthly_debt_service: number;
  total_annual_debt_service: number;
  dscr?: number;
  interest_coverage_ratio?: number;
  debt_yield?: number;
  break_even_occupancy?: number;
  ltv?: number;
  mortgage_count: number;
}

export interface CovenantMonitoring {
  property_id: number;
  property_code: string;
  loan_number: string;
  covenant_type: 'dscr' | 'ltv' | 'debt_yield' | 'interest_coverage';
  covenant_value: number;
  threshold: number;
  status: 'compliant' | 'warning' | 'breach';
  period: string;
  severity: 'low' | 'medium' | 'high';
}

export interface MaturityCalendarItem {
  property_id: number;
  property_code: string;
  loan_number: string;
  maturity_date: string;
  months_until_maturity: number;
  principal_balance: number;
  interest_rate: number;
  lender_name?: string;
  status: 'upcoming' | 'due_soon' | 'overdue';
}

export interface MaturityCalendar {
  upcoming_maturities: MaturityCalendarItem[];
  total_upcoming: number;
  due_within_12_months: number;
  due_within_24_months: number;
}
