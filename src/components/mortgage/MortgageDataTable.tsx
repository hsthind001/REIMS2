/**
 * Mortgage Data Table Component
 * 
 * Displays mortgage statements in a table format with key metrics
 */
import { useState, useEffect } from 'react';
import { mortgageService } from '../../lib/mortgage';
import type { MortgageStatement } from '../../types/mortgage';
import { AlertCircle, CheckCircle, Eye, Edit, Trash2 } from 'lucide-react';

interface MortgageDataTableProps {
  propertyId: number;
  periodId: number;
  onViewDetail?: (mortgageId: number) => void;
  onEdit?: (mortgageId: number) => void;
  onDelete?: (mortgageId: number) => void;
}

export function MortgageDataTable({
  propertyId,
  periodId,
  onViewDetail,
  onEdit,
  onDelete
}: MortgageDataTableProps) {
  const [mortgages, setMortgages] = useState<MortgageStatement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMortgages();
  }, [propertyId, periodId]);

  const loadMortgages = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mortgageService.getMortgagesByPropertyPeriod(propertyId, periodId);
      setMortgages(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load mortgage statements');
      console.error('Failed to load mortgages:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value?: number) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
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
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading mortgage statements...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
          <span className="text-red-800">{error}</span>
        </div>
      </div>
    );
  }

  if (mortgages.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-8 text-center">
        <p className="text-gray-600">No mortgage statements found for this period.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Loan Number
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Statement Date
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Principal Balance
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Interest Rate
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Monthly Payment
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Annual Debt Service
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Maturity Date
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {mortgages.map((mortgage) => (
            <tr key={mortgage.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">{mortgage.loan_number}</div>
                {mortgage.loan_type && (
                  <div className="text-xs text-gray-500">{mortgage.loan_type}</div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(mortgage.statement_date)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                {formatCurrency(mortgage.principal_balance)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                {formatPercentage(mortgage.interest_rate)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                {formatCurrency(mortgage.monthly_debt_service)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                {formatCurrency(mortgage.annual_debt_service)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(mortgage.maturity_date)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                {mortgage.needs_review ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Review
                  </span>
                ) : mortgage.has_errors ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Errors
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    OK
                  </span>
                )}
                {mortgage.extraction_confidence !== undefined && (
                  <div className="text-xs text-gray-500 mt-1">
                    {mortgage.extraction_confidence.toFixed(0)}% confidence
                  </div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                <div className="flex items-center justify-center space-x-2">
                  {onViewDetail && (
                    <button
                      onClick={() => onViewDetail(mortgage.id)}
                      className="text-blue-600 hover:text-blue-900"
                      title="View Details"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  )}
                  {onEdit && (
                    <button
                      onClick={() => onEdit(mortgage.id)}
                      className="text-indigo-600 hover:text-indigo-900"
                      title="Edit"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                  )}
                  {onDelete && (
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this mortgage statement?')) {
                          onDelete(mortgage.id);
                        }
                      }}
                      className="text-red-600 hover:text-red-900"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


