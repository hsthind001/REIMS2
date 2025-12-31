/**
 * Enhanced Anomaly Detail Component
 * 
 * Comprehensive anomaly detail view with:
 * - Contribution waterfall charts
 * - Peer/cross-property comparison
 * - Direct links to review queue
 * - PDF coordinates for verification
 * - SHAP/LIME visualizations
 * - Similar cases display
 */

import { useState, useEffect } from 'react';
import { Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { FileText, ExternalLink, AlertCircle, TrendingUp, TrendingDown, Users, Copy } from 'lucide-react';
import { anomaliesService, type Anomaly, type DetailedAnomalyResponse } from '../../lib/anomalies';
import { XAIExplanation } from './XAIExplanation';
import { AnomalyPDFViewer } from '../AnomalyPDFViewer';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface AnomalyDetailProps {
  anomalyId: number;
  onClose?: () => void;
}

interface ContributionData {
  name: string;
  value: number;
  type: 'positive' | 'negative' | 'total';
}

interface PeerComparison {
  property_name: string;
  property_id: number;
  value: number;
  deviation: number;
  percentile: number;
}

interface SimilarCase {
  id: number;
  property_name: string;
  detected_at: string;
  variance: number;
  resolution_type?: string;
  root_cause?: string;
}

export default function AnomalyDetail({ anomalyId, onClose }: AnomalyDetailProps) {
  const [anomaly, setAnomaly] = useState<DetailedAnomalyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [contributionData, setContributionData] = useState<ContributionData[]>([]);
  const [peerComparison, setPeerComparison] = useState<PeerComparison[]>([]);
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [coordinates, setCoordinates] = useState<any>(null);
  const [showPDFViewer, setShowPDFViewer] = useState<boolean>(false);

  useEffect(() => {
    loadAnomalyDetail();
  }, [anomalyId]);

  const loadAnomalyDetail = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load detailed anomaly
      const detailed = await anomaliesService.getAnomalyDetailed(anomalyId);
      setAnomaly(detailed);

      // Load contribution waterfall data
      await loadContributionData(detailed);

      // Load peer comparison
      await loadPeerComparison(detailed);

      // Load similar cases
      await loadSimilarCases(detailed);

      // Load PDF coordinates
      await loadPDFCoordinates(anomalyId);
    } catch (err: any) {
      setError(err.message || 'Failed to load anomaly details');
      console.error('Error loading anomaly detail:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadContributionData = async (anomaly: DetailedAnomalyResponse) => {
    try {
      // Fetch contribution data from backend
      const response = await fetch(`${API_BASE_URL}/anomalies/${anomaly.id}/contribution-waterfall`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setContributionData(data.contributions || []);
      } else {
        setContributionData([]);
      }
    } catch (err) {
      setContributionData([]);
    }
  };

  const loadPeerComparison = async (anomaly: DetailedAnomalyResponse) => {
    try {
      const response = await fetch(`${API_BASE_URL}/anomalies/${anomaly.id}/peer-comparison`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setPeerComparison(data.peers || []);
      }
    } catch (err) {
      console.error('Error loading peer comparison:', err);
    }
  };

  const loadSimilarCases = async (anomaly: DetailedAnomalyResponse) => {
    try {
      const response = await fetch(`${API_BASE_URL}/anomalies/${anomaly.id}/similar-cases`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setSimilarCases(data.similar_cases || []);
      }
    } catch (err) {
      console.error('Error loading similar cases:', err);
    }
  };

  const loadPDFCoordinates = async (anomalyId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/anomalies/${anomalyId}/field-coordinates`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setPdfUrl(data.pdf_url);
        setCoordinates(data.coordinates);
      }
    } catch (err) {
      console.error('Error loading PDF coordinates:', err);
    }
  };

  const generateReviewQueueLink = () => {
    if (!anomaly) return '';
    return `#review-queue?anomaly_id=${anomaly.id}&table_name=${anomaly.details?.document_type || 'income_statement_data'}&record_id=${anomaly.record_id || ''}`;
  };

  const copyReviewLink = () => {
    const link = generateReviewQueueLink();
    navigator.clipboard.writeText(window.location.origin + link);
    alert('Review queue link copied to clipboard!');
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading anomaly details...</p>
      </div>
    );
  }

  if (error || !anomaly) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc3545' }}>
        <p>Error: {error || 'Anomaly not found'}</p>
        <button onClick={onClose} style={{ marginTop: '1rem', padding: '0.5rem 1rem', borderRadius: '4px' }}>
          Close
        </button>
      </div>
    );
  }

  const accountCode = anomaly.account_code || anomaly.field_name || 'N/A';
  const fieldName =
    anomaly.field_name && anomaly.account_code && anomaly.field_name !== anomaly.account_code
      ? anomaly.field_name
      : null;

  return (
    <div style={{
      padding: '2rem',
      backgroundColor: '#fff',
      borderRadius: '8px',
      maxHeight: '90vh',
      overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem',
        paddingBottom: '1rem',
        borderBottom: '2px solid #dee2e6',
      }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            Anomaly Details
          </h2>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6c757d' }}>
            <span>ID: {anomaly.id}</span>
            <span>•</span>
            <span>Account Code: {accountCode}</span>
            {fieldName && (
              <>
                <span>•</span>
                <span>Field: {fieldName}</span>
              </>
            )}
            <span style={{
              padding: '0.25rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: anomaly.severity === 'critical' ? '#fee' : '#fff3cd',
              color: anomaly.severity === 'critical' ? '#dc3545' : '#856404',
              fontWeight: 600,
            }}>
              {anomaly.severity.toUpperCase()}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              borderRadius: '4px',
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Main Content Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem',
      }}>
        {/* Values Comparison */}
        <div style={{
          padding: '1.5rem',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
            Values
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                Actual Value
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#dc3545' }}>
                {typeof anomaly.actual_value === 'number'
                  ? `$${anomaly.actual_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : anomaly.actual_value || 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                Expected Value
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0c5460' }}>
                {typeof anomaly.expected_value === 'number'
                  ? `$${anomaly.expected_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  : anomaly.expected_value || 'N/A'}
              </div>
            </div>
            {anomaly.deviation && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '0.25rem' }}>
                  Deviation
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                  {typeof anomaly.deviation === 'number'
                    ? `$${Math.abs(anomaly.deviation).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : anomaly.deviation}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{
          padding: '1.5rem',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
            Quick Actions
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <a
              href={generateReviewQueueLink()}
              style={{
                padding: '0.75rem',
                borderRadius: '4px',
                border: '1px solid #0dcaf0',
                backgroundColor: '#e7f5ff',
                color: '#0dcaf0',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontWeight: 600,
              }}
            >
              <ExternalLink size={18} />
              Go to Review Queue
            </a>
            <button
              onClick={copyReviewLink}
              style={{
                padding: '0.75rem',
                borderRadius: '4px',
                border: '1px solid #6c757d',
                backgroundColor: '#fff',
                color: '#6c757d',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontWeight: 600,
              }}
            >
              <Copy size={18} />
              Copy Review Link
            </button>
            {pdfUrl && (
              <button
                onClick={() => setShowPDFViewer(true)}
                style={{
                  padding: '0.75rem',
                  borderRadius: '4px',
                  border: '1px solid #198754',
                  backgroundColor: '#d4edda',
                  color: '#198754',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontWeight: 600,
                }}
              >
                <FileText size={18} />
                View PDF Coordinates
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Contribution Waterfall */}
      {contributionData.length > 0 && (
        <div style={{
          padding: '1.5rem',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
            Contribution Waterfall
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={contributionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#0dcaf0">
                {contributionData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.type === 'total' ? '#198754' : entry.type === 'positive' ? '#dc3545' : '#6c757d'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Peer Comparison */}
      {peerComparison.length > 0 && (
        <div style={{
          padding: '1.5rem',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={18} />
            Peer/Cross-Property Comparison
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Property</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Value</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Deviation</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Percentile</th>
                </tr>
              </thead>
              <tbody>
                {peerComparison.map((peer, index) => (
                  <tr key={index} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={{ padding: '0.75rem' }}>{peer.property_name}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      ${peer.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td style={{
                      padding: '0.75rem',
                      textAlign: 'right',
                      color: peer.deviation > 0 ? '#dc3545' : '#198754',
                    }}>
                      {peer.deviation > 0 ? '+' : ''}${peer.deviation.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      {peer.percentile.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SHAP/LIME Visualizations */}
      <div style={{
        padding: '1.5rem',
        border: '1px solid #dee2e6',
        borderRadius: '8px',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
          Explainable AI (XAI) Insights
        </h3>
        <XAIExplanation anomalyId={anomalyId} autoLoad={true} />
      </div>

      {/* Similar Cases */}
      {similarCases.length > 0 && (
        <div style={{
          padding: '1.5rem',
          border: '1px solid #dee2e6',
          borderRadius: '8px',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} />
            Similar Cases
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {similarCases.map((similar) => (
              <div
                key={similar.id}
                style={{
                  padding: '1rem',
                  border: '1px solid #dee2e6',
                  borderRadius: '4px',
                  backgroundColor: '#f8f9fa',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <div style={{ fontWeight: 600 }}>{similar.property_name}</div>
                  <a
                    href={`#anomaly-details?anomaly_id=${similar.id}`}
                    style={{
                      color: '#0dcaf0',
                      textDecoration: 'none',
                      fontSize: '0.875rem',
                    }}
                  >
                    View Details →
                  </a>
                </div>
                <div style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '0.5rem' }}>
                  Detected: {new Date(similar.detected_at).toLocaleDateString()}
                  {similar.variance && ` • Variance: $${similar.variance.toLocaleString()}`}
                </div>
                {similar.resolution_type && (
                  <div style={{ fontSize: '0.875rem', color: '#198754' }}>
                    Resolved: {similar.resolution_type}
                    {similar.root_cause && ` • ${similar.root_cause}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PDF Viewer Modal */}
      {showPDFViewer && pdfUrl && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '90%',
            height: '90%',
            backgroundColor: '#fff',
            borderRadius: '8px',
            position: 'relative',
          }}>
            <AnomalyPDFViewer
              pdfUrl={pdfUrl}
              coordinates={coordinates}
              highlightType="actual"
              onClose={() => setShowPDFViewer(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
