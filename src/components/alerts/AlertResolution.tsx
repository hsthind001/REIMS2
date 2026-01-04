/**
 * Alert Resolution Component
 * Structured resolution workflow for alerts
 */
import { useState } from 'react';
import { type Alert } from '../../lib/alerts';

interface AlertResolutionProps {
  alert: Alert;
  onResolve: (alertId: number, resolutionData: ResolutionData) => Promise<void>;
  onCancel: () => void;
}

export interface ResolutionData {
  resolution_notes: string;
  action_items?: string[];
  evidence_documents?: number[];
  resolution_type: 'fixed' | 'false_positive' | 'mitigated' | 'deferred';
}

export default function AlertResolution({ alert, onResolve, onCancel }: AlertResolutionProps) {
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [resolutionType, setResolutionType] = useState<'fixed' | 'false_positive' | 'mitigated' | 'deferred'>('fixed');
  const [actionItems, setActionItems] = useState<string[]>(['']);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleActionItemChange = (index: number, value: string) => {
    const newItems = [...actionItems];
    newItems[index] = value;
    setActionItems(newItems);
  };

  const addActionItem = () => {
    setActionItems([...actionItems, '']);
  };

  const removeActionItem = (index: number) => {
    if (actionItems.length > 1) {
      setActionItems(actionItems.filter((_, i) => i !== index));
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!resolutionNotes.trim()) {
      newErrors.notes = 'Resolution notes are required';
    }

    if (resolutionNotes.trim().length < 20) {
      newErrors.notes = 'Resolution notes must be at least 20 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      return;
    }

    try {
      setLoading(true);

      const resolutionData: ResolutionData = {
        resolution_notes: resolutionNotes,
        action_items: actionItems.filter(item => item.trim()),
        resolution_type: resolutionType
      };

      await onResolve(alert.id, resolutionData);
    } catch (err: any) {
      window.alert(err.message || 'Failed to resolve alert');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      padding: '1.5rem',
      background: '#fff',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      maxWidth: '800px',
      margin: '0 auto'
    }}>
      <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Resolve Alert</h2>

      {/* Alert Summary */}
      <div style={{
        padding: '1rem',
        background: '#f8f9fa',
        borderRadius: '4px',
        marginBottom: '1.5rem'
      }}>
        <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>{alert.title}</div>
        <div style={{ fontSize: '0.875rem', color: '#666' }}>
          {alert.alert_type.replace(/_/g, ' ')} • {alert.severity} • Property {alert.property_id}
        </div>
      </div>

      {/* Resolution Type */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Resolution Type *
        </label>
        <select
          value={resolutionType}
          onChange={(e) => setResolutionType(e.target.value as any)}
          style={{
            width: '100%',
            padding: '0.75rem',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
        >
          <option value="fixed">Issue Fixed</option>
          <option value="false_positive">False Positive</option>
          <option value="mitigated">Risk Mitigated</option>
          <option value="deferred">Deferred for Later Review</option>
        </select>
      </div>

      {/* Resolution Notes */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Resolution Notes *
        </label>
        <textarea
          value={resolutionNotes}
          onChange={(e) => setResolutionNotes(e.target.value)}
          rows={6}
          style={{
            width: '100%',
            padding: '0.75rem',
            border: errors.notes ? '1px solid #dc3545' : '1px solid #ddd',
            borderRadius: '4px',
            fontFamily: 'inherit'
          }}
          placeholder="Describe how this alert was resolved, what actions were taken, and any follow-up required..."
        />
        {errors.notes && (
          <div style={{ color: '#dc3545', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            {errors.notes}
          </div>
        )}
      </div>

      {/* Action Items */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
          Action Items (Optional)
        </label>
        {actionItems.map((item, index) => (
          <div key={index} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <input
              type="text"
              value={item}
              onChange={(e) => handleActionItemChange(index, e.target.value)}
              placeholder={`Action item ${index + 1}`}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            />
            {actionItems.length > 1 && (
              <button
                onClick={() => removeActionItem(index)}
                style={{
                  padding: '0.75rem 1rem',
                  background: '#dc3545',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Remove
              </button>
            )}
          </div>
        ))}
        <button
          onClick={addActionItem}
          style={{
            padding: '0.5rem 1rem',
            background: '#6c757d',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.875rem'
          }}
        >
          + Add Action Item
        </button>
      </div>

      {/* Resolution Type Descriptions */}
      <div style={{
        padding: '1rem',
        background: '#f8f9fa',
        borderRadius: '4px',
        marginBottom: '1.5rem',
        fontSize: '0.875rem'
      }}>
        <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>Resolution Type Guidelines:</div>
        <ul style={{ margin: 0, paddingLeft: '1.5rem', lineHeight: '1.8' }}>
          <li><strong>Issue Fixed:</strong> The underlying problem has been resolved</li>
          <li><strong>False Positive:</strong> The alert was triggered incorrectly</li>
          <li><strong>Risk Mitigated:</strong> Actions taken to reduce risk, but issue may persist</li>
          <li><strong>Deferred:</strong> Will be addressed in a future review cycle</li>
        </ul>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
        <button
          onClick={onCancel}
          disabled={loading}
          style={{
            padding: '0.75rem 1.5rem',
            background: '#6c757d',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: '600'
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading || !resolutionNotes.trim()}
          style={{
            padding: '0.75rem 1.5rem',
            background: '#28a745',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: loading || !resolutionNotes.trim() ? 'not-allowed' : 'pointer',
            fontWeight: '600'
          }}
        >
          {loading ? 'Resolving...' : 'Submit Resolution'}
        </button>
      </div>
    </div>
  );
}
