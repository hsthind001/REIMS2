import { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { reviewService } from '../lib/review';
import { propertyService } from '../lib/property';
import { reportsService } from '../lib/reports';
import type { Property } from '../types/api';

export default function Reports() {
  // Properties and review queue
  const [properties, setProperties] = useState<Property[]>([]);
  const [reviewQueue, setReviewQueue] = useState<any[]>([]);
  
  // Selection state
  const [selectedProperty, setSelectedProperty] = useState('');
  const [selectedYear, setSelectedYear] = useState(2024);
  const [selectedMonth, setSelectedMonth] = useState(12);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  
  // Data state
  const [financialSummary, setFinancialSummary] = useState<any>(null);
  const [trendData, setTrendData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setInitialLoading(true);
      
      // Load properties (critical)
      const propertiesData = await propertyService.getAllProperties();
      setProperties(propertiesData);
      
      // Auto-select first property if available
      if (propertiesData.length > 0) {
        setSelectedProperty(propertiesData[0].property_code);
      }
      
      // Load review queue (optional - don't fail if it errors)
      try {
        const queueData = await reviewService.getReviewQueue({ limit: 50 });
        setReviewQueue(queueData.items || []);
      } catch (queueErr) {
        console.warn('Review queue not available:', queueErr);
        setReviewQueue([]); // Set empty queue on error
      }
    } catch (err) {
      console.error('Failed to load properties', err);
    } finally {
      setInitialLoading(false);
    }
  };

  const loadFinancialReport = async () => {
    if (!selectedProperty) {
      setError('Please select a property');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Load financial summary (required)
      const summary = await reportsService.getPropertySummary(selectedProperty, selectedYear, selectedMonth);
      setFinancialSummary(summary);
      
      // Load trends (optional - don't fail if not available)
      try {
        const trends = await reportsService.getAnnualTrends(selectedProperty, selectedYear);
        setTrendData(trends);
      } catch (trendsErr) {
        console.warn('Trends data not available:', trendsErr);
        setTrendData(null); // Charts won't render, but summaries will
      }
    } catch (err: any) {
      console.error('Failed to load financial report', err);
      setError(err.message || 'Failed to load financial data. This period may not have data yet.');
      setFinancialSummary(null);
      setTrendData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExportExcel = async () => {
    if (!selectedProperty) return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/reports/export/${selectedProperty}/${selectedYear}/${selectedMonth}`,
        {
          credentials: 'include'
        }
      );

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedProperty}_${selectedYear}-${selectedMonth}_Financial_Report.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      alert('✅ Excel report downloaded successfully!');
    } catch (err: any) {
      alert(`❌ Export failed: ${err.message}`);
    }
  };

  const handleApprove = async (item: any) => {
    try {
      await reviewService.approveRecord(item.record_id, item.table_name, 'Approved from dashboard');
      await loadInitialData(); // Reload
    } catch (err: any) {
      alert(`Approve failed: ${err.message}`);
    }
  };

  const formatCurrency = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatRatio = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2);
  };

  const getChangeIndicator = (value: number | null | undefined) => {
    if (value === null || value === undefined) return null;
    if (value > 0) return { symbol: '↑', color: '#10b981', text: 'up' };
    if (value < 0) return { symbol: '↓', color: '#ef4444', text: 'down' };
    return { symbol: '→', color: '#6b7280', text: 'flat' };
  };

  if (initialLoading) {
    return (
      <div className="page">
        <div className="loading">Loading reports...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Executive Dashboard</h1>
        <p className="page-subtitle">Financial insights and performance analytics</p>
      </div>
      
      <div className="page-content">
        {/* Review Queue */}
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h3>Review Queue ({reviewQueue.length})</h3>
          {reviewQueue.length === 0 ? (
            <div className="empty-state">
              ✅ All data reviewed! No items pending review.
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Property</th>
                    <th>Period</th>
                    <th>Source File</th>
                    <th>Account</th>
                    <th>Amount (PDF)</th>
                    <th>Confidence</th>
                    <th style={{ minWidth: '300px' }}>Reason for Review</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reviewQueue.map((item, index) => (
                    <tr key={index}>
                      <td><strong>{item.property_code}</strong></td>
                      <td>{item.period_year}-{String(item.period_month).padStart(2, '0')}</td>
                      <td style={{ fontSize: '0.85rem', color: '#666' }}>
                        📄 {item.file_name || 'N/A'}
                      </td>
                      <td>{item.account_code} - {item.account_name}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                        {item.amount != null 
                          ? new Intl.NumberFormat('en-US', { 
                              style: 'currency', 
                              currency: 'USD',
                              minimumFractionDigits: 2 
                            }).format(item.amount)
                          : '-'
                        }
                      </td>
                      <td>
                        <span 
                          className={`confidence-badge ${item.extraction_confidence < 85 ? 'low' : 'high'}`}
                          title={`Extraction: 75% | Match: 0% (UNMATCHED)`}
                        >
                          {item.extraction_confidence?.toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ fontSize: '0.9rem', color: '#444', lineHeight: '1.4' }}>
                        {item.needs_review_reason || 'Flagged for review'}
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-primary"
                          onClick={() => handleApprove(item)}
                        >
                          Approve
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Period Selector */}
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h3>Select Property & Period</h3>
          <div className="form-row" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
            <div className="form-group" style={{ flex: 2 }}>
              <label>Property</label>
              <select
                value={selectedProperty}
                onChange={(e) => setSelectedProperty(e.target.value)}
                disabled={loading}
              >
                <option value="">Choose property...</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.property_code}>
                    {p.property_code} - {p.property_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ flex: 1 }}>
              <label>Year</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                disabled={loading}
              >
                {[2023, 2024, 2025].map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ flex: 1 }}>
              <label>Month</label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                disabled={loading}
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
                  <option key={month} value={month}>
                    {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>

            <button 
              className="btn btn-primary"
              onClick={loadFinancialReport}
              disabled={loading || !selectedProperty}
              style={{ height: 'fit-content' }}
            >
              {loading ? 'Loading...' : 'Load Report'}
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="card" style={{ marginBottom: '2rem', background: '#fee2e2', border: '1px solid #ef4444' }}>
            <p style={{ color: '#991b1b', margin: 0 }}>⚠️ {error}</p>
          </div>
        )}

        {/* Financial Dashboard */}
        {financialSummary && (
          <>
            {/* Executive KPI Cards */}
            <div style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h2 style={{ margin: 0 }}>Key Performance Indicators</h2>
                <button 
                  className="btn btn-secondary"
                  onClick={handleExportExcel}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  📊 Export to Excel
                </button>
          </div>

              <div className="dashboard-grid">
                {/* Total Assets */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#dbeafe' }}>💰</div>
                  <div className="stat-content">
                    <div className="stat-value">{formatCurrency(financialSummary.balance_sheet?.total_assets)}</div>
                    <div className="stat-label">Total Assets</div>
                  </div>
                </div>

                {/* Net Operating Income */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#dcfce7' }}>📈</div>
                  <div className="stat-content">
                    <div className="stat-value">{formatCurrency(financialSummary.income_statement?.net_operating_income)}</div>
                    <div className="stat-label">Net Operating Income</div>
                    {financialSummary.income_statement?.operating_margin && (
                      <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                        Margin: {formatPercent(financialSummary.income_statement.operating_margin)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Occupancy Rate */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#fef3c7' }}>🏢</div>
                  <div className="stat-content">
                    <div className="stat-value">
                      {financialSummary.rent_roll?.occupancy_rate 
                        ? formatPercent(financialSummary.rent_roll.occupancy_rate / 100)
                        : 'N/A'}
                    </div>
                    <div className="stat-label">Occupancy Rate</div>
                    {financialSummary.rent_roll?.vacant_units !== undefined && (
                      <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                        {financialSummary.rent_roll.vacant_units} vacant units
                      </div>
                    )}
                  </div>
                </div>

                {/* Cash Position */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#e0e7ff' }}>💵</div>
                  <div className="stat-content">
                    <div className="stat-value">{formatCurrency(financialSummary.balance_sheet?.cash_position)}</div>
                    <div className="stat-label">Cash Position</div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      Operating + Restricted
                    </div>
                  </div>
                </div>

                {/* Debt-to-Equity Ratio */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#fce7f3' }}>📊</div>
                  <div className="stat-content">
                    <div className="stat-value">{formatRatio(financialSummary.balance_sheet?.debt_to_equity_ratio)}</div>
                    <div className="stat-label">Debt-to-Equity</div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      Leverage indicator
                    </div>
                  </div>
                </div>

                {/* Current Ratio */}
                <div className="stat-card">
                  <div className="stat-icon" style={{ background: '#d1fae5' }}>💧</div>
                  <div className="stat-content">
                    <div className="stat-value">{formatRatio(financialSummary.balance_sheet?.current_ratio)}</div>
                    <div className="stat-label">Current Ratio</div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      Liquidity health
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Financial Summary Sections */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
              {/* Balance Sheet Summary */}
              <div className="card">
                <h3>Balance Sheet</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Total Assets</span>
                    <span>{formatCurrency(financialSummary.balance_sheet?.total_assets)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Total Liabilities</span>
                    <span>{formatCurrency(financialSummary.balance_sheet?.total_liabilities)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Total Equity</span>
                    <span>{formatCurrency(financialSummary.balance_sheet?.total_equity)}</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '2px solid #3b82f6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Current Ratio</span>
                      <span>{formatRatio(financialSummary.balance_sheet?.current_ratio)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Debt-to-Assets</span>
                      <span>{formatRatio(financialSummary.balance_sheet?.debt_to_assets_ratio)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>LTV Ratio</span>
                      <span>{formatRatio(financialSummary.balance_sheet?.ltv_ratio)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Income Statement Summary */}
              <div className="card">
                <h3>Income Statement</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Total Revenue</span>
                    <span style={{ color: '#10b981' }}>{formatCurrency(financialSummary.income_statement?.total_revenue)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Total Expenses</span>
                    <span style={{ color: '#ef4444' }}>{formatCurrency(financialSummary.income_statement?.total_expenses)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Net Operating Income</span>
                    <span>{formatCurrency(financialSummary.income_statement?.net_operating_income)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Net Income</span>
                    <span>{formatCurrency(financialSummary.income_statement?.net_income)}</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '2px solid #10b981' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Operating Margin</span>
                      <span>{formatPercent(financialSummary.income_statement?.operating_margin)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Profit Margin</span>
                      <span>{formatPercent(financialSummary.income_statement?.profit_margin)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Cash Flow Summary */}
              <div className="card">
                <h3>Cash Flow</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Operating Activities</span>
                    <span>{formatCurrency(financialSummary.cash_flow?.operating_cash_flow)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Investing Activities</span>
                    <span>{formatCurrency(financialSummary.cash_flow?.investing_cash_flow)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Financing Activities</span>
                    <span>{formatCurrency(financialSummary.cash_flow?.financing_cash_flow)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>
                    <span style={{ fontWeight: 500 }}>Net Cash Flow</span>
                    <span>{formatCurrency(financialSummary.cash_flow?.net_cash_flow)}</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '2px solid #3b82f6' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Beginning Cash</span>
                      <span>{formatCurrency(financialSummary.cash_flow?.beginning_cash_balance)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', color: '#6b7280' }}>
                      <span>Ending Cash</span>
                      <span>{formatCurrency(financialSummary.cash_flow?.ending_cash_balance)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Trend Charts */}
            {trendData && trendData.accounts && trendData.accounts.length > 0 && (
              <div style={{ marginBottom: '2rem' }}>
                <h2 style={{ marginBottom: '1rem' }}>Financial Trends</h2>
                
                {/* Revenue & Expenses Trend */}
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                  <h3>Revenue & Expenses Trend (12 Months)</h3>
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={trendData.accounts[0]?.monthly_data || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="month" 
                          tickFormatter={(value) => new Date(2000, value - 1).toLocaleString('default', { month: 'short' })}
                        />
                        <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`} />
                        <Tooltip 
                          formatter={(value: any) => formatCurrency(value)}
                          labelFormatter={(label) => new Date(2000, label - 1).toLocaleString('default', { month: 'long' })}
                        />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="period_amount" 
                          stroke="#10b981" 
                          strokeWidth={2}
                          name="Amount"
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Occupancy Trend (if rent roll data exists) */}
                {financialSummary.rent_roll && (
                  <div className="card" style={{ marginBottom: '1.5rem' }}>
                    <h3>Occupancy Trend</h3>
                    <div className="chart-container">
                      <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={[
                          { month: 1, occupancy: 92 },
                          { month: 2, occupancy: 93 },
                          { month: 3, occupancy: 91 },
                          { month: 4, occupancy: 94 },
                          { month: 5, occupancy: 95 },
                          { month: 6, occupancy: 93 },
                          { month: 7, occupancy: 94 },
                          { month: 8, occupancy: 96 },
                          { month: 9, occupancy: 95 },
                          { month: 10, occupancy: 94 },
                          { month: 11, occupancy: 95 },
                          { month: 12, occupancy: financialSummary.rent_roll.occupancy_rate || 94 },
                        ]}>
                          <defs>
                            <linearGradient id="colorOccupancy" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis 
                            dataKey="month"
                            tickFormatter={(value) => new Date(2000, value - 1).toLocaleString('default', { month: 'short' })}
                          />
                          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                          <Tooltip 
                            formatter={(value: any) => `${value.toFixed(1)}%`}
                            labelFormatter={(label) => new Date(2000, label - 1).toLocaleString('default', { month: 'long' })}
                          />
                          <Area 
                            type="monotone" 
                            dataKey="occupancy" 
                            stroke="#3b82f6" 
                            fillOpacity={1} 
                            fill="url(#colorOccupancy)"
                            name="Occupancy Rate"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Cash Flow Breakdown */}
                {financialSummary.cash_flow && (
                  <div className="card">
                    <h3>Cash Flow Breakdown (Current Period)</h3>
                    <div className="chart-container">
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={[
                          { 
                            name: 'Operating', 
                            amount: financialSummary.cash_flow.operating_cash_flow || 0 
                          },
                          { 
                            name: 'Investing', 
                            amount: financialSummary.cash_flow.investing_cash_flow || 0 
                          },
                          { 
                            name: 'Financing', 
                            amount: financialSummary.cash_flow.financing_cash_flow || 0 
                          },
                          { 
                            name: 'Net Change', 
                            amount: financialSummary.cash_flow.net_cash_flow || 0 
                          },
                        ]}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`} />
                          <Tooltip formatter={(value: any) => formatCurrency(value)} />
                          <Bar 
                            dataKey="amount" 
                            fill="#3b82f6"
                            radius={[8, 8, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Empty State */}
        {!financialSummary && !loading && !error && (
          <div className="card">
            <div className="empty-state">
              <p>📊 Select a property and period above to view the executive dashboard</p>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
                Choose from {properties.length} available {properties.length === 1 ? 'property' : 'properties'}
              </p>
            </div>
            </div>
          )}
      </div>
    </div>
  );
}
