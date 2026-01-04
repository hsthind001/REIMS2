/**
 * Bulk Anomaly Actions Component
 * 
 * Enables bulk resolution of similar anomalies with pattern matching
 */

import { useState, useEffect, useMemo } from 'react';
import { CheckSquare, Square, Filter, X, CheckCircle, AlertCircle } from 'lucide-react';
import { anomaliesService, type Anomaly } from '../../lib/anomalies';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface BulkAnomalyActionsProps {
  anomalies: Anomaly[];
  onBulkResolve?: (anomalyIds: number[], resolution: string) => void;
  onClose?: () => void;
}

interface PatternMatch {
  pattern: string;
  count: number;
  anomalies: Anomaly[];
}

export default function BulkAnomalyActions({
  anomalies,
  onBulkResolve,
  onClose,
}: BulkAnomalyActionsProps) {
  const [selectedAnomalies, setSelectedAnomalies] = useState<Set<number>>(new Set());
  const [patternMatches, setPatternMatches] = useState<PatternMatch[]>([]);
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);
  const [resolution, setResolution] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    analyzePatterns();
  }, [anomalies]);

  const analyzePatterns = () => {
    // Group anomalies by pattern
    const patterns: Record<string, Anomaly[]> = {};

    anomalies.forEach(anomaly => {
      // Create pattern key based on characteristics
      const patternKey = [
        anomaly.field_name || anomaly.account_code,
        anomaly.anomaly_type,
        anomaly.severity,
        // Group by similar magnitude (within 20%)
        anomaly.actual_value && anomaly.expected_value
          ? Math.floor(Math.abs(Number(anomaly.actual_value) - Number(anomaly.expected_value)) / (Number(anomaly.expected_value) * 0.2))
          : 'unknown',
      ].join('|');

      if (!patterns[patternKey]) {
        patterns[patternKey] = [];
      }
      patterns[patternKey].push(anomaly);
    });

    // Convert to PatternMatch array
    const matches: PatternMatch[] = Object.entries(patterns)
      .filter(([_, anomalies]) => anomalies.length > 1) // Only patterns with multiple anomalies
      .map(([pattern, anomalies]) => ({
        pattern,
        count: anomalies.length,
        anomalies,
      }))
      .sort((a, b) => b.count - a.count); // Sort by count descending

    setPatternMatches(matches);
  };

  const handlePatternSelect = (pattern: string) => {
    setSelectedPattern(pattern);
    const match = patternMatches.find(m => m.pattern === pattern);
    if (match) {
      setSelectedAnomalies(new Set(match.anomalies.map(a => a.id)));
    }
  };

  const handleAnomalyToggle = (anomalyId: number) => {
    setSelectedAnomalies(prev => {
      const next = new Set(prev);
      if (next.has(anomalyId)) {
        next.delete(anomalyId);
      } else {
        next.add(anomalyId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedPattern) {
      const match = patternMatches.find(m => m.pattern === selectedPattern);
      if (match) {
        setSelectedAnomalies(new Set(match.anomalies.map(a => a.id)));
      }
    } else {
      setSelectedAnomalies(new Set(anomalies.map(a => a.id)));
    }
  };

  const handleDeselectAll = () => {
    setSelectedAnomalies(new Set());
  };

  const handleBulkResolve = async () => {
    if (selectedAnomalies.size === 0) {
      alert('Please select at least one anomaly to resolve');
      return;
    }

    if (!resolution.trim()) {
      alert('Please provide a resolution reason');
      return;
    }

    setLoading(true);
    try {
      const anomalyIds = Array.from(selectedAnomalies);
      
      // Resolve each anomaly
      await Promise.all(
        anomalyIds.map(id =>
          fetch(`${API_BASE_URL}/anomalies/${id}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resolution }),
          })
        )
      );

      onBulkResolve?.(anomalyIds, resolution);
      
      // Clear selection
      setSelectedAnomalies(new Set());
      setResolution('');
      setSelectedPattern(null);
    } catch (err) {
      console.error('Error resolving anomalies:', err);
      alert('Failed to resolve anomalies. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getPatternDescription = (pattern: string): string => {
    const parts = pattern.split('|');
    return `${parts[0]} - ${parts[1]} (${parts[2]})`;
  };

  return (
    <div style={{
      padding: '1.5rem',
      backgroundColor: '#fff',
      borderRadius: '8px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
      }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
          Bulk Anomaly Actions
        </h3>
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
            <X size={20} />
          </button>
        )}
      </div>

      {/* Pattern Matching */}
      {patternMatches.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.75rem',
          }}>
            <Filter size={18} />
            <h4 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>
              Similar Patterns ({patternMatches.length})
            </h4>
          </div>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            maxHeight: '200px',
            overflowY: 'auto',
            border: '1px solid #dee2e6',
            borderRadius: '4px',
            padding: '0.5rem',
          }}>
            {patternMatches.map(match => (
              <button
                key={match.pattern}
                onClick={() => handlePatternSelect(match.pattern)}
                style={{
                  padding: '0.75rem',
                  border: selectedPattern === match.pattern ? '2px solid #0dcaf0' : '1px solid #dee2e6',
                  borderRadius: '4px',
                  backgroundColor: selectedPattern === match.pattern ? '#e7f5ff' : '#fff',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>{getPatternDescription(match.pattern)}</span>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: '#0dcaf0',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}>
                  {match.count} items
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Selection Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        padding: '0.75rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '4px',
      }}>
        <div>
          <strong>{selectedAnomalies.size}</strong> of <strong>{anomalies.length}</strong> selected
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={handleSelectAll}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #0dcaf0',
              borderRadius: '4px',
              backgroundColor: '#fff',
              color: '#0dcaf0',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            Select All
          </button>
          <button
            onClick={handleDeselectAll}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #6c757d',
              borderRadius: '4px',
              backgroundColor: '#fff',
              color: '#6c757d',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            Deselect All
          </button>
        </div>
      </div>

      {/* Anomaly List */}
      <div style={{
        maxHeight: '400px',
        overflowY: 'auto',
        border: '1px solid #dee2e6',
        borderRadius: '4px',
        marginBottom: '1rem',
      }}>
        {anomalies.map(anomaly => (
          <div
            key={anomaly.id}
            style={{
              padding: '0.75rem',
              borderBottom: '1px solid #dee2e6',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              backgroundColor: selectedAnomalies.has(anomaly.id) ? '#e7f5ff' : '#fff',
            }}
          >
            <button
              onClick={() => handleAnomalyToggle(anomaly.id)}
              style={{
                border: 'none',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              {selectedAnomalies.has(anomaly.id) ? (
                <CheckSquare size={20} style={{ color: '#0dcaf0' }} />
              ) : (
                <Square size={20} style={{ color: '#6c757d' }} />
              )}
            </button>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                {anomaly.field_name || anomaly.account_code}
              </div>
              <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                {anomaly.anomaly_type} • {anomaly.severity}
                {anomaly.actual_value && anomaly.expected_value && (
                  <span> • Variance: ${Math.abs(Number(anomaly.actual_value) - Number(anomaly.expected_value)).toLocaleString()}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resolution Input */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
          Resolution Reason:
        </label>
        <textarea
          value={resolution}
          onChange={(e) => setResolution(e.target.value)}
          placeholder="Enter resolution reason for bulk action..."
          style={{
            width: '100%',
            padding: '0.75rem',
            borderRadius: '4px',
            border: '1px solid #dee2e6',
            minHeight: '100px',
            resize: 'vertical',
          }}
        />
      </div>

      {/* Action Button */}
      <button
        onClick={handleBulkResolve}
        disabled={selectedAnomalies.size === 0 || !resolution.trim() || loading}
        style={{
          width: '100%',
          padding: '0.75rem',
          borderRadius: '4px',
          border: 'none',
          backgroundColor: selectedAnomalies.size === 0 || !resolution.trim() || loading ? '#6c757d' : '#198754',
          color: '#fff',
          fontWeight: 600,
          cursor: selectedAnomalies.size === 0 || !resolution.trim() || loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
        }}
      >
        {loading ? (
          <>
            <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
            Resolving...
          </>
        ) : (
          <>
            <CheckCircle size={18} />
            Resolve {selectedAnomalies.size} Anomaly{selectedAnomalies.size !== 1 ? 'ies' : ''}
          </>
        )}
      </button>
    </div>
  );
}
