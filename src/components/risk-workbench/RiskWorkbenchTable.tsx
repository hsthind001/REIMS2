/**
 * Risk Workbench Table Component
 * 
 * Unified table view of anomalies, alerts, and review items
 */

import { useState, useMemo } from 'react';
import { Eye, AlertCircle, Trash2, ArrowUp, ArrowDown } from 'lucide-react';
import { ExportButton } from '../ExportButton';
import { Skeleton } from '../ui/Skeleton';
import { Button } from '../ui/Button';

export interface RiskItem {
  id: number;
  type: 'anomaly' | 'alert' | 'review_item';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'urgent' | 'warning' | 'info';
  property_id: number;
  property_name?: string;
  account_code?: string;
  account_name?: string;
  age_days: number;
  impact_amount?: number;
  status: string;
  assignee?: string;
  due_date?: string;
  title?: string;
  description?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

interface RiskWorkbenchTableProps {
  items: RiskItem[];
  loading?: boolean;
  onItemClick?: (item: RiskItem) => void;
  onAcknowledge?: (item: RiskItem) => void;
  onResolve?: (item: RiskItem) => void;
  onReview?: (item: RiskItem) => void;
  onDelete?: (item: RiskItem) => void;
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  urgent: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  medium: 'bg-blue-100 text-blue-800 border-blue-200',
  low: 'bg-gray-100 text-gray-800 border-gray-200',
  info: 'bg-sky-100 text-sky-800 border-sky-200',
};

export default function RiskWorkbenchTable({
  items,
  loading = false,
  onItemClick,
  onAcknowledge,
  onResolve,
  onReview,
  onDelete,
}: RiskWorkbenchTableProps) {
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({
    key: 'created_at',
    direction: 'desc',
  });

  const filteredAndSortedItems = useMemo(() => {
    let filtered = [...items];

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[sortConfig.key as keyof RiskItem];
      const bValue = b[sortConfig.key as keyof RiskItem];
      
      if (aValue === undefined || aValue === null) return 1;
      if (bValue === undefined || bValue === null) return -1;
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' 
          ? aValue - bValue
          : bValue - aValue;
      }
      
      return 0;
    });

    return filtered;
  }, [items, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const getExportData = () => {
    return filteredAndSortedItems.map(item => ({
      'Account Code': item.account_code || '',
      'Account Name': item.account_name || '',
      Type: item.type,
      Severity: item.severity,
      Property: item.property_name || `Property ${item.property_id}`,
      'Age (Days)': item.age_days,
      'Impact Amount': item.impact_amount || 0,
      Status: item.status,
      Assignee: item.assignee || 'Unassigned',
      'Due Date': item.due_date || '',
      Title: item.title || '',
      'Created At': item.created_at,
    }));
  };

  const getSeverityBadge = (severity: string) => {
    const style = SEVERITY_STYLES[severity] || 'bg-gray-100 text-gray-800 border-gray-200';
    
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${style}`}>
        {severity.toUpperCase()}
      </span>
    );
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'anomaly':
        return <AlertCircle size={16} className="text-red-500" />;
      case 'alert':
        return <AlertCircle size={16} className="text-orange-500" />;
      case 'review_item':
        return <Eye size={16} className="text-blue-500" />;
      default:
        return null;
    }
  };

  const renderSortIcon = (key: string) => {
    if (sortConfig.key !== key) return <div className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-30 inline-block" />;
    return sortConfig.direction === 'asc' 
      ? <ArrowUp size={14} className="ml-1 inline-block text-blue-500" />
      : <ArrowDown size={14} className="ml-1 inline-block text-blue-500" />;
  };

  const TableHeader = ({ prop, label }: { prop: string, label: string }) => (
    <th
      className="px-4 py-3 text-left font-semibold text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors group select-none whitespace-nowrap"
      onClick={() => handleSort(prop)}
    >
      <div className="flex items-center">
        {label}
        {renderSortIcon(prop)}
      </div>
    </th>
  );

  return (
    <div className="p-6">
      {/* Actions */}
      <div className="flex justify-end items-center mb-6">
        <div className="flex gap-2">
          <ExportButton
            data={getExportData()}
            filename={`risk-workbench-${new Date().toISOString().split('T')[0]}`}
            format="both"
            sheetName="Risk Items"
            variant="secondary"
            size="md"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-gray-200 rounded-lg shadow-sm">
        {loading ? (
          <div className="p-4 space-y-4">
            {[...Array(6)].map((_, idx) => (
              <div key={idx} className="flex gap-4 items-center">
                <Skeleton className="w-[12%] h-4" />
                <Skeleton className="w-[18%] h-4" />
                <Skeleton className="w-[10%] h-4" />
                <Skeleton className="w-[10%] h-4" />
                <Skeleton className="w-[14%] h-4" />
                <Skeleton className="w-[8%] h-4" />
                <Skeleton className="w-[10%] h-4" />
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <TableHeader prop="account_code" label="Account Code" />
                <TableHeader prop="account_name" label="Account Name" />
                <TableHeader prop="type" label="Type" />
                <TableHeader prop="severity" label="Severity" />
                <TableHeader prop="property_name" label="Property" />
                <TableHeader prop="age_days" label="Age" />
                <TableHeader prop="impact_amount" label="Impact" />
                <TableHeader prop="status" label="Status" />
                <th className="px-4 py-3 text-left font-semibold text-gray-900">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAndSortedItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                    No risk items found
                  </td>
                </tr>
              ) : (
                filteredAndSortedItems.map((item) => (
                  <tr
                    key={`${item.type}-${item.id}`}
                    className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                    onClick={() => onItemClick?.(item)}
                  >
                    <td className="px-4 py-3 font-mono text-sm text-gray-600">
                      {item.account_code || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {item.account_name || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(item.type)}
                        <span className="capitalize">{item.type.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {getSeverityBadge(item.severity)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {item.property_name || `Property ${item.property_id}`}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {item.age_days} days
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {item.impact_amount !== undefined && item.impact_amount !== null
                        ? `$${item.impact_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : 'N/A'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize 
                        ${item.status === 'active' ? 'bg-green-100 text-green-800' : 
                          item.status === 'resolved' ? 'bg-gray-100 text-gray-800' : 
                          'bg-blue-100 text-blue-800'}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                        {item.type === 'alert' && onAcknowledge && (
                          <Button
                            onClick={() => onAcknowledge(item)}
                            variant="secondary"
                            size="sm"
                            className="bg-white border-blue-200 text-blue-600 hover:bg-blue-50 text-xs px-2 py-1 h-auto"
                          >
                            Acknowledge
                          </Button>
                        )}
                        {onResolve && (
                          <Button
                            onClick={() => onResolve(item)}
                            variant="secondary"
                            size="sm"
                             className="bg-white border-green-200 text-green-600 hover:bg-green-50 text-xs px-2 py-1 h-auto"
                          >
                            Resolve
                          </Button>
                        )}
                        {onReview && (
                          <Button
                            onClick={() => onReview(item)}
                            variant="secondary"
                            size="sm"
                             className="bg-white border-gray-200 text-gray-600 hover:bg-gray-50 text-xs px-2 py-1 h-auto"
                          >
                            Review
                          </Button>
                        )}
                        {item.type === 'alert' && onDelete && (
                          <Button
                            onClick={() => onDelete(item)}
                            variant="danger"
                            size="sm"
                            className="text-xs px-2 py-1 h-auto flex items-center gap-1"
                            title="Delete this alert"
                          >
                            <Trash2 size={12} />
                            Delete
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-4 text-sm text-gray-500">
        Showing {filteredAndSortedItems.length} of {items.length} items
      </div>
    </div>
  );
}
