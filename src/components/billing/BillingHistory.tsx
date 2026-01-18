import { useState, useEffect } from 'react';
import { Download, FileText, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { Invoice } from '../../types/billing';
import { billingService } from '../../services/billingService';

export function BillingHistory() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const data = await billingService.getInvoices(20);
      setInvoices(data);
    } catch (err) {
      console.error('Failed to load invoices:', err);
      setError('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const configs = {
      paid: { icon: CheckCircle, color: 'text-success', label: 'Paid' },
      open: { icon: Clock, color: 'text-warning', label: 'Open' },
      draft: { icon: FileText, color: 'text-text-secondary', label: 'Draft' },
      void: { icon: XCircle, color: 'text-text-secondary', label: 'Void' },
      uncollectible: { icon: XCircle, color: 'text-danger', label: 'Uncollectible' },
    };

    const config = configs[status as keyof typeof configs] || configs.open;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 ${config.color}`}>
        <Icon className="w-4 h-4" />
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="text-center text-text-secondary">Loading invoices...</div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center text-danger">{error}</div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-text-primary">Billing History</h2>
        <div className="text-sm text-text-secondary">
          {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
        </div>
      </div>

      {invoices.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 mx-auto mb-3 text-text-secondary" />
          <p className="text-text-secondary">No invoices yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 font-semibold text-text-primary">Invoice</th>
                <th className="text-left py-3 px-4 font-semibold text-text-primary">Date</th>
                <th className="text-left py-3 px-4 font-semibold text-text-primary">Amount</th>
                <th className="text-left py-3 px-4 font-semibold text-text-primary">Status</th>
                <th className="text-right py-3 px-4 font-semibold text-text-primary">Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} className="border-b border-border hover:bg-background">
                  <td className="py-3 px-4 font-medium text-text-primary">
                    {invoice.invoice_number}
                  </td>
                  <td className="py-3 px-4 text-text-secondary">
                    {new Date(invoice.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 font-semibold text-text-primary">
                    ${invoice.amount.toFixed(2)} {invoice.currency.toUpperCase()}
                  </td>
                  <td className="py-3 px-4">
                    {getStatusBadge(invoice.status)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {invoice.pdf_url ? (
                      <a
                        href={invoice.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-info hover:text-info-dark"
                      >
                        <Download className="w-4 h-4" />
                        <span className="text-sm">Download</span>
                      </a>
                    ) : (
                      <span className="text-sm text-text-secondary">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
