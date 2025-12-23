/**
 * Risk Workbench Page
 * 
 * Unified view of anomalies, alerts, and review items
 */

import { useState, useEffect } from 'react';
import RiskWorkbenchTable, { RiskItem } from '../../components/risk-workbench/RiskWorkbenchTable';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export default function RiskWorkbench() {
  const [items, setItems] = useState<RiskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    propertyId: null as number | null,
    documentType: '',
    anomalyCategory: '',
    slaBreach: null as boolean | null,
  });

  useEffect(() => {
    loadRiskItems();
  }, [filters]);

  const loadRiskItems = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.propertyId) params.append('property_id', filters.propertyId.toString());
      if (filters.documentType) params.append('document_type', filters.documentType);
      if (filters.anomalyCategory) params.append('anomaly_category', filters.anomalyCategory);
      if (filters.slaBreach !== null) params.append('sla_breach', filters.slaBreach.toString());
      params.append('page', '1');
      params.append('page_size', '1000');

      const response = await fetch(`${API_BASE_URL}/risk-workbench/unified?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform API response to RiskItem format
      const transformedItems: RiskItem[] = data.items.map((item: any) => ({
        id: item.id,
        type: item.type,
        severity: item.severity.toLowerCase(),
        property_id: item.property_id || 0,
        property_name: item.property_name,
        age_days: Math.floor(item.age_seconds / 86400) || 0,
        impact_amount: item.impact_amount ? parseFloat(item.impact_amount) : undefined,
        status: item.status || 'active',
        assignee: item.assignee,
        due_date: item.due_date,
        title: item.title,
        description: item.description,
        created_at: item.created_at,
        updated_at: item.updated_at,
        metadata: item.metadata || {},
      }));

      setItems(transformedItems);
    } catch (err: any) {
      setError(err.message || 'Failed to load risk items');
      console.error('Error loading risk items:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleItemClick = (item: RiskItem) => {
    // Navigate to detail view based on type
    if (item.type === 'anomaly') {
      window.location.hash = `#anomaly-detail?id=${item.id}`;
    } else if (item.type === 'alert') {
      window.location.hash = `#alert-detail?id=${item.id}`;
    } else if (item.type === 'review_item') {
      window.location.hash = `#review-queue?item=${item.id}`;
    }
  };

  const handleAcknowledge = async (item: RiskItem) => {
    try {
      const response = await fetch(`${API_BASE_URL}/alerts/${item.id}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        await loadRiskItems();
      }
    } catch (err) {
      console.error('Error acknowledging alert:', err);
    }
  };

  const handleResolve = async (item: RiskItem) => {
    try {
      const endpoint = item.type === 'alert' 
        ? `${API_BASE_URL}/alerts/${item.id}/resolve`
        : `${API_BASE_URL}/anomalies/${item.id}/resolve`;
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        await loadRiskItems();
      }
    } catch (err) {
      console.error('Error resolving item:', err);
    }
  };

  const handleReview = (item: RiskItem) => {
    window.location.hash = `#review-queue?item=${item.id}`;
  };

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc3545' }}>
        <p>Error: {error}</p>
        <button 
          onClick={loadRiskItems}
          style={{ marginTop: '1rem', padding: '0.5rem 1rem', borderRadius: '4px', border: '1px solid #ddd' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          Risk Workbench
        </h1>
        <p style={{ color: '#6c757d' }}>
          Unified view of anomalies, alerts, and review items across your portfolio
        </p>
      </div>

      {/* Summary Cards */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem',
      }}>
        <div style={{
          padding: '1.5rem',
          backgroundColor: '#fff',
          borderRadius: '8px',
          border: '1px solid #dee2e6',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 600, color: '#dc3545' }}>
            {items.filter(i => i.severity === 'critical' || i.severity === 'urgent').length}
          </div>
          <div style={{ color: '#6c757d', fontSize: '0.875rem' }}>Critical Items</div>
        </div>
        <div style={{
          padding: '1.5rem',
          backgroundColor: '#fff',
          borderRadius: '8px',
          border: '1px solid #dee2e6',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 600, color: '#fd7e14' }}>
            {items.filter(i => i.type === 'alert').length}
          </div>
          <div style={{ color: '#6c757d', fontSize: '0.875rem' }}>Active Alerts</div>
        </div>
        <div style={{
          padding: '1.5rem',
          backgroundColor: '#fff',
          borderRadius: '8px',
          border: '1px solid #dee2e6',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 600, color: '#0dcaf0' }}>
            {items.filter(i => i.type === 'anomaly').length}
          </div>
          <div style={{ color: '#6c757d', fontSize: '0.875rem' }}>Anomalies</div>
        </div>
        <div style={{
          padding: '1.5rem',
          backgroundColor: '#fff',
          borderRadius: '8px',
          border: '1px solid #dee2e6',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}>
          <div style={{ fontSize: '2rem', fontWeight: 600, color: '#198754' }}>
            {items.filter(i => i.status === 'resolved').length}
          </div>
          <div style={{ color: '#6c757d', fontSize: '0.875rem' }}>Resolved</div>
        </div>
      </div>

      {/* Risk Workbench Table */}
      <RiskWorkbenchTable
        items={items}
        loading={loading}
        onItemClick={handleItemClick}
        onAcknowledge={handleAcknowledge}
        onResolve={handleResolve}
        onReview={handleReview}
      />
    </div>
  );
}
