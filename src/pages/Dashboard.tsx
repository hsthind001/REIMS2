import { useState, useEffect } from 'react';
import { propertyService } from '../lib/property';
import { documentService } from '../lib/document';
import { reviewService } from '../lib/review';
import type { Property, DocumentUpload } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export default function Dashboard() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [documents, setDocuments] = useState<DocumentUpload[]>([]);
  const [stats, setStats] = useState({
    totalProperties: 0,
    totalDocuments: 0,
    pendingReviews: 0,
    completedExtractions: 0,
  });
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [propertiesData, documentsResponse, reviewQueueData] = await Promise.all([
        propertyService.getAllProperties(),
        documentService.getDocuments({ limit: 100 }),
        reviewService.getReviewQueue({ limit: 1000 }).catch(() => ({ items: [], total: 0 })) // Fetch review queue, fallback to empty on error
      ]);

      setProperties(propertiesData);
      const docs = documentsResponse.items || documentsResponse as any;
      setDocuments(docs.slice(0, 10)); // Recent 10

      // Calculate stats
      const reviewItems = reviewQueueData.items || [];
      setStats({
        totalProperties: propertiesData.length,
        totalDocuments: (documentsResponse.total || (documentsResponse as any).length),
        pendingReviews: reviewItems.length, // Actual count from review queue
        completedExtractions: docs.filter((d: DocumentUpload) => d.extraction_status === 'completed').length
      });

      // Load quality score
      try {
        const qualityRes = await fetch(`${API_BASE_URL}/quality/score`, { credentials: 'include' });
        if (qualityRes.ok) {
          const qualityData = await qualityRes.json();
          setQualityScore(qualityData.overall_score || null);
        }
      } catch (err) {
        console.error('Failed to load quality score:', err);
      }
    } catch (err) {
      console.error('Failed to load dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'var(--success-color)';
      case 'processing': return 'var(--primary-color)';
      case 'pending': return 'var(--warning-color)';
      case 'failed': return 'var(--error-color)';
      default: return 'var(--secondary-color)';
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p className="page-subtitle">Financial document processing overview</p>
      </div>
      
      <div className="page-content">
        {/* Summary Cards */}
        <div className="dashboard-grid">
          <div className="stat-card">
            <div className="stat-icon" style={{ background: '#e3f2fd' }}>🏢</div>
            <div className="stat-content">
              <div className="stat-value">{stats.totalProperties}</div>
              <div className="stat-label">Total Properties</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: '#f3e5f5' }}>📄</div>
            <div className="stat-content">
              <div className="stat-value">{stats.totalDocuments}</div>
              <div className="stat-label">Documents Uploaded</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: '#e8f5e9' }}>✓</div>
            <div className="stat-content">
              <div className="stat-value">{stats.completedExtractions}</div>
              <div className="stat-label">Completed Extractions</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: '#fff3e0' }}>⏳</div>
            <div className="stat-content">
              <div className="stat-value">{stats.pendingReviews}</div>
              <div className="stat-label">Pending Reviews</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: '#e3f2fd' }}>📊</div>
            <div className="stat-content">
              <div className="stat-value">
                {qualityScore !== null ? `${qualityScore}/100` : 'N/A'}
              </div>
              <div className="stat-label">Data Quality Score</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {qualityScore !== null && qualityScore >= 95 ? '✅ Excellent' : qualityScore !== null && qualityScore >= 90 ? '🟢 Good' : qualityScore !== null && qualityScore >= 80 ? '🟡 Fair' : qualityScore !== null ? '🔴 Needs Attention' : ''}
              </div>
            </div>
          </div>
        </div>

        {/* Properties Overview */}
        <div className="card">
          <h3>Properties</h3>
          {properties.length === 0 ? (
            <div className="empty-state">No properties found</div>
          ) : (
            <div className="properties-grid">
              {properties.map((property) => (
                <div key={property.id} className="property-card">
                  <div className="property-header">
                    <strong>{property.property_code}</strong>
                    <span className={`status-badge status-${property.status}`}>
                      {property.status}
                    </span>
                  </div>
                  <div className="property-name">{property.property_name}</div>
                  <div className="property-info">
                    <div>{property.city}, {property.state}</div>
                    <div>{property.property_type || 'N/A'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Uploads */}
        <div className="card">
          <h3>Recent Document Uploads</h3>
          {documents.length === 0 ? (
            <div className="empty-state">No documents uploaded yet</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td className="filename">{doc.file_name}</td>
                      <td>
                        <span className="badge">{doc.document_type.replace('_', ' ')}</span>
                      </td>
                      <td>
                        <span 
                          className="status-dot" 
                          style={{ 
                            backgroundColor: getStatusColor(doc.extraction_status),
                            display: 'inline-block',
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            marginRight: '0.5rem'
                          }}
                        />
                        {doc.extraction_status}
                      </td>
                      <td>{new Date(doc.upload_date).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
