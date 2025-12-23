/**
 * Risk Workbench Table Component
 * 
 * Unified table view of anomalies, alerts, and review items
 */

import { useState, useEffect, useMemo } from 'react';
import { Download, Filter, Save, Share2, CheckCircle, XCircle, Eye, AlertCircle } from 'lucide-react';
import { ExportButton } from '../ExportButton';
import { exportToExcel, exportToCSV } from '../../lib/exportUtils';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export interface RiskItem {
  id: number;
  type: 'anomaly' | 'alert' | 'review_item';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'urgent' | 'warning' | 'info';
  property_id: number;
  property_name?: string;
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
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc3545',
  urgent: '#dc3545',
  high: '#fd7e14',
  warning: '#ffc107',
  medium: '#0dcaf0',
  low: '#6c757d',
  info: '#0d6efd',
};

const SEVERITY_BG_COLORS: Record<string, string> = {
  critical: '#fee',
  urgent: '#fee',
  high: '#fff4e6',
  warning: '#fffbf0',
  medium: '#e7f5ff',
  low: '#f8f9fa',
  info: '#e7f3ff',
};

export default function RiskWorkbenchTable({
  items,
  loading = false,
  onItemClick,
  onAcknowledge,
  onResolve,
  onReview,
}: RiskWorkbenchTableProps) {
  const [filters, setFilters] = useState({
    property: '',
    documentType: '',
    category: '',
    severity: '',
  });
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({
    key: 'created_at',
    direction: 'desc',
  });

  const filteredAndSortedItems = useMemo(() => {
    let filtered = [...items];

    // Apply filters
    if (filters.property) {
      filtered = filtered.filter(item => 
        item.property_name?.toLowerCase().includes(filters.property.toLowerCase())
      );
    }
    if (filters.severity) {
      filtered = filtered.filter(item => item.severity === filters.severity);
    }
    if (filters.category && filters.category !== 'all') {
      filtered = filtered.filter(item => 
        item.metadata?.anomaly_category === filters.category
      );
    }

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
  }, [items, filters, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const getExportData = () => {
    return filteredAndSortedItems.map(item => ({
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
    const color = SEVERITY_COLORS[severity] || '#6c757d';
    const bgColor = SEVERITY_BG_COLORS[severity] || '#f8f9fa';
    
    return (
      <span
        style={{
          padding: '0.25rem 0.5rem',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          color,
          backgroundColor: bgColor,
          border: `1px solid ${color}20`,
        }}
      >
        {severity.toUpperCase()}
      </span>
    );
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'anomaly':
        return <AlertCircle size={16} style={{ color: '#dc3545' }} />;
      case 'alert':
        return <AlertCircle size={16} style={{ color: '#fd7e14' }} />;
      case 'review_item':
        return <Eye size={16} style={{ color: '#0dcaf0' }} />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading risk items...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      {/* Filters and Actions */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Filter by property..."
            value={filters.property}
            onChange={(e) => setFilters(prev => ({ ...prev, property: e.target.value }))}
            style={{
              padding: '0.5rem',
              borderRadius: '4px',
              border: '1px solid #ddd',
              minWidth: '200px',
            }}
          />
          <select
            value={filters.severity}
            onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
            style={{
              padding: '0.5rem',
              borderRadius: '4px',
              border: '1px solid #ddd',
            }}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
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
      <div style={{ overflowX: 'auto', border: '1px solid #ddd', borderRadius: '4px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('type')}
              >
                Type
              </th>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('severity')}
              >
                Severity
              </th>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('property_name')}
              >
                Property
              </th>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('age_days')}
              >
                Age
              </th>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('impact_amount')}
              >
                Impact
              </th>
              <th
                style={{
                  padding: '0.75rem',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                onClick={() => handleSort('status')}
              >
                Status
              </th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: 600 }}>
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedItems.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
                  No risk items found
                </td>
              </tr>
            ) : (
              filteredAndSortedItems.map((item) => (
                <tr
                  key={`${item.type}-${item.id}`}
                  style={{
                    borderBottom: '1px solid #dee2e6',
                    cursor: 'pointer',
                  }}
                  onClick={() => onItemClick?.(item)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <td style={{ padding: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {getTypeIcon(item.type)}
                    <span style={{ textTransform: 'capitalize' }}>{item.type.replace('_', ' ')}</span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>{getSeverityBadge(item.severity)}</td>
                  <td style={{ padding: '0.75rem' }}>
                    {item.property_name || `Property ${item.property_id}`}
                  </td>
                  <td style={{ padding: '0.75rem' }}>{item.age_days} days</td>
                  <td style={{ padding: '0.75rem' }}>
                    {item.impact_amount 
                      ? `$${item.impact_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : 'N/A'}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ textTransform: 'capitalize' }}>{item.status}</span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {item.type === 'alert' && onAcknowledge && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onAcknowledge(item);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            border: '1px solid #0dcaf0',
                            backgroundColor: '#fff',
                            color: '#0dcaf0',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          Acknowledge
                        </button>
                      )}
                      {onResolve && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onResolve(item);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            border: '1px solid #198754',
                            backgroundColor: '#fff',
                            color: '#198754',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          Resolve
                        </button>
                      )}
                      {onReview && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onReview(item);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.75rem',
                            border: '1px solid #6c757d',
                            backgroundColor: '#fff',
                            color: '#6c757d',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          Review
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '1rem', color: '#6c757d', fontSize: '0.875rem' }}>
        Showing {filteredAndSortedItems.length} of {items.length} items
      </div>
    </div>
  );
}
