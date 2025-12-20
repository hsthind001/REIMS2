import { useState, useEffect } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

interface ValidationRule {
  id: number;
  rule_name: string;
  rule_type: string;
  formula: string;
  tolerance?: string;
  is_enabled: boolean;
  alert_level: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  pass_rate: number;
  applies_to_all_properties: boolean;
  property_ids?: number[];
  actions_on_failure: {
    send_email: boolean;
    create_alert: boolean;
    block_approval: boolean;
    create_action_item: boolean;
    email_recipients?: string[];
  };
  frequency: string;
  created_at: string;
  updated_at: string;
}

interface RuleTemplate {
  name: string;
  category: string;
  rule_count: number;
}

export default function ValidationRules() {
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [disabledRules, setDisabledRules] = useState<ValidationRule[]>([]);
  const [templates, setTemplates] = useState<RuleTemplate[]>([]);
  const [selectedRule, setSelectedRule] = useState<ValidationRule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  const [ruleForm, setRuleForm] = useState({
    rule_name: '',
    rule_type: 'Financial Metric',
    formula: '',
    tolerance: '',
    alert_level: 'MEDIUM' as const,
    applies_to_all_properties: true,
    property_ids: [] as number[],
    actions_on_failure: {
      send_email: true,
      create_alert: true,
      block_approval: false,
      create_action_item: false,
      email_recipients: ['CEO', 'CFO']
    },
    frequency: 'Every data update'
  });

  useEffect(() => {
    loadRules();
    loadTemplates();
  }, []);

  const loadRules = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to load validation rules');

      const data = await response.json();
      const allRules = data.rules || [];
      setRules(allRules.filter((r: ValidationRule) => r.is_enabled));
      setDisabledRules(allRules.filter((r: ValidationRule) => !r.is_enabled));
    } catch (err) {
      console.error('Failed to load validation rules:', err);
      setError('Failed to load validation rules');
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/validations/templates`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      }
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(ruleForm)
      });

      if (!response.ok) throw new Error('Failed to create validation rule');

      setShowCreateModal(false);
      resetRuleForm();
      loadRules();
    } catch (err) {
      console.error('Failed to create rule:', err);
      setError('Failed to create validation rule');
    }
  };

  const handleUpdateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRule) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations/${selectedRule.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(ruleForm)
      });

      if (!response.ok) throw new Error('Failed to update validation rule');

      setShowEditModal(false);
      setSelectedRule(null);
      resetRuleForm();
      loadRules();
    } catch (err) {
      console.error('Failed to update rule:', err);
      setError('Failed to update validation rule');
    }
  };

  const handleToggleRule = async (ruleId: number, currentState: boolean) => {
    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations/${ruleId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ is_enabled: !currentState })
      });

      if (!response.ok) throw new Error('Failed to toggle rule');

      loadRules();
    } catch (err) {
      console.error('Failed to toggle rule:', err);
      setError('Failed to toggle validation rule');
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this validation rule?')) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations/${ruleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete rule');

      loadRules();
    } catch (err) {
      console.error('Failed to delete rule:', err);
      setError('Failed to delete validation rule');
    }
  };

  const handleTestRule = async (ruleId: number) => {
    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/validations/${ruleId}/test`, {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to test rule');

      const result = await response.json();
      alert(`Test completed:\nPassed: ${result.passed}\nFailed: ${result.failed}\nPass Rate: ${result.pass_rate}%`);
    } catch (err) {
      console.error('Failed to test rule:', err);
      setError('Failed to test validation rule');
    }
  };

  const resetRuleForm = () => {
    setRuleForm({
      rule_name: '',
      rule_type: 'Financial Metric',
      formula: '',
      tolerance: '',
      alert_level: 'MEDIUM',
      applies_to_all_properties: true,
      property_ids: [],
      actions_on_failure: {
        send_email: true,
        create_alert: true,
        block_approval: false,
        create_action_item: false,
        email_recipients: ['CEO', 'CFO']
      },
      frequency: 'Every data update'
    });
  };

  const openEditModal = (rule: ValidationRule) => {
    setSelectedRule(rule);
    setRuleForm({
      rule_name: rule.rule_name,
      rule_type: rule.rule_type,
      formula: rule.formula,
      tolerance: rule.tolerance || '',
      alert_level: rule.alert_level,
      applies_to_all_properties: rule.applies_to_all_properties,
      property_ids: rule.property_ids || [],
      actions_on_failure: rule.actions_on_failure,
      frequency: rule.frequency
    });
    setShowEditModal(true);
  };

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return 'var(--error-color)';
      case 'HIGH': return '#ff6b6b';
      case 'MEDIUM': return 'var(--warning-color)';
      case 'LOW': return '#74c0fc';
      case 'INFO': return 'var(--info-color)';
      default: return 'var(--secondary-color)';
    }
  };

  const getAlertLevelIcon = (level: string) => {
    switch (level) {
      case 'CRITICAL': return '🔴';
      case 'HIGH': return '🟠';
      case 'MEDIUM': return '🟡';
      case 'LOW': return '🔵';
      case 'INFO': return 'ℹ️';
      default: return '⚪';
    }
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading validation rules...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Validation Rules Manager</h1>
        <p className="page-subtitle">Create and manage financial validation rules and thresholds</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="page-content">
        {/* Active Rules */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Active Rules ({rules.length} enabled)</h3>
            <div>
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                + Create New Rule
              </button>
              <button className="btn btn-secondary" style={{ marginLeft: '0.5rem' }}>
                Import Rule Template
              </button>
              <button className="btn btn-secondary" style={{ marginLeft: '0.5rem' }}>
                Bulk Edit
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '1rem' }}>
            {rules.map(rule => (
              <div
                key={rule.id}
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>
                      ✅ {rule.rule_name}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                      <strong>Rule:</strong> {rule.formula}
                    </div>
                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                      {rule.tolerance && (
                        <div>
                          <strong>Tolerance:</strong> {rule.tolerance}
                        </div>
                      )}
                      <div>
                        <strong>Tests:</strong> {rule.total_tests}
                      </div>
                      <div>
                        <strong>Pass Rate:</strong>{' '}
                        <span style={{
                          color: rule.pass_rate === 100 ? 'var(--success-color)' : rule.pass_rate >= 95 ? 'var(--primary-color)' : 'var(--error-color)'
                        }}>
                          {rule.pass_rate.toFixed(1)}% {rule.pass_rate === 100 ? '✅' : rule.pass_rate >= 95 ? '🟢' : '🔴'}
                        </span>
                      </div>
                      <div>
                        <strong>Alert Level:</strong>{' '}
                        <span style={{ color: getAlertLevelColor(rule.alert_level) }}>
                          {getAlertLevelIcon(rule.alert_level)} {rule.alert_level}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
                    <button className="btn btn-secondary" onClick={() => openEditModal(rule)}>
                      Edit
                    </button>
                    <button className="btn btn-secondary" onClick={() => handleToggleRule(rule.id, rule.is_enabled)}>
                      Disable
                    </button>
                    <button className="btn btn-secondary" onClick={() => handleTestRule(rule.id)}>
                      Test Rule
                    </button>
                    {rule.failed_tests > 0 && (
                      <button className="btn btn-secondary">View Failures</button>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {rules.length === 0 && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                No active validation rules. Click "Create New Rule" to add one.
              </div>
            )}
          </div>
        </div>

        {/* Disabled Rules */}
        {disabledRules.length > 0 && (
          <div className="card">
            <h3>Disabled Rules ({disabledRules.length})</h3>
            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
              {disabledRules.map(rule => (
                <li key={rule.id} style={{ marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{rule.rule_name}</span>
                  {' '}
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '0.25rem 0.5rem' }}
                    onClick={() => handleToggleRule(rule.id, rule.is_enabled)}
                  >
                    Enable
                  </button>
                  <button
                    className="btn"
                    style={{ fontSize: '0.8rem', padding: '0.25rem 0.5rem', marginLeft: '0.5rem', background: 'var(--error-color)', color: 'white' }}
                    onClick={() => handleDeleteRule(rule.id)}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Rule Templates */}
        <div className="card">
          <h3>Rule Templates</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {templates.map((template, idx) => (
              <div
                key={idx}
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>{template.name}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                  {template.category} • {template.rule_count} rules
                </div>
                <button className="btn btn-secondary" style={{ width: '100%' }}>
                  Load Template
                </button>
              </div>
            ))}

            {templates.length === 0 && (
              <>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 'bold' }}>Industry Standard Financial Ratios</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>12 rules</div>
                </div>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 'bold' }}>GAAP Compliance Checks</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>8 rules</div>
                </div>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 'bold' }}>Lender Covenant Monitoring</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>5 rules</div>
                </div>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1rem' }}>
                  <div style={{ fontWeight: 'bold' }}>IRS Tax Compliance</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>6 rules</div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Create Rule Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" style={{ maxWidth: '600px' }} onClick={(e) => e.stopPropagation()}>
            <h2>Create Validation Rule</h2>
            <form onSubmit={handleCreateRule}>
              <div className="form-group">
                <label>Rule Name*</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.rule_name}
                  onChange={(e) => setRuleForm({ ...ruleForm, rule_name: e.target.value })}
                  placeholder="e.g., DSCR Threshold Check"
                  required
                />
              </div>

              <div className="form-group">
                <label>Rule Type*</label>
                <select
                  className="input"
                  value={ruleForm.rule_type}
                  onChange={(e) => setRuleForm({ ...ruleForm, rule_type: e.target.value })}
                  required
                >
                  <option>Financial Metric</option>
                  <option>Balance Sheet</option>
                  <option>Income Statement</option>
                  <option>Cash Flow</option>
                  <option>Custom Formula</option>
                </select>
              </div>

              <div className="form-group">
                <label>Formula*</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.formula}
                  onChange={(e) => setRuleForm({ ...ruleForm, formula: e.target.value })}
                  placeholder="e.g., NOI / Annual Debt Service >= 1.25"
                  required
                />
              </div>

              <div className="form-group">
                <label>Tolerance</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.tolerance}
                  onChange={(e) => setRuleForm({ ...ruleForm, tolerance: e.target.value })}
                  placeholder="e.g., ±$1,000 or ±1%"
                />
              </div>

              <div className="form-group">
                <label>Alert Level*</label>
                <select
                  className="input"
                  value={ruleForm.alert_level}
                  onChange={(e) => setRuleForm({ ...ruleForm, alert_level: e.target.value as any })}
                  required
                >
                  <option value="INFO">ℹ️ INFO</option>
                  <option value="LOW">🔵 LOW</option>
                  <option value="MEDIUM">🟡 MEDIUM</option>
                  <option value="HIGH">🟠 HIGH</option>
                  <option value="CRITICAL">🔴 CRITICAL</option>
                </select>
              </div>

              <div className="form-group">
                <label>Apply To</label>
                <label>
                  <input
                    type="checkbox"
                    checked={ruleForm.applies_to_all_properties}
                    onChange={(e) => setRuleForm({ ...ruleForm, applies_to_all_properties: e.target.checked })}
                  />
                  {' '}All Properties
                </label>
              </div>

              <div className="form-group">
                <label>Actions on Failure</label>
                <label>
                  <input
                    type="checkbox"
                    checked={ruleForm.actions_on_failure.send_email}
                    onChange={(e) => setRuleForm({
                      ...ruleForm,
                      actions_on_failure: { ...ruleForm.actions_on_failure, send_email: e.target.checked }
                    })}
                  />
                  {' '}Send email alert
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={ruleForm.actions_on_failure.create_alert}
                    onChange={(e) => setRuleForm({
                      ...ruleForm,
                      actions_on_failure: { ...ruleForm.actions_on_failure, create_alert: e.target.checked }
                    })}
                  />
                  {' '}Create dashboard alert
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={ruleForm.actions_on_failure.block_approval}
                    onChange={(e) => setRuleForm({
                      ...ruleForm,
                      actions_on_failure: { ...ruleForm.actions_on_failure, block_approval: e.target.checked }
                    })}
                  />
                  {' '}Block data approval until resolved
                </label>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                <button type="submit" className="btn btn-primary">Create Rule</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Rule Modal */}
      {showEditModal && selectedRule && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal-content" style={{ maxWidth: '600px' }} onClick={(e) => e.stopPropagation()}>
            <h2>Edit Validation Rule</h2>
            <form onSubmit={handleUpdateRule}>
              <div className="form-group">
                <label>Rule Name*</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.rule_name}
                  onChange={(e) => setRuleForm({ ...ruleForm, rule_name: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Formula*</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.formula}
                  onChange={(e) => setRuleForm({ ...ruleForm, formula: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Tolerance</label>
                <input
                  type="text"
                  className="input"
                  value={ruleForm.tolerance}
                  onChange={(e) => setRuleForm({ ...ruleForm, tolerance: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Alert Level*</label>
                <select
                  className="input"
                  value={ruleForm.alert_level}
                  onChange={(e) => setRuleForm({ ...ruleForm, alert_level: e.target.value as any })}
                  required
                >
                  <option value="INFO">ℹ️ INFO</option>
                  <option value="LOW">🔵 LOW</option>
                  <option value="MEDIUM">🟡 MEDIUM</option>
                  <option value="HIGH">🟠 HIGH</option>
                  <option value="CRITICAL">🔴 CRITICAL</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                <button type="submit" className="btn btn-primary">Save Changes</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
