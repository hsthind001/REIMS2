/**
 * Natural Language Query Page - Enhanced Version
 *
 * Complete NLQ system with:
 * - Temporal support (10+ types)
 * - 50+ financial formulas
 * - Multi-agent orchestration
 * - Property-specific queries
 * - Example queries
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../components/AuthContext';
import NLQSearchBar from '../components/NLQSearchBar';
import { nlqService, type Formula } from '../services/nlqService';
import '../App.css';

interface Property {
  id: number;
  property_code: string;
  property_name: string;
}

export default function NaturalLanguageQueryNew() {
  const { user } = useAuth();
  const [selectedProperty, setSelectedProperty] = useState<string>('');
  const [formulas, setFormulas] = useState<Record<string, Formula>>({});
  const [formulasLoading, setFormulasLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(false);

  const exampleQueries = {
    'Financial Data': [
      'What was the cash position in November 2025?',
      'Show me total revenue for Q4 2025',
      'What are total assets for property ESP?',
      'Show operating expenses for last month',
      'Compare net income YTD vs last year',
    ],
    'Formulas & Calculations': [
      'How is DSCR calculated?',
      'What is the formula for Current Ratio?',
      'Explain NOI calculation',
      'Calculate DSCR for property ESP in November 2025',
      'What is the benchmark for good DSCR?',
    ],
    'Temporal Queries': [
      'Show data for last 3 months',
      'Compare Q4 2025 vs Q4 2024',
      'Year to date revenue',
      'Month to date expenses',
      'Between August and December 2025',
    ],
    'Audit & History': [
      'Who changed cash position in November 2025?',
      'Show me audit history for property ESP',
      'What was modified last week?',
      'List all changes by user John Doe',
    ],
  };

  const categories = ['all', 'liquidity', 'leverage', 'mortgage', 'income_statement', 'rent_roll'];

  useEffect(() => {
    loadProperties();
    loadFormulas();
    checkHealth();
  }, [selectedCategory]);

  const loadProperties = async () => {
    try {
      setPropertiesLoading(true);
      const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';
      const response = await fetch(`${API_BASE_URL}/properties`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch properties');
      }

      const data = await response.json();
      setProperties(data);
    } catch (error) {
      console.error('Failed to load properties:', error);
      // Set empty array on error so the dropdown still works
      setProperties([]);
    } finally {
      setPropertiesLoading(false);
    }
  };

  const loadFormulas = async () => {
    try {
      setFormulasLoading(true);
      const response = await nlqService.getFormulas(
        selectedCategory === 'all' ? undefined : selectedCategory
      );
      setFormulas(response.formulas || {});
    } catch (error) {
      console.error('Failed to load formulas:', error);
    } finally {
      setFormulasLoading(false);
    }
  };

  const checkHealth = async () => {
    try {
      const health = await nlqService.healthCheck();
      setHealthStatus(health);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">🤖 Natural Language Query</h1>
          <p className="page-subtitle">
            Ask questions about your financial data in plain English - powered by AI
          </p>
        </div>
      </div>

      {/* Health Status */}
      {healthStatus && (
        <div className="card" style={{ background: '#ecfdf5', border: '1px solid #10b981', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '24px' }}>✅</span>
            <div>
              <div style={{ fontWeight: 600, color: '#10b981' }}>NLQ System Online</div>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                {healthStatus.agents?.length || 0} agents available •{' '}
                {Object.keys(healthStatus.features || {}).filter(k => healthStatus.features[k]).length} features enabled
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Property Selector */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label style={{ fontWeight: 600, color: 'var(--text)' }}>
            Filter by Property (Optional):
          </label>
          <select
            className="input"
            value={selectedProperty}
            onChange={(e) => setSelectedProperty(e.target.value)}
            style={{ maxWidth: '250px' }}
            disabled={propertiesLoading}
          >
            <option value="">
              {propertiesLoading ? 'Loading properties...' : 'All Properties'}
            </option>
            {properties.map((prop) => (
              <option key={prop.property_code} value={prop.property_code}>
                {prop.property_name} ({prop.property_code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Search */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <NLQSearchBar
          propertyCode={selectedProperty || undefined}
          propertyId={properties.find((p) => p.property_code === selectedProperty)?.id}
          userId={user?.id}
        />
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* Left Column - Example Queries */}
        <div className="card">
          <h3 className="card-title">💡 Example Queries</h3>

          <div style={{ marginBottom: '20px' }}>
            {Object.entries(exampleQueries).map(([category, queries]) => (
              <details key={category} open={category === 'Financial Data'} style={{ marginBottom: '12px' }}>
                <summary style={{
                  padding: '12px',
                  background: '#f8fafc',
                  cursor: 'pointer',
                  fontWeight: 600,
                  borderRadius: '4px',
                  userSelect: 'none',
                }}>
                  {category}
                </summary>
                <div style={{ padding: '12px 0' }}>
                  {queries.map((query, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '8px 12px',
                        margin: '4px 0',
                        background: '#fff',
                        border: '1px solid var(--border)',
                        borderRadius: '4px',
                        fontSize: '14px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#e6f7ff';
                        e.currentTarget.style.borderColor = '#1890ff';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#fff';
                        e.currentTarget.style.borderColor = 'var(--border)';
                      }}
                    >
                      💭 {query}
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </div>

        {/* Right Column - Formulas & Features */}
        <div>
          {/* Supported Features */}
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 className="card-title">🎯 Supported Features</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ Temporal Queries (10+ types)
              </div>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ 50+ Financial Formulas
              </div>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ Multi-Statement Analysis
              </div>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ Audit Trail Queries
              </div>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ Reconciliation Queries
              </div>
              <div className="badge badge-success" style={{ padding: '8px 12px' }}>
                ✓ Natural Language
              </div>
            </div>
          </div>

          {/* Formula Browser */}
          <div className="card">
            <h3 className="card-title">📐 Formula Browser</h3>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                Category:
              </label>
              <select
                className="input"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.replace(/_/g, ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            {formulasLoading ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <div className="spinner" style={{ margin: '0 auto' }}></div>
              </div>
            ) : (
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {Object.entries(formulas).slice(0, 10).map(([key, formula]) => (
                  <details
                    key={key}
                    style={{
                      padding: '8px',
                      margin: '4px 0',
                      background: '#f8fafc',
                      border: '1px solid var(--border)',
                      borderRadius: '4px',
                      fontSize: '13px',
                    }}
                  >
                    <summary style={{
                      cursor: 'pointer',
                      fontWeight: 600,
                      userSelect: 'none',
                    }}>
                      {formula.name}
                    </summary>
                    <div style={{ padding: '8px 0', fontSize: '12px', lineHeight: '1.5' }}>
                      <div style={{ marginBottom: '4px' }}>
                        <strong>Formula:</strong> <code>{formula.formula}</code>
                      </div>
                      {formula.explanation && (
                        <div style={{ color: 'var(--text-muted)' }}>
                          {formula.explanation}
                        </div>
                      )}
                    </div>
                  </details>
                ))}
                {Object.keys(formulas).length > 10 && (
                  <div style={{ textAlign: 'center', padding: '12px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    ... and {Object.keys(formulas).length - 10} more formulas
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
