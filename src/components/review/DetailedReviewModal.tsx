/**
 * Detailed Review Modal Component
 * 
 * Comprehensive review interface with PDF context, field-level corrections,
 * account mapping suggestions, and impact analysis
 */

import { useState, useEffect } from 'react';
import { X, Check, AlertTriangle, FileText, TrendingUp, TrendingDown, Info } from 'lucide-react';
import { reviewService } from '../../lib/review';
import { propertyService } from '../../lib/property';
import { AnomalyPDFViewer } from '../AnomalyPDFViewer';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

interface ReviewQueueItem {
  record_id: number;
  table_name: string;
  property_code: string;
  property_name: string;
  period_year: number;
  period_month: number;
  account_code?: string;
  account_name?: string;
  amount?: number;
  period_amount?: number;
  monthly_rent?: number;
  extraction_confidence?: number;
  match_confidence?: number;
  match_strategy?: string;
  needs_review: boolean;
  reviewed: boolean;
  document_id?: number;
  field_coordinates?: any;
}

interface DetailedReviewModalProps {
  item: ReviewQueueItem;
  onSave: (corrections: Record<string, any>, notes: string) => Promise<void>;
  onApprove: () => Promise<void>;
  onClose: () => void;
}

interface FieldCorrection {
  field_name: string;
  original_value: any;
  corrected_value: any;
  confidence?: number;
  field_type: 'numeric' | 'text' | 'account_code';
}

interface AccountSuggestion {
  account_code: string;
  account_name: string;
  confidence: number;
  match_reason: string;
  usage_count?: number;
}

interface ImpactAnalysis {
  dscr_impact?: {
    before: number;
    after: number;
    change: number;
    status_before: string;
    status_after: string;
  };
  covenant_impact?: {
    affected_covenants: string[];
    impact_level: 'none' | 'low' | 'medium' | 'high';
  };
  financial_impact?: {
    total_variance: number;
    requires_dual_approval: boolean;
  };
}

export function DetailedReviewModal({ item, onSave, onApprove, onClose }: DetailedReviewModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'fields' | 'pdf' | 'suggestions' | 'impact'>('fields');
  
  // Field corrections
  const [fieldCorrections, setFieldCorrections] = useState<FieldCorrection[]>([]);
  const [accountSuggestions, setAccountSuggestions] = useState<AccountSuggestion[]>([]);
  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysis | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfCoordinates, setPdfCoordinates] = useState<any>(null);
  const [notes, setNotes] = useState('');
  const [recordDetails, setRecordDetails] = useState<any>(null);
  
  // Property and period context
  const [property, setProperty] = useState<any>(null);

  useEffect(() => {
    loadReviewData();
  }, [item]);

  const loadReviewData = async () => {
    setLoading(true);
    try {
      // Load record details
      const detailsResponse = await fetch(
        `${API_BASE_URL}/review/${item.record_id}?table_name=${item.table_name}`,
        { credentials: 'include' }
      );
      if (detailsResponse.ok) {
        const details = await detailsResponse.json();
        setRecordDetails(details);
        
        // Initialize field corrections from record details
        const fields: FieldCorrection[] = [];
        if (details.account_code) {
          fields.push({
            field_name: 'account_code',
            original_value: details.account_code,
            corrected_value: details.account_code,
            confidence: item.match_confidence,
            field_type: 'account_code'
          });
        }
        if (details.account_name) {
          fields.push({
            field_name: 'account_name',
            original_value: details.account_name,
            corrected_value: details.account_name,
            field_type: 'text'
          });
        }
        if (details.amount !== undefined) {
          fields.push({
            field_name: 'amount',
            original_value: details.amount,
            corrected_value: details.amount,
            confidence: item.extraction_confidence,
            field_type: 'numeric'
          });
        }
        if (details.period_amount !== undefined) {
          fields.push({
            field_name: 'period_amount',
            original_value: details.period_amount,
            corrected_value: details.period_amount,
            confidence: item.extraction_confidence,
            field_type: 'numeric'
          });
        }
        setFieldCorrections(fields);
      }

      // Load account suggestions if account_code needs correction
      if (item.account_code === 'UNMATCHED' || !item.account_code || (item.match_confidence && item.match_confidence < 95)) {
        await loadAccountSuggestions();
      }

      // Load PDF URL and coordinates if available
      if (item.document_id) {
        await loadPdfContext();
      }

      // Load property details
      const properties = await propertyService.getAllProperties();
      const prop = properties.find(p => p.property_code === item.property_code);
      if (prop) {
        setProperty(prop);
      }

      // Calculate impact analysis
      await calculateImpactAnalysis();

    } catch (error) {
      console.error('Error loading review data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAccountSuggestions = async () => {
    try {
      // Use auto-suggestion service endpoint
      const response = await fetch(
        `${API_BASE_URL}/review/auto-suggest?property_id=${property?.id || ''}&table_name=${item.table_name}&raw_label=${encodeURIComponent(item.account_name || '')}`,
        { credentials: 'include' }
      );
      if (response.ok) {
        const suggestions = await response.json();
        setAccountSuggestions(suggestions.suggestions || []);
      }
    } catch (error) {
      console.error('Error loading account suggestions:', error);
    }
  };

  const loadPdfContext = async () => {
    try {
      // Get PDF URL from document
      const response = await fetch(
        `${API_BASE_URL}/documents/${item.document_id}/pdf-url`,
        { credentials: 'include' }
      );
      if (response.ok) {
        const data = await response.json();
        setPdfUrl(data.pdf_url);
        
        // If field coordinates are available, set them
        if (item.field_coordinates) {
          setPdfCoordinates(item.field_coordinates);
        }
      }
    } catch (error) {
      console.error('Error loading PDF context:', error);
    }
  };

  const calculateImpactAnalysis = async () => {
    try {
      // Calculate impact of corrections
      const corrections = fieldCorrections
        .filter(f => f.original_value !== f.corrected_value)
        .reduce((acc, f) => {
          acc[f.field_name] = f.corrected_value;
          return acc;
        }, {} as Record<string, any>);

      if (Object.keys(corrections).length === 0) {
        setImpactAnalysis(null);
        return;
      }

      // For now, calculate a simplified impact analysis
      // In a full implementation, this would call a dedicated impact analysis endpoint
      const totalVariance = fieldCorrections
        .filter(f => f.original_value !== f.corrected_value && f.field_type === 'numeric')
        .reduce((sum, f) => {
          const oldVal = typeof f.original_value === 'number' ? f.original_value : 0;
          const newVal = typeof f.corrected_value === 'number' ? f.corrected_value : 0;
          return sum + Math.abs(newVal - oldVal);
        }, 0);

      const requiresDualApproval = totalVariance > 10000; // Threshold for dual approval

      setImpactAnalysis({
        financial_impact: {
          total_variance: totalVariance,
          requires_dual_approval: requiresDualApproval
        },
        // DSCR and covenant impact would be calculated by backend
        dscr_impact: undefined,
        covenant_impact: undefined
      });
    } catch (error) {
      console.error('Error calculating impact analysis:', error);
    }
  };

  const updateFieldCorrection = (fieldName: string, newValue: any) => {
    setFieldCorrections(prev => prev.map(f => 
      f.field_name === fieldName 
        ? { ...f, corrected_value: newValue }
        : f
    ));
    
    // Recalculate impact when corrections change
    setTimeout(() => calculateImpactAnalysis(), 500);
  };

  const selectAccountSuggestion = (suggestion: AccountSuggestion) => {
    updateFieldCorrection('account_code', suggestion.account_code);
    updateFieldCorrection('account_name', suggestion.account_name);
    setActiveTab('fields');
  };

  const handleSave = async () => {
    const corrections = fieldCorrections
      .filter(f => f.original_value !== f.corrected_value)
      .reduce((acc, f) => {
        acc[f.field_name] = f.corrected_value;
        return acc;
      }, {} as Record<string, any>);

    if (Object.keys(corrections).length === 0) {
      alert('No changes to save. Use "Approve" if the record is correct as-is.');
      return;
    }

    setSaving(true);
    try {
      await onSave(corrections, notes);
      onClose();
    } catch (error: any) {
      alert(`Failed to save: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!window.confirm('Approve this record without changes?')) {
      return;
    }

    setSaving(true);
    try {
      await onApprove();
      onClose();
    } catch (error: any) {
      alert(`Failed to approve: ${error.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal-content" style={{ maxWidth: '90vw', maxHeight: '90vh' }}>
          <div className="modal-body" style={{ textAlign: 'center', padding: '3rem' }}>
            <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
            <p>Loading review data...</p>
          </div>
        </div>
      </div>
    );
  }

  const hasChanges = fieldCorrections.some(f => f.original_value !== f.corrected_value);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '95vw', maxHeight: '95vh', width: '1200px' }}>
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>Detailed Review</h2>
            <p style={{ margin: '0.5rem 0 0', color: '#6b7280', fontSize: '0.875rem' }}>
              {item.property_code} • {item.period_year}-{String(item.period_month).padStart(2, '0')} • {item.table_name}
            </p>
          </div>
          <button onClick={onClose} className="close-btn" style={{ fontSize: '1.5rem', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
        </div>

        <div className="modal-body" style={{ padding: '1.5rem', overflowY: 'auto', maxHeight: 'calc(95vh - 200px)' }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
            <button
              onClick={() => setActiveTab('fields')}
              style={{
                padding: '0.75rem 1.5rem',
                border: 'none',
                background: activeTab === 'fields' ? '#3b82f6' : 'transparent',
                color: activeTab === 'fields' ? 'white' : '#374151',
                cursor: 'pointer',
                borderBottom: activeTab === 'fields' ? '2px solid #3b82f6' : '2px solid transparent',
                fontWeight: activeTab === 'fields' ? '600' : '400'
              }}
            >
              Fields
            </button>
            {pdfUrl && (
              <button
                onClick={() => setActiveTab('pdf')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: activeTab === 'pdf' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'pdf' ? 'white' : '#374151',
                  cursor: 'pointer',
                  borderBottom: activeTab === 'pdf' ? '2px solid #3b82f6' : '2px solid transparent',
                  fontWeight: activeTab === 'pdf' ? '600' : '400'
                }}
              >
                <FileText size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                PDF Context
              </button>
            )}
            {accountSuggestions.length > 0 && (
              <button
                onClick={() => setActiveTab('suggestions')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: activeTab === 'suggestions' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'suggestions' ? 'white' : '#374151',
                  cursor: 'pointer',
                  borderBottom: activeTab === 'suggestions' ? '2px solid #3b82f6' : '2px solid transparent',
                  fontWeight: activeTab === 'suggestions' ? '600' : '400'
                }}
              >
                Suggestions ({accountSuggestions.length})
              </button>
            )}
            {hasChanges && (
              <button
                onClick={() => setActiveTab('impact')}
                style={{
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  background: activeTab === 'impact' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'impact' ? 'white' : '#374151',
                  cursor: 'pointer',
                  borderBottom: activeTab === 'impact' ? '2px solid #3b82f6' : '2px solid transparent',
                  fontWeight: activeTab === 'impact' ? '600' : '400'
                }}
              >
                <TrendingUp size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                Impact Analysis
              </button>
            )}
          </div>

          {/* Tab Content */}
          {activeTab === 'fields' && (
            <div>
              <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem' }}>Field Corrections</h3>
              <div style={{ display: 'grid', gap: '1rem' }}>
                {fieldCorrections.map((field, idx) => (
                  <div key={idx} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <label style={{ fontWeight: '600', textTransform: 'capitalize' }}>
                        {field.field_name.replace(/_/g, ' ')}
                        {field.confidence !== undefined && (
                          <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: field.confidence < 85 ? '#dc2626' : field.confidence < 95 ? '#f59e0b' : '#10b981' }}>
                            ({field.confidence.toFixed(1)}% confidence)
                          </span>
                        )}
                      </label>
                      {field.original_value !== field.corrected_value && (
                        <span style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: '600' }}>CHANGED</span>
                      )}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Original</div>
                        <div style={{ padding: '0.5rem', background: '#f9fafb', borderRadius: '0.25rem', fontFamily: 'monospace' }}>
                          {field.original_value?.toString() || 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Corrected</div>
                        {field.field_type === 'account_code' ? (
                          <input
                            type="text"
                            value={field.corrected_value || ''}
                            onChange={(e) => updateFieldCorrection(field.field_name, e.target.value)}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem', border: '1px solid #d1d5db' }}
                            placeholder="e.g., 1010-0000"
                          />
                        ) : field.field_type === 'numeric' ? (
                          <input
                            type="number"
                            step="0.01"
                            value={field.corrected_value || 0}
                            onChange={(e) => updateFieldCorrection(field.field_name, parseFloat(e.target.value) || 0)}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem', border: '1px solid #d1d5db' }}
                          />
                        ) : (
                          <input
                            type="text"
                            value={field.corrected_value || ''}
                            onChange={(e) => updateFieldCorrection(field.field_name, e.target.value)}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.25rem', border: '1px solid #d1d5db' }}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Correction Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Describe the reason for these corrections..."
                  rows={4}
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', resize: 'vertical' }}
                />
              </div>
            </div>
          )}

          {activeTab === 'pdf' && pdfUrl && (
            <div>
              <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem' }}>PDF Context</h3>
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.5rem', overflow: 'hidden' }}>
                <AnomalyPDFViewer
                  pdfUrl={pdfUrl}
                  coordinates={pdfCoordinates?.coordinates ?? pdfCoordinates}
                  highlightType="actual"
                  onClose={() => {}}
                />
              </div>
            </div>
          )}

          {activeTab === 'suggestions' && (
            <div>
              <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem' }}>Account Mapping Suggestions</h3>
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {accountSuggestions.map((suggestion, idx) => (
                  <div
                    key={idx}
                    onClick={() => selectAccountSuggestion(suggestion)}
                    style={{
                      padding: '1rem',
                      border: '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      background: idx === 0 ? '#eff6ff' : 'white'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
                    onMouseLeave={(e) => e.currentTarget.style.background = idx === 0 ? '#eff6ff' : 'white'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '1rem' }}>
                          {suggestion.account_code} - {suggestion.account_name}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
                          {suggestion.match_reason}
                        </div>
                        {suggestion.usage_count !== undefined && (
                          <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                            Used {suggestion.usage_count} time(s) previously
                          </div>
                        )}
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: '600', color: suggestion.confidence >= 95 ? '#10b981' : suggestion.confidence >= 85 ? '#f59e0b' : '#dc2626' }}>
                          {suggestion.confidence.toFixed(1)}%
                        </div>
                        {idx === 0 && (
                          <div style={{ fontSize: '0.75rem', color: '#3b82f6', marginTop: '0.25rem' }}>Recommended</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'impact' && impactAnalysis && (
            <div>
              <h3 style={{ marginBottom: '1rem', fontSize: '1.125rem' }}>Impact Analysis</h3>
              
              {impactAnalysis.financial_impact && (
                <div style={{ marginBottom: '1.5rem', padding: '1rem', background: impactAnalysis.financial_impact.requires_dual_approval ? '#fef3c7' : '#f0fdf4', borderRadius: '0.5rem', border: `1px solid ${impactAnalysis.financial_impact.requires_dual_approval ? '#fbbf24' : '#86efac'}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Info size={20} />
                    <strong>Financial Impact</strong>
                  </div>
                  <div style={{ marginLeft: '1.75rem' }}>
                    <div>Total Variance: ${Math.abs(impactAnalysis.financial_impact.total_variance).toLocaleString()}</div>
                    {impactAnalysis.financial_impact.requires_dual_approval && (
                      <div style={{ marginTop: '0.5rem', color: '#92400e', fontWeight: '600' }}>
                        ⚠️ Requires Dual Approval
                      </div>
                    )}
                  </div>
                </div>
              )}

              {impactAnalysis.dscr_impact && (
                <div style={{ marginBottom: '1.5rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <TrendingUp size={20} />
                    <strong>DSCR Impact</strong>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginLeft: '1.75rem' }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Before</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: '600' }}>{impactAnalysis.dscr_impact.before.toFixed(2)}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{impactAnalysis.dscr_impact.status_before}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>After</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: '600' }}>{impactAnalysis.dscr_impact.after.toFixed(2)}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{impactAnalysis.dscr_impact.status_after}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Change</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: '600', color: impactAnalysis.dscr_impact.change >= 0 ? '#10b981' : '#dc2626' }}>
                        {impactAnalysis.dscr_impact.change >= 0 ? '+' : ''}{impactAnalysis.dscr_impact.change.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {impactAnalysis.covenant_impact && impactAnalysis.covenant_impact.affected_covenants.length > 0 && (
                <div style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <AlertTriangle size={20} />
                    <strong>Covenant Impact</strong>
                  </div>
                  <div style={{ marginLeft: '1.75rem' }}>
                    <div style={{ marginBottom: '0.5rem' }}>
                      Impact Level: <strong>{impactAnalysis.covenant_impact.impact_level.toUpperCase()}</strong>
                    </div>
                    <div>
                      Affected Covenants: {impactAnalysis.covenant_impact.affected_covenants.join(', ')}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem', borderTop: '1px solid #e5e7eb' }}>
          <button
            onClick={handleApprove}
            className="btn-secondary"
            disabled={saving || hasChanges}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Check size={16} />
            Approve As-Is
          </button>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button onClick={onClose} className="btn-secondary" disabled={saving}>
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="btn-primary"
              disabled={saving || !hasChanges}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              {saving ? 'Saving...' : 'Save Corrections'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
