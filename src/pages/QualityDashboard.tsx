import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface QualityScore {
  overall_score: number;
  extraction_accuracy: number;
  validation_pass_rate: number;
  data_completeness: number;
  field_confidence_avg: number;
  failed_extractions: number;
  target_extraction_accuracy: number;
  target_validation_pass_rate: number;
  target_data_completeness: number;
  target_field_confidence: number;
}

interface PropertyQuality {
  property_id: number;
  property_name: string;
  quality_score: number;
  issues_count: number;
  status: 'excellent' | 'good' | 'warning' | 'critical';
}

interface ExtractionQuality {
  document_name: string;
  field_name: string;
  extracted_value: string;
  confidence: number;
  status: 'pass' | 'warning' | 'fail';
}

interface ValidationResult {
  rule_name: string;
  total_tests: number;
  passed: number;
  failed: number;
  pass_rate: number;
}

export default function QualityDashboard() {
  const [activeTab, setActiveTab] = useState<'overview' | 'extractions' | 'validations' | 'trends' | 'settings'>('overview');
  const [qualityScore, setQualityScore] = useState<QualityScore | null>(null);
  const [propertyQuality, setPropertyQuality] = useState<PropertyQuality[]>([]);
  const [extractions, setExtractions] = useState<ExtractionQuality[]>([]);
  const [validations, setValidations] = useState<ValidationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadQualityData();
  }, []);

  const loadQualityData = async () => {
    try {
      setLoading(true);
      setError('');

      const [scoreRes, extractionsRes, validationsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/quality/score`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/quality/extractions`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/quality/validations`, { credentials: 'include' })
      ]);

      if (scoreRes.ok) {
        const scoreData = await scoreRes.json();
        setQualityScore(scoreData);
        setPropertyQuality(scoreData.properties || []);
      }

      if (extractionsRes.ok) {
        const extractionsData = await extractionsRes.json();
        setExtractions(extractionsData.extractions || []);
      }

      if (validationsRes.ok) {
        const validationsData = await validationsRes.json();
        setValidations(validationsData.results || []);
      }
    } catch (err) {
      console.error('Failed to load quality data:', err);
      setError('Failed to load quality data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusEmoji = (score: number) => {
    if (score >= 95) return '✅';
    if (score >= 90) return '🟢';
    if (score >= 80) return '🟡';
    return '🔴';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'var(--success-color)';
      case 'good': return 'var(--primary-color)';
      case 'warning': return 'var(--warning-color)';
      case 'critical': return 'var(--error-color)';
      default: return 'var(--secondary-color)';
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading quality dashboard...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Data Quality Control Center</h1>
        <p className="page-subtitle">Monitor extraction accuracy, validation results, and data completeness</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="page-content">
        {/* Tab Navigation */}
        <div className="tabs">
          <button
            className={activeTab === 'overview' ? 'tab active' : 'tab'}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={activeTab === 'extractions' ? 'tab active' : 'tab'}
            onClick={() => setActiveTab('extractions')}
          >
            Extractions
          </button>
          <button
            className={activeTab === 'validations' ? 'tab active' : 'tab'}
            onClick={() => setActiveTab('validations')}
          >
            Validations
          </button>
          <button
            className={activeTab === 'trends' ? 'tab active' : 'tab'}
            onClick={() => setActiveTab('trends')}
          >
            Trends
          </button>
          <button
            className={activeTab === 'settings' ? 'tab active' : 'tab'}
            onClick={() => setActiveTab('settings')}
          >
            Settings
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && qualityScore && (
          <div className="tab-content">
            {/* Overall Quality Score */}
            <div className="card">
              <h2 style={{ fontSize: '2rem', marginBottom: '1rem' }}>
                Data Quality Score: {qualityScore.overall_score}/100 {getStatusEmoji(qualityScore.overall_score)}
              </h2>

              <div className="dashboard-grid">
                <div className="stat-card">
                  <div className="stat-content">
                    <div className="stat-value">{qualityScore.extraction_accuracy}%</div>
                    <div className="stat-label">Extraction Accuracy</div>
                    <div className="stat-target">Target: {qualityScore.target_extraction_accuracy}%</div>
                  </div>
                  <div style={{ color: qualityScore.extraction_accuracy >= qualityScore.target_extraction_accuracy ? 'var(--success-color)' : 'var(--warning-color)' }}>
                    {qualityScore.extraction_accuracy >= qualityScore.target_extraction_accuracy ? '✅' : '⚠️'}
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-content">
                    <div className="stat-value">{qualityScore.validation_pass_rate}%</div>
                    <div className="stat-label">Validation Pass Rate</div>
                    <div className="stat-target">Target: {qualityScore.target_validation_pass_rate}%</div>
                  </div>
                  <div style={{ color: qualityScore.validation_pass_rate >= qualityScore.target_validation_pass_rate ? 'var(--success-color)' : 'var(--warning-color)' }}>
                    {qualityScore.validation_pass_rate >= qualityScore.target_validation_pass_rate ? '✅' : '⚠️'}
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-content">
                    <div className="stat-value">{qualityScore.data_completeness}%</div>
                    <div className="stat-label">Data Completeness</div>
                    <div className="stat-target">Target: {qualityScore.target_data_completeness}%</div>
                  </div>
                  <div style={{ color: qualityScore.data_completeness >= qualityScore.target_data_completeness ? 'var(--success-color)' : 'var(--warning-color)' }}>
                    {qualityScore.data_completeness >= qualityScore.target_data_completeness ? '🟢' : '🟡'}
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-content">
                    <div className="stat-value">{qualityScore.field_confidence_avg}%</div>
                    <div className="stat-label">Avg Field Confidence</div>
                    <div className="stat-target">Target: {qualityScore.target_field_confidence}%</div>
                  </div>
                  <div style={{ color: qualityScore.field_confidence_avg >= qualityScore.target_field_confidence ? 'var(--success-color)' : 'var(--warning-color)' }}>
                    {qualityScore.field_confidence_avg >= qualityScore.target_field_confidence ? '✅' : '⚠️'}
                  </div>
                </div>
              </div>

              <div className="stat-card" style={{ marginTop: '1rem' }}>
                <div className="stat-content">
                  <div className="stat-value">{qualityScore.failed_extractions}</div>
                  <div className="stat-label">Failed Extractions</div>
                </div>
                <div style={{ color: qualityScore.failed_extractions === 0 ? 'var(--success-color)' : 'var(--error-color)' }}>
                  {qualityScore.failed_extractions === 0 ? '✅' : '❌'}
                </div>
              </div>
            </div>

            {/* Quality by Property */}
            <div className="card">
              <h3>Quality by Property</h3>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Property</th>
                      <th>Quality Score</th>
                      <th>Issues</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {propertyQuality.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>
                          No property quality data available
                        </td>
                      </tr>
                    ) : (
                      propertyQuality.map((prop, idx) => (
                        <tr key={idx}>
                          <td><strong>{prop.property_name}</strong></td>
                          <td>{prop.quality_score}/100</td>
                          <td>{prop.issues_count}</td>
                          <td>
                            <span style={{ color: getStatusColor(prop.status) }}>
                              {prop.status === 'excellent' ? '✅' : prop.status === 'good' ? '🟢' : prop.status === 'warning' ? '🟡' : '🔴'}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Extractions Tab */}
        {activeTab === 'extractions' && (
          <div className="tab-content">
            <div className="card">
              <h3>Field-Level Confidence Scores</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Extraction confidence for all document fields
              </p>

              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Document</th>
                      <th>Field Name</th>
                      <th>Extracted Value</th>
                      <th>Confidence</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractions.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                          No extraction data available
                        </td>
                      </tr>
                    ) : (
                      extractions.map((ext, idx) => (
                        <tr key={idx}>
                          <td>{ext.document_name}</td>
                          <td><code>{ext.field_name}</code></td>
                          <td><strong>{ext.extracted_value}</strong></td>
                          <td>{ext.confidence}%</td>
                          <td>
                            <span style={{
                              color: ext.status === 'pass' ? 'var(--success-color)' : ext.status === 'warning' ? 'var(--warning-color)' : 'var(--error-color)'
                            }}>
                              {ext.status === 'pass' ? '✅' : ext.status === 'warning' ? '⚠️' : '❌'}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--background-light)', borderRadius: '0.5rem' }}>
                <strong>Re-extraction Recommendations</strong>
                <p style={{ marginTop: '0.5rem' }}>
                  {extractions.filter(e => e.confidence < 90).length === 0
                    ? '✅ No documents need re-extraction at this time'
                    : `⚠️ ${extractions.filter(e => e.confidence < 90).length} fields have confidence below 90% and may need re-extraction`
                  }
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Validations Tab */}
        {activeTab === 'validations' && (
          <div className="tab-content">
            <div className="card">
              <h3>Validation Rule Results</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Pass rates for all validation rules
              </p>

              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Rule Name</th>
                      <th>Total Tests</th>
                      <th>Passed</th>
                      <th>Failed</th>
                      <th>Pass Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validations.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                          No validation data available
                        </td>
                      </tr>
                    ) : (
                      validations.map((val, idx) => (
                        <tr key={idx}>
                          <td><strong>{val.rule_name}</strong></td>
                          <td>{val.total_tests}</td>
                          <td style={{ color: 'var(--success-color)' }}>{val.passed}</td>
                          <td style={{ color: val.failed > 0 ? 'var(--error-color)' : 'inherit' }}>{val.failed}</td>
                          <td>
                            <span style={{
                              color: val.pass_rate === 100 ? 'var(--success-color)' : val.pass_rate >= 95 ? 'var(--primary-color)' : 'var(--warning-color)'
                            }}>
                              {val.pass_rate.toFixed(1)}%
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Trends Tab */}
        {activeTab === 'trends' && (
          <div className="tab-content">
            <div className="card">
              <h3>Quality Score History</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Overall quality score trends over time
              </p>

              <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--background-light)', borderRadius: '0.5rem' }}>
                <p>📊 Quality trends visualization coming soon</p>
                <p style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
                  Current Score: {qualityScore?.overall_score || 0}/100 |
                  Trend: ↗️ Improving
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="tab-content">
            <div className="card">
              <h3>Quality Thresholds</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Configure quality monitoring thresholds and alerts
              </p>

              <div className="form-group">
                <label>Minimum Extraction Confidence (%)</label>
                <input type="number" className="input" defaultValue={90} min={0} max={100} />
              </div>

              <div className="form-group">
                <label>Minimum Validation Pass Rate (%)</label>
                <input type="number" className="input" defaultValue={95} min={0} max={100} />
              </div>

              <div className="form-group">
                <label>Data Completeness Target (%)</label>
                <input type="number" className="input" defaultValue={90} min={0} max={100} />
              </div>

              <div className="form-group">
                <label>
                  <input type="checkbox" defaultChecked /> Alert on Quality Drop
                </label>
              </div>

              <div className="form-group">
                <label>
                  <input type="checkbox" defaultChecked /> Auto-Reextract on Low Confidence (&lt; 85%)
                </label>
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <button className="btn btn-primary" style={{ marginRight: '0.5rem' }}>Save Settings</button>
                <button className="btn btn-secondary">Reset to Defaults</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
