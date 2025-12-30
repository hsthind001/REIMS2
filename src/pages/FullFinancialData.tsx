import { useEffect, useState } from 'react';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { propertyService } from '../lib/property';
import { documentService } from '../lib/document';
import { financialDataService, type FinancialDataItem, type FinancialDataResponse } from '../lib/financial_data';
import { financialPeriodsService, type FinancialPeriod } from '../lib/financial_periods';
import { MortgageDataTable } from '../components/mortgage/MortgageDataTable';
import { MortgageMetrics } from '../components/mortgage/MortgageMetrics';
import { reconciliationService, type ComparisonData } from '../lib/reconciliation';
import type { Property, DocumentUpload as DocumentUploadType } from '../types/api';

type StatementType = 'income_statement' | 'balance_sheet' | 'cash_flow' | 'mortgage_statement';

const parseHashParams = () => {
  const hash = window.location.hash || '';
  const params = new URLSearchParams(hash.split('?')[1] || '');
  return {
    property: params.get('property') || '',
    year: Number(params.get('year')) || new Date().getFullYear(),
    month: Number(params.get('month')) || new Date().getMonth() + 1,
    doc: (params.get('doc') as StatementType) || null,
  };
};

export default function FullFinancialData() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentUploadType[]>([]);
  const [selectedStatementType, setSelectedStatementType] = useState<StatementType | null>(null);
  const [financialData, setFinancialData] = useState<FinancialDataResponse | null>(null);
  const [loadingFinancialData, setLoadingFinancialData] = useState(false);
  const [currentPeriodId, setCurrentPeriodId] = useState<number | null>(null);
  const [availablePeriods, setAvailablePeriods] = useState<FinancialPeriod[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<number | null>(null);
  const [selectedYear, setSelectedYear] = useState<number>(parseHashParams().year);
  const [selectedMonth, setSelectedMonth] = useState<number>(parseHashParams().month);
  const [mortgageComparison, setMortgageComparison] = useState<ComparisonData | null>(null);
  const [loadingMortgageComparison, setLoadingMortgageComparison] = useState(false);
  const [mortgageMessage, setMortgageMessage] = useState<string>('');

  const setPeriodFromDoc = async (doc: DocumentUploadType) => {
    const year = doc.period_year || selectedYear;
    const month = doc.period_month || selectedMonth;
    setSelectedYear(year);
    setSelectedMonth(month);

    if (selectedProperty) {
      try {
        const period = await financialPeriodsService.getOrCreatePeriod(selectedProperty.id, year, month);
        setSelectedPeriodId(period.id);
        setCurrentPeriodId(period.id);
      } catch (err) {
        console.error('Failed to sync period from document:', err);
      }
    }
  };

  const { property: propertyFromHash, doc: docFromHash } = parseHashParams();

  useEffect(() => {
    // Load properties and select initial one
    const loadProps = async () => {
      try {
        const props = await propertyService.getAllProperties();
        setProperties(props);
        const match = props.find(p => p.property_code === propertyFromHash);
        setSelectedProperty(match || props[0] || null);
      } catch (err) {
        console.error('Failed to load properties:', err);
      }
    };
    loadProps();
  }, [propertyFromHash]);

  useEffect(() => {
    if (selectedProperty) {
      loadAvailablePeriods(selectedProperty.id);
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  useEffect(() => {
    // Auto-select statement type based on docs or hash param
    if (!selectedStatementType && availableDocuments.length > 0) {
      const preferredOrder: StatementType[] = ['income_statement', 'balance_sheet', 'cash_flow', 'mortgage_statement'];
      const hashPreferred = docFromHash && (docFromHash as StatementType);
      const firstDoc =
        availableDocuments.find(d => hashPreferred ? d.document_type === hashPreferred : false) ||
        availableDocuments.find(d => d.extraction_status === 'completed' && preferredOrder.includes(d.document_type as StatementType)) ||
        availableDocuments.find(d => preferredOrder.includes(d.document_type as StatementType));

      if (firstDoc) {
        setSelectedStatementType(firstDoc.document_type as StatementType);
      }
    }
  }, [availableDocuments, selectedStatementType, docFromHash]);

  useEffect(() => {
    // When statement changes, load data (non-mortgage)
    if (selectedProperty && selectedStatementType && selectedStatementType !== 'mortgage_statement') {
      loadFullFinancialData(selectedStatementType);
      setMortgageComparison(null);
    }
  }, [selectedStatementType, selectedProperty, availableDocuments]);

  useEffect(() => {
    // When mortgage statement selected, load comparison table
    if (selectedStatementType === 'mortgage_statement' && selectedProperty) {
      loadMortgageComparison();
    }
  }, [selectedStatementType, selectedProperty, selectedYear, selectedMonth]);

  const loadAvailablePeriods = async (propertyId: number) => {
    try {
      const periods = await financialPeriodsService.listPeriods({ property_id: propertyId });
      const sorted = [...periods].sort((a, b) => {
        if (a.period_year !== b.period_year) return b.period_year - a.period_year;
        return b.period_month - a.period_month;
      });
      setAvailablePeriods(sorted);

      // Try to select period from hash/year-month, else most recent
      let match = sorted.find(
        (p) => p.period_year === selectedYear && p.period_month === selectedMonth
      );

      if (!match && selectedYear && selectedMonth) {
        // Ensure period exists
        match = await financialPeriodsService.getOrCreatePeriod(propertyId, selectedYear, selectedMonth);
        // Add to list if new
        const exists = sorted.find((p) => p.id === match.id);
        if (!exists) {
          setAvailablePeriods((prev) => [match!, ...prev]);
        }
      }

      if (!match && sorted.length > 0) {
        match = sorted[0];
      }

      if (match) {
        setSelectedPeriodId(match.id);
        setSelectedYear(match.period_year);
        setSelectedMonth(match.period_month);
        setCurrentPeriodId(match.id);
        loadAvailableDocuments(match.period_year, match.period_month, selectedProperty?.property_code || '');
        setMortgageComparison(null);
      }
    } catch (err) {
      console.error('Failed to load periods:', err);
      setAvailablePeriods([]);
      setSelectedPeriodId(null);
    }
  };

  const loadAvailableDocuments = async (periodYear: number, periodMonth: number, propertyCode: string) => {
    if (!propertyCode) return;
    try {
      const docs = await documentService.getDocuments({
        property_code: propertyCode,
        period_year: periodYear,
        period_month: periodMonth,
        limit: 200,
      });
      setAvailableDocuments(docs.items || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadCurrentPeriod = async (propertyId: number, year: number, month: number) => {
    try {
      const period = await financialPeriodsService.getOrCreatePeriod(propertyId, year, month);
      setCurrentPeriodId(period.id);
    } catch (err) {
      console.error('Failed to load current period:', err);
      setCurrentPeriodId(null);
    }
  };

  const loadMortgageComparison = async () => {
    if (!selectedProperty) return;
    try {
      setLoadingMortgageComparison(true);
      setMortgageMessage('');

      // Prefer doc for current selected period, else use most recent mortgage doc
      const mortgageDocs = availableDocuments
        .filter(d => d.document_type === 'mortgage_statement')
        .sort((a, b) => {
          const aKey = (a.period_year || 0) * 100 + (a.period_month || 0);
          const bKey = (b.period_year || 0) * 100 + (b.period_month || 0);
          return bKey - aKey;
        });

      const periodMatch = mortgageDocs.find(
        d => d.period_year === selectedYear && d.period_month === selectedMonth
      );

      const docToUse = periodMatch || mortgageDocs[0];

      if (docToUse) {
        // Sync UI to doc period if different
        if (docToUse.period_year && docToUse.period_month) {
          setSelectedYear(docToUse.period_year);
          setSelectedMonth(docToUse.period_month);
          await setPeriodFromDoc(docToUse);
        }

        const comparison = await reconciliationService.getComparison(
          selectedProperty.property_code,
          docToUse.period_year || selectedYear,
          docToUse.period_month || selectedMonth,
          'mortgage_statement'
        );
        setMortgageComparison(comparison);
      } else {
        setMortgageComparison(null);
        setMortgageMessage(`No mortgage statement found. Upload a mortgage statement for this property/period.`);
      }
    } catch (err) {
      console.error('Failed to load mortgage comparison:', err);
      setMortgageComparison(null);
      setMortgageMessage('Unable to load mortgage comparison. Please try again or pick another period.');
    } finally {
      setLoadingMortgageComparison(false);
    }
  };

  const loadFullFinancialData = async (documentType: Exclude<StatementType, 'mortgage_statement'>) => {
    if (!selectedProperty) return;

    setLoadingFinancialData(true);
    setFinancialData(null);

    try {
      const matchingDocs = availableDocuments.filter(d => d.document_type === documentType);
      let doc: DocumentUploadType | undefined;

      const completed = matchingDocs.filter(d => d.extraction_status === 'completed');
      if (completed.length > 0) {
        doc = completed.sort((a, b) => (b.id || 0) - (a.id || 0))[0];
      } else if (matchingDocs.length > 0) {
        doc = matchingDocs.sort((a, b) => (b.id || 0) - (a.id || 0))[0];
      }

      if (!doc) {
        // Fallback: fetch directly
        const fresh = await documentService.getDocuments({
          property_code: selectedProperty.property_code,
          document_type: documentType,
          limit: 10,
        });
        doc = fresh.items?.find(d => d.extraction_status === 'completed') || fresh.items?.[0];
        if (doc && fresh.items) {
          setAvailableDocuments(prev => {
            const existing = prev.map(d => d.id);
            const newDocs = fresh.items.filter(d => !existing.includes(d.id));
            return [...prev, ...newDocs];
          });
        }
      }

      if (doc && doc.id) {
        const summary = await financialDataService.getSummary(doc.id);
        const totalItems = summary.total_items || 0;
        const pageSize = Math.min(1000, Math.max(totalItems, 100));

        const firstPage = await financialDataService.getFinancialData(doc.id, { limit: pageSize, skip: 0 });
        const allItems: FinancialDataItem[] = [...(firstPage.items || [])];
        let skip = allItems.length;

        while (allItems.length < (firstPage.total_items || 0)) {
          const nextPage = await financialDataService.getFinancialData(doc.id, {
            limit: Math.min(1000, (firstPage.total_items || 0) - allItems.length),
            skip,
          });
          if (!nextPage.items || nextPage.items.length === 0) break;
          allItems.push(...nextPage.items);
          skip += nextPage.items.length;
        }

        setFinancialData({
          ...firstPage,
          items: allItems,
          limit: allItems.length,
        });
      } else {
        setFinancialData(null);
      }
    } catch (err) {
      console.error('Failed to load full financial data:', err);
      setFinancialData(null);
    } finally {
      setLoadingFinancialData(false);
    }
  };

  const statementTypes: StatementType[] = ['income_statement', 'balance_sheet', 'cash_flow', 'mortgage_statement'];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="info"
              className="bg-background text-text-primary border border-border shadow-none hover:shadow-md"
              onClick={() => { window.location.hash = ''; }}
            >
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Financial Command
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Complete Financial Data</h1>
              <p className="text-text-secondary text-sm">
                Full document-level view with every line item and extraction confidence.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedProperty?.id || ''}
              onChange={(e) => {
                const prop = properties.find(p => p.id === Number(e.target.value));
                setSelectedProperty(prop || null);
                setSelectedStatementType(null);
                setFinancialData(null);
              }}
              className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            >
              {properties.map(p => (
                <option key={p.id} value={p.id}>{p.property_name}</option>
              ))}
            </select>

            <select
              value={selectedPeriodId || ''}
              onChange={(e) => {
                const period = availablePeriods.find(p => p.id === Number(e.target.value));
                  if (period) {
                    setSelectedPeriodId(period.id);
                    setSelectedYear(period.period_year);
                    setSelectedMonth(period.period_month);
                    setCurrentPeriodId(period.id);
                    setSelectedStatementType(null);
                    setFinancialData(null);
                    setMortgageComparison(null);
                    if (selectedProperty) {
                      loadAvailableDocuments(period.period_year, period.period_month, selectedProperty.property_code);
                      loadCurrentPeriod(selectedProperty.id, period.period_year, period.period_month);
                    }
                  }
              }}
              className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            >
              {availablePeriods.length === 0 && <option value="">No periods</option>}
              {availablePeriods.map(period => {
                const monthLabel = new Date(2000, period.period_month - 1).toLocaleString('default', { month: 'long' });
                return (
                  <option key={period.id} value={period.id}>
                    {`${period.period_year}-${String(period.period_month).padStart(2, '0')} (${monthLabel})`}
                  </option>
                );
              })}
            </select>

            <Button
              variant="info"
              className="bg-background text-text-primary border border-border shadow-none hover:shadow-md"
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={() => {
                if (selectedProperty && selectedPeriodId) {
                  const period = availablePeriods.find(p => p.id === selectedPeriodId);
                  if (period) {
                    loadAvailableDocuments(period.period_year, period.period_month, selectedProperty.property_code);
                    loadCurrentPeriod(selectedProperty.id, period.period_year, period.period_month);
                    if (selectedStatementType && selectedStatementType !== 'mortgage_statement') {
                      loadFullFinancialData(selectedStatementType);
                    } else if (selectedStatementType === 'mortgage_statement') {
                      loadMortgageComparison();
                    }
                  }
                }
              }}
            >
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-[320px_1fr] gap-4">
          <div className="space-y-4">
            <Card className="p-4">
              <div className="text-sm font-semibold mb-3 text-text-secondary">Statement Type</div>
              <div className="grid grid-cols-2 gap-2">
                {statementTypes.map((type) => {
                  const docs = availableDocuments.filter(d => d.document_type === type);
                          const doc = docs.find(d => d.extraction_status === 'completed') || docs[0];
                          return (
                            <button
                              key={type}
                              onClick={async () => {
                                setSelectedStatementType(type);
                                if (doc) {
                                  await setPeriodFromDoc(doc);
                                  if (type === 'mortgage_statement') {
                                    loadMortgageComparison();
                                  } else {
                                    loadFullFinancialData(type);
                                  }
                                } else {
                                  setMortgageComparison(null);
                                  setMortgageMessage(`No ${type.replace('_', ' ')} document for the selected period.`);
                                }
                              }}
                              className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors border ${
                                selectedStatementType === type
                                  ? 'bg-info text-white border-info'
                                  : doc
                                  ? 'bg-background border-border hover:bg-background'
                                  : 'bg-background border-dashed border-warning text-warning hover:bg-background'
                              }`}
                              title={doc ? `${doc.extraction_status} - Upload ID: ${doc.id}` : 'No document available for this period'}
                            >
                              <div className="flex items-center justify-between">
                                <span>{type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                                {doc && (
                                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface border border-border">
                            {doc.extraction_status}
                          </span>
                        )}
                      </div>
                                {docs.length > 1 && (
                                  <div className="text-[11px] text-text-secondary mt-1">
                                    {docs.length} versions available
                                  </div>
                                )}
                                {!doc && (
                                  <div className="text-[11px] text-warning mt-1">
                                    No document for {selectedYear}-{String(selectedMonth).padStart(2, '0')}
                                  </div>
                                )}
                            </button>
                          );
                        })}
              </div>
            </Card>

            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-text-secondary">Available Documents</div>
                <div className="text-xs text-text-tertiary">{availableDocuments.length} total</div>
              </div>
              <div className="space-y-2 overflow-y-auto pr-1 max-h-[60vh]">
                        {availableDocuments.length === 0 ? (
                          <div className="text-sm text-text-tertiary">
                            No documents uploaded for this property yet.
                          </div>
                        ) : (
                          availableDocuments
                            .filter(d => statementTypes.includes(d.document_type as StatementType))
                            .map((doc) => (
                              <button
                                key={doc.id}
                                onClick={() => {
                                  setSelectedStatementType(doc.document_type as StatementType);
                                  if (doc.period_year && doc.period_month) {
                                    setSelectedYear(doc.period_year);
                                    setSelectedMonth(doc.period_month);
                                    const period = availablePeriods.find(p => p.period_year === doc.period_year && p.period_month === doc.period_month);
                                    if (period) {
                                      setSelectedPeriodId(period.id);
                                      setCurrentPeriodId(period.id);
                                    }
                                  }
                                  if (doc.document_type === 'mortgage_statement') {
                                    loadMortgageComparison();
                                  } else {
                                    loadFullFinancialData(doc.document_type as Exclude<StatementType, 'mortgage_statement'>);
                                  }
                                }}
                                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                                  selectedStatementType === doc.document_type ? 'border-info bg-info-light/15' : 'border-border bg-background hover:bg-background'
                                }`}
                              >
                                <div className="flex items-center justify-between text-sm font-medium">
                                  <span className="capitalize">{doc.document_type.replace('_', ' ')}</span>
                                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface border border-border">
                                    {doc.extraction_status}
                                  </span>
                                </div>
                                <div className="text-xs text-text-secondary mt-1">
                                  Upload #{doc.id} • Period {doc.period_year || '—'}/{String(doc.period_month || 0).padStart(2, '0')}
                                </div>
                              </button>
                            ))
                        )}
              </div>
              <div className="text-[11px] text-text-tertiary mt-2">
                Scroll to see all uploads. Documents may belong to different periods.
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            {selectedStatementType === 'mortgage_statement' ? (
              selectedProperty && currentPeriodId ? (
                <div className="space-y-4">
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">Mortgage Statement - Complete Line Items</h3>
                        <p className="text-sm text-text-secondary">
                          Showing all {mortgageComparison?.comparison.records.length || 0} of {mortgageComparison?.comparison.records.length || 0} extracted line items
                        </p>
                      </div>
                      <div className="text-sm text-text-secondary text-right">
                        {selectedProperty?.property_code || '—'}<br />
                        {selectedYear}/{String(selectedMonth).padStart(2, '0')}
                      </div>
                    </div>

                    {mortgageComparison && mortgageComparison.comparison ? (
                      <div className="space-y-4">
                        <div className="overflow-x-auto border border-border rounded-lg">
                          <table className="min-w-full divide-y divide-border">
                            <thead className="sticky top-0 bg-surface z-10 border-b-2 border-border">
                              <tr>
                                <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Line</th>
                                <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Code</th>
                                <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Name</th>
                                <th className="text-right py-3 px-4 text-sm font-semibold bg-surface">Amount</th>
                                <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Confidence</th>
                                <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Status</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-border">
                              {mortgageComparison.comparison.records.map((record, index) => {
                                const isMatch = record.match_status === 'exact' || record.match_status === 'tolerance';
                                const hasDifference = record.match_status === 'mismatch' || (record.difference !== null && record.difference !== 0 && record.match_status !== 'exact');

                                // Choose a display amount: prefer PDF value, fall back to DB value
                                const amount =
                                  record.pdf_value !== null && record.pdf_value !== undefined
                                    ? record.pdf_value
                                    : record.db_value !== null && record.db_value !== undefined
                                    ? record.db_value
                                    : null;

                                // Map match status to a numeric confidence proxy (exact = 100, tolerance = 90, mismatch = 40)
                                const confidence =
                                  record.match_status === 'exact'
                                    ? 100
                                    : record.match_status === 'tolerance'
                                    ? 90
                                    : record.match_status === 'mismatch'
                                    ? 40
                                    : 0;

                                return (
                                  <tr
                                    key={index}
                                    className={`transition-colors ${
                                      hasDifference ? 'bg-danger/5 hover:bg-danger/10' :
                                      isMatch ? 'bg-success/5 hover:bg-success/10' :
                                      'hover:bg-background'
                                    }`}
                                  >
                                    <td className="py-2 px-4 text-sm text-text-secondary">
                                      {index + 1}
                                    </td>
                                    <td className="py-2 px-4 text-sm font-mono text-text-primary">
                                      {record.account_code || '-'}
                                    </td>
                                    <td className="py-2 px-4 text-sm text-text-secondary">
                                      {record.account_name || '-'}
                                    </td>
                                    <td className="py-2 px-4 text-sm text-right font-mono text-text-primary">
                                      {amount !== null
                                        ? amount.toLocaleString(undefined, { style: 'currency', currency: 'USD' })
                                        : '—'}
                                    </td>
                                    <td className="py-2 px-4 text-sm text-center">
                                      <div className="text-xs font-medium">E: {confidence}%</div>
                                      <div className="text-[11px] text-text-tertiary">M: 0%</div>
                                    </td>
                                    <td className="py-2 px-4 text-sm text-center">
                                      {(() => {
                                        const status = record.match_status || 'unknown';
                                        const color =
                                          status === 'exact'
                                            ? '#22c55e' // green
                                            : status === 'tolerance'
                                            ? '#facc15' // yellow
                                            : status === 'mismatch'
                                            ? '#ef4444' // red
                                            : '#cbd5e1'; // neutral
                                        return (
                                          <span
                                            title={status}
                                            style={{
                                              display: 'inline-block',
                                              width: 12,
                                              height: 12,
                                              borderRadius: '9999px',
                                              backgroundColor: color
                                            }}
                                            aria-label={status}
                                          />
                                        );
                                      })()}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ) : loadingMortgageComparison ? null : (
                      <div className="text-text-secondary">
                        {mortgageMessage || `No mortgage comparison data found for ${selectedYear}-${String(selectedMonth).padStart(2, '0')}. Ensure a mortgage statement is uploaded for this period.`}
                      </div>
                    )}
                  </Card>
                </div>
              ) : (
                <Card className="p-8 text-center">
                  <div className="text-text-secondary">
                    Please select a property and period to view mortgage statements.
                  </div>
                </Card>
              )
            ) : loadingFinancialData ? (
              <Card className="p-8 text-center">
                <div className="text-text-secondary">Loading complete financial document data...</div>
                <div className="text-xs text-text-tertiary mt-2">Fetching all line items with zero data loss</div>
              </Card>
            ) : financialData && financialData.items && financialData.items.length > 0 ? (
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">
                      {financialData.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} - Complete Line Items
                    </h3>
                    <p className="text-sm text-text-secondary mt-1">
                      Showing all {financialData.items.length} of {financialData.total_items} extracted line items
                    </p>
                  </div>
                  <div className="text-sm text-text-secondary text-right">
                    {financialData.property_code}<br />
                    {financialData.period_year}/{String(financialData.period_month).padStart(2, '0')}
                  </div>
                </div>

                <div className="overflow-x-auto overflow-y-auto max-h-[70vh] border border-border rounded-lg">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-surface z-10 border-b-2 border-border">
                      <tr>
                        <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Line</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Code</th>
                        <th className="text-left py-3 px-4 text-sm font-semibold bg-surface">Account Name</th>
                        <th className="text-right py-3 px-4 text-sm font-semibold bg-surface">Amount</th>
                        <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Confidence</th>
                        <th className="text-center py-3 px-4 text-sm font-semibold bg-surface">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {financialData.items.map((item: FinancialDataItem) => (
                        <tr
                          key={item.id}
                          className={`border-b border-border hover:bg-background ${
                            item.is_total ? 'font-bold bg-info-light/10' :
                            item.is_subtotal ? 'font-semibold bg-background' : ''
                          }`}
                        >
                          <td className="py-2 px-4 text-sm text-text-secondary">
                            {item.line_number || '-'}
                          </td>
                          <td className="py-2 px-4">
                            <span className="font-mono font-medium">{item.account_code}</span>
                          </td>
                          <td className="py-2 px-4">
                            <div className="flex items-center gap-2">
                              {item.account_name}
                              {item.is_total && (
                                <span className="px-2 py-0.5 bg-info text-white rounded text-xs">
                                  TOTAL
                                </span>
                              )}
                              {item.is_subtotal && (
                                <span className="px-2 py-0.5 bg-premium text-white rounded text-xs">
                                  SUBTOTAL
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-2 px-4 text-right font-mono">
                            {item.amounts.amount !== undefined && item.amounts.amount !== null
                              ? `$${item.amounts.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                              : item.amounts.period_amount !== undefined && item.amounts.period_amount !== null
                              ? `$${item.amounts.period_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                              : item.amounts.ytd_amount !== undefined && item.amounts.ytd_amount !== null
                              ? `YTD: $${item.amounts.ytd_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                              : '-'}
                          </td>
                          <td className="py-2 px-4 text-center">
                            <div className="text-xs">
                              <div className="font-medium">
                                E: {item.extraction_confidence.toFixed(0)}%
                              </div>
                              <div className="text-text-secondary">
                                M: {item.match_confidence?.toFixed(0) || 0}%
                              </div>
                            </div>
                          </td>
                          <td className="py-2 px-4 text-center">
                            {item.severity === 'critical' && <span className="text-danger">🔴</span>}
                            {item.severity === 'warning' && <span className="text-warning">🟡</span>}
                            {item.severity === 'excellent' && <span className="text-success">🟢</span>}
                            {item.needs_review && (
                              <span className="ml-2 text-xs text-warning">Review</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <Card className="p-8 text-center">
                <div className="text-text-secondary mb-3">
                  {selectedStatementType
                    ? `No ${selectedStatementType.replace('_', ' ')} document found.`
                    : 'Please select a statement type on the left.'}
                </div>
                {availableDocuments.length > 0 && (
                  <div className="text-xs text-text-tertiary max-w-md mx-auto">
                    Use the left rail to pick the statement type. Documents may be for different periods.
                  </div>
                )}
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
