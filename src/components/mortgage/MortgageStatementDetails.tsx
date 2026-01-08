/**
 * Mortgage Statement Details Component
 *
 * Displays detailed mortgage statement data in table format similar to financial statements
 */
import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Card } from '../design-system';

interface MortgageData {
  id: number;
  loan_number: string;
  lender_name?: string;
  statement_date: string;
  payment_due_date?: string;

  // Balances
  principal_balance: number;
  tax_escrow_balance?: number;
  insurance_escrow_balance?: number;
  reserve_balance?: number;
  other_escrow_balance?: number;
  suspense_balance?: number;
  total_loan_balance?: number;

  // Payment Due
  principal_due?: number;
  interest_due?: number;
  tax_escrow_due?: number;
  insurance_escrow_due?: number;
  reserve_due?: number;
  late_fees?: number;
  other_fees?: number;
  total_payment_due?: number;

  // Loan Details
  interest_rate?: number;
  original_loan_amount?: number;
  maturity_date?: string;
  origination_date?: string;
  remaining_term_months?: number;
  payment_frequency?: string;
  loan_term_months?: number;
  amortization_type?: string;

  // YTD
  ytd_principal_paid?: number;
  ytd_interest_paid?: number;
  ytd_taxes_disbursed?: number;
  ytd_insurance_disbursed?: number;
  ytd_reserve_disbursed?: number;
  ytd_total_paid?: number;

  // Calculated
  monthly_debt_service?: number;
  annual_debt_service?: number;
  ltv_ratio?: number;

  // Metadata
  extraction_confidence?: number;
  needs_review: boolean;
  reviewed?: boolean;
  has_errors?: boolean;
}

interface MortgageStatementDetailsProps {
  propertyId: number;
  periodYear: number;
  periodMonth: number;
}

interface MortgageField {
  label: string;
  value: any;
  category: string;
  isTotal?: boolean;
}

export function MortgageStatementDetails({
  propertyId,
  periodYear,
  periodMonth
}: MortgageStatementDetailsProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mortgageData, setMortgageData] = useState<MortgageData[]>([]);

  // Helper function to safely format currency values
  const formatCurrency = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === null || value === undefined) {
      return '0.00';
    }
    return value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };

  const formatDate = (value: string | undefined | null): string => {
    if (!value) return '-';
    try {
      return new Date(value).toLocaleDateString();
    } catch {
      return value;
    }
  };

  const formatPercent = (value: number | undefined | null): string => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(3)}%`;
  };

  useEffect(() => {
    loadMortgageData();
  }, [propertyId, periodYear, periodMonth]);

  const loadMortgageData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Get financial period first
      const periods = await api.get<any[]>(
        `/financial-periods?property_id=${propertyId}&period_year=${periodYear}&period_month=${periodMonth}`
      );

      if (!periods || periods.length === 0) {
        setError(`No financial period found for ${periodYear}/${periodMonth}`);
        setMortgageData([]);
        return;
      }

      const periodId = periods[0].id;

      // Get mortgage data for this period - using correct endpoint
      const data = await api.get<MortgageData[]>(
        `/mortgage/properties/${propertyId}/periods/${periodId}`
      );

      setMortgageData(data || []);
    } catch (err: any) {
      console.error('Failed to load mortgage data:', err);
      setError(err?.message || 'Failed to load mortgage statement data');
      setMortgageData([]);
    } finally {
      setLoading(false);
    }
  };

  // Convert mortgage object to field array for table display
  const getMortgageFields = (mortgage: MortgageData): MortgageField[] => {
    return [
      // Loan Identification
      { label: 'Loan Number', value: mortgage.loan_number, category: 'Loan Identification' },
      { label: 'Lender Name', value: mortgage.lender_name || '-', category: 'Loan Identification' },
      { label: 'Statement Date', value: formatDate(mortgage.statement_date), category: 'Loan Identification' },
      { label: 'Payment Due Date', value: formatDate(mortgage.payment_due_date), category: 'Loan Identification' },

      // Current Balances
      { label: 'Principal Balance', value: `$${formatCurrency(mortgage.principal_balance)}`, category: 'Current Balances' },
      { label: 'Tax Escrow Balance', value: `$${formatCurrency(mortgage.tax_escrow_balance)}`, category: 'Current Balances' },
      { label: 'Insurance Escrow Balance', value: `$${formatCurrency(mortgage.insurance_escrow_balance)}`, category: 'Current Balances' },
      { label: 'Reserve Balance', value: `$${formatCurrency(mortgage.reserve_balance)}`, category: 'Current Balances' },
      { label: 'Other Escrow Balance', value: `$${formatCurrency(mortgage.other_escrow_balance)}`, category: 'Current Balances' },
      { label: 'Suspense Balance', value: `$${formatCurrency(mortgage.suspense_balance)}`, category: 'Current Balances' },
      { label: 'Total Loan Balance', value: `$${formatCurrency(mortgage.total_loan_balance)}`, category: 'Current Balances', isTotal: true },

      // Payment Due
      { label: 'Principal Due', value: `$${formatCurrency(mortgage.principal_due)}`, category: 'Payment Due' },
      { label: 'Interest Due', value: `$${formatCurrency(mortgage.interest_due)}`, category: 'Payment Due' },
      { label: 'Tax Escrow Due', value: `$${formatCurrency(mortgage.tax_escrow_due)}`, category: 'Payment Due' },
      { label: 'Insurance Escrow Due', value: `$${formatCurrency(mortgage.insurance_escrow_due)}`, category: 'Payment Due' },
      { label: 'Reserve Due', value: `$${formatCurrency(mortgage.reserve_due)}`, category: 'Payment Due' },
      { label: 'Late Fees', value: `$${formatCurrency(mortgage.late_fees)}`, category: 'Payment Due' },
      { label: 'Other Fees', value: `$${formatCurrency(mortgage.other_fees)}`, category: 'Payment Due' },
      { label: 'Total Payment Due', value: `$${formatCurrency(mortgage.total_payment_due)}`, category: 'Payment Due', isTotal: true },

      // Loan Terms
      { label: 'Interest Rate', value: formatPercent(mortgage.interest_rate), category: 'Loan Terms' },
      { label: 'Original Loan Amount', value: mortgage.original_loan_amount ? `$${formatCurrency(mortgage.original_loan_amount, 0)}` : '-', category: 'Loan Terms' },
      { label: 'Maturity Date', value: formatDate(mortgage.maturity_date), category: 'Loan Terms' },
      { label: 'Origination Date', value: formatDate(mortgage.origination_date), category: 'Loan Terms' },
      { label: 'Loan Term (Months)', value: mortgage.loan_term_months || '-', category: 'Loan Terms' },
      { label: 'Remaining Term (Months)', value: mortgage.remaining_term_months || '-', category: 'Loan Terms' },
      { label: 'Payment Frequency', value: mortgage.payment_frequency || '-', category: 'Loan Terms' },
      { label: 'Amortization Type', value: mortgage.amortization_type || '-', category: 'Loan Terms' },

      // Year-to-Date Totals
      { label: 'YTD Principal Paid', value: `$${formatCurrency(mortgage.ytd_principal_paid)}`, category: 'Year-to-Date Totals' },
      { label: 'YTD Interest Paid', value: `$${formatCurrency(mortgage.ytd_interest_paid)}`, category: 'Year-to-Date Totals' },
      { label: 'YTD Taxes Disbursed', value: `$${formatCurrency(mortgage.ytd_taxes_disbursed)}`, category: 'Year-to-Date Totals' },
      { label: 'YTD Insurance Disbursed', value: `$${formatCurrency(mortgage.ytd_insurance_disbursed)}`, category: 'Year-to-Date Totals' },
      { label: 'YTD Reserve Disbursed', value: `$${formatCurrency(mortgage.ytd_reserve_disbursed)}`, category: 'Year-to-Date Totals' },
      { label: 'YTD Total Paid', value: `$${formatCurrency(mortgage.ytd_total_paid)}`, category: 'Year-to-Date Totals', isTotal: true },

      // Calculated Metrics
      { label: 'Monthly Debt Service', value: mortgage.monthly_debt_service ? `$${formatCurrency(mortgage.monthly_debt_service)}` : '-', category: 'Calculated Metrics' },
      { label: 'Annual Debt Service', value: mortgage.annual_debt_service ? `$${formatCurrency(mortgage.annual_debt_service)}` : '-', category: 'Calculated Metrics' },
      { label: 'LTV Ratio', value: mortgage.ltv_ratio ? `${(mortgage.ltv_ratio * 100).toFixed(2)}%` : '-', category: 'Calculated Metrics' },
    ];
  };

  const getStatusColor = (extraction_confidence?: number, needs_review?: boolean, has_errors?: boolean) => {
    if (has_errors) return 'text-danger';
    if (needs_review) return 'text-warning';
    if (!extraction_confidence) return 'text-text-tertiary';
    if (extraction_confidence >= 95) return 'text-success';
    if (extraction_confidence >= 85) return 'text-warning';
    return 'text-danger';
  };

  const getStatusIcon = (extraction_confidence?: number, needs_review?: boolean, has_errors?: boolean) => {
    if (has_errors) return '🔴';
    if (needs_review) return '🟡';
    if (!extraction_confidence) return '⚪';
    if (extraction_confidence >= 95) return '🟢';
    if (extraction_confidence >= 85) return '🟡';
    return '🔴';
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="text-text-secondary mb-2">Loading mortgage statement details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6 bg-yellow-50 border-yellow-200">
        <div className="text-center text-yellow-800">
          <div className="text-xl mb-2">⚠️</div>
          <div>{error}</div>
        </div>
      </Card>
    );
  }

  if (mortgageData.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center text-text-secondary">
          <div className="text-4xl mb-4">📄</div>
          <div className="text-lg font-semibold mb-2">No Mortgage Data Available</div>
          <div className="text-sm">
            No mortgage statements found for {periodYear}/{String(periodMonth).padStart(2, '0')}.
          </div>
          <div className="text-xs mt-2">
            Upload a mortgage statement to view details here.
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {mortgageData.map((mortgage, index) => {
        const fields = getMortgageFields(mortgage);
        let currentCategory = '';

        return (
          <Card key={mortgage.id} className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-lg font-semibold">
                  Mortgage Statement - Complete Field Data
                </h4>
                <p className="text-sm text-text-secondary mt-1">
                  Showing all {fields.length} extracted fields • Loan #{mortgage.loan_number}
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm text-text-secondary">
                  {mortgage.lender_name || 'Unknown Lender'}
                </div>
                <div className="text-xs text-text-tertiary">
                  Statement: {formatDate(mortgage.statement_date)}
                </div>
              </div>
            </div>

            <div className="overflow-x-auto max-h-[600px] overflow-y-auto border border-border rounded-lg">
              <table className="w-full">
                <thead className="sticky top-0 bg-surface z-10 border-b-2 border-border">
                  <tr>
                    <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Field</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Category</th>
                    <th className="text-right py-3 px-4 text-sm font-semibold bg-surface">Value</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Confidence</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((field, idx) => {
                    const showCategoryHeader = field.category !== currentCategory;
                    currentCategory = field.category;

                    return (
                      <tr
                        key={idx}
                        className={`border-b border-border hover:bg-background ${
                          field.isTotal ? 'font-bold bg-info-light/10' : ''
                        }`}
                      >
                        <td className="py-2 px-4">
                          <div className="flex items-center gap-2">
                            {field.label}
                            {field.isTotal && (
                              <span className="px-2 py-0.5 bg-info text-white rounded text-xs">
                                TOTAL
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2 px-4">
                          {showCategoryHeader && (
                            <span className="px-2 py-1 bg-premium/10 text-premium rounded text-xs font-medium">
                              {field.category}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-4 text-right font-medium">
                          {field.value}
                        </td>
                        <td className="py-2 px-4 text-center">
                          <div className="text-xs">
                            {mortgage.extraction_confidence
                              ? `${mortgage.extraction_confidence.toFixed(1)}%`
                              : '-'
                            }
                          </div>
                        </td>
                        <td className="py-2 px-4 text-center">
                          <span className={getStatusColor(mortgage.extraction_confidence, mortgage.needs_review, mortgage.has_errors)}>
                            {getStatusIcon(mortgage.extraction_confidence, mortgage.needs_review, mortgage.has_errors)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Quality Indicator */}
            <div className="mt-4 pt-4 border-t border-border">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <div className="flex items-center gap-4">
                  <div>
                    Extraction Confidence: <span className={getStatusColor(mortgage.extraction_confidence)}>
                      {mortgage.extraction_confidence ? `${mortgage.extraction_confidence.toFixed(1)}%` : 'N/A'}
                    </span>
                  </div>
                  {mortgage.needs_review && (
                    <div className="text-warning">⚠️ Needs Review</div>
                  )}
                  {mortgage.has_errors && (
                    <div className="text-danger">❌ Has Errors</div>
                  )}
                  {mortgage.reviewed && (
                    <div className="text-success">✓ Reviewed</div>
                  )}
                </div>
                <div className="text-text-tertiary">
                  Total Fields: {fields.length}
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
