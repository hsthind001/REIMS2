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
  const [queryMode, setQueryMode] = useState('ask');
  const { query, loading, error, result } = useNLQ();

  const handleSearch = async (modeOverride = null) => {
    if (!question.trim()) return;

    const nextMode = modeOverride || queryMode;
    const context = { query_mode: nextMode };
    if (propertyCode) context.property_code = propertyCode;
    if (propertyId) context.property_id = propertyId;

    await query(question, context);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !loading) {
      e.preventDefault();
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

  const insights =
    result?.insights ||
    result?.metadata?.insights ||
    [];

  const followUpSuggestions = [
    'Show trend',
    'Break down by month',
    'Compare to last quarter',
    'Export the data'
  ];

  const renderDataTable = (data) => {
    if (!Array.isArray(data) || data.length === 0 || typeof data[0] !== 'object') {
      return (
        <div className="nlq-data-empty">
          No structured data returned for this query.
        </div>
      );
    }

    const columns = Object.keys(data[0]);
    return (
      <div className="nlq-data-table-wrapper">
        <table className="nlq-data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => (
                  <td key={`${rowIndex}-${column}`}>
                    {row[column] !== null && row[column] !== undefined
                      ? String(row[column])
                      : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="nlq-search-container">
      <div className="nlq-search-header">
        <h3>💬 Ask a Question</h3>
        <p>Ask anything about your financial data in natural language</p>
      </div>

      <div className="nlq-search-input-group">
        <div className="nlq-search-input-area">
          <textarea
            className="nlq-search-textarea"
            rows={3}
            placeholder={`Try multi-step questions, for example:\n• What was cash position in November 2025?\n• Show revenue for Q4 2025\n• Break down operating expenses by month`}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <div className="nlq-search-actions">
            <div className="nlq-mode-toggle" role="group" aria-label="Query mode">
              <button
                type="button"
                className={`nlq-mode-button ${queryMode === 'ask' ? 'is-active' : ''}`}
                onClick={() => setQueryMode('ask')}
                disabled={loading}
              >
                💬 Ask
              </button>
              <button
                type="button"
                className={`nlq-mode-button ${queryMode === 'run' ? 'is-active' : ''}`}
                onClick={() => setQueryMode('run')}
                disabled={loading}
              >
                ⚡ Run
              </button>
            </div>
            <button
              className="nlq-search-button"
              onClick={() => handleSearch()}
              disabled={loading || !question.trim()}
            >
              {loading ? (
                <>
                  <span className="nlq-spinner"></span>
                  Thinking...
                </>
              ) : (
                <>
                  🔍 {queryMode === 'ask' ? 'Ask' : 'Run'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Quick suggestions */}
      {!result && !loading && !error && (
        <div className="nlq-suggestions">
          <p>Try asking:</p>
          <div className="nlq-suggestion-chips">
            <button onClick={() => setQuestion(`What was cash position in November 2025?`)}>
              Cash position
            </button>
            <button onClick={() => setQuestion(`How is DSCR calculated?`)}>
              Formula explanation
            </button>
            <button onClick={() => setQuestion(`Show revenue for Q4 2025`)}>
              Quarterly revenue
            </button>
            <button onClick={() => setQuestion(`Calculate current ratio${propertyCode ? ` for ${propertyCode}` : ''}`)}>
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

          <div className="nlq-result-sections">
            <section className="nlq-result-section">
              <div className="nlq-section-header">Answer</div>
              <div className="nlq-answer">
                {result.answer.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
            </section>

            <section className="nlq-result-section">
              <div className="nlq-section-header">Insights</div>
              {insights.length > 0 ? (
                <ul className="nlq-insights">
                  {insights.map((insight, index) => (
                    <li key={index}>{insight}</li>
                  ))}
                </ul>
              ) : (
                <div className="nlq-insights-empty">
                  No insights were generated for this query yet.
                </div>
              )}
            </section>

            <section className="nlq-result-section">
              <div className="nlq-section-header">Data</div>
              {result.data && result.data.length > 0 ? (
                renderDataTable(result.data)
              ) : (
                <div className="nlq-data-empty">
                  No data table is available for this result.
                </div>
              )}
              {result.data && result.data.length > 0 && (
                <details className="nlq-data-details">
                  <summary>View raw JSON</summary>
                  <pre className="nlq-data-json">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              )}
            </section>
          </div>

          <div className="nlq-followups">
            <div className="nlq-followups-label">Follow-up suggestions</div>
            <div className="nlq-suggestion-chips">
              {followUpSuggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setQuestion(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

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
