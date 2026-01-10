/**
 * NLQ Search Bar Component
 *
 * Simple search interface for natural language queries
 *
 * @example
 * <NLQSearchBar propertyCode="ESP" />
 */

import React, { useMemo, useState, useEffect } from 'react';
import { useNLQ } from '../hooks/useNLQ';
import './NLQSearchBar.css';

const NLQSearchBar = ({
  propertyCode = null,
  propertyId = null,
  quickPrompts = [],
  externalQuestion = '',
  onQuerySubmit
}) => {
  const [question, setQuestion] = useState('');
  const { query, loading, error, result } = useNLQ();

  useEffect(() => {
    if (externalQuestion && externalQuestion !== question) {
      setQuestion(externalQuestion);
    }
  }, [externalQuestion, question]);

  const submitQuestion = async (text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const context = {};
    if (propertyCode) context.property_code = propertyCode;
    if (propertyId) context.property_id = propertyId;

    if (onQuerySubmit) {
      onQuerySubmit(trimmed);
    }

    await query(trimmed, Object.keys(context).length > 0 ? context : null);
  };

  const handleSearch = async () => {
    await submitQuestion(question);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !loading) {
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

  const insights = useMemo(() => {
    const items = [];
    if (result?.confidence_score !== undefined) {
      items.push(`Confidence: ${(result.confidence_score * 100).toFixed(0)}%`);
    }
    if (result?.execution_time_ms) {
      items.push(`Execution time: ${formatExecutionTime(result.execution_time_ms)}`);
    }
    if (result?.metadata?.temporal_info?.has_temporal) {
      items.push(`Time period: ${result.metadata.temporal_info.normalized_expression}`);
    }
    if (result?.metadata?.agents_used?.length) {
      items.push(`Agents used: ${result.metadata.agents_used.join(', ')}`);
    }
    return items;
  }, [result]);

  const followUpSuggestions = useMemo(() => {
    const propertySuffix = propertyCode ? ` for ${propertyCode}` : '';
    return [
      `Break down by month${propertySuffix}`,
      `Compare to the previous period${propertySuffix}`,
      `Show supporting data${propertySuffix}`,
      `Explain key drivers${propertySuffix}`
    ];
  }, [propertyCode]);

  const handleQuickPrompt = (prompt) => {
    setQuestion(prompt);
  };

  const handleFollowUp = (prompt) => {
    setQuestion(prompt);
    submitQuestion(prompt);
  };

  return (
    <div className="nlq-search-container">
      <div className="nlq-search-header">
        <h3>💬 Ask a Question</h3>
        <p>Ask anything about your financial data in natural language</p>
      </div>

      <div className="nlq-search-input-group">
        <textarea
          className="nlq-search-input nlq-search-textarea"
          placeholder="e.g., What was cash position in November 2025?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          rows={3}
        />
        <button
          className="nlq-search-button"
          onClick={handleSearch}
          disabled={loading || !question.trim()}
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

      {quickPrompts.length > 0 && (
        <div className="nlq-quick-prompts">
          <span>Quick prompts:</span>
          <div className="nlq-suggestion-chips">
            {quickPrompts.map((prompt) => (
              <button key={prompt} onClick={() => handleQuickPrompt(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

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
            <h4>✅ Result</h4>
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
              <ul className="nlq-insights-list">
                {insights.length > 0 ? (
                  insights.map((item) => (
                    <li key={item} style={{ color: item.includes('Confidence') ? getConfidenceColor(result.confidence_score) : undefined }}>
                      {item}
                    </li>
                  ))
                ) : (
                  <li>No additional insights were returned for this query.</li>
                )}
              </ul>
            </section>

            <section className="nlq-result-section">
              <div className="nlq-section-header">Data</div>
              {result.data && result.data.length > 0 ? (
                <details className="nlq-data-details">
                  <summary>📊 View Raw Data ({result.data.length} records)</summary>
                  <pre className="nlq-data-json">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              ) : (
                <p className="nlq-empty-state">No structured data returned.</p>
              )}

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
            </section>
          </div>

          <div className="nlq-followup">
            <p>Explore deeper:</p>
            <div className="nlq-suggestion-chips">
              {followUpSuggestions.map((suggestion) => (
                <button key={suggestion} onClick={() => handleFollowUp(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NLQSearchBar;
