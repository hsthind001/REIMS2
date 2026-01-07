/**
 * Mortgage Statement Details Component
 *
 * Displays detailed mortgage statement data for a property/period
 */
import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { Card } from '../ui/Card';

interface MortgageData {
  id: number;
  loan_number: string;
  lender_name?: string;
  statement_date: string;
  payment_due_date?: string;

  // Balances
  principal_balance: number;
  tax_escrow_balance: number;
  insurance_escrow_balance: number;
  reserve_balance: number;
  other_escrow_balance: number;
  suspense_balance: number;
  total_loan_balance: number;

  // Payment Due
  principal_due: number;
  interest_due: number;
  tax_escrow_due: number;
  insurance_escrow_due: number;
  reserve_due: number;
  late_fees: number;
  other_fees: number;
  total_payment_due: number;

  // Loan Details
  interest_rate: number;
  original_loan_amount?: number;
  maturity_date?: string;
  origination_date?: string;
  remaining_term_months?: number;
  payment_frequency?: string;

  // YTD
  ytd_principal_paid: number;
  ytd_interest_paid: number;
  ytd_taxes_disbursed: number;
  ytd_insurance_disbursed: number;
  ytd_reserve_disbursed: number;
  ytd_total_paid: number;

  // Calculated
  monthly_debt_service?: number;
  annual_debt_service?: number;
  ltv_ratio?: number;

  // Metadata
  extraction_confidence?: number;
  needs_review: boolean;
}

interface MortgageStatementDetailsProps {
  propertyId: number;
  periodYear: number;
  periodMonth: number;
}

export function MortgageStatementDetails({
  propertyId,
  periodYear,
  periodMonth
}: MortgageStatementDetailsProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mortgageData, setMortgageData] = useState<MortgageData[]>([]);

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

      // Get mortgage data for this period
      const data = await api.get<MortgageData[]>(
        `/mortgage-statements?property_id=${propertyId}&period_id=${periodId}`
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
      {mortgageData.map((mortgage, index) => (
        <Card key={mortgage.id} className="p-6">
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-semibold">
                Mortgage Statement - Loan #{mortgage.loan_number}
              </h4>
              <div className="text-sm text-text-secondary">
                {mortgage.lender_name || 'Unknown Lender'}
              </div>
            </div>
            {mortgage.statement_date && (
              <div className="text-sm text-text-secondary mt-1">
                Statement Date: {new Date(mortgage.statement_date).toLocaleDateString()}
              </div>
            )}
          </div>

          {/* Balances Section */}
          <div className="mb-6">
            <h5 className="text-md font-semibold mb-3">Current Balances</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Principal Balance</div>
                <div className="text-lg font-bold">${mortgage.principal_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Tax Escrow</div>
                <div className="text-lg font-semibold">${mortgage.tax_escrow_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Insurance Escrow</div>
                <div className="text-lg font-semibold">${mortgage.insurance_escrow_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Total Loan Balance</div>
                <div className="text-lg font-bold text-info">${mortgage.total_loan_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
          </div>

          {/* Payment Due Section */}
          <div className="mb-6">
            <h5 className="text-md font-semibold mb-3">Payment Due {mortgage.payment_due_date ? `(Due: ${new Date(mortgage.payment_due_date).toLocaleDateString()})` : ''}</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Principal</div>
                <div className="text-lg font-semibold">${mortgage.principal_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Interest</div>
                <div className="text-lg font-semibold">${mortgage.interest_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Tax Escrow</div>
                <div className="text-lg font-semibold">${mortgage.tax_escrow_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded border-2 border-info">
                <div className="text-xs text-text-secondary">Total Payment Due</div>
                <div className="text-lg font-bold text-info">${mortgage.total_payment_due.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
          </div>

          {/* Loan Details Section */}
          <div className="mb-6">
            <h5 className="text-md font-semibold mb-3">Loan Details</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Interest Rate</div>
                <div className="text-lg font-semibold">{mortgage.interest_rate.toFixed(3)}%</div>
              </div>
              {mortgage.original_loan_amount && (
                <div className="bg-background p-3 rounded">
                  <div className="text-xs text-text-secondary">Original Amount</div>
                  <div className="text-lg font-semibold">${mortgage.original_loan_amount.toLocaleString()}</div>
                </div>
              )}
              {mortgage.maturity_date && (
                <div className="bg-background p-3 rounded">
                  <div className="text-xs text-text-secondary">Maturity Date</div>
                  <div className="text-lg font-semibold">{new Date(mortgage.maturity_date).toLocaleDateString()}</div>
                </div>
              )}
              {mortgage.remaining_term_months && (
                <div className="bg-background p-3 rounded">
                  <div className="text-xs text-text-secondary">Remaining Term</div>
                  <div className="text-lg font-semibold">{mortgage.remaining_term_months} months</div>
                </div>
              )}
            </div>
          </div>

          {/* YTD Section */}
          <div className="mb-4">
            <h5 className="text-md font-semibold mb-3">Year-to-Date Summary</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Principal Paid</div>
                <div className="text-lg font-semibold">${mortgage.ytd_principal_paid.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Interest Paid</div>
                <div className="text-lg font-semibold">${mortgage.ytd_interest_paid.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded">
                <div className="text-xs text-text-secondary">Taxes Disbursed</div>
                <div className="text-lg font-semibold">${mortgage.ytd_taxes_disbursed.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="bg-background p-3 rounded border-2 border-success">
                <div className="text-xs text-text-secondary">Total YTD Paid</div>
                <div className="text-lg font-bold text-success">${mortgage.ytd_total_paid.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
          </div>

          {/* Quality Indicator */}
          {mortgage.extraction_confidence && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <div>
                  Extraction Confidence: {mortgage.extraction_confidence.toFixed(1)}%
                </div>
                {mortgage.needs_review && (
                  <div className="text-warning">⚠️ Needs Review</div>
                )}
              </div>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
