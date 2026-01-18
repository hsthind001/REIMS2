/**
 * Alert Rules Management Page
 * Create, edit, and manage alert rules
 */
import { useState, useEffect } from 'react';
import { AlertRuleService } from '../lib/alertRules';
import type { AlertRule, AlertRuleTemplate } from '../lib/alertRules';
import '../App.css';

export default function AlertRules() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [templates, setTemplates] = useState<AlertRuleTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AlertRule | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadRules();
    loadTemplates();
  }, [filter]);

  const loadRules = async () => {
    try {
      setLoading(true);
      setError(null);

      const rulesData = await AlertRuleService.getRules({
        is_active: filter === 'all' ? undefined : filter === 'active'
      });

      setRules(rulesData);
    } catch (err: any) {
      setError(err.message || 'Failed to load rules');
      console.error('Error loading rules:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await AlertRuleService.getTemplates();
      setTemplates(response.templates);
    } catch (err: any) {
      console.error('Error loading templates:', err);
    }
  };

  const handleCreateFromTemplate = async (templateId: string) => {
    try {
      await AlertRuleService.createFromTemplate(templateId);
      setShowTemplateModal(false);
      await loadRules();
      alert('Rule created successfully');
    } catch (err: any) {
      alert(err.message || 'Failed to create rule');
    }
  };

  const handleToggleActive = async (rule: AlertRule) => {
    try {
      if (rule.is_active) {
        await AlertRuleService.deactivateRule(rule.id);
      } else {
        await AlertRuleService.activateRule(rule.id);
      }
      await loadRules();
    } catch (err: any) {
      alert(err.message || 'Failed to update rule');
    }
  };

  const handleDelete = async (ruleId: number) => {
    if (!confirm('Are you sure you want to delete this rule?')) {
      return;
    }

    try {
      await AlertRuleService.deleteRule(ruleId);
      await loadRules();
      alert('Rule deleted successfully');
    } catch (err: any) {
      alert(err.message || 'Failed to delete rule');
    }
  };

  const filteredRules = rules.filter(rule => {
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      return (
        rule.rule_name.toLowerCase().includes(searchLower) ||
        rule.field_name.toLowerCase().includes(searchLower) ||
        rule.description?.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="container">
        <div className="empty-state">
          <div className="spinner"></div>
          <p>Loading alert rules...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div style={{ marginBottom: '2rem' }}>
        <h1>Alert Rules Management</h1>
        <p style={{ color: '#666' }}>Create and manage rules for automatic alert generation</p>
      </div>

      {/* Actions Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => setShowCreateForm(true)}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#007bff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            + Create Rule
          </button>
          <button
            onClick={() => setShowTemplateModal(true)}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#28a745',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            📋 Create from Template
          </button>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search rules..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              minWidth: '200px'
            }}
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            style={{
              padding: '0.5rem',
              border: '1px solid #ddd',
              borderRadius: '4px'
            }}
          >
            <option value="all">All Rules</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '1rem',
          background: '#f8d7da',
          color: '#721c24',
          borderRadius: '4px',
          marginBottom: '1.5rem'
        }}>
          {error}
        </div>
      )}

      {/* Rules Table */}
      <div className="card">
        <h3 className="card-title">Alert Rules ({filteredRules.length})</h3>
        {filteredRules.length === 0 ? (
          <div className="empty-state">
            <p>No rules found. Create your first rule to get started.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Name</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Type</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Field</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Condition</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Threshold</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Severity</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Status</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Executions</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRules.map((rule) => (
                  <tr key={rule.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ fontWeight: '500' }}>{rule.rule_name}</div>
                      {rule.description && (
                        <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
                          {rule.description.substring(0, 50)}...
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem' }}>{rule.rule_type}</td>
                    <td style={{ padding: '0.75rem' }}>{rule.field_name}</td>
                    <td style={{ padding: '0.75rem' }}>{rule.condition.replace(/_/g, ' ')}</td>
                    <td style={{ padding: '0.75rem' }}>
                      {rule.threshold_value !== undefined && rule.threshold_value !== null ? rule.threshold_value.toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        background: rule.severity === 'critical' ? '#dc3545' : '#ffc107',
                        color: '#fff',
                        fontSize: '0.875rem'
                      }}>
                        {rule.severity}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        background: rule.is_active ? '#28a745' : '#6c757d',
                        color: '#fff',
                        fontSize: '0.875rem',
                        cursor: 'pointer'
                      }}
                      onClick={() => handleToggleActive(rule)}
                      >
                        {rule.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem' }}>{rule.execution_count || 0}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => setSelectedRule(rule)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            background: '#17a2b8',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.875rem'
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(rule.id)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            background: '#dc3545',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.875rem'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Template Modal */}
      {showTemplateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: '#fff',
            borderRadius: '8px',
            padding: '2rem',
            maxWidth: '600px',
            maxHeight: '80vh',
            overflow: 'auto',
            width: '90%'
          }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Create Rule from Template</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {templates.map((template) => (
                <div
                  key={template.id}
                  style={{
                    padding: '1rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                  onClick={() => handleCreateFromTemplate(template.id)}
                >
                  <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>{template.name}</div>
                  <div style={{ fontSize: '0.875rem', color: '#666' }}>{template.description}</div>
                  <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.5rem' }}>
                    Field: {template.field_name} • Threshold: {template.default_threshold}
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={() => setShowTemplateModal(false)}
              style={{
                marginTop: '1.5rem',
                padding: '0.75rem 1.5rem',
                background: '#6c757d',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
