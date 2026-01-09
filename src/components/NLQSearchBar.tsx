/**
 * NLQ Search Bar Component
 *
 * Comprehensive natural language query interface with:
 * - Temporal support
 * - Confidence scoring
 * - Quick suggestions
 * - Error handling
 */

import { useState } from 'react';
import { nlqService, type NLQQueryResponse } from '../services/nlqService';
import '../App.css';

interface NLQSearchBarProps {
  propertyCode?: string;
  propertyId?: number;
  userId?: number;
  compact?: boolean;
  onResult?: (result: NLQQueryResponse) => void;
}

export default function NLQSearchBar({
  propertyCode,
  propertyId,
  userId,
  compact = false,
  onResult,
}: NLQSearchBarProps) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NLQQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showData, setShowData] = useState(false);

  const handleSearch = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await nlqService.query({
        question,
        context: {
          property_code: propertyCode,
          property_id: propertyId,
          user_id: userId,
        },
        user_id: userId,
      });

      setResult(response);
      if (onResult) {
        onResult(response);
      }
    } catch (err: any) {
      setError(err.message || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSearch();
    }
  };

  const quickQuestions = [
    `What was cash position in November 2025?`,
    `How is DSCR calculated?`,
    `Show revenue for Q4 2025`,
    `Calculate current ratio${propertyCode ? ` for ${propertyCode}` : ''}`,
  ];

  const getConfidenceColor = (score: number): string => {
    if (score >= 0.8) return '#10b981'; // green
    if (score >= 0.6) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const formatTime = (ms?: number): string => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="nlq-search-container" style={{
      maxWidth: compact ? '100%' : '900px',
      margin: compact ? '0' : '20px auto',
    }}>
      {!compact && (
        <div style={{ marginBottom: '16px' }}>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '20px', color: 'var(--primary)' }}>
            💬 Ask a Question
          </h3>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>
            Ask anything about your financial data in natural language
          </p>
        </div>
      )}

      {/* Search Input */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
        <input
          type="text"
          className="input"
          placeholder="e.g., What was cash position in November 2025?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={loading}
          style={{ flex: 1, padding: '12px', fontSize: '15px' }}
        />
        <button
          className="btn-primary"
          onClick={handleSearch}
          disabled={loading || !question.trim()}
          style={{ padding: '12px 24px', whiteSpace: 'nowrap' }}
        >
          {loading ? '🔄 Thinking...' : '🔍 Ask'}
        </button>
      </div>

      {/* Quick Questions */}
      {!result && !loading && !error && !compact && (
        <div style={{ marginBottom: '16px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 8px 0' }}>
            Try asking:
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {quickQuestions.map((q, idx) => (
              <button
                key={idx}
                className="btn-secondary"
                onClick={() => setQuestion(q)}
                style={{
                  padding: '6px 12px',
                  fontSize: '13px',
                  border: '1px solid var(--border)',
                  borderRadius: '16px',
                  background: '#e6f7ff',
                  color: 'var(--primary)',
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
          <p style={{ color: 'var(--text-muted)' }}>Analyzing your question...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="alert alert-error">
          <span>❌</span>
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="card" style={{ background: '#f9fafb', borderLeft: '4px solid #10b981' }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
            paddingBottom: '12px',
            borderBottom: '1px solid var(--border)',
          }}>
            <h4 style={{ margin: 0, color: '#10b981', fontSize: '16px' }}>✅ Answer</h4>
            <div style={{ display: 'flex', gap: '16px', fontSize: '13px' }}>
              <span style={{
                color: getConfidenceColor(result.confidence_score),
                fontWeight: 600,
              }}>
                Confidence: {(result.confidence_score * 100).toFixed(0)}%
              </span>
              {result.execution_time_ms && (
                <span style={{ color: 'var(--text-muted)' }}>
                  ⚡ {formatTime(result.execution_time_ms)}
                </span>
              )}
            </div>
          </div>

          {/* Answer */}
          <div style={{ fontSize: '15px', lineHeight: '1.6', color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
            {result.answer}
          </div>

          {/* Data */}
          {result.data && result.data.length > 0 && (
            <details
              style={{
                marginTop: '16px',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                background: '#fff',
              }}
              open={showData}
              onToggle={(e) => setShowData((e.target as HTMLDetailsElement).open)}
            >
              <summary style={{
                padding: '12px',
                cursor: 'pointer',
                fontWeight: 600,
                color: 'var(--primary)',
                userSelect: 'none',
              }}>
                📊 View Raw Data ({result.data.length} records)
              </summary>
              <pre style={{
                margin: 0,
                padding: '16px',
                background: '#f5f5f5',
                borderTop: '1px solid var(--border)',
                overflowX: 'auto',
                fontSize: '12px',
                lineHeight: '1.5',
              }}>
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </details>
          )}

          {/* Metadata */}
          {result.metadata && (
            <details
              style={{
                marginTop: '12px',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                background: '#fff',
              }}
            >
              <summary style={{
                padding: '12px',
                cursor: 'pointer',
                fontWeight: 600,
                color: 'var(--primary)',
                userSelect: 'none',
              }}>
                ℹ️ Query Details
              </summary>
              <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
                {result.metadata.temporal_info?.has_temporal && (
                  <div style={{ marginBottom: '8px', fontSize: '14px' }}>
                    <strong>Time period:</strong>{' '}
                    {result.metadata.temporal_info.normalized_expression}
                  </div>
                )}
                {result.metadata.agents_used && (
                  <div style={{ fontSize: '14px' }}>
                    <strong>Agents used:</strong>{' '}
                    {result.metadata.agents_used.join(', ')}
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}

      <style>{`
        .nlq-search-container .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid rgba(var(--primary-rgb), 0.2);
          border-radius: 50%;
          border-top-color: var(--primary);
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .nlq-search-container details summary:hover {
          background: #f5f5f5;
        }
      `}</style>
    </div>
  );
}
