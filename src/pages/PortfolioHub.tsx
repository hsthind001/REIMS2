import { useState, useEffect } from 'react';
import { 
  Building2, 
  FileText,
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Sparkles
} from 'lucide-react';
import { Card, Button, ProgressBar } from '../components/design-system';
import { propertyService } from '../lib/property';
import { reportsService } from '../lib/reports';
import { documentService } from '../lib/document';
import { financialDataService } from '../lib/financial_data';
import { DocumentUpload } from '../components/DocumentUpload';
import type { Property, PropertyCreate, DocumentUpload as DocumentUploadType } from '../types/api';
import type { FinancialDataItem, FinancialDataResponse } from '../lib/financial_data';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface PropertyMetrics {
  value: number;
  noi: number;
  dscr: number;
  ltv: number;
  occupancy: number;
  capRate: number;
  status: 'critical' | 'warning' | 'good';
  trends: {
    noi: number[];
    occupancy: number[];
  };
}

interface PropertyCosts {
  insurance: number;
  mortgage: number;
  utilities: number;
  initialBuying: number;
  maintenance: number;
  taxes: number;
  other: number;
  total: number;
}

interface UnitInfo {
  totalUnits: number;
  occupiedUnits: number;
  availableUnits: number;
  totalSqft: number;
  units: Array<{
    unitNumber: string;
    sqft: number;
    status: 'occupied' | 'available';
    tenant?: string;
  }>;
}

interface MarketIntelligence {
  locationScore: number;
  marketCapRate: number;
  yourCapRate: number;
  rentGrowth: number;
  yourRentGrowth: number;
  demographics: {
    population: number;
    medianIncome: number;
    employmentType: string;
  };
  comparables: Array<{
    name: string;
    distance: number;
    capRate: number;
    occupancy: number;
  }>;
  aiInsights: string[];
}

interface TenantMatch {
  tenantName: string;
  matchScore: number;
  creditScore: number;
  industry: string;
  desiredSqft: { min: number; max: number };
  estimatedRent: number;
  confidence: number;
  reasons: string[];
}

type DetailTab = 'overview' | 'financials' | 'market' | 'tenants' | 'docs';

export default function PortfolioHub() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [metrics, setMetrics] = useState<PropertyMetrics | null>(null);
  const [costs, setCosts] = useState<PropertyCosts | null>(null);
  const [unitInfo, setUnitInfo] = useState<UnitInfo | null>(null);
  const [marketIntel, setMarketIntel] = useState<MarketIntelligence | null>(null);
  const [loadingMarketIntel, setLoadingMarketIntel] = useState(false);
  const [tenantMatches, setTenantMatches] = useState<TenantMatch[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'noi' | 'risk' | 'value'>('noi');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [financialStatements, setFinancialStatements] = useState<any>(null);
  const [selectedStatement, setSelectedStatement] = useState<'income' | 'balance' | 'cashflow'>('income');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [propertyMetricsMap, setPropertyMetricsMap] = useState<Map<number, any>>(new Map());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [financialData, setFinancialData] = useState<FinancialDataResponse | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentUploadType[]>([]);
  const [loadingDocumentData, setLoadingDocumentData] = useState(false);
  const [tenantMix, setTenantMix] = useState<any[]>([]);

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadPropertyDetails(selectedProperty.id);
      loadFinancialStatements(selectedProperty.property_code);
      loadTenantMix(selectedProperty.id);
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  const loadProperties = async () => {
    try {
      setLoading(true);
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0 && !selectedProperty) {
        setSelectedProperty(data[0]);
      }

      // Load metrics for all properties for sorting
      loadAllPropertyMetrics(data);
    } catch (err) {
      console.error('Failed to load properties:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAllPropertyMetrics = async (props: Property[]) => {
    try {
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
        credentials: 'include'
      });
      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        const metricsMap = new Map();

        // Create a map of property_id -> metrics for easy lookup
        for (const metric of metricsData) {
          const prop = props.find(p => p.property_code === metric.property_code);
          if (prop) {
            metricsMap.set(prop.id, metric);
          }
        }

        setPropertyMetricsMap(metricsMap);
      }
    } catch (err) {
      console.error('Failed to load property metrics for sorting:', err);
    }
  };

  const loadPropertyDetails = async (propertyId: number) => {
    // Clear previous data immediately when switching properties
    setMetrics(null);
    setCosts(null);
    setUnitInfo(null);
    
    try {
      // Get property code for matching
      const currentProperty = properties.find(p => p.id === propertyId);
      if (!currentProperty) {
        console.error('Property not found:', propertyId);
        return;
      }

      // Try to get metrics from the map first (already loaded for list display)
      const propertyMetricFromMap = propertyMetricsMap.get(propertyId);
      
      // Try to load period-specific metrics first, then fall back to summary
      let propertyMetric: any = null;
      let periodSpecificMetrics: any = null;
      
      try {
        // Try period-specific endpoint first
        const periodRes = await fetch(`${API_BASE_URL}/metrics/${currentProperty.property_code}/${selectedYear}/${selectedMonth}`, {
          credentials: 'include'
        });
        if (periodRes.ok) {
          periodSpecificMetrics = await periodRes.json();
          console.log(`Period-specific metrics for ${currentProperty.property_code} ${selectedYear}-${selectedMonth}:`, periodSpecificMetrics);
          propertyMetric = {
            property_code: periodSpecificMetrics.property_code,
            total_assets: periodSpecificMetrics.total_assets,
            net_income: periodSpecificMetrics.net_income,
            occupancy_rate: periodSpecificMetrics.occupancy_rate,
            total_expenses: periodSpecificMetrics.total_expenses,
            total_units: periodSpecificMetrics.total_units,
            occupied_units: periodSpecificMetrics.occupied_units,
            total_leasable_sqft: periodSpecificMetrics.total_leasable_sqft
          };
        } else {
          console.warn(`No period-specific data for ${currentProperty.property_code} ${selectedYear}-${selectedMonth}, using summary`);
        }
      } catch (periodErr) {
        console.warn('Failed to load period-specific metrics, using summary:', periodErr);
      }
      
      // Fall back to summary if period-specific not available
      if (!propertyMetric) {
        const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
          credentials: 'include'
        });
        const metricsData = metricsRes.ok ? await metricsRes.json() : [];
        // Match by property_code since API returns property_code, not property_id
        propertyMetric = metricsData.find((m: any) => m.property_code === currentProperty.property_code) || propertyMetricFromMap;
      }
      
      if (propertyMetric) {
        // Calculate DSCR from real data only - no fallbacks
        let dscr: number | null = null;
        let ltv: number | null = null;
        let capRate: number | null = null;

        try {
          const [ltvRes, capRateRes] = await Promise.all([
            fetch(`${API_BASE_URL}/metrics/${propertyId}/ltv`, { credentials: 'include' }),
            fetch(`${API_BASE_URL}/metrics/${propertyId}/cap-rate`, { credentials: 'include' })
          ]);

          if (ltvRes.ok) {
            const ltvData = await ltvRes.json();
            ltv = ltvData.ltv || null;

            // Calculate DSCR: NOI / (Loan Amount * 0.08) - only if we have real data
            const loanAmount = ltvData.loan_amount || 0;
            const annualDebtService = loanAmount * 0.08;
            if (annualDebtService > 0 && propertyMetric.net_income) {
              dscr = propertyMetric.net_income / annualDebtService;
            }
          }

          if (capRateRes.ok) {
            const capRateData = await capRateRes.json();
            capRate = capRateData.cap_rate || null;
          }
        } catch (apiErr) {
          console.error('Failed to fetch LTV/Cap Rate:', apiErr);
        }

        // Calculate status only if we have real DSCR data
        const status = dscr !== null 
          ? (dscr < 1.25 ? 'critical' : dscr < 1.35 ? 'warning' : 'good')
          : 'warning';

        // Fetch real historical trends from API - only real data
        let noiTrend: number[] = [];
        let occupancyTrend: number[] = [];
        try {
          const histRes = await fetch(`${API_BASE_URL}/metrics/historical?property_id=${propertyId}&months=12`, {
            credentials: 'include'
          });
          if (histRes.ok) {
            const histData = await histRes.json();
            noiTrend = histData.data?.noi?.map((n: number) => n / 1000000) || [];
            occupancyTrend = histData.data?.occupancy || [];
          }
        } catch (histErr) {
          console.error('Failed to load historical trends:', histErr);
        }

        // Use period-specific data if available, otherwise use summary
        const metricsValue = periodSpecificMetrics?.total_assets || propertyMetric?.total_assets || 0;
        const metricsNoi = periodSpecificMetrics?.net_income || propertyMetric?.net_income || 0;
        const metricsOccupancy = periodSpecificMetrics?.occupancy_rate || propertyMetric?.occupancy_rate || 0;
        
        setMetrics({
          value: metricsValue,
          noi: metricsNoi,
          dscr: dscr || 0,
          ltv: ltv || 0,
          occupancy: metricsOccupancy,
          capRate: capRate || 0,
          status,
          trends: {
            noi: noiTrend,
            occupancy: occupancyTrend
          }
        });
      } else {
        // No metrics found for this property - show zeros only
        console.log('No metrics found for property:', currentProperty.property_code);
        // Only use data from map if it exists, otherwise show zeros
        if (propertyMetricFromMap) {
          setMetrics({
            value: propertyMetricFromMap.total_assets || 0,
            noi: propertyMetricFromMap.net_income || 0,
            dscr: 0, // No fallback
            ltv: 0, // No fallback
            occupancy: propertyMetricFromMap.occupancy_rate || 0,
            capRate: 0, // No fallback
            status: 'warning',
            trends: {
              noi: [],
              occupancy: []
            }
          });
        } else {
          setMetrics({
            value: 0,
            noi: 0,
            dscr: 0,
            ltv: 0,
            occupancy: 0,
            capRate: 0,
            status: 'warning',
            trends: {
              noi: [],
              occupancy: []
            }
          });
        }
      }

      // Load costs - use period-specific data if available, otherwise try costs endpoint
      if (periodSpecificMetrics?.total_expenses !== null && periodSpecificMetrics?.total_expenses !== undefined) {
        // Use period-specific expense data
        const totalExpenses = periodSpecificMetrics.total_expenses || 0;
        // Calculate cost breakdown from total_expenses (same logic as backend)
        const costsData = {
          insurance: Math.round(totalExpenses * 0.15),
          mortgage: Math.round(totalExpenses * 0.45),
          utilities: Math.round(totalExpenses * 0.20),
          maintenance: Math.round(totalExpenses * 0.10),
          taxes: Math.round(totalExpenses * 0.08),
          other: Math.round(totalExpenses * 0.02),
          total: Math.round(totalExpenses)
        };
        
        console.log('Using period-specific expense data:', costsData);
        setCosts({
          insurance: costsData.insurance || 0,
          mortgage: costsData.mortgage || 0,
          utilities: costsData.utilities || 0,
          initialBuying: periodSpecificMetrics?.total_assets || 0,
          maintenance: costsData.maintenance || 0,
          taxes: costsData.taxes || 0,
          other: costsData.other || 0,
          total: costsData.total || 0
        });
      } else {
        // Fall back to costs endpoint (gets latest period)
        try {
          const costsRes = await fetch(`${API_BASE_URL}/metrics/${propertyId}/costs`, {
            credentials: 'include'
          });
          if (costsRes.ok) {
            const costsData = await costsRes.json();
            console.log('Costs API response for property', propertyId, ':', costsData);
            // Check if there's actual cost data (not all zeros)
            if (costsData.total_costs > 0 && costsData.costs) {
              setCosts({
                insurance: costsData.costs.insurance || 0,
                mortgage: costsData.costs.mortgage || 0,
                utilities: costsData.costs.utilities || 0,
                initialBuying: propertyMetric?.total_assets || 0,
                maintenance: costsData.costs.maintenance || 0,
                taxes: costsData.costs.taxes || 0,
                other: costsData.costs.other || 0,
                total: costsData.total_costs || 0
              });
            } else {
              // No cost data from detailed endpoint
              console.warn('Costs API returned zero or missing data for property', propertyId, costsData);
              const totalFromSummary = propertyMetric?.total_assets || 0;
              setCosts({
                insurance: 0,
                mortgage: 0,
                utilities: 0,
                initialBuying: totalFromSummary,
                maintenance: 0,
                taxes: 0,
                other: 0,
                total: totalFromSummary
              });
            }
          } else if (costsRes.status === 404) {
            // No detailed cost data
            console.warn(`Costs API 404 for property ${propertyId} - using summary data`);
            const totalFromSummary = propertyMetric?.total_assets || 0;
            setCosts({
              insurance: 0,
              mortgage: 0,
              utilities: 0,
              initialBuying: totalFromSummary,
              maintenance: 0,
              taxes: 0,
              other: 0,
              total: totalFromSummary
            });
          } else {
            // Other API error
            const errorText = await costsRes.text();
            console.error(`Costs API error for property ${propertyId}: ${costsRes.status} ${costsRes.statusText}`, errorText);
            const totalFromSummary = propertyMetric?.total_assets || 0;
            setCosts({
              insurance: 0,
              mortgage: 0,
              utilities: 0,
              initialBuying: totalFromSummary,
              maintenance: 0,
              taxes: 0,
              other: 0,
              total: totalFromSummary
            });
          }
        } catch (costsErr) {
          console.error('Failed to fetch property costs:', costsErr);
          const totalFromSummary = propertyMetric?.total_assets || 0;
          setCosts({
            insurance: 0,
            mortgage: 0,
            utilities: 0,
            initialBuying: totalFromSummary,
            maintenance: 0,
            taxes: 0,
            other: 0,
            total: totalFromSummary
          });
        }
      }

      // Load unit info - use period-specific data if available, otherwise try units endpoint
      if (periodSpecificMetrics?.total_units !== null && periodSpecificMetrics?.total_units !== undefined) {
        // Use period-specific unit data
        const totalUnits = periodSpecificMetrics.total_units || 0;
        const occupiedUnits = periodSpecificMetrics.occupied_units || 0;
        const totalSqft = periodSpecificMetrics.total_leasable_sqft || 0;
        const availableUnits = totalUnits - occupiedUnits;
        
        console.log('Using period-specific unit data:', { totalUnits, occupiedUnits, availableUnits, totalSqft });
        setUnitInfo({
          totalUnits,
          occupiedUnits,
          availableUnits,
          totalSqft,
          units: [] // Individual unit details would need separate query
        });
      } else {
        // Fall back to units endpoint (gets latest period)
        try {
          const unitsRes = await fetch(`${API_BASE_URL}/metrics/${propertyId}/units?limit=20`, {
            credentials: 'include'
          });
          if (unitsRes.ok) {
            const unitsData = await unitsRes.json();
            console.log('Units API response for property', propertyId, ':', unitsData);
            // Check if data exists (not just 0s from empty database)
            if (unitsData.totalUnits > 0 || unitsData.units.length > 0) {
              setUnitInfo({
                totalUnits: unitsData.totalUnits,
                occupiedUnits: unitsData.occupiedUnits,
                availableUnits: unitsData.availableUnits,
                totalSqft: unitsData.totalSqft,
                units: unitsData.units
              });
            } else {
              // No unit data from detailed endpoint
              console.warn('Units API returned zero data for property', propertyId, unitsData);
              setUnitInfo({
                totalUnits: 0,
                occupiedUnits: 0,
                availableUnits: 0,
                totalSqft: 0,
                units: []
              });
            }
          } else if (unitsRes.status === 404) {
            // No detailed unit data
            console.warn(`Units API 404 for property ${propertyId} - no unit data available`);
            setUnitInfo({
              totalUnits: 0,
              occupiedUnits: 0,
              availableUnits: 0,
              totalSqft: 0,
              units: []
            });
          } else {
            // Other API error
            const errorText = await unitsRes.text();
            console.error(`Units API error for property ${propertyId}: ${unitsRes.status} ${unitsRes.statusText}`, errorText);
            setUnitInfo({
              totalUnits: 0,
              occupiedUnits: 0,
              availableUnits: 0,
              totalSqft: 0,
              units: []
            });
          }
        } catch (unitsErr) {
          console.error('Failed to fetch unit details:', unitsErr);
          setUnitInfo({
            totalUnits: 0,
            occupiedUnits: 0,
            availableUnits: 0,
            totalSqft: 0,
            units: []
          });
        }
      }

      // Load market intelligence
      await loadMarketIntelligence(propertyId);

      // Load tenant matches
      await loadTenantMatches(propertyId);
    } catch (err) {
      console.error('Failed to load property details:', err);
    }
  };

  const loadMarketIntelligence = async (propertyId: number) => {
    setLoadingMarketIntel(true);
    try {
      // Use the correct market intelligence endpoint
      const res = await fetch(`${API_BASE_URL}/properties/${propertyId}/market-intelligence`, {
        credentials: 'include'
      });

      let research = null;
      if (res.ok) {
        const data = await res.json();
        research = data;  // Data is directly in the response
      }
      
      // Always set market intelligence data (with fallback if API fails)
      // Get property for property_code
      const currentProperty = properties.find(p => p.id === propertyId);
      
      // Get property metrics for comparison
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
        credentials: 'include'
      });
      const metricsData = metricsRes.ok ? await metricsRes.json() : [];
      // Match by property_code since API returns property_code, not property_id
      const propertyMetric = currentProperty ? metricsData.find((m: any) => m.property_code === currentProperty.property_code) : null;
      
      // Fetch real cap rate from API - only real data
      let yourCapRate: number | null = null;
      try {
        const capRateRes = await fetch(`${API_BASE_URL}/metrics/${propertyId}/cap-rate`, {
          credentials: 'include'
        });
        if (capRateRes.ok) {
          const capRateData = await capRateRes.json();
          yourCapRate = capRateData.cap_rate || null;
        }
      } catch (capErr) {
        console.error('Failed to fetch cap rate for market intel:', capErr);
      }
      
      // Only set market intelligence if we have real data
      if (research) {
        setMarketIntel({
          locationScore: research.location_score || 0,
          marketCapRate: research.market_cap_rate || 0,
          yourCapRate: yourCapRate || 0,
          rentGrowth: research.rent_growth || 0,
          yourRentGrowth: propertyMetric?.rent_growth_yoy || 0,
          demographics: {
            population: research.demographics?.population || 0,
            medianIncome: research.demographics?.median_income || 0,
            employmentType: research.demographics?.employment_type || ''
          },
          comparables: research.comparables || [],
          aiInsights: research.key_findings || research.insights || []
        });
      } else {
        // No data - set to zeros/empty
        setMarketIntel({
          locationScore: 0,
          marketCapRate: 0,
          yourCapRate: yourCapRate || 0,
          rentGrowth: 0,
          yourRentGrowth: propertyMetric?.rent_growth_yoy || 0,
          demographics: {
            population: 0,
            medianIncome: 0,
            employmentType: ''
          },
          comparables: [],
          aiInsights: []
        });
      }
    } catch (err) {
      console.error('Failed to load market intelligence:', err);
      // Set to zeros/empty on error - no mock data
      setMarketIntel({
        locationScore: 0,
        marketCapRate: 0,
        yourCapRate: 0,
        rentGrowth: 0,
        yourRentGrowth: 0,
        demographics: {
          population: 0,
          medianIncome: 0,
          employmentType: ''
        },
        comparables: [],
        aiInsights: []
      });
    } finally {
      setLoadingMarketIntel(false);
    }
  };

  const loadTenantMatches = async (propertyId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/tenant-recommendations/properties/${propertyId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        const recommendations = data.recommendations || [];
        // Only map real data - no fallbacks
        setTenantMatches(recommendations.map((r: any) => ({
          tenantName: r.tenant_name || '',
          matchScore: r.confidence_score || 0,
          creditScore: r.credit_score || 0,
          industry: r.industry || '',
          desiredSqft: r.desired_sqft || { min: 0, max: 0 },
          estimatedRent: r.estimated_rent || 0,
          confidence: r.confidence_score || 0,
          reasons: r.reasons || []
        })));
      } else {
        // No data - set empty array
        setTenantMatches([]);
      }
    } catch (err) {
      console.error('Failed to load tenant matches:', err);
      // Set empty array on error - no mock data
      setTenantMatches([]);
    }
  };

  const loadTenantMix = async (propertyId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/metrics/${propertyId}/tenant-mix`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setTenantMix(data.tenantMix || []);
      } else {
        // Fallback to empty array
        setTenantMix([]);
      }
    } catch (err) {
      console.error('Failed to load tenant mix:', err);
      setTenantMix([]);
    }
  };

  const loadFinancialStatements = async (propertyCode: string) => {
    if (!propertyCode) return;
    
    try {
      const summary = await reportsService.getPropertySummary(propertyCode, selectedYear, selectedMonth);
      setFinancialStatements(summary);
    } catch (err: any) {
      console.error('Failed to load financial statements:', err);
      // Don't show error - just leave statements as null
    }
  };

  const loadAvailableDocuments = async (propertyCode: string) => {
    if (!propertyCode) return;
    
    try {
      const docs = await documentService.getDocuments({
        property_code: propertyCode,
        period_year: selectedYear,
        period_month: selectedMonth,
        limit: 50
      });
      setAvailableDocuments(docs.items || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadFinancialDocumentData = async (documentType: 'income_statement' | 'balance_sheet' | 'cash_flow') => {
    if (!selectedProperty) return;
    
    setLoadingDocumentData(true);
    setFinancialData(null); // Clear previous data
    
    try {
      console.log('Loading financial data for:', {
        documentType,
        propertyCode: selectedProperty.property_code,
        period: `${selectedYear}/${selectedMonth}`,
        availableDocuments: availableDocuments.length
      });

      // Find the document for this type and period - try completed first, then any status
      let doc = availableDocuments.find(d => 
        d.document_type === documentType &&
        d.extraction_status === 'completed'
      );

      // If no completed document, try any document with this type
      if (!doc) {
        doc = availableDocuments.find(d => d.document_type === documentType);
        console.log('No completed document found, trying any document:', doc);
      }

      // Log all available documents for debugging
      console.log('All available documents:', availableDocuments.map(d => ({
        id: d.id,
        type: d.document_type,
        status: d.extraction_status,
        period_id: d.period_id
      })));

      if (doc && doc.id) {
        console.log('Found document, loading financial data:', doc.id);
        
        try {
          // First get summary to know total count
          const summary = await financialDataService.getSummary(doc.id);
          console.log('Financial data summary:', summary);
          
          // Load ALL items - use a high limit to get everything
          const data = await financialDataService.getFinancialData(doc.id, {
            limit: Math.max(summary.total_items || 10000, 10000), // Load all items, minimum 10k
            skip: 0
          });
          
          console.log('Loaded financial data:', {
            total_items: data.total_items,
            items_received: data.items.length,
            document_type: data.document_type
          });
          
          // If we got paginated results, load remaining pages
          if (data.total_items > data.items.length) {
            console.log('Loading additional pages...', {
              total: data.total_items,
              current: data.items.length
            });
            
            const allItems = [...data.items];
            let skip = data.items.length;
            
            // Load remaining pages
            while (allItems.length < data.total_items) {
              const nextPage = await financialDataService.getFinancialData(doc.id, {
                limit: 1000, // Load in batches of 1000
                skip: skip
              });
              
              allItems.push(...nextPage.items);
              skip += nextPage.items.length;
              
              console.log('Loaded page:', {
                items_in_page: nextPage.items.length,
                total_loaded: allItems.length,
                total_expected: data.total_items
              });
              
              // Break if no more items
              if (nextPage.items.length === 0) break;
            }
            
            console.log('All items loaded:', allItems.length);
            
            // Update data with all items
            setFinancialData({
              ...data,
              items: allItems,
              limit: allItems.length
            });
          } else {
            console.log('All items loaded in first request:', data.items.length);
            setFinancialData(data);
          }
        } catch (dataErr) {
          console.error('Error loading financial data for document:', doc.id, dataErr);
          setFinancialData(null);
        }
      } else {
        console.warn('No document found for:', {
          documentType,
          propertyCode: selectedProperty.property_code,
          period: `${selectedYear}/${selectedMonth}`
        });
        setFinancialData(null);
      }
    } catch (err) {
      console.error('Failed to load financial document data:', err);
      setFinancialData(null);
    } finally {
      setLoadingDocumentData(false);
    }
  };

  useEffect(() => {
    if (selectedProperty) {
      loadAvailableDocuments(selectedProperty.property_code);
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  useEffect(() => {
    if (selectedProperty && availableDocuments.length > 0) {
      const docTypeMap = {
        'income': 'income_statement' as const,
        'balance': 'balance_sheet' as const,
        'cashflow': 'cash_flow' as const
      };
      loadFinancialDocumentData(docTypeMap[selectedStatement]);
    }
  }, [selectedStatement, availableDocuments, selectedProperty]);

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'critical': return 'danger';
      case 'warning': return 'warning';
      case 'good': return 'success';
      default: return 'default';
    }
  };

  const filteredProperties = properties.filter(p => 
    p.property_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.property_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedProperties = [...filteredProperties].sort((a, b) => {
    const aMetrics = propertyMetricsMap.get(a.id);
    const bMetrics = propertyMetricsMap.get(b.id);

    if (sortBy === 'noi') {
      const aNoi = aMetrics?.net_income || 0;
      const bNoi = bMetrics?.net_income || 0;
      return bNoi - aNoi; // Descending
    } else if (sortBy === 'risk') {
      // Lower DSCR = higher risk, so sort ascending
      const aRisk = aMetrics?.dscr || 999;
      const bRisk = bMetrics?.dscr || 999;
      return aRisk - bRisk;
    } else if (sortBy === 'value') {
      const aValue = aMetrics?.total_assets || 0;
      const bValue = bMetrics?.total_assets || 0;
      return bValue - aValue; // Descending
    }
    return 0;
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Portfolio Hub</h1>
            <p className="text-text-secondary mt-1">Property management, market intelligence, and tenant optimization</p>
          </div>
          <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
            Add Property
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
          {/* Left Panel - Property List (30%) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Filters */}
            <Card className="p-4">
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                  <input
                    type="text"
                    placeholder="Search properties..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="flex-1 px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                  >
                    <option value="noi">Sort by NOI</option>
                    <option value="risk">Sort by Risk</option>
                    <option value="value">Sort by Value</option>
                  </select>
                  <Button variant="primary" size="sm" icon={<Filter className="w-4 h-4" />}>
                    Filter
                  </Button>
                </div>
              </div>
            </Card>

            {/* Property Cards */}
            <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {sortedProperties.map((property) => {
                const isSelected = selectedProperty?.id === property.id;
                // Get this property's metrics from the map
                const propertyMetric = propertyMetricsMap.get(property.id);
                // Use selected property's detailed metrics if this is the selected property, otherwise use summary metrics
                const displayMetrics = isSelected && metrics ? metrics : null;
                const displayValue = displayMetrics?.value || propertyMetric?.total_assets || 0;
                const displayNoi = displayMetrics?.noi || propertyMetric?.net_income || 0;
                const displayOccupancy = displayMetrics?.occupancy || propertyMetric?.occupancy_rate || 0;
                const displayDscr = displayMetrics?.dscr || null;
                // Determine status: use selected property's status if selected, otherwise default to 'good'
                const status = displayMetrics?.status || (displayOccupancy > 90 ? 'good' : displayOccupancy > 70 ? 'warning' : 'critical');
                const variant = getStatusVariant(status) as any;

                return (
                  <Card
                    key={property.id}
                    variant={isSelected ? variant : 'default'}
                    className={`p-4 cursor-pointer transition-all ${
                      isSelected ? 'ring-2 ring-info shadow-lg' : ''
                    }`}
                    onClick={() => setSelectedProperty(property)}
                    hover
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-info" />
                        <div>
                          <div className="font-semibold text-text-primary">{property.property_name}</div>
                          <div className="text-sm text-text-secondary">{property.property_code}</div>
                        </div>
                      </div>
                      {status === 'critical' && <span className="text-danger">🔴</span>}
                      {status === 'warning' && <span className="text-warning">🟡</span>}
                      {status === 'good' && <span className="text-success">🟢</span>}
                    </div>
                    
                    {(displayMetrics || propertyMetric) && (
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-text-secondary">Value:</span>
                          <span className="font-medium">${(displayValue / 1000000).toFixed(1)}M</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-text-secondary">NOI:</span>
                          <span className="font-medium">${(displayNoi / 1000).toFixed(0)}K</span>
                        </div>
                        {displayDscr !== null && (
                          <div className="flex justify-between">
                            <span className="text-text-secondary">DSCR:</span>
                            <span className="font-medium">{displayDscr.toFixed(2)}</span>
                          </div>
                        )}
                        <div className="mt-2 h-1.5 w-full bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-info rounded-full"
                            style={{ width: `${Math.min(displayOccupancy, 100)}%` }}
                          />
                        </div>
                        {displayMetrics?.trends?.noi && displayMetrics.trends.noi.length > 0 && (
                          <div className="text-xs text-text-secondary text-center">
                            {displayMetrics.trends.noi.slice(-12).map((_, i) => (
                              <span key={i} className="inline-block w-1 h-3 bg-info rounded-t mx-0.5" />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Panel - Property Details (70%) */}
          <div className="lg:col-span-7">
            {selectedProperty ? (
              <div className="space-y-6">
                {/* Property Header */}
                <Card className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
                        <Building2 className="w-6 h-6" />
                        {selectedProperty.property_name}
                      </h2>
                      <p className="text-text-secondary mt-1">
                        {selectedProperty.property_code} • {selectedProperty.city}, {selectedProperty.state}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="primary" size="sm" icon={<Edit className="w-4 h-4" />}>
                        Edit
                      </Button>
                      <Button variant="danger" size="sm" icon={<Trash2 className="w-4 h-4" />}>
                        Delete
                      </Button>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex gap-1 border-b border-border">
                    {(['overview', 'financials', 'market', 'tenants', 'docs'] as DetailTab[]).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 font-medium text-sm transition-colors ${
                          activeTab === tab
                            ? 'text-info border-b-2 border-info'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </button>
                    ))}
                  </div>
                </Card>

                {/* Tab Content */}
                {activeTab === 'overview' && (
                  <div className="space-y-6">
                    {/* Period Selector */}
                    <Card className="p-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium text-text-secondary">View Period</h3>
                        <div className="flex gap-2">
                          <select
                            value={selectedYear}
                            onChange={(e) => {
                              setSelectedYear(Number(e.target.value));
                            }}
                            className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info text-sm"
                          >
                            {[2023, 2024, 2025, 2026, 2027].map(year => (
                              <option key={year} value={year}>{year}</option>
                            ))}
                          </select>
                          <select
                            value={selectedMonth}
                            onChange={(e) => {
                              setSelectedMonth(Number(e.target.value));
                            }}
                            className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info text-sm"
                          >
                            {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
                              <option key={month} value={month}>
                                {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    </Card>

                    {/* Key Metrics */}
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Key Metrics</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-text-secondary">Purchase Price</div>
                          <div className="text-xl font-bold">${(costs?.initialBuying || 0) / 1000000}M</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Current Value</div>
                          <div className="text-xl font-bold">${(metrics?.value || 0) / 1000000}M</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Hold Period</div>
                          <div className="text-xl font-bold">
                            {selectedProperty?.acquisition_date ?
                              (() => {
                                const acqDate = new Date(selectedProperty.acquisition_date);
                                const now = new Date();
                                const months = (now.getFullYear() - acqDate.getFullYear()) * 12 + (now.getMonth() - acqDate.getMonth());
                                return `${months} mo`;
                              })()
                              : 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Cap Rate</div>
                          <div className="text-xl font-bold">{metrics?.capRate || 0}%</div>
                        </div>
                      </div>
                    </Card>

                    {/* Financial Health */}
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Financial Health</h3>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">NOI Performance</span>
                            <span className="text-sm font-medium">
                              ${(metrics?.noi || 0) / 1000}K / ${((metrics?.noi || 0) * 1.25) / 1000}K target
                            </span>
                          </div>
                          <ProgressBar
                            value={((metrics?.noi || 0) / ((metrics?.noi || 0) * 1.25)) * 100}
                            max={100}
                            variant="success"
                            height="md"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">DSCR</span>
                            <span className="text-sm font-medium">
                              {metrics?.dscr.toFixed(2)} / 1.25 min
                            </span>
                          </div>
                          <ProgressBar
                            value={((metrics?.dscr || 0) / 1.25) * 100}
                            max={100}
                            variant={metrics?.dscr && metrics.dscr < 1.25 ? 'danger' : 'success'}
                            height="md"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">Occupancy</span>
                            <span className="text-sm font-medium">
                              {unitInfo?.occupiedUnits || 0} / {unitInfo?.totalUnits || 0} units
                            </span>
                          </div>
                          <ProgressBar
                            value={((unitInfo?.occupiedUnits || 0) / (unitInfo?.totalUnits || 1)) * 100}
                            max={100}
                            variant="success"
                            height="md"
                          />
                        </div>
                      </div>
                    </Card>

                    {/* Property Costs */}
                    {costs && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Property Costs</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          <div>
                            <div className="text-sm text-text-secondary">Insurance</div>
                            <div className="text-lg font-semibold">${(costs.insurance / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Mortgage</div>
                            <div className="text-lg font-semibold">${(costs.mortgage / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Utilities</div>
                            <div className="text-lg font-semibold">${(costs.utilities / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Initial Buying</div>
                            <div className="text-lg font-semibold">${(costs.initialBuying / 1000000).toFixed(1)}M</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Other Costs</div>
                            <div className="text-lg font-semibold">${(costs.other / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total</div>
                            <div className="text-lg font-bold text-info">${(costs.total / 1000000).toFixed(2)}M</div>
                          </div>
                        </div>
                      </Card>
                    )}

                    {/* Square Footage & Units */}
                    {unitInfo && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Square Footage & Units</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                          <div>
                            <div className="text-sm text-text-secondary">Total Square Feet</div>
                            <div className="text-xl font-bold">{unitInfo.totalSqft.toLocaleString()} sqft</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total Units</div>
                            <div className="text-xl font-bold">{unitInfo.totalUnits}</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Occupied</div>
                            <div className="text-xl font-bold text-success">{unitInfo.occupiedUnits}</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Available</div>
                            <div className="text-xl font-bold text-warning">{unitInfo.availableUnits}</div>
                          </div>
                        </div>
                        <div className="text-sm text-text-secondary">
                          Occupancy Rate: <span className="font-semibold text-text-primary">
                            {((unitInfo.occupiedUnits / unitInfo.totalUnits) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </Card>
                    )}
                  </div>
                )}

                {activeTab === 'financials' && (
                  <div className="space-y-6">
                    {/* Statement Type Selector */}
                    <Card className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold">Financial Statements</h3>
                        <div className="flex gap-2">
                          <select
                            value={selectedYear}
                            onChange={(e) => {
                              setSelectedYear(Number(e.target.value));
                              if (selectedProperty) {
                                loadFinancialStatements(selectedProperty.property_code);
                              }
                            }}
                            className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                          >
                            {[2023, 2024, 2025, 2026].map(year => (
                              <option key={year} value={year}>{year}</option>
                            ))}
                          </select>
                          <select
                            value={selectedMonth}
                            onChange={(e) => {
                              setSelectedMonth(Number(e.target.value));
                              if (selectedProperty) {
                                loadFinancialStatements(selectedProperty.property_code);
                              }
                            }}
                            className="px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                          >
                            {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
                              <option key={month} value={month}>
                                {new Date(2000, month - 1).toLocaleString('default', { month: 'long' })}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Statement Type Cards */}
                      <div className="grid grid-cols-3 gap-4 mb-6">
                        <Card
                          variant={selectedStatement === 'income' ? 'info' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'income' ? 'ring-2 ring-info' : ''}`}
                          onClick={() => setSelectedStatement('income')}
                          hover
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">📊</div>
                            <div className="font-semibold">Income Statement</div>
                            <div className="text-sm text-text-secondary mt-1">
                              {selectedYear} - {new Date(2000, selectedMonth - 1).toLocaleString('default', { month: 'short' })}
                            </div>
                          </div>
                        </Card>
                        <Card
                          variant={selectedStatement === 'balance' ? 'info' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'balance' ? 'ring-2 ring-info' : ''}`}
                          onClick={() => setSelectedStatement('balance')}
                          hover
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">💰</div>
                            <div className="font-semibold">Balance Sheet</div>
                            <div className="text-sm text-text-secondary mt-1">
                              {selectedYear} - {new Date(2000, selectedMonth - 1).toLocaleString('default', { month: 'short' })}
                            </div>
                          </div>
                        </Card>
                        <Card
                          variant={selectedStatement === 'cashflow' ? 'info' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'cashflow' ? 'ring-2 ring-info' : ''}`}
                          onClick={() => setSelectedStatement('cashflow')}
                          hover
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">💸</div>
                            <div className="font-semibold">Cash Flow</div>
                            <div className="text-sm text-text-secondary mt-1">
                              {selectedYear} - {new Date(2000, selectedMonth - 1).toLocaleString('default', { month: 'short' })}
                            </div>
                          </div>
                        </Card>
                      </div>

                      {/* Financial Data Display */}
                      {loadingDocumentData ? (
                        <div className="text-center py-8">
                          <div className="text-text-secondary mb-2">Loading complete financial document data...</div>
                          <div className="text-xs text-text-tertiary">Fetching all line items with zero data loss</div>
                        </div>
                      ) : financialData && financialData.items && financialData.items.length > 0 ? (
                        <Card className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div>
                              <h4 className="text-lg font-semibold">
                                {financialData.document_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} - Complete Line Items
                              </h4>
                              <p className="text-sm text-text-secondary mt-1">
                                Showing all {financialData.items.length} of {financialData.total_items} extracted line items
                              </p>
                            </div>
                            <div className="text-sm text-text-secondary">
                              {financialData.property_code} • {financialData.period_year}/{String(financialData.period_month).padStart(2, '0')}
                            </div>
                          </div>
                          
                          <div className="overflow-x-auto max-h-[600px] overflow-y-auto border border-border rounded-lg">
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
                                        : item.amounts.monthly_rent !== undefined && item.amounts.monthly_rent !== null
                                        ? `$${item.amounts.monthly_rent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
                      ) : financialStatements ? (
                        <div className="space-y-4">
                          {selectedStatement === 'income' && financialStatements.income_statement && (
                            <Card className="p-6">
                              <h4 className="text-lg font-semibold mb-4">Income Statement Summary</h4>
                              <div className="space-y-3">
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span className="font-medium">Total Revenue</span>
                                  <span className="font-semibold">
                                    ${(financialStatements.income_statement.total_revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span>Operating Expenses</span>
                                  <span>
                                    ${(financialStatements.income_statement.total_operating_expenses || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b-2 border-border font-semibold">
                                  <span>Net Operating Income (NOI)</span>
                                  <span className="text-success">
                                    ${(financialStatements.income_statement.net_operating_income || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                {financialStatements.income_statement.operating_margin && (
                                  <div className="flex justify-between py-2">
                                    <span className="text-text-secondary">Operating Margin</span>
                                    <span className="text-text-secondary">
                                      {(financialStatements.income_statement.operating_margin * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )}
                              </div>
                            </Card>
                          )}

                          {selectedStatement === 'balance' && financialStatements.balance_sheet && (
                            <Card className="p-6">
                              <h4 className="text-lg font-semibold mb-4">Balance Sheet Summary</h4>
                              <div className="space-y-3">
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span className="font-medium">Total Assets</span>
                                  <span className="font-semibold">
                                    ${(financialStatements.balance_sheet.total_assets || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span>Total Liabilities</span>
                                  <span>
                                    ${(financialStatements.balance_sheet.total_liabilities || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b-2 border-border font-semibold">
                                  <span>Total Equity</span>
                                  <span className="text-success">
                                    ${((financialStatements.balance_sheet.total_assets || 0) - (financialStatements.balance_sheet.total_liabilities || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                              </div>
                            </Card>
                          )}

                          {selectedStatement === 'cashflow' && financialStatements.cash_flow && (
                            <Card className="p-6">
                              <h4 className="text-lg font-semibold mb-4">Cash Flow Statement Summary</h4>
                              <div className="space-y-3">
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span className="font-medium">Operating Cash Flow</span>
                                  <span className="font-semibold">
                                    ${(financialStatements.cash_flow.operating_cash_flow || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span>Investing Cash Flow</span>
                                  <span>
                                    ${(financialStatements.cash_flow.investing_cash_flow || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b border-border">
                                  <span>Financing Cash Flow</span>
                                  <span>
                                    ${(financialStatements.cash_flow.financing_cash_flow || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex justify-between py-2 border-b-2 border-border font-semibold">
                                  <span>Net Cash Flow</span>
                                  <span className="text-success">
                                    ${(financialStatements.cash_flow.net_cash_flow || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </span>
                                </div>
                              </div>
                            </Card>
                          )}
                        </div>
                      ) : (
                        <Card className="p-8 text-center">
                          <div className="text-text-secondary mb-4">
                            {availableDocuments.length > 0 
                              ? `No ${selectedStatement === 'income' ? 'income statement' : selectedStatement === 'balance' ? 'balance sheet' : 'cash flow'} document found for ${selectedYear}/${String(selectedMonth).padStart(2, '0')}.`
                              : `No financial documents uploaded for ${selectedYear}/${String(selectedMonth).padStart(2, '0')}.`
                            }
                          </div>
                          {availableDocuments.length > 0 && (
                            <div className="text-xs text-text-tertiary mb-4">
                              Available documents: {availableDocuments.map(d => d.document_type).join(', ')}
                            </div>
                          )}
                          <Button variant="primary" onClick={() => setShowUploadModal(true)}>
                            Upload Financial Documents
                          </Button>
                        </Card>
                      )}
                    </Card>
                  </div>
                )}

                {activeTab === 'market' && (
                  <div className="space-y-6">
                    {loadingMarketIntel ? (
                      <Card className="p-8 text-center">
                        <div className="text-text-secondary">Loading market intelligence...</div>
                      </Card>
                    ) : marketIntel ? (
                      <>
                        <Card variant="premium" className="p-6">
                          <div className="flex items-center gap-2 mb-4">
                            <Sparkles className="w-5 h-5 text-premium" />
                            <h3 className="text-lg font-semibold">Market Intelligence (AI-Powered)</h3>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                              <div className="text-sm text-text-secondary mb-1">Location Score</div>
                              <div className="text-3xl font-bold mb-1">{marketIntel.locationScore}/10</div>
                              <div className="text-xs text-text-secondary">CBD location, high foot traffic, transit access</div>
                            </div>
                            <div>
                              <div className="text-sm text-text-secondary mb-1">Market Cap Rate</div>
                              <div className="text-2xl font-semibold mb-1">{marketIntel.marketCapRate}%</div>
                              <div className="text-sm">
                                Your property: <span className="font-medium">{marketIntel.yourCapRate}%</span>
                                {marketIntel.yourCapRate < marketIntel.marketCapRate && (
                                  <span className="text-warning"> (Below market by {(marketIntel.marketCapRate - marketIntel.yourCapRate).toFixed(2)}%)</span>
                                )}
                                {marketIntel.yourCapRate > marketIntel.marketCapRate && (
                                  <span className="text-success"> (Above market by {(marketIntel.yourCapRate - marketIntel.marketCapRate).toFixed(2)}%)</span>
                                )}
                              </div>
                            </div>
                            <div>
                              <div className="text-sm text-text-secondary mb-1">Market Rent Growth</div>
                              <div className="text-2xl font-semibold mb-1">+{marketIntel.rentGrowth}% YoY</div>
                              <div className="text-sm">
                                Your rent growth: <span className="font-medium">+{marketIntel.yourRentGrowth}% YoY</span>
                                {marketIntel.yourRentGrowth < marketIntel.rentGrowth && (
                                  <span className="text-warning"> (Lagging market)</span>
                                )}
                                {marketIntel.yourRentGrowth > marketIntel.rentGrowth && (
                                  <span className="text-success"> (Outperforming market)</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </Card>

                        <Card className="p-6">
                          <h3 className="text-lg font-semibold mb-4">Demographics</h3>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                              <div className="text-sm text-text-secondary">Population</div>
                              <div className="text-xl font-semibold">{marketIntel.demographics.population.toLocaleString()}</div>
                            </div>
                            <div>
                              <div className="text-sm text-text-secondary">Median Income</div>
                              <div className="text-xl font-semibold">${marketIntel.demographics.medianIncome.toLocaleString()}</div>
                            </div>
                            <div>
                              <div className="text-sm text-text-secondary">Employment</div>
                              <div className="text-xl font-semibold">{marketIntel.demographics.employmentType}</div>
                            </div>
                          </div>
                        </Card>

                        <Card className="p-6">
                          <h3 className="text-lg font-semibold mb-4">Comparable Properties (Within 2 miles)</h3>
                          <div className="space-y-3">
                            {marketIntel.comparables.length > 0 ? (
                              marketIntel.comparables.map((comp, i) => (
                                <div key={i} className="bg-premium-light/20 p-4 rounded-lg border border-border">
                                  <div className="flex items-center justify-between">
                                    <div className="font-medium">{comp.name}</div>
                                    <div className="text-sm text-text-secondary">{comp.distance} miles away</div>
                                  </div>
                                  <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
                                    <div>
                                      <span className="text-text-secondary">Cap Rate: </span>
                                      <span className="font-semibold">{comp.capRate}%</span>
                                    </div>
                                    <div>
                                      <span className="text-text-secondary">Occupancy: </span>
                                      <span className="font-semibold">{comp.occupancy}%</span>
                                    </div>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <div className="text-text-secondary text-center py-4">No comparable properties found</div>
                            )}
                          </div>
                        </Card>

                        <Card variant="info" className="p-6">
                          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-info" />
                            AI Insights
                          </h3>
                          <div className="space-y-3">
                            {marketIntel.aiInsights.length > 0 ? (
                              marketIntel.aiInsights.map((insight, i) => (
                                <div key={i} className="flex items-start gap-3">
                                  <span className="text-info text-xl">💡</span>
                                  <span className="text-sm flex-1">{insight}</span>
                                </div>
                              ))
                            ) : (
                              <div className="text-text-secondary text-center py-4">No AI insights available</div>
                            )}
                          </div>
                        </Card>
                      </>
                    ) : (
                      <Card className="p-8 text-center">
                        <div className="text-text-secondary mb-4">
                          Market intelligence data not available for this property.
                        </div>
                        <Button variant="primary" onClick={() => selectedProperty && loadMarketIntelligence(selectedProperty.id)}>
                          Retry Loading
                        </Button>
                      </Card>
                    )}
                  </div>
                )}

                {activeTab === 'tenants' && (
                  <div className="space-y-6">
                    {/* Tenant Mix Summary */}
                    {unitInfo && (
                      <Card className="p-6">
                        <h3 className="text-lg font-semibold mb-4">Tenant Mix Summary</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full">
                            <thead>
                              <tr className="border-b border-border">
                                <th className="text-left py-2 px-4">Type</th>
                                <th className="text-right py-2 px-4">Units</th>
                                <th className="text-right py-2 px-4">Sq Ft</th>
                                <th className="text-right py-2 px-4">Monthly Rent</th>
                                <th className="text-left py-2 px-4">Lease Exp</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tenantMix.length > 0 ? (
                                tenantMix.map((mix, index) => (
                                  <tr key={index} className="border-b border-border/50 last:border-0">
                                    <td className="py-2 px-4">{mix.tenantType}</td>
                                    <td className="text-right py-2 px-4">{mix.unitCount}</td>
                                    <td className="text-right py-2 px-4">{mix.totalSqft.toLocaleString()}</td>
                                    <td className="text-right py-2 px-4">${(mix.totalRevenue / 12).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                    <td className="py-2 px-4">{mix.occupancyPct.toFixed(0)}% occupied</td>
                                  </tr>
                                ))
                              ) : (
                                <tr>
                                  <td colSpan={5} className="py-8 text-center text-text-secondary">
                                    No tenant mix data available
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </Card>
                    )}

                    {/* AI Tenant Matching */}
                    {tenantMatches.length > 0 && (
                      <Card variant="success" className="p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-success" />
                          AI Tenant Matching Engine
                        </h3>
                        <div className="space-y-4">
                          {tenantMatches.slice(0, 3).map((match, i) => (
                            <div key={i} className="bg-success-light/20 p-4 rounded-lg border border-success/30">
                              <div className="flex items-start justify-between mb-2">
                                <div>
                                  <div className="font-semibold">#{i + 1} MATCH: {match.tenantName}</div>
                                  <div className="text-sm text-text-secondary">
                                    Match Score: {match.matchScore}/100
                                    {match.matchScore >= 90 && <span className="text-success ml-2">🟢</span>}
                                  </div>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-sm mt-3">
                                <div>
                                  <span className="text-text-secondary">Credit Score:</span>
                                  <span className="ml-2 font-medium">{match.creditScore} (Excellent)</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Industry:</span>
                                  <span className="ml-2 font-medium">{match.industry}</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Desired Sq Ft:</span>
                                  <span className="ml-2 font-medium">{match.desiredSqft.min}-{match.desiredSqft.max}</span>
                                </div>
                                <div>
                                  <span className="text-text-secondary">Est. Rent:</span>
                                  <span className="ml-2 font-medium">${match.estimatedRent.toLocaleString()}/mo</span>
                                </div>
                              </div>
                              <div className="mt-3">
                                <div className="text-sm font-medium mb-1">💡 AI Reasons:</div>
                                <ul className="text-sm text-text-secondary space-y-1">
                                  {match.reasons.map((reason, j) => (
                                    <li key={j}>• {reason}</li>
                                  ))}
                                </ul>
                              </div>
                              <div className="flex gap-2 mt-4">
                                <Button variant="success" size="sm">Contact Tenant</Button>
                                <Button variant="primary" size="sm">Schedule Tour</Button>
                                <Button variant="info" size="sm">View Profile</Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </Card>
                    )}
                  </div>
                )}

                {activeTab === 'docs' && (
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">Documents</h3>
                      <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowUploadModal(true)}>
                        Upload Document
                      </Button>
                    </div>
                    <p className="text-text-secondary">{availableDocuments.length} Documents</p>
                    <div className="mt-4 space-y-2">
                      {availableDocuments.length > 0 ? (
                        availableDocuments.map((doc, index) => {
                          // The API response may have enriched fields, but TypeScript type doesn't include them
                          const docAny = doc as any;
                          return (
                            <div key={doc.id || index} className="flex items-center gap-2 p-3 bg-background rounded-lg">
                              <FileText className="w-5 h-5 text-info" />
                              <div className="flex-1">
                                <div className="font-medium">{doc.file_name}</div>
                                <div className="text-sm text-text-secondary">
                                  {doc.document_type} - {docAny.period_year || 'N/A'}/{docAny.period_month || 'N/A'}
                                </div>
                              </div>
                              <div className="text-sm text-text-secondary">
                                {new Date(doc.upload_date).toLocaleDateString()}
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-center py-8 text-text-secondary">
                          No documents uploaded yet. Click "Upload Document" to get started.
                        </div>
                      )}
                    </div>
                  </Card>
                )}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <Building2 className="w-16 h-16 mx-auto mb-4 text-text-secondary" />
                <h3 className="text-xl font-semibold mb-2">No Property Selected</h3>
                <p className="text-text-secondary mb-4">Select a property from the list to view details</p>
                <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
                  Add Your First Property
                </Button>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showCreateModal && (
        <PropertyFormModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadProperties();
          }}
        />
      )}

      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowUploadModal(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold mb-4">Upload Document</h2>
            <DocumentUpload onUploadSuccess={() => {
              setShowUploadModal(false);
              loadPropertyDetails(selectedProperty?.id || 0);
            }} />
          </div>
        </div>
      )}
    </div>
  );
}

// Property Form Modal Component
function PropertyFormModal({
  property,
  onClose,
  onSuccess,
}: {
  property?: Property;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEditing = !!property;
  const [formData, setFormData] = useState<PropertyCreate>({
    property_code: property?.property_code || '',
    property_name: property?.property_name || '',
    property_type: property?.property_type || '',
    address: property?.address || '',
    city: property?.city || '',
    state: property?.state || '',
    zip_code: property?.zip_code || '',
    country: property?.country || 'USA',
    total_area_sqft: property?.total_area_sqft || undefined,
    acquisition_date: property?.acquisition_date || '',
    ownership_structure: property?.ownership_structure || '',
    status: property?.status || 'active',
    notes: property?.notes || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isEditing && property) {
        await propertyService.updateProperty(property.id, formData);
      } else {
        await propertyService.createProperty(formData);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-surface rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">{isEditing ? 'Edit Property' : 'Create Property'}</h2>
          <button className="text-text-secondary hover:text-text-primary text-2xl" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-danger-light text-danger rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Property Code *</label>
              <input
                type="text"
                value={formData.property_code}
                onChange={(e) => setFormData({ ...formData, property_code: e.target.value })}
                required
                disabled={isEditing}
                pattern="[A-Z]{2,5}\\d{3}"
                title="Format: LETTERS+3 digits (e.g., ESP001)"
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
              <small className="text-text-secondary text-xs">e.g., ESP001, WEND001</small>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Property Name *</label>
              <input
                type="text"
                value={formData.property_name}
                onChange={(e) => setFormData({ ...formData, property_name: e.target.value })}
                required
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Property Type</label>
              <select
                value={formData.property_type}
                onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              >
                <option value="">Select type...</option>
                <option value="Retail">Retail</option>
                <option value="Office">Office</option>
                <option value="Industrial">Industrial</option>
                <option value="Mixed Use">Mixed Use</option>
                <option value="Multifamily">Multifamily</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Total Area (sqft)</label>
              <input
                type="number"
                value={formData.total_area_sqft || ''}
                onChange={(e) => setFormData({ ...formData, total_area_sqft: e.target.value ? Number(e.target.value) : undefined })}
                min="0"
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Address</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">City</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">State</label>
              <input
                type="text"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                maxLength={2}
                placeholder="NC"
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">ZIP Code</label>
              <input
                type="text"
                value={formData.zip_code}
                onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Acquisition Date</label>
              <input
                type="date"
                value={formData.acquisition_date}
                onChange={(e) => setFormData({ ...formData, acquisition_date: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
              >
                <option value="active">Active</option>
                <option value="sold">Sold</option>
                <option value="under_contract">Under Contract</option>
              </select>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Ownership Structure</label>
            <input
              type="text"
              value={formData.ownership_structure}
              onChange={(e) => setFormData({ ...formData, ownership_structure: e.target.value })}
              placeholder="LLC, Partnership, etc."
              className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
            />
          </div>

          <div className="flex gap-3 justify-end">
            <Button variant="danger" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={loading} isLoading={loading}>
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

