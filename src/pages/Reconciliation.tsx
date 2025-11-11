import { useState, useEffect } from 'react';
import { propertyService } from '../lib/property';
import { reconciliationService, type ComparisonData, type ComparisonRecord } from '../lib/reconciliation';
import type { Property } from '../types/api';

export default function Reconciliation() {
  // Property and period selection
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [selectedYear, setSelectedYear] = useState(2024);
  const [selectedMonth, setSelectedMonth] = useState(12);
  const [selectedDocType, setSelectedDocType] = useState<string>('balance_sheet');
  
  // Reconciliation data
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const splitPosition = 50; // Fixed 50/50 split for now
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set());
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    loadProperties();
  }, []);

  // Clear comparison data when selection criteria changes
  useEffect(() => {
    // Clear stale data when user changes document type, property, year, or month
    if (comparisonData) {
      setComparisonData(null);
      setSelectedRecords(new Set());
      setError(null);
    }
  }, [selectedDocType, selectedProperty, selectedYear, selectedMonth]);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0) {
        setSelectedProperty(data[0].property_code);
      }
    } catch (err) {
      console.error('Failed to load properties:', err);
    }
  };

  const handleStartReconciliation = async () => {
    if (!selectedProperty) {
      setError('Please select a property');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const data = await reconciliationService.getComparison(
        selectedProperty,
        selectedYear,
        selectedMonth,
        selectedDocType
      );
      
      setComparisonData(data);
    } catch (err: any) {
      console.error('Reconciliation failed:', err);
      setError(err.response?.data?.detail || 'Failed to start reconciliation');
      setComparisonData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleResolveDifference = (record: ComparisonRecord) => {
    // TODO: Implement resolution dialog in Phase 2
    alert(`Resolve difference for ${record.account_code}: ${record.account_name}`);
  };

  const handleBulkAcceptPDF = async () => {
    if (selectedRecords.size === 0) {
      alert('Please select records to resolve');
      return;
    }

    try {
      setLoading(true);
      // In real implementation, would need difference IDs
      await reconciliationService.bulkResolve({
        difference_ids: Array.from(selectedRecords).map(code => parseInt(code)),
        action: 'accept_pdf'
      });
      
      alert(`✅ Resolved ${selectedRecords.size} differences`);
      setSelectedRecords(new Set());
      
      // Refresh data
      await handleStartReconciliation();
    } catch (err: any) {
      alert(`❌ Bulk resolve failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExportReport = async () => {
    if (!comparisonData) return;

    try {
      const blob = await reconciliationService.generateReport(comparisonData.session_id, 'excel');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reconciliation_${selectedProperty}_${selectedYear}-${selectedMonth}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      alert('✅ Report downloaded successfully!');
    } catch (err: any) {
      alert(`❌ Export failed: ${err.message}`);
    }
  };

  const toggleRecordSelection = (accountCode: string) => {
    const newSelected = new Set(selectedRecords);
    if (newSelected.has(accountCode)) {
      newSelected.delete(accountCode);
    } else {
      newSelected.add(accountCode);
    }
    setSelectedRecords(newSelected);
  };

  const getMatchStatusColor = (status: string): string => {
    switch (status) {
      case 'exact': return '#10b981'; // green
      case 'tolerance': return '#f59e0b'; // yellow
      case 'mismatch': return '#ef4444'; // red
      case 'missing_pdf': return '#6b7280'; // gray
      case 'missing_db': return '#8b5cf6'; // purple
      default: return '#6b7280';
    }
  };

  const getMatchStatusLabel = (status: string): string => {
    switch (status) {
      case 'exact': return 'Match';
      case 'tolerance': return 'Within Tolerance';
      case 'mismatch': return 'Mismatch';
      case 'missing_pdf': return 'Missing in PDF';
      case 'missing_db': return 'Missing in DB';
      default: return status;
    }
  };

  const filteredRecords = comparisonData?.comparison.records.filter(record => {
    if (filterStatus === 'all') return true;
    if (filterStatus === 'differences') return record.match_status !== 'exact';
    if (filterStatus === 'matches') return record.match_status === 'exact';
    if (filterStatus === 'needs_review') return record.needs_review;
    return true;
  }) || [];

  return (
    <div className="page">
      <div className="page-header">
        <h1>Financial Reconciliation</h1>
        <p className="page-subtitle">Compare PDF documents with database records</p>
      </div>
      
      <div className="page-content">
        {/* Selection Panel */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3>Select Document to Reconcile</h3>
          <div className="form-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="form-group">
              <label><strong>Property</strong></label>
              <select
                value={selectedProperty}
                onChange={(e) => setSelectedProperty(e.target.value)}
                disabled={loading}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="">Select property...</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.property_code}>
                    {p.property_code} - {p.property_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label><strong>Year</strong></label>
              <input
                type="number"
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                disabled={loading}
                min="2020"
                max="2030"
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              />
            </div>

            <div className="form-group">
              <label><strong>Month</strong></label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                disabled={loading}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => (
                  <option key={month} value={month}>
                    {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label><strong>Document Type</strong></label>
              <select
                value={selectedDocType}
                onChange={(e) => setSelectedDocType(e.target.value)}
                disabled={loading}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
              >
                <option value="balance_sheet">📊 Balance Sheet</option>
                <option value="income_statement">💰 Income Statement</option>
                <option value="cash_flow">💵 Cash Flow</option>
                <option value="rent_roll">🏠 Rent Roll</option>
              </select>
            </div>

            <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                className="btn btn-primary"
                onClick={handleStartReconciliation}
                disabled={loading || !selectedProperty}
                style={{ width: '100%' }}
              >
                {loading ? 'Loading...' : 'Start Reconciliation'}
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="card" style={{ marginBottom: '1.5rem', background: '#fee2e2', border: '1px solid #ef4444' }}>
            <p style={{ color: '#991b1b', margin: 0 }}>⚠️ {error}</p>
          </div>
        )}

        {/* Reconciliation View */}
        {comparisonData && (
          <>
            {/* Summary Stats */}
            <div className="dashboard-grid" style={{ marginBottom: '1.5rem' }}>
              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#e3f2fd' }}>📊</div>
                <div className="stat-content">
                  <div className="stat-value">{comparisonData.comparison.total_records}</div>
                  <div className="stat-label">Total Records</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#d1fae5' }}>✓</div>
                <div className="stat-content">
                  <div className="stat-value">{comparisonData.comparison.matches}</div>
                  <div className="stat-label">Matches</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#fee2e2' }}>⚠</div>
                <div className="stat-content">
                  <div className="stat-value">{comparisonData.comparison.differences}</div>
                  <div className="stat-label">Differences</div>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon" style={{ background: '#fef3c7' }}>📝</div>
                <div className="stat-content">
                  <div className="stat-value">{selectedRecords.size}</div>
                  <div className="stat-label">Selected</div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => setFilterStatus('all')}
                    style={{ background: filterStatus === 'all' ? '#3b82f6' : undefined, color: filterStatus === 'all' ? 'white' : undefined }}
                  >
                    All ({comparisonData.comparison.total_records})
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => setFilterStatus('matches')}
                    style={{ background: filterStatus === 'matches' ? '#3b82f6' : undefined, color: filterStatus === 'matches' ? 'white' : undefined }}
                  >
                    Matches ({comparisonData.comparison.matches})
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => setFilterStatus('differences')}
                    style={{ background: filterStatus === 'differences' ? '#3b82f6' : undefined, color: filterStatus === 'differences' ? 'white' : undefined }}
                  >
                    Differences ({comparisonData.comparison.differences})
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={handleBulkAcceptPDF}
                    disabled={selectedRecords.size === 0}
                  >
                    Accept PDF Values ({selectedRecords.size})
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={handleExportReport}
                  >
                    📊 Export Report
                  </button>
                </div>
              </div>
            </div>

            {/* Split View */}
            <div className="card">
              <div style={{ display: 'grid', gridTemplateColumns: `${splitPosition}% ${100 - splitPosition}%`, gap: '1rem', minHeight: '600px' }}>
                {/* PDF Viewer (Left Panel) */}
                <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.375rem', overflow: 'hidden' }}>
                  <div style={{ background: '#f3f4f6', padding: '0.5rem', borderBottom: '1px solid #e5e7eb', fontWeight: 'bold' }}>
                    📄 Original PDF
                  </div>
                  {comparisonData.pdf_url ? (
                    <iframe
                      src={comparisonData.pdf_url}
                      style={{ width: '100%', height: 'calc(100% - 40px)', border: 'none' }}
                      title="PDF Viewer"
                    />
                  ) : (
                    <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
                      PDF not available
                    </div>
                  )}
                </div>

                {/* Data Table (Right Panel) */}
                <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.375rem', overflow: 'auto' }}>
                  <div style={{ background: '#f3f4f6', padding: '0.5rem', borderBottom: '1px solid #e5e7eb', fontWeight: 'bold' }}>
                    📊 Database Records
                  </div>
                  <div style={{ maxHeight: 'calc(100% - 40px)', overflow: 'auto' }}>
                    <table className="data-table" style={{ width: '100%' }}>
                      <thead style={{ position: 'sticky', top: 0, background: 'white', zIndex: 1 }}>
                        <tr>
                          <th style={{ padding: '0.5rem' }}>
                            <input
                              type="checkbox"
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedRecords(new Set(filteredRecords.map(r => r.account_code)));
                                } else {
                                  setSelectedRecords(new Set());
                                }
                              }}
                              checked={selectedRecords.size === filteredRecords.length && filteredRecords.length > 0}
                            />
                          </th>
                          <th>{selectedDocType === 'rent_roll' ? 'Unit' : 'Account Code'}</th>
                          <th>{selectedDocType === 'rent_roll' ? 'Tenant' : 'Account Name'}</th>
                          {selectedDocType === 'rent_roll' ? (
                            <>
                              <th>Tenant ID</th>
                              <th>Lease Type</th>
                              <th style={{ textAlign: 'right' }}>Sq Ft</th>
                              <th style={{ textAlign: 'right' }}>Monthly Rent</th>
                              <th style={{ textAlign: 'right' }}>$/SF (Mo)</th>
                              <th style={{ textAlign: 'right' }}>Annual Rent</th>
                              <th style={{ textAlign: 'right' }}>$/SF (Yr)</th>
                              <th>Lease Start</th>
                              <th>Lease End</th>
                              <th style={{ textAlign: 'right' }}>Term (Mo)</th>
                              <th style={{ textAlign: 'right' }}>Tenancy (Yrs)</th>
                              <th style={{ textAlign: 'right' }}>Security Dep</th>
                              <th style={{ textAlign: 'right' }}>LOC</th>
                              <th>Occupancy</th>
                              <th>Status</th>
                            </>
                          ) : (
                            <>
                              <th style={{ textAlign: 'right' }}>PDF Value</th>
                              <th style={{ textAlign: 'right' }}>DB Value</th>
                              <th style={{ textAlign: 'right' }}>Difference</th>
                            </>
                          )}
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredRecords.map((record) => (
                          <tr
                            key={record.account_code}
                            style={{
                              background: selectedRecords.has(record.account_code) ? '#eff6ff' : undefined
                            }}
                          >
                            <td style={{ padding: '0.5rem' }}>
                              <input
                                type="checkbox"
                                checked={selectedRecords.has(record.account_code)}
                                onChange={() => toggleRecordSelection(record.account_code)}
                              />
                            </td>
                            <td style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{record.account_code}</td>
                            <td>{record.account_name}</td>
                            
                            {selectedDocType === 'rent_roll' && record.rent_roll_fields ? (
                              <>
                                {/* Rent Roll: Extended columns with ALL fields */}
                                <td style={{ fontSize: '0.75rem', color: '#6b7280' }}>{record.rent_roll_fields.tenant_code || '-'}</td>
                                <td style={{ fontSize: '0.875rem' }}>{record.rent_roll_fields.lease_type || '-'}</td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.rent_roll_fields.unit_area_sqft !== null && record.rent_roll_fields.unit_area_sqft !== undefined ? record.rent_roll_fields.unit_area_sqft.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 'bold' }}>
                                  {record.pdf_value !== null ? `$${record.pdf_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                  {record.rent_roll_fields.monthly_rent_per_sqft !== null && record.rent_roll_fields.monthly_rent_per_sqft !== undefined ? `$${record.rent_roll_fields.monthly_rent_per_sqft.toFixed(2)}` : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.rent_roll_fields.annual_rent !== null && record.rent_roll_fields.annual_rent !== undefined ? `$${record.rent_roll_fields.annual_rent.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                  {record.rent_roll_fields.annual_rent_per_sqft !== null && record.rent_roll_fields.annual_rent_per_sqft !== undefined ? `$${record.rent_roll_fields.annual_rent_per_sqft.toFixed(2)}` : '-'}
                                </td>
                                <td style={{ fontSize: '0.875rem' }}>{record.rent_roll_fields.lease_start_date || '-'}</td>
                                <td style={{ fontSize: '0.875rem' }}>{record.rent_roll_fields.lease_end_date || '-'}</td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 'bold', color: '#2563eb' }}>
                                  {record.rent_roll_fields.lease_term_months || '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.rent_roll_fields.tenancy_years !== null && record.rent_roll_fields.tenancy_years !== undefined ? record.rent_roll_fields.tenancy_years.toFixed(1) : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.rent_roll_fields.security_deposit !== null && record.rent_roll_fields.security_deposit !== undefined ? `$${record.rent_roll_fields.security_deposit.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.rent_roll_fields.loc_amount !== null && record.rent_roll_fields.loc_amount !== undefined && record.rent_roll_fields.loc_amount > 0 ? `$${record.rent_roll_fields.loc_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '-'}
                                </td>
                                <td>
                                  <span style={{ 
                                    padding: '0.25rem 0.5rem', 
                                    borderRadius: '0.25rem', 
                                    fontSize: '0.75rem',
                                    fontWeight: 'bold',
                                    background: record.rent_roll_fields.occupancy_status === 'occupied' ? '#d1fae5' : '#fee2e2',
                                    color: record.rent_roll_fields.occupancy_status === 'occupied' ? '#065f46' : '#991b1b'
                                  }}>
                                    {record.rent_roll_fields.occupancy_status || 'unknown'}
                                  </span>
                                </td>
                                <td>
                                  <span style={{ 
                                    fontSize: '0.75rem',
                                    padding: '0.25rem 0.5rem',
                                    borderRadius: '0.25rem',
                                    background: record.rent_roll_fields.lease_status === 'active' ? '#e0f2fe' : '#fef3c7',
                                    color: record.rent_roll_fields.lease_status === 'active' ? '#075985' : '#92400e'
                                  }}>
                                    {record.rent_roll_fields.lease_status || '-'}
                                  </span>
                                </td>
                              </>
                            ) : (
                              <>
                                {/* Financial Statements: Standard amount comparison */}
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.pdf_value !== null ? record.pdf_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                                  {record.db_value !== null ? record.db_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'monospace', color: record.difference && record.difference > 0 ? '#ef4444' : undefined }}>
                                  {record.difference !== null ? record.difference.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                                </td>
                              </>
                            )}
                            
                            <td>
                              <span
                                style={{
                                  display: 'inline-block',
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '0.25rem',
                                  fontSize: '0.75rem',
                                  fontWeight: 'bold',
                                  background: getMatchStatusColor(record.match_status),
                                  color: 'white'
                                }}
                              >
                                {getMatchStatusLabel(record.match_status)}
                              </span>
                            </td>
                            <td>
                              {record.match_status !== 'exact' && (
                                <button
                                  className="btn btn-sm btn-secondary"
                                  onClick={() => handleResolveDifference(record)}
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                >
                                  Resolve
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Empty State */}
        {!comparisonData && !loading && (
          <div className="card">
            <div className="empty-state">
              <p>🔄 Select a property, period, and document type above to start reconciliation</p>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
                The system will compare PDF-extracted data with database records side-by-side
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

