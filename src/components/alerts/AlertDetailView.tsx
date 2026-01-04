/**
 * Alert Detail View Component
 * Comprehensive view of a single alert with related information
 */
import { useState, useEffect } from 'react';
import { AlertService, type Alert } from '../../lib/alerts';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface AlertDetailViewProps {
  alertId: number;
  onClose?: () => void;
  onAcknowledge?: (alertId: number) => void;
  onResolve?: (alertId: number) => void;
  onDismiss?: (alertId: number) => void;
}

export default function AlertDetailView({
  alertId,
  onClose,
  onAcknowledge,
  onResolve,
  onDismiss
}: AlertDetailViewProps) {
  const [currentAlert, setCurrentAlert] = useState<Alert | null>(null);
  const [relatedAlerts, setRelatedAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showResolutionForm, setShowResolutionForm] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadAlertDetails();
  }, [alertId]);

  const loadAlertDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      const [alertData, relatedData] = await Promise.all([
        AlertService.getAlert(alertId),
        AlertService.getRelatedAlerts(alertId)
      ]);

      setCurrentAlert(alertData);
      setRelatedAlerts(relatedData.related_alerts || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load alert details');
      console.error('Error loading alert:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!currentAlert) return;

    try {
      setActionLoading(true);
      // Get current user ID from auth context or localStorage
      const userId = parseInt(localStorage.getItem('userId') || '1', 10);
      await AlertService.acknowledgeAlert(alertId, userId);
      await loadAlertDetails();
      onAcknowledge?.(alertId);
    } catch (err: any) {
      window.alert(err.message || 'Failed to acknowledge alert');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!currentAlert || !resolutionNotes.trim()) {
      window.alert('Please provide resolution notes');
      return;
    }

    try {
      setActionLoading(true);
      const userId = parseInt(localStorage.getItem('userId') || '1', 10);
      await AlertService.resolveAlert(alertId, userId, resolutionNotes);
      setShowResolutionForm(false);
      setResolutionNotes('');
      await loadAlertDetails();
      onResolve?.(alertId);
    } catch (err: any) {
      window.alert(err.message || 'Failed to resolve alert');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDismiss = async () => {
    if (!currentAlert) return;

    const reason = prompt('Please provide a reason for dismissing this alert:');
    if (!reason) return;

    try {
      setActionLoading(true);
      const userId = parseInt(localStorage.getItem('userId') || '1', 10);
      await AlertService.dismissAlert(alertId, userId, reason);
      await loadAlertDetails();
      onDismiss?.(alertId);
    } catch (err: any) {
      window.alert(err.message || 'Failed to dismiss alert');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading alert details...</p>
      </div>
    );
  }

  if (error || !currentAlert) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#dc3545' }}>
        <p>Error: {error || 'Alert not found'}</p>
        {onClose && (
          <button onClick={onClose} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
            Close
          </button>
        )}
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'URGENT':
      case 'CRITICAL':
        return '#dc3545';
      case 'WARNING':
        return '#ffc107';
      case 'INFO':
        return '#17a2b8';
      default:
        return '#6c757d';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'ACTIVE':
        return '#dc3545';
      case 'ACKNOWLEDGED':
        return '#ffc107';
      case 'RESOLVED':
        return '#28a745';
      case 'DISMISSED':
        return '#6c757d';
      default:
        return '#6c757d';
    }
  };

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem' }}>{currentAlert.title}</h2>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <span style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              background: getSeverityColor(currentAlert.severity),
              color: '#fff',
              fontSize: '0.875rem',
              fontWeight: '600'
            }}>
              {currentAlert.severity}
            </span>
            <span style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              background: getStatusColor(currentAlert.status),
              color: '#fff',
              fontSize: '0.875rem',
              fontWeight: '600'
            }}>
              {currentAlert.status}
            </span>
            {currentAlert.priority_score && (
              <span style={{
                padding: '0.25rem 0.75rem',
                borderRadius: '4px',
                background: '#6c757d',
                color: '#fff',
                fontSize: '0.875rem'
              }}>
                Priority: {currentAlert.priority_score.toFixed(1)}
              </span>
            )}
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              background: '#6c757d',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        )}
      </div>

      {/* Alert Details Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        {/* Basic Information */}
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Basic Information</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Alert Type</div>
              <div style={{ fontWeight: '500' }}>{currentAlert.alert_type.replace(/_/g, ' ')}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Property ID</div>
              <div style={{ fontWeight: '500' }}>{currentAlert.property_id}</div>
            </div>
            {currentAlert.financial_period_id && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Period ID</div>
                <div style={{ fontWeight: '500' }}>{currentAlert.financial_period_id}</div>
              </div>
            )}
            <div>
              <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Assigned Committee</div>
              <div style={{ fontWeight: '500' }}>{currentAlert.assigned_committee.replace(/_/g, ' ')}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Triggered At</div>
              <div style={{ fontWeight: '500' }}>
                {new Date(currentAlert.triggered_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Threshold Information */}
        {(currentAlert.threshold_value !== undefined || currentAlert.actual_value !== undefined) && (
          <div style={{
            padding: '1.5rem',
            background: '#fff',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Threshold Information</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {currentAlert.threshold_value !== undefined && (
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Threshold</div>
                  <div style={{ fontWeight: '500' }}>
                    {currentAlert.threshold_value.toLocaleString()} {currentAlert.threshold_unit || ''}
                  </div>
                </div>
              )}
              {currentAlert.actual_value !== undefined && (
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Actual Value</div>
                  <div style={{ fontWeight: '500' }}>
                    {currentAlert.actual_value.toLocaleString()} {currentAlert.threshold_unit || ''}
                  </div>
                </div>
              )}
              {currentAlert.related_metric && (
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Related Metric</div>
                  <div style={{ fontWeight: '500' }}>{currentAlert.related_metric}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Status Timeline */}
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Status Timeline</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#666' }}>Created</div>
              <div style={{ fontSize: '0.875rem' }}>
                {new Date(currentAlert.triggered_at).toLocaleString()}
              </div>
            </div>
            {currentAlert.acknowledged_at && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>Acknowledged</div>
                <div style={{ fontSize: '0.875rem' }}>
                  {new Date(currentAlert.acknowledged_at).toLocaleString()}
                </div>
              </div>
            )}
            {currentAlert.resolved_at && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>Resolved</div>
                <div style={{ fontSize: '0.875rem' }}>
                  {new Date(currentAlert.resolved_at).toLocaleString()}
                </div>
              </div>
            )}
            {currentAlert.escalated_at && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>Escalated</div>
                <div style={{ fontSize: '0.875rem' }}>
                  {new Date(currentAlert.escalated_at).toLocaleString()} (Level {currentAlert.escalation_level || 0})
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Description */}
      {currentAlert.description && (
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '1.5rem'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Description</h3>
          <p style={{ lineHeight: '1.6', color: '#333' }}>{currentAlert.description}</p>
        </div>
      )}

      {/* Resolution Notes */}
      {currentAlert.resolution_notes && (
        <div style={{
          padding: '1.5rem',
          background: '#f8f9fa',
          borderRadius: '8px',
          marginBottom: '1.5rem'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Resolution Notes</h3>
          <p style={{ lineHeight: '1.6', color: '#333' }}>{currentAlert.resolution_notes}</p>
        </div>
      )}

      {/* Related Alerts */}
      {relatedAlerts.length > 0 && (
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '1.5rem'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>
            Related Alerts ({relatedAlerts.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {relatedAlerts.map((related) => (
              <div
                key={related.id}
                style={{
                  padding: '0.75rem',
                  background: '#f8f9fa',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
                onClick={() => window.location.hash = `#/risk-management?alert=${related.id}`}
              >
                <div style={{ fontWeight: '500' }}>{related.title}</div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>
                  {related.severity} • {related.status} • {new Date(related.triggered_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      {currentAlert.status === 'ACTIVE' && (
        <div style={{
          padding: '1.5rem',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '1.5rem'
        }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Actions</h3>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {!currentAlert.acknowledged_at && (
              <button
                onClick={handleAcknowledge}
                disabled={actionLoading}
                style={{
                  padding: '0.75rem 1.5rem',
                  background: '#ffc107',
                  color: '#000',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: actionLoading ? 'not-allowed' : 'pointer',
                  fontWeight: '600'
                }}
              >
                {actionLoading ? 'Processing...' : 'Acknowledge'}
              </button>
            )}
            <button
              onClick={() => setShowResolutionForm(true)}
              disabled={actionLoading}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#28a745',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontWeight: '600'
              }}
            >
              Resolve
            </button>
            <button
              onClick={handleDismiss}
              disabled={actionLoading}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#6c757d',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading ? 'not-allowed' : 'pointer',
                fontWeight: '600'
              }}
            >
              Dismiss
            </button>
          </div>

          {showResolutionForm && (
            <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f8f9fa', borderRadius: '4px' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                Resolution Notes *
              </label>
              <textarea
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  marginBottom: '1rem'
                }}
                placeholder="Describe how this alert was resolved..."
              />
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={handleResolve}
                  disabled={actionLoading || !resolutionNotes.trim()}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#28a745',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: actionLoading || !resolutionNotes.trim() ? 'not-allowed' : 'pointer'
                  }}
                >
                  Submit Resolution
                </button>
                <button
                  onClick={() => {
                    setShowResolutionForm(false);
                    setResolutionNotes('');
                  }}
                  style={{
                    padding: '0.5rem 1rem',
                    background: '#6c757d',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
