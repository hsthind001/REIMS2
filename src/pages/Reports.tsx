import { useState, useEffect } from 'react';
import { reviewService } from '../lib/review';
import { propertyService } from '../lib/property';
import type { Property } from '../types/api';

export default function Reports() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [reviewQueue, setReviewQueue] = useState<any[]>([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [propertiesData, queueData] = await Promise.all([
        propertyService.getAllProperties(),
        reviewService.getReviewQueue({ limit: 50 })
      ]);

      setProperties(propertiesData);
      setReviewQueue(queueData.items || []);
    } catch (err) {
      console.error('Failed to load data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (item: any) => {
    try {
      await reviewService.approveRecord(item.id, item.table_name, 'Approved from dashboard');
      await loadData(); // Reload
    } catch (err: any) {
      alert(`Approve failed: ${err.message}`);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Reports & Review Queue</h1>
        <p className="page-subtitle">Review extracted data and generate reports</p>
      </div>
      
      <div className="page-content">
        {/* Review Queue */}
        <div className="card">
          <h3>Review Queue ({reviewQueue.length})</h3>
          {loading ? (
            <div className="loading">Loading...</div>
          ) : reviewQueue.length === 0 ? (
            <div className="empty-state">
              ✅ All data reviewed! No items pending review.
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property</th>
                    <th>Period</th>
                    <th>Account</th>
                    <th>Confidence</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewQueue.map((item, index) => (
                    <tr key={index}>
                      <td><strong>{item.property_code}</strong></td>
                      <td>{item.period_year}-{String(item.period_month).padStart(2, '0')}</td>
                      <td>{item.account_code} - {item.account_name}</td>
                      <td>
                        <span className={`confidence-badge ${item.extraction_confidence < 85 ? 'low' : 'high'}`}>
                          {item.extraction_confidence?.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-primary"
                          onClick={() => handleApprove(item)}
                        >
                          Approve
                        </button>
                        <button className="btn btn-sm btn-secondary">
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Financial Summary Selection */}
        <div className="card">
          <h3>Financial Reports</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Select Property</label>
              <select
                value={selectedProperty}
                onChange={(e) => setSelectedProperty(e.target.value)}
              >
                <option value="">Choose property...</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.property_code}>
                    {p.property_code} - {p.property_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedProperty ? (
            <div className="report-summary">
              <p>Select a period and report type to view financial data</p>
              <button className="btn btn-primary">View Balance Sheet</button>
              <button className="btn btn-secondary">View Income Statement</button>
              <button className="btn btn-secondary">View Cash Flow</button>
            </div>
          ) : (
            <div className="empty-state">
              Select a property to view financial reports
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
