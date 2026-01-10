/**
 * NLQ Search Bar Component
 *
 * Simple search interface for natural language queries
 *
 * @example
 * <NLQSearchBar propertyCode="ESP" />
 */

import React, { useState } from 'react';
import { useNLQ } from '../hooks/useNLQ';
import './NLQSearchBar.css';

const NLQSearchBar = ({ propertyCode = null, propertyId = null }) => {
  const [question, setQuestion] = useState('');
  const { query, loading, error, result } = useNLQ();

  const handleSearch = async () => {
    if (!question.trim()) return;

    const context = {};
    if (propertyCode) context.property_code = propertyCode;
    if (propertyId) context.property_id = propertyId;

    await query(question, Object.keys(context).length > 0 ? context : null);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleSearch();
    }
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return '#52c41a'; // green
    if (score >= 0.6) return '#faad14'; // yellow
    return '#f5222d'; // red
  };

  const formatExecutionTime = (ms) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="nlq-search-container">
      <div className="nlq-search-header">
        <h3>💬 Ask a Question</h3>
        <p>Ask anything about your financial data in natural language</p>
      </div>

      <div className="nlq-search-input-group">
        <input
          type="text"
          className="nlq-search-input"
          placeholder="e.g., What was cash position in November 2025?"
          aria-label="Ask a financial question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
        />
        <button
          className="nlq-search-button"
          onClick={handleSearch}
          disabled={loading || !question.trim()}
          aria-label="Submit natural language query"
        >
          {loading ? (
            <>
              <span className="nlq-spinner"></span>
              Thinking...
            </>
          ) : (
            <>
              🔍 Ask
            </>
          )}
        </button>
      </div>

      {/* Quick suggestions */}
      {!result && !loading && !error && (
        <div className="nlq-suggestions">
          <p>Try asking:</p>
          <div className="nlq-suggestion-chips">
            <button
              onClick={() => setQuestion(`What was cash position in November 2025?`)}
              aria-label="Use suggestion: cash position"
            >
              Cash position
            </button>
            <button
              onClick={() => setQuestion(`How is DSCR calculated?`)}
              aria-label="Use suggestion: formula explanation"
            >
              Formula explanation
            </button>
            <button
              onClick={() => setQuestion(`Show revenue for Q4 2025`)}
              aria-label="Use suggestion: quarterly revenue"
            >
              Quarterly revenue
            </button>
            <button
              onClick={() => setQuestion(`Calculate current ratio${propertyCode ? ` for ${propertyCode}` : ''}`)}
              aria-label="Use suggestion: calculate metric"
            >
              Calculate metric
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="nlq-loading">
          <div className="nlq-spinner-large"></div>
          <p>Analyzing your question...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="nlq-error">
          <h4>❌ Error</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="nlq-result">
          <div className="nlq-result-header">
            <h4>✅ Answer</h4>
            <div className="nlq-result-meta">
              <span
                className="nlq-confidence"
                style={{ color: getConfidenceColor(result.confidence_score) }}
              >
                Confidence: {(result.confidence_score * 100).toFixed(0)}%
              </span>
              {result.execution_time_ms && (
                <span className="nlq-execution-time">
                  ⚡ {formatExecutionTime(result.execution_time_ms)}
                </span>
              )}
            </div>
          </div>

          <div className="nlq-answer">
            {result.answer.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          {/* Data display */}
          {result.data && result.data.length > 0 && (
            <details className="nlq-data-details">
              <summary>📊 View Raw Data ({result.data.length} records)</summary>
              <pre className="nlq-data-json">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </details>
          )}

          {/* Metadata */}
          {result.metadata && (
            <details className="nlq-metadata-details">
              <summary>ℹ️ Query Details</summary>
              <div className="nlq-metadata">
                {result.metadata.temporal_info?.has_temporal && (
                  <div>
                    <strong>Time period:</strong>{' '}
                    {result.metadata.temporal_info.normalized_expression}
                  </div>
                )}
                {result.metadata.agents_used && (
                  <div>
                    <strong>Agents used:</strong>{' '}
                    {result.metadata.agents_used.join(', ')}
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default NLQSearchBar;
