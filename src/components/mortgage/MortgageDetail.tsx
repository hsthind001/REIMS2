/**
 * Mortgage Detail Component
 * 
 * Displays detailed mortgage statement information with payment history
 */
import { useState, useEffect } from 'react';
import { mortgageService } from '../../lib/mortgage';
import type { MortgageStatementDetailResponse } from '../../types/mortgage';
import { X, Calendar, DollarSign, Percent, FileText } from 'lucide-react';

interface MortgageDetailProps {
  mortgageId: number;
  onClose: () => void;
}

export function MortgageDetail({ mortgageId, onClose }: MortgageDetailProps) {
  const [mortgage, setMortgage] = useState<MortgageStatementDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMortgageDetail();
  }, [mortgageId]);

  const loadMortgageDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mortgageService.getMortgageDetail(mortgageId);
      setMortgage(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load mortgage details');
      console.error('Failed to load mortgage detail:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value?: number) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercentage = (value?: number) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(2)}%`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading mortgage details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !mortgage) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Mortgage Details</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="bg-red-50 border border-red-200 rounded p-4">
            <p className="text-red-800">{error || 'Mortgage not found'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-lg p-8 max-w-4xl w-full mx-4 my-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Mortgage Statement Details</h2>
            <p className="text-sm text-gray-500 mt-1">Loan Number: {mortgage.loan_number}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Loan Information */}
          <section className="border-b border-gray-200 pb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <FileText className="h-5 w-5 mr-2" />
              Loan Information
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-gray-500">Loan Type</label>
                <p className="text-sm font-medium">{mortgage.loan_type || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Property Address</label>
                <p className="text-sm font-medium">{mortgage.property_address || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Borrower Name</label>
                <p className="text-sm font-medium">{mortgage.borrower_name || 'N/A'}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Original Loan Amount</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.original_loan_amount)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Interest Rate</label>
                <p className="text-sm font-medium">{formatPercentage(mortgage.interest_rate)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Loan Term</label>
                <p className="text-sm font-medium">
                  {mortgage.loan_term_months ? `${mortgage.loan_term_months} months` : 'N/A'}
                </p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Maturity Date</label>
                <p className="text-sm font-medium">{formatDate(mortgage.maturity_date)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Remaining Term</label>
                <p className="text-sm font-medium">
                  {mortgage.remaining_term_months ? `${mortgage.remaining_term_months} months` : 'N/A'}
                </p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Payment Frequency</label>
                <p className="text-sm font-medium">{mortgage.payment_frequency || 'N/A'}</p>
              </div>
            </div>
          </section>

          {/* Current Balances */}
          <section className="border-b border-gray-200 pb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <DollarSign className="h-5 w-5 mr-2" />
              Current Balances
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-gray-500">Principal Balance</label>
                <p className="text-lg font-bold text-gray-900">{formatCurrency(mortgage.principal_balance)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Tax Escrow</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.tax_escrow_balance)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Insurance Escrow</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.insurance_escrow_balance)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Reserve Balance</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.reserve_balance)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Suspense Balance</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.suspense_balance)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Total Loan Balance</label>
                <p className="text-lg font-bold text-gray-900">{formatCurrency(mortgage.total_loan_balance)}</p>
              </div>
            </div>
          </section>

          {/* Payment Breakdown */}
          <section className="border-b border-gray-200 pb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Calendar className="h-5 w-5 mr-2" />
              Payment Breakdown
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-gray-500">Principal Due</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.principal_due)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Interest Due</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.interest_due)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Tax Escrow Due</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.tax_escrow_due)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Insurance Escrow Due</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.insurance_escrow_due)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Reserve Due</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.reserve_due)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Late Fees</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.late_fees)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Other Fees</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.other_fees)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Total Payment Due</label>
                <p className="text-lg font-bold text-gray-900">{formatCurrency(mortgage.total_payment_due)}</p>
              </div>
            </div>
          </section>

          {/* YTD Totals */}
          <section className="border-b border-gray-200 pb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Year-to-Date Totals</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-gray-500">Principal Paid</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.ytd_principal_paid)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Interest Paid</label>
                <p className="text-sm font-medium">{formatCurrency(mortgage.ytd_interest_paid)}</p>
              </div>
              <div>
                <label className="text-xs text-gray-500">Total Paid</label>
                <p className="text-lg font-bold text-gray-900">{formatCurrency(mortgage.ytd_total_paid)}</p>
              </div>
            </div>
          </section>

          {/* Payment History */}
          {mortgage.payment_history && mortgage.payment_history.length > 0 && (
            <section>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Payment History</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Principal</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Interest</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {mortgage.payment_history.map((payment, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {payment.payment_date ? formatDate(payment.payment_date) : 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-sm text-right">{formatCurrency(payment.principal_paid)}</td>
                        <td className="px-4 py-3 text-sm text-right">{formatCurrency(payment.interest_paid)}</td>
                        <td className="px-4 py-3 text-sm text-right font-medium">
                          {formatCurrency(payment.total_payment)}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded text-xs ${
                            payment.payment_status === 'on_time' ? 'bg-green-100 text-green-800' :
                            payment.payment_status === 'late' ? 'bg-yellow-100 text-yellow-800' :
                            payment.payment_status === 'missed' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {payment.payment_status || 'N/A'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-6 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}


