import { useState, useEffect, useRef } from 'react';
import {
  Building2,
  FileText,
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Sparkles,
  List,
  Map as MapIcon,
  Download,
  TrendingUp,
  ArrowRight
} from 'lucide-react';
import { usePortfolioStore } from '../store';
import { useAuth } from '../components/AuthContext';
import { 
  Button,
  Card,
  ProgressBar,
  MetricCard,
  Input,
  Select,
  Checkbox,
  type SelectOption
} from '../components/ui';
import { PropertyMap } from '../components/PropertyMap';
import { propertyService } from '../lib/property';
import { mortgageService } from '../lib/mortgage';
import { reportsService } from '../lib/reports';
import { documentService } from '../lib/document';
import { AlertService } from '../lib/alerts';
import { financialDataService } from '../lib/financial_data';
import { financialPeriodsService } from '../lib/financial_periods';
import { DocumentUpload } from '../components/DocumentUpload';
import { MortgageMetricsWidget } from '../components/mortgage/MortgageMetricsWidget';
import { MortgageStatementDetails } from '../components/mortgage/MortgageStatementDetails';
import { InlineEdit } from '../components/ui/InlineEdit';
import { exportPropertyListToCSV, exportPropertyListToExcel } from '../lib/exportUtils';
import type { Property, PropertyCreate, DocumentUpload as DocumentUploadType } from '../types/api';
import type { FinancialDataItem, FinancialDataResponse } from '../lib/financial_data';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

// Utility function to safely format error messages
const formatErrorMessage = (error: any): string => {
  if (typeof error === 'string') return error;
  if (error instanceof Error) return error.message;

  // Handle API error with nested detail: {detail: {detail: [...]}}
  if (error?.detail?.detail && Array.isArray(error.detail.detail)) {
    return error.detail.detail.map((e: any) => {
      // Format field name nicely
      const field = e.loc && e.loc.length > 0 ? e.loc[e.loc.length - 1] : '';
      const fieldName = field ? field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : '';
      return fieldName ? `${fieldName}: ${e.msg}` : e.msg;
    }).join('; ');
  }

  // Handle Pydantic validation errors: {detail: [{type, loc, msg, input, ctx}]}
  if (error?.detail) {
    if (Array.isArray(error.detail)) {
      // Array of validation errors
      return error.detail.map((e: any) => {
        const field = e.loc && e.loc.length > 0 ? e.loc[e.loc.length - 1] : '';
        const fieldName = field ? field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) : '';
        return fieldName ? `${fieldName}: ${e.msg}` : e.msg;
      }).join('; ');
    }
    if (typeof error.detail === 'object' && error.detail.msg) {
      // Single validation error object
      return error.detail.msg;
    }
    if (typeof error.detail === 'string') {
      // String detail
      return error.detail;
    }
  }

  // Handle message property
  if (error?.message && error.message !== 'Invalid request - please check your input') {
    return String(error.message);
  }

  // Fallback: stringify the whole error
  try {
    return JSON.stringify(error);
  } catch {
    return 'Unknown error';
  }
};

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
  locationScore: number | null;
  marketCapRate: number;
  yourCapRate: number;
  rentGrowth: number | null;
  yourRentGrowth: number;
  demographics: {
    population: number | null;
    medianIncome: number | null;
    employmentType: string;
    dataSource?: string | null;
  };
  comparables: Array<{
    name: string;
    distance: number;
    capRate: number;
    occupancy: number;
  }>;
  aiInsights: string[];
  dataQuality?: string;
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

export default function Properties() {
  // Portfolio Store - Persistent state
  const {
    selectedProperty,
    setSelectedProperty,
    selectedYear,
    setSelectedYear,
    viewMode,
    setViewMode,
    filters,
    setFilters,
    resetFilters,
    comparisonMode,
    toggleComparisonMode,
    selectedForComparison,
    addToComparison,
    removeFromComparison,
    clearComparison
  } = usePortfolioStore();

  const { logout, refreshUser } = useAuth();

  // Local state - Non-persistent
  const [properties, setProperties] = useState<Property[]>([]);
  const [showAdvancedFilter, setShowAdvancedFilter] = useState(false);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [metrics, setMetrics] = useState<PropertyMetrics | null>(null);
  const [costs, setCosts] = useState<PropertyCosts | null>(null);
  const [unitInfo, setUnitInfo] = useState<UnitInfo | null>(null);
  const [marketIntel, setMarketIntel] = useState<MarketIntelligence | null>(null);
  const [loadingMarketIntel, setLoadingMarketIntel] = useState(false);
  const [tenantMatches, setTenantMatches] = useState<TenantMatch[]>([]);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [propertyToDelete, setPropertyToDelete] = useState<Property | null>(null);
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [financialStatements, setFinancialStatements] = useState<any>(null);
  const [selectedStatement, setSelectedStatement] = useState<'income' | 'balance' | 'cashflow' | 'mortgage'>('income');
  const [propertyMetricsMap, setPropertyMetricsMap] = useState<Map<number, any>>(new Map());
  const [propertyDscrMap, setPropertyDscrMap] = useState<Map<number, number | null>>(new Map());
  const [selectedMonth, setSelectedMonth] = useState(12); // Default to December 2023
  const [financialData, setFinancialData] = useState<FinancialDataResponse | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentUploadType[]>([]);
  const [loadingDocumentData, setLoadingDocumentData] = useState(false);
  const [tenantMix, setTenantMix] = useState<any[]>([]);
  const [tenantDetails, setTenantDetails] = useState<any[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(false);
  const [alertCounts, setAlertCounts] = useState<Map<number, number>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Convert selectedForComparison Set to comparisonSet for backward compatibility
  const comparisonSet = selectedForComparison;

  // Derived state from filters
  const searchTerm = filters.search;
  const setSearchTerm = (search: string) => setFilters({ search });
  const quickFilter = (Array.isArray(filters.status) && filters.status.length > 0
    ? filters.status[0]
    : 'all') as 'all' | 'high-performers' | 'at-risk' | 'recent';

  const setQuickFilter = (status: string) => setFilters({ status: [status] });
  const [sortBy, setSortBy] = useState<'noi' | 'risk' | 'value'>('noi');
  
  // Advanced Filters State for Modal
  const [tempFilters, setTempFilters] = useState({
    minNOI: filters.minNOI || '',
    minOccupancy: filters.minOccupancy || '',
    minUnits: filters.minUnits || '',
    maxLTV: filters.maxLTV || '',
    tags: filters.tags || [] as string[]
  });

  // Sync temp filters when modal opens
  useEffect(() => {
    if (showAdvancedFilter) {
      setTempFilters({
        minNOI: filters.minNOI || '',
        minOccupancy: filters.minOccupancy || '',
        minUnits: filters.minUnits || '',
        maxLTV: filters.maxLTV || '',
        tags: filters.tags || []
      });
    }
  }, [showAdvancedFilter, filters]);
  
  const handleApplyAdvancedFilters = () => {
    setFilters({
      minNOI: tempFilters.minNOI ? Number(tempFilters.minNOI) : undefined,
      minOccupancy: tempFilters.minOccupancy ? Number(tempFilters.minOccupancy) : undefined,
      minUnits: tempFilters.minUnits ? Number(tempFilters.minUnits) : undefined,
      maxLTV: tempFilters.maxLTV ? Number(tempFilters.maxLTV) : undefined,
      tags: tempFilters.tags.length > 0 ? tempFilters.tags : undefined
    });
    setShowAdvancedFilter(false);
  };
  
  const toggleTag = (tag: string) => {
    setTempFilters(prev => {
      const newTags = prev.tags.includes(tag) 
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag];
      return { ...prev, tags: newTags };
    });
  };

  const handleClearFilters = () => {
    resetFilters();
  };
  const comparisonModalRef = useRef<HTMLDivElement | null>(null);
  const locationScore = marketIntel?.locationScore ?? 0;
  const metricsLoading = Boolean(selectedProperty && !metrics);

  useEffect(() => {
    loadProperties();
    // Initialize to most recent period with data
    initializeToLatestPeriod();
  }, []);

  const initializeToLatestPeriod = async () => {
    try {
      const periods = await financialPeriodsService.listPeriods();
      if (periods && periods.length > 0) {
        // Sort by year and month descending to get most recent
        const sorted = periods.sort((a, b) =>
          (b.period_year - a.period_year) || (b.period_month - a.period_month)
        );
        const latest = sorted[0];
        setSelectedYear(latest.period_year);
        setSelectedMonth(latest.period_month);
      }
    } catch (error) {
      console.error('Failed to load latest period:', error);
      // Keep defaults (2023-11) if fetch fails
    }
  };

  useEffect(() => {
    if (selectedProperty) {
      loadPropertyDetails(selectedProperty.id);
      loadFinancialStatements(selectedProperty.property_code);
      loadTenantMix(selectedProperty.id);
      loadTenantDetails(selectedProperty.id);
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  const handlePropertyNameSave = async (nextName: string) => {
    if (!selectedProperty) return;
    const trimmed = nextName.trim();
    if (!trimmed) {
      throw new Error('Name is required');
    }

    const previous = selectedProperty;
    const optimistic = { ...selectedProperty, property_name: trimmed, name: trimmed };

    // Optimistic UI update for detail header and list cards
    setSelectedProperty(optimistic);
    setProperties((prev) =>
      prev.map((p) => (p.id === optimistic.id ? { ...p, property_name: trimmed, name: trimmed } : p))
    );

    try {
      const updated = await propertyService.updateProperty(selectedProperty.id, { property_name: trimmed });
      setSelectedProperty(updated);
      setProperties((prev) => prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p)));
    } catch (error) {
      // Revert on failure so the user never sees stale data
      setSelectedProperty(previous);
      setProperties((prev) => prev.map((p) => (p.id === previous.id ? previous : p)));
      throw error;
    }
  };

  const loadProperties = async () => {
    try {
      setIsLoading(true);
      setLoadError(null);
      const data = await propertyService.getAllProperties();
      setProperties(data);
      if (data.length > 0 && !selectedProperty) {
        setSelectedProperty(data[0]);
      } else if (data.length === 0) {
        setSelectedProperty(null);
      }

      // Load metrics for all properties for sorting
      await loadAllPropertyMetrics(data);
    } catch (err: any) {
      console.error('Failed to load properties:', err);
      if (err?.status === 401) {
        setLoadError('Session expired. Please sign in again.');
        // Trigger a re-check of authentication status
        // If truly expired, the auth context will handle logout
        refreshUser().catch(console.error);
      } else if (err?.status === 403) {
        setLoadError('Access Denied: You do not have permission to view properties.');
      } else {
        setLoadError(err?.message || 'Unable to load properties. Please try again.');
      }
      setProperties([]);
      setSelectedProperty(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAllPropertyMetrics = async (props: Property[]) => {
    try {
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100&year=${selectedYear}`, {
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
        
        setPropertyMetricsMap(metricsMap);
        
        // Fetch DSCR for all properties using the batch API endpoint
        const propertyIds = props.map(p => p.id);
        if (propertyIds.length === 0) return;

        try {
          const dscrResponse = await fetch(`${API_BASE_URL}/risk-alerts/dscr/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ property_ids: propertyIds })
          });
          
          if (dscrResponse.ok) {
            const dscrData = await dscrResponse.json();
            if (dscrData.success && dscrData.results) {
              const dscrMap = new Map<number, number | null>();
              Object.entries(dscrData.results).forEach(([pid, val]) => {
                dscrMap.set(Number(pid), val as number | null);
              });
              setPropertyDscrMap(dscrMap);
            }
          }
        } catch (err) {
          console.error('Failed to batch fetch DSCR:', err);
        }
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
            net_operating_income: periodSpecificMetrics.net_operating_income, // Use NOI, not net_income
            net_income: periodSpecificMetrics.net_income, // Keep for fallback
            occupancy_rate: periodSpecificMetrics.occupancy_rate,
            total_expenses: periodSpecificMetrics.total_expenses,
            total_units: periodSpecificMetrics.total_units,
            occupied_units: periodSpecificMetrics.occupied_units,
            total_leasable_sqft: periodSpecificMetrics.total_leasable_sqft,
            dscr: periodSpecificMetrics.dscr, // Include DSCR from period-specific data
            ltv_ratio: periodSpecificMetrics.ltv_ratio, // Include LTV from period-specific data
            period_id: periodSpecificMetrics.period_id // Include period_id for reference
          };
        } else {
          console.warn(`No period-specific data for ${currentProperty.property_code} ${selectedYear}-${selectedMonth}, using summary`);
        }
      } catch (periodErr) {
        console.warn('Failed to load period-specific metrics, using summary:', periodErr);
      }
      
      // Fall back to summary if period-specific not available
      if (!propertyMetric) {
        const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100&year=${selectedYear}`, {
          credentials: 'include'
        });
        const metricsData = metricsRes.ok ? await metricsRes.json() : [];
        // Match by property_code since API returns property_code, not property_id
        propertyMetric = metricsData.find((m: any) => m.property_code === currentProperty.property_code) || propertyMetricFromMap;
      }
      
      if (propertyMetric) {
        // Get DSCR from latest complete period (same logic as Command Center)
        let dscr: number | null = null;
        let ltv: number | null = propertyMetric.ltv_ratio !== null && propertyMetric.ltv_ratio !== undefined ? propertyMetric.ltv_ratio : null;
        let capRate: number | null = null;

        try {
          // Fetch DSCR from latest complete period using mortgageService
          const dscrData = await mortgageService.getLatestCompleteDSCR(propertyId, selectedYear);
          if (dscrData && dscrData.dscr !== null && dscrData.dscr !== undefined) {
            dscr = dscrData.dscr;
          }
        } catch (dscrErr) {
          console.error('Failed to fetch DSCR from latest complete period:', dscrErr);
        }

        // Always fall back to metrics summary if DSCR wasn't fetched from latest complete period
        if (dscr === null) {
          dscr = propertyMetric.dscr !== null && propertyMetric.dscr !== undefined ? propertyMetric.dscr : null;
        }

        try {
          // Fetch cap rate
          const capRateRes = await fetch(`${API_BASE_URL}/metrics/${propertyId}/cap-rate`, { credentials: 'include' });

          if (capRateRes.ok) {
            const capRateData = await capRateRes.json();
            capRate = capRateData.cap_rate || null;
          }
        } catch (apiErr) {
          console.error('Failed to fetch Cap Rate:', apiErr);
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
        // Use net_operating_income (NOI) instead of net_income for consistency with Command Center
        const metricsNoi = periodSpecificMetrics?.net_operating_income || propertyMetric?.net_operating_income || 
                          periodSpecificMetrics?.net_income || propertyMetric?.net_income || 0;
        const metricsOccupancy = periodSpecificMetrics?.occupancy_rate || propertyMetric?.occupancy_rate || 0;
        
        setMetrics({
          value: metricsValue,
          noi: metricsNoi,
          dscr: dscr !== null ? dscr : 0,
          ltv: ltv !== null ? ltv : 0,
          occupancy: metricsOccupancy,
          capRate: capRate !== null ? capRate : 0,
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
            noi: propertyMetricFromMap.net_operating_income || propertyMetricFromMap.net_income || 0,
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

      // Load costs - try costs endpoint first, otherwise show zeros (no hardcoded data)
      // Property costs should come from actual expense data, not estimates
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
              // No cost data - show zeros (no hardcoded estimates)
              console.warn('Costs API returned zero or missing data for property', propertyId, costsData);
              setCosts({
                insurance: 0,
                mortgage: 0,
                utilities: 0,
                initialBuying: periodSpecificMetrics?.total_assets || propertyMetric?.total_assets || 0,
                maintenance: 0,
                taxes: 0,
                other: 0,
                total: periodSpecificMetrics?.total_expenses || propertyMetric?.total_expenses || 0
              });
            }
          } else if (costsRes.status === 404) {
            // No detailed cost data - show zeros (no hardcoded estimates)
            console.warn(`Costs API 404 for property ${propertyId} - showing zeros`);
            setCosts({
              insurance: 0,
              mortgage: 0,
              utilities: 0,
              initialBuying: periodSpecificMetrics?.total_assets || propertyMetric?.total_assets || 0,
              maintenance: 0,
              taxes: 0,
              other: 0,
              total: periodSpecificMetrics?.total_expenses || propertyMetric?.total_expenses || 0
            });
          } else {
            // Other API error - show zeros (no hardcoded estimates)
            const errorText = await costsRes.text();
            console.error(`Costs API error for property ${propertyId}: ${costsRes.status} ${costsRes.statusText}`, errorText);
            setCosts({
              insurance: 0,
              mortgage: 0,
              utilities: 0,
              initialBuying: periodSpecificMetrics?.total_assets || propertyMetric?.total_assets || 0,
              maintenance: 0,
              taxes: 0,
              other: 0,
              total: periodSpecificMetrics?.total_expenses || propertyMetric?.total_expenses || 0
            });
          }
        } catch (costsErr) {
          console.error('Failed to fetch property costs:', costsErr);
          // Show zeros if no data (no hardcoded estimates)
          setCosts({
            insurance: 0,
            mortgage: 0,
            utilities: 0,
            initialBuying: periodSpecificMetrics?.total_assets || propertyMetric?.total_assets || 0,
            maintenance: 0,
            taxes: 0,
            other: 0,
            total: periodSpecificMetrics?.total_expenses || propertyMetric?.total_expenses || 0
          });
        }

      // Load unit info - use period-specific data if available AND has rent roll data, otherwise try units endpoint
      // Check if period-specific metrics has valid rent roll data (total_units > 0 and total_leasable_sqft > 0)
      const hasValidPeriodData = periodSpecificMetrics?.total_units !== null && 
                                  periodSpecificMetrics?.total_units !== undefined && 
                                  periodSpecificMetrics?.total_units > 0 &&
                                  periodSpecificMetrics?.total_leasable_sqft !== null &&
                                  periodSpecificMetrics?.total_leasable_sqft !== undefined &&
                                  periodSpecificMetrics?.total_leasable_sqft > 0;
      
      if (hasValidPeriodData) {
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
        // Fall back to units endpoint - always use latest available rent roll period
        // The units endpoint automatically finds the latest period with rent roll data
        try {
          // Always fetch latest rent roll (units endpoint has fallback logic to find latest period)
          // Don't pass period_id - let the endpoint find the latest rent roll period
          const unitsRes = await fetch(`${API_BASE_URL}/metrics/${propertyId}/units?limit=100`, {
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
      console.error('Failed to load asset details:', err);
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
      
      // Get property metrics for comparison (filtered by selected year)
      const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100&year=${selectedYear}`, {
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
          locationScore: research.location_score ?? null,
          marketCapRate: research.market_cap_rate || 0,
          yourCapRate: yourCapRate || 0,
          rentGrowth: research.rent_growth ?? null,
          yourRentGrowth: propertyMetric?.rent_growth_yoy || 0,
          demographics: {
            population: research.demographics?.population ?? null,
            medianIncome: research.demographics?.median_income ?? null,
            employmentType: research.demographics?.employment_type || 'Data not available',
            dataSource: research.demographics?.data_source || null
          },
          comparables: research.comparables || [],
          aiInsights: research.key_findings || research.insights || [],
          dataQuality: research.data_quality || 'pending'
        });
      } else {
        // No data - set to zeros/empty
        setMarketIntel({
          locationScore: null,
          marketCapRate: 0,
          yourCapRate: yourCapRate || 0,
          rentGrowth: null,
          yourRentGrowth: propertyMetric?.rent_growth_yoy || 0,
          demographics: {
            population: null,
            medianIncome: null,
            employmentType: 'Data not available',
            dataSource: null
          },
          comparables: [],
          aiInsights: []
        });
      }
    } catch (err) {
      console.error('Failed to load market intelligence:', err);
      // Set to zeros/empty on error - no mock data
      setMarketIntel({
        locationScore: null,
        marketCapRate: 0,
        yourCapRate: 0,
        rentGrowth: null,
        yourRentGrowth: 0,
        demographics: {
          population: null,
          medianIncome: null,
          employmentType: 'Data not available',
          dataSource: null
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

  const loadTenantDetails = async (propertyId: number) => {
    setLoadingTenants(true);
    try {
      const res = await fetch(`${API_BASE_URL}/metrics/${propertyId}/tenants`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setTenantDetails(data.tenants || []);
      } else {
        setTenantDetails([]);
      }
    } catch (err) {
      console.error('Failed to load tenant details:', err);
      setTenantDetails([]);
    } finally {
      setLoadingTenants(false);
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
    if (!propertyCode) return [];

    try {
      const docs = await documentService.getDocuments({
        property_code: propertyCode,
        period_year: selectedYear,
        period_month: selectedMonth,
        limit: 50
      });
      const items = docs.items || [];
      setAvailableDocuments(items);
      return items;
    } catch (err) {
      console.error('Failed to load documents:', err);
      return [];
    }
  };

  const loadFinancialDocumentData = async (
    documentType: 'income_statement' | 'balance_sheet' | 'cash_flow' | 'mortgage_statement',
    docsToUse?: DocumentUploadType[]
  ) => {
    if (!selectedProperty) return;

    setLoadingDocumentData(true);
    setFinancialData(null); // Clear previous data

    try {
      // Mortgage statements are handled by the MortgageStatementDetails component
      // Skip loading financial data for mortgage statements
      if (documentType === 'mortgage_statement') {
        console.log('Skipping financial data load for mortgage_statement - handled by dedicated component');
        setLoadingDocumentData(false);
        return;
      }

      // Use provided documents or fall back to state
      const documentsToSearch = docsToUse || availableDocuments;

      console.log('Loading financial data for:', {
        documentType,
        propertyCode: selectedProperty.property_code,
        period: `${selectedYear}/${selectedMonth}`,
        availableDocuments: documentsToSearch.length
      });

      // Find the document for this type and period - try completed first, then any status
      let doc = documentsToSearch.find(d =>
        d.document_type === documentType &&
        d.extraction_status === 'completed'
      );

      // If no completed document, try any document with this type
      if (!doc) {
        doc = documentsToSearch.find(d => d.document_type === documentType);
        console.log('No completed document found, trying any document:', doc);
      }

      // Log all available documents for debugging
      console.log('All available documents:', documentsToSearch.map(d => ({
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

          // Load items in batches (API max limit is 1000)
          const firstBatchSize = Math.min(summary.total_items || 1000, 1000);
          const data = await financialDataService.getFinancialData(doc.id, {
            limit: firstBatchSize,
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
      // Clear financial data when period changes
      setFinancialData(null);
      setFinancialStatements(null);
      // Load available documents for new period
      loadAvailableDocuments(selectedProperty.property_code);
    }
  }, [selectedProperty, selectedYear, selectedMonth]);

  useEffect(() => {
    if (selectedProperty && availableDocuments.length > 0) {
      const docTypeMap = {
        'income': 'income_statement' as const,
        'balance': 'balance_sheet' as const,
        'cashflow': 'cash_flow' as const,
        'mortgage': 'mortgage_statement' as const
      };
      console.log('Loading financial data for statement:', selectedStatement, 'docs available:', availableDocuments.length, 'period:', `${selectedYear}/${selectedMonth}`);
      loadFinancialDocumentData(docTypeMap[selectedStatement]);
    } else {
      console.log('Skipping financial data load:', { selectedProperty: !!selectedProperty, availableDocuments: availableDocuments.length, period: `${selectedYear}/${selectedMonth}` });
    }
  }, [selectedStatement, availableDocuments, selectedProperty, selectedYear, selectedMonth]);

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'critical': return 'danger';
      case 'warning': return 'warning';
      case 'good': return 'success';
      default: return 'default';
    }
  };

  useEffect(() => {
    if (comparisonSet.size === 0) {
      setAlertCounts(new Map());
      return;
    }
    let cancelled = false;
    const loadAlerts = async () => {
      const entries = await Promise.all(
        Array.from(comparisonSet).map(async (id) => {
          try {
            const summary = await AlertService.getSummary({ property_id: id, days: 90 });
            return [id, summary?.active_alerts ?? summary?.total_alerts ?? 0] as const;
          } catch (err) {
            console.error('Failed to load alerts for property', id, err);
            return [id, 0] as const;
          }
        })
      );
      if (!cancelled) {
        setAlertCounts(new Map(entries));
      }
    };
    loadAlerts();
    return () => {
      cancelled = true;
    };
  }, [comparisonSet]);

  const matchesQuickFilter = (p: Property) => {
    const metrics = propertyMetricsMap.get(p.id);
    if (quickFilter === 'high-performers') {
      const occ = metrics?.occupancy_rate ?? 0;
      const dscr = metrics?.dscr ?? 0;
      return occ >= 90 && dscr >= 1.35;
    }
    if (quickFilter === 'at-risk') {
      const occ = metrics?.occupancy_rate ?? 100;
      const dscr = metrics?.dscr ?? 999;
      return occ < 80 || dscr < 1.25;
    }
    if (quickFilter === 'recent') {
      if (!p.created_at) return false;
      const days = (Date.now() - new Date(p.created_at).getTime()) / (1000 * 60 * 60 * 24);
      return days <= 90;
    }
    return true;
  };

  const matchesAdvancedFilter = (p: Property) => {
     const metrics = propertyMetricsMap.get(p.id);
     
     // Min NOI
     if (filters.minNOI !== undefined) {
       const noi = metrics?.net_operating_income || metrics?.net_income || 0;
       if (noi < filters.minNOI) return false;
     }
     
     // Min Occupancy
     if (filters.minOccupancy !== undefined) {
        const occ = metrics?.occupancy_rate ?? 0;
        if (occ < filters.minOccupancy) return false;
     }
     
     // Min Units
     if (filters.minUnits !== undefined) {
        // Assuming unit count is part of property data or metrics, currently using hardcoded check or derived
        // If unit count isn't readily available, we might skip or assume 0. 
        // Note: unitInfo logic implies units fetch. For now, checking if property has total_units field
        const units = (p as any).total_units || 0; 
        if (units < filters.minUnits) return false;
     }

     // Max LTV
     if (filters.maxLTV !== undefined) {
        const ltv = metrics?.ltv_ratio ? metrics.ltv_ratio * 100 : 0;
        if (ltv > filters.maxLTV) return false;
     }
     
     // Tags
     if (filters.tags && filters.tags.length > 0) {
        // Assuming tags are on the property object or we match against some criteria
        // For now, let's assume property.tags exists or we match loosely
        const pTags = (p as any).tags || [];
        const hasTag = filters.tags.some(t => pTags.includes(t));
        // If property has no tags but we selected tags, filter out? Or permissive?
        // Let's assume strict match for now if property supports tags
        if (!hasTag) return false;
     }
     
     return true;
  };

  const filteredProperties = properties
    .filter(p =>
      p.property_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.property_code.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .filter(matchesQuickFilter)
    .filter(matchesAdvancedFilter);

  const filtersApplied = Boolean(searchTerm.trim()) ||
    quickFilter !== 'all' ||
    filters.minNOI !== undefined ||
    filters.minOccupancy !== undefined ||
    filters.minUnits !== undefined ||
    filters.maxLTV !== undefined ||
    (filters.tags && filters.tags.length > 0);

  // Prefetch alert counts for visible properties (up to 20 to avoid heavy load)
  // Prefetch alert counts for visible properties (up to 20 to avoid heavy load)
  useEffect(() => {
    const visible = filteredProperties.slice(0, 20);
    if (visible.length === 0) {
      setAlertCounts(new Map());
      return;
    }
    let cancelled = false;
    const loadAlerts = async () => {
      try {
        const propertyIds = visible.map(p => p.id);
        const res = await fetch(`${API_BASE_URL}/risk-alerts/summary/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ property_ids: propertyIds, lookback_days: 90 })
        });

        if (!cancelled && res.ok) {
            const data = await res.json();
            if (data.success && data.results) {
                const entries: [number, number][] = [];
                Object.entries(data.results).forEach(([pid, counts]: [string, any]) => {
                    // Use active or total based on previous logic preference
                    const count = counts.active_alerts ?? counts.total_alerts ?? 0;
                    entries.push([Number(pid), count]);
                });
                setAlertCounts(new Map(entries));
            }
        }
      } catch (err) {
        if (!cancelled) {
             console.error('Failed to load batch alerts', err);
        }
      }
    };
    loadAlerts();
    return () => {
      cancelled = true;
    };
  }, [filteredProperties]);

  const sortedProperties = [...filteredProperties].sort((a, b) => {
    const aMetrics = propertyMetricsMap.get(a.id);
    const bMetrics = propertyMetricsMap.get(b.id);

    if (sortBy === 'noi') {
      // Use net_operating_income (NOI) instead of net_income for consistency with Command Center
      const aNoi = aMetrics?.net_operating_income || aMetrics?.net_income || 0;
      const bNoi = bMetrics?.net_operating_income || bMetrics?.net_income || 0;
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

  const comparisonProperties = properties.filter((p) => comparisonSet.has(p.id));
  const comparisonStats = (() => {
    const metrics: Record<string, number[]> = {
      value: [],
      noi: [],
      dscr: [],
      ltv: [],
      occupancy: [],
      capRate: [],
      docs: [],
      alerts: [],
    };
    comparisonProperties.forEach((p) => {
      const m = propertyMetricsMap.get(p.id);
      const value = m?.total_assets || 0;
      const noi = m?.net_operating_income || m?.net_income || 0;
      const dscr = m?.dscr ?? null;
      const ltv = m?.ltv_ratio ?? null;
      const occ = m?.occupancy_rate ?? null;
      const capRate = value > 0 ? (noi / value) * 100 : null;
      const docs = availableDocuments.filter((d) => d.property_code === p.property_code).length;
      const alerts = alertCounts.get(p.id) ?? 0;
      metrics.value.push(value);
      metrics.noi.push(noi);
      if (dscr !== null) metrics.dscr.push(dscr);
      if (ltv !== null) metrics.ltv.push(ltv);
      if (occ !== null) metrics.occupancy.push(occ);
      if (capRate !== null) metrics.capRate.push(capRate);
      metrics.docs.push(docs);
      metrics.alerts.push(alerts);
    });
    const calc = (arr: number[]) => ({ max: Math.max(...arr, 0), min: Math.min(...arr, Infinity) });
    return {
      value: calc(metrics.value),
      noi: calc(metrics.noi),
      dscr: metrics.dscr.length ? calc(metrics.dscr) : { max: 0, min: 0 },
      ltv: metrics.ltv.length ? calc(metrics.ltv) : { max: 0, min: 0 },
      occupancy: metrics.occupancy.length ? calc(metrics.occupancy) : { max: 0, min: 0 },
      capRate: metrics.capRate.length ? calc(metrics.capRate) : { max: 0, min: 0 },
      docs: calc(metrics.docs),
      alerts: calc(metrics.alerts),
    };
  })();

  // Basic focus trap and Escape handling for comparison modal
  useEffect(() => {
    if (!showComparisonModal) return;
    const modalEl = comparisonModalRef.current;
    const focusable = modalEl?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    focusable?.[0]?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowComparisonModal(false);
        return;
      }
      if (e.key === 'Tab' && focusable && focusable.length > 0) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [showComparisonModal]);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Portfolio Hub</h1>
            <p className="text-text-secondary mt-1">Property management, market intelligence, and tenant optimization</p>
          </div>
          <div className="flex gap-2">
            <Button
              className="bg-blue-50 border-blue-200"
              icon={<Download className="w-4 h-4" />}
              onClick={() => exportPropertyListToCSV(properties)}
              size="sm"
            >
              CSV
            </Button>
            <Button
              className="bg-blue-50 border-blue-200"
              icon={<Download className="w-4 h-4" />}
              onClick={() => exportPropertyListToExcel(properties)}
              size="sm"
            >
              Excel
            </Button>
            <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => window.location.hash = 'add-property'}>
              Add Property
            </Button>
          </div>
        </div>

        {loadError && (
          <Card className="p-4 mb-4 border border-danger/30 bg-red-50 text-danger">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="font-medium">{loadError}</div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={loadProperties}>
                  Retry
                </Button>
                {loadError?.includes('Session expired') ? (
                  <Button variant="primary" size="sm" onClick={() => logout()}>
                    Sign In
                  </Button>
                ) : (
                  <Button variant="primary" size="sm" onClick={() => window.location.reload()}>
                    Refresh App
                  </Button>
                )}
              </div>
            </div>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
          {/* Left Panel - Property List (30%) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Filters */}
            <Card className="p-4">
              <div className="space-y-3">
                <div className="relative">
                  <Input
                    placeholder="Search properties..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    leftIcon={<Search className="w-4 h-4 text-text-secondary" />}
                    fullWidth
                  />
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                  <div className="flex-1 min-w-[160px]">
                    <Select
                      options={[
                        { value: 'noi', label: 'Sort by NOI' },
                        { value: 'risk', label: 'Sort by Risk' },
                        { value: 'value', label: 'Sort by Value' }
                      ]}
                      value={sortBy}
                      onChange={(val) => setSortBy(val as any)}
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { id: 'all', label: 'All' },
                      { id: 'high-performers', label: 'High Performers' },
                      { id: 'at-risk', label: 'At Risk' },
                      { id: 'recent', label: 'Recent Activity' },
                    ].map((filter) => (
                      <button
                        key={filter.id}
                        aria-pressed={quickFilter === filter.id}
                        className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                          quickFilter === filter.id
                            ? 'bg-info text-white border-info'
                            : 'text-text-secondary bg-background hover:text-text-primary'
                        }`}
                        onClick={() => {
                          setQuickFilter(filter.id as any);
                          if (filter.id === 'high-performers') setSortBy('noi');
                          if (filter.id === 'at-risk') setSortBy('risk');
                        }}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" icon={<Filter className="w-4 h-4" />} onClick={() => setShowAdvancedFilter(true)}>
                      Advanced
                    </Button>
                    <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                      Clear
                    </Button>
                  </div>
                </div>
              </div>

              {/* View Mode Toggle */}
              <div className="flex gap-2 border border-border rounded-lg p-1">
                <button
                  onClick={() => setViewMode('list')}
                  className={`flex items-center gap-2 px-3 py-2 rounded transition-colors ${
                    viewMode === 'list'
                      ? 'bg-info text-white'
                      : 'text-text-secondary hover:bg-background'
                  }`}
                >
                  <List className="w-4 h-4" />
                  <span className="text-sm font-medium">List</span>
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`flex items-center gap-2 px-3 py-2 rounded transition-colors ${
                    viewMode === 'map'
                      ? 'bg-info text-white'
                      : 'text-text-secondary hover:bg-background'
                  }`}
                >
                  <MapIcon className="w-4 h-4" />
                  <span className="text-sm font-medium">Map</span>
                </button>
              </div>
            </Card>

            {/* Property Gallery (List View) */}
            {viewMode === 'list' && (
            <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {isLoading ? (
                <Card className="p-6 text-center text-text-secondary">Loading properties…</Card>
              ) : sortedProperties.length === 0 ? (
                <Card className="p-6 text-center">
                  <div className="font-semibold text-text-primary mb-2">
                    {filtersApplied ? 'No properties match the current filters' : 'No properties available yet'}
                  </div>
                  <p className="text-text-secondary mb-3">
                    {filtersApplied ? 'Try clearing filters or search to see your properties.' : 'Add a property to get started.'}
                  </p>
                  <div className="flex justify-center gap-2">
                    {filtersApplied && (
                      <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                        Clear Filters
                      </Button>
                    )}
                    <Button variant="primary" size="sm" onClick={() => window.location.hash = 'add-property'}>
                      Add Property
                    </Button>
                  </div>
                </Card>
              ) : (
              sortedProperties.map((property) => {
                const isSelected = selectedProperty?.id === property.id;
                const isCompared = comparisonSet.has(property.id);
                const propertyMetric = propertyMetricsMap.get(property.id);
                const displayMetrics = isSelected && metrics ? metrics : null;
                const displayValue = displayMetrics?.value || propertyMetric?.total_assets || 0;
                const displayNoi = displayMetrics?.noi || propertyMetric?.net_operating_income || propertyMetric?.net_income || 0;
                const displayOccupancy = displayMetrics?.occupancy || propertyMetric?.occupancy_rate || 0;
                const displayDscr = displayMetrics?.dscr || propertyDscrMap.get(property.id) || propertyMetric?.dscr || null;
                const status = displayMetrics?.status || (displayOccupancy > 90 ? 'good' : displayOccupancy > 70 ? 'warning' : 'critical');
                const variant = getStatusVariant(status) as any;

                const occupancyPercent = Math.min(displayOccupancy, 100);
                const ltv = propertyMetric?.ltv_ratio ?? null;
                const docCount = availableDocuments.filter((d) => d.property_code === property.property_code).length;
                const alertsCount = alertCounts.get(property.id) ?? 0;

                return (
                  <Card
                    key={property.id}
                    variant={isSelected ? 'elevated' : 'default'}
                    className={`group relative p-4 cursor-pointer transition-all duration-200 overflow-hidden ${
                      isSelected ? 'ring-2 ring-info shadow-md' : 'hover:shadow-lg hover:-translate-y-0.5'
                    }`}
                    onClick={() => setSelectedProperty(property)}
                  >
                    {/* Comparison Checkbox (Top Left) - Visible on Hover or Checked */}
                    <div 
                      className={`absolute top-3 left-3 z-20 transition-opacity duration-200 ${isCompared ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Checkbox 
                        checked={isCompared} 
                        onChange={(e) => {
                          if (e.target.checked) addToComparison(property.id);
                          else removeFromComparison(property.id);
                        }}
                        className="bg-surface/80 backdrop-blur-sm rounded-sm"
                      />
                    </div>

                    {/* Header Section */}
                    <div className="flex justify-between items-start mb-3 pl-8"> 
                      <div className="flex gap-3">
                        <div className={`p-2 rounded-lg transition-colors ${isSelected ? 'bg-info/10 text-info' : 'bg-surface-hover text-text-secondary group-hover:bg-primary/5 group-hover:text-primary'}`}>
                          <Building2 className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-text-primary leading-tight transition-colors group-hover:text-primary">
                            {property.property_name}
                          </h4>
                          <div className="flex items-center gap-2 text-xs text-text-secondary mt-1">
                            <span className="font-mono bg-surface-hover px-1.5 py-0.5 rounded text-xs">{property.property_code}</span>
                            {docCount > 0 && <span className="flex items-center gap-0.5"><FileText className="w-3 h-3" /> {docCount}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-text-primary text-lg">
                          ${(displayValue / 1000000).toFixed(1)}M
                        </div>
                        <div className="text-xs text-text-secondary font-medium">
                          NOI <span className={displayNoi > 0 ? 'text-success' : ''}>${(displayNoi / 1000).toFixed(0)}K</span>
                          <span className="mx-1 text-border">|</span>
                          LTV {ltv ? `${(ltv * 100).toFixed(0)}%` : '-'}
                        </div>
                      </div>
                    </div>

                    {/* Occupancy Bar */}
                    <div className="space-y-1.5 mb-4">
                      <div className="flex justify-between text-xs items-end">
                        <span className="text-text-secondary font-medium">Occupancy</span>
                        <span className={`${
                          occupancyPercent >= 90 ? 'text-success' : occupancyPercent >= 75 ? 'text-warning' : 'text-danger'
                        } font-bold`}>{occupancyPercent.toFixed(0)}%</span>
                      </div>
                      <ProgressBar 
                        value={occupancyPercent} 
                        max={100} 
                        height="sm" 
                        variant={occupancyPercent >= 90 ? 'success' : occupancyPercent >= 75 ? 'warning' : 'danger'} 
                        className="opacity-80 group-hover:opacity-100 transition-opacity"
                      />
                    </div>

                    {/* Footer Metrics Grid */}
                    <div className="grid grid-cols-4 gap-2 text-center text-xs border-t border-border pt-3">
                        <div>
                             <div className="text-text-secondary mb-0.5">DSCR</div>
                             <div className={`font-semibold ${displayDscr && displayDscr < 1.15 ? 'text-danger' : ''}`}>
                                 {displayDscr ? displayDscr.toFixed(2) : '-'}
                             </div>
                        </div>
                        <div className="col-span-1">
                             <div className="text-text-secondary mb-0.5">Alerts</div>
                               {alertsCount > 0 ? (
                                   <div className="font-bold text-danger flex items-center justify-center gap-1">
                                       <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" /> {alertsCount}
                                   </div>
                               ) : (
                                   <div className="text-text-tertiary">-</div>
                               )}
                        </div>
                        <div className="col-span-1">
                             <div className="text-text-secondary mb-0.5">Trend</div>
                             <div className="h-4 flex items-end justify-center gap-0.5 opacity-60">
                                  {(displayMetrics?.trends?.noi || propertyMetric?.noi_trend || []).slice(-5).map((val: number, i: number, arr: number[]) => (
                                      <div key={i} className="w-0.5 bg-text-primary rounded-full" style={{ height: `${(val / (Math.max(...arr, 1))) * 100}%` }} />
                                  ))}
                             </div>
                        </div>
                        <div className="col-span-1 flex items-center justify-center">
                            <div className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
                                status === 'critical' ? 'bg-danger/10 text-danger' : 
                                status === 'warning' ? 'bg-warning/10 text-warning' : 
                                'bg-success/10 text-success'
                            }`}>
                                {status === 'critical' ? 'Risk' : status === 'warning' ? 'Watch' : 'Fine'}
                            </div>
                        </div>
                    </div>

                    {/* Hover Quick Actions Overlay */}
                    <div className="absolute inset-x-0 bottom-0 p-3 bg-surface/90 backdrop-blur-md border-t border-border flex items-center justify-between opacity-0 translate-y-2 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-200 z-10">
                        <div className="text-xs text-text-secondary font-medium">
                            {ltv ? `LTV: ${(ltv * 100).toFixed(0)}%` : 'No LTV'}
                        </div>
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-8 text-xs hover:bg-primary/10 hover:text-primary p-0 px-2"
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedProperty(property);
                            }}
                        >
                            View Details <ArrowRight className="ml-1 w-3 h-3" />
                        </Button>
                    </div>
                  </Card>
                );
              })
              )}
            </div>
            )}

            {/* Comparison Call-to-Action */}
            {comparisonSet.size > 1 && (
              <Card className="p-4 bg-surface border border-border space-y-3">
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="text-sm text-text-secondary">Compare Selected Properties</div>
                    <div className="text-lg font-semibold text-text-primary">{comparisonSet.size} selected</div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearComparison}
                    >
                      Clear
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={async () => {
                        const link = window.location.href.replace(/#.*$/, '') + '#compare';
                        try {
                          await navigator.clipboard.writeText(link);
                        } catch {
                          // noop
                        }
                      }}
                    >
                      Share link
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Sparkles className="w-4 h-4" />}
                      onClick={() => setShowComparisonModal(true)}
                    >
                      Side-by-Side View
                    </Button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr>
                        <th className="text-left py-2 pr-4 font-semibold text-text-secondary">Metric</th>
                        {properties.filter((p) => comparisonSet.has(p.id)).map((p) => (
                          <th key={p.id} className="text-left py-2 pr-4 font-semibold text-text-primary">
                            {p.property_code || p.property_name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {['Value', 'NOI', 'DSCR', 'LTV', 'Occupancy', 'Cap Rate', 'Docs', 'Alerts'].map((metric) => (
                        <tr key={metric} className="border-t border-border">
                          <td className="py-2 pr-4 font-medium text-text-primary">{metric}</td>
                          {properties.filter((p) => comparisonSet.has(p.id)).map((p) => {
                            const m = propertyMetricsMap.get(p.id);
                            const value = m?.total_assets || 0;
                            const noi = m?.net_operating_income || m?.net_income || 0;
                            const dscr = m?.dscr ?? null;
                            const ltv = m?.ltv_ratio ?? null;
                            const occ = m?.occupancy_rate ?? null;
                            const capRate = value > 0 ? (noi / value) * 100 : null;
                            const docs = availableDocuments.filter((d) => d.property_code === p.property_code).length;
                            const alerts = alertCounts.get(p.id) ?? 0;

                            let display = '—';
                            switch (metric) {
                              case 'Value':
                                display = value ? `$${(value / 1_000_000).toFixed(1)}M` : '—';
                                break;
                              case 'NOI':
                                display = noi ? `$${(noi / 1_000).toFixed(1)}K` : '—';
                                break;
                              case 'DSCR':
                                display = dscr !== null ? dscr.toFixed(2) : '—';
                                break;
                              case 'LTV':
                                display = ltv !== null ? `${(ltv * 100).toFixed(0)}%` : '—';
                                break;
                              case 'Occupancy':
                                display = occ !== null ? `${occ.toFixed(0)}%` : '—';
                                break;
                              case 'Cap Rate':
                                display = capRate !== null ? `${capRate.toFixed(1)}%` : '—';
                                break;
                              case 'Docs':
                                display = `${docs}`;
                                break;
                              case 'Alerts':
                                display = `${alerts}`;
                                break;
                            }

                            const statMap: Record<string, { min: number; max: number }> = {
                              'Value': comparisonStats.value,
                              'NOI': comparisonStats.noi,
                              'DSCR': comparisonStats.dscr,
                              'Occupancy': comparisonStats.occupancy,
                              'Cap Rate': comparisonStats.capRate,
                              'Docs': comparisonStats.docs,
                              'Alerts': comparisonStats.alerts,
                              'LTV': comparisonStats.ltv,
                            };
                            const invertHeat = metric === 'LTV';
                            const stat = statMap[metric];
                            let heatStyle: React.CSSProperties = {};
                            const numericVal = metric === 'Value' ? value
                              : metric === 'NOI' ? noi
                              : metric === 'DSCR' ? dscr
                              : metric === 'Occupancy' ? occ
                              : metric === 'Cap Rate' ? capRate
                              : metric === 'Docs' ? docs
                              : metric === 'Alerts' ? alerts
                              : metric === 'LTV' ? ltv
                              : null;
                            if (stat && numericVal !== null && stat.max !== stat.min) {
                              const ratio = (numericVal - stat.min) / (stat.max - stat.min);
                              const intensity = Math.max(0.08, Math.min(0.4, invertHeat ? 0.4 - ratio * 0.3 : 0.1 + ratio * 0.3));
                              heatStyle = { backgroundColor: `rgba(34,197,94,${intensity})` }; // green hue
                            }

                            const highlight = () => {
                              if (metric === 'LTV') {
                                if (ltv === comparisonStats.ltv.min) return 'bg-green-50 text-text-primary';
                                if (ltv === comparisonStats.ltv.max) return 'bg-red-50 text-text-primary';
                              } else if (metric === 'Docs') {
                                if (docs === comparisonStats.docs.max) return 'bg-green-50 text-text-primary';
                                if (docs === comparisonStats.docs.min) return 'bg-red-50 text-text-primary';
                              } else {
                                const map: Record<string, { min: number; max: number }> = {
                                  'Value': comparisonStats.value,
                                  'NOI': comparisonStats.noi,
                                  'DSCR': comparisonStats.dscr,
                                  'Occupancy': comparisonStats.occupancy,
                                  'Cap Rate': comparisonStats.capRate,
                                };
                                const val = metric === 'Value' ? value
                                  : metric === 'NOI' ? noi
                                  : metric === 'DSCR' ? dscr
                                  : metric === 'Occupancy' ? occ
                                  : metric === 'Cap Rate' ? capRate
                                  : null;
                                const stat = map[metric];
                                if (val !== null && stat) {
                                  if (val === stat.max) return 'bg-green-50 text-text-primary';
                                  if (val === stat.min) return 'bg-red-50 text-text-primary';
                                }
                              }
                              return '';
                            };

                            return (
                              <td key={p.id} className={`py-2 pr-4 text-text-secondary ${highlight()}`}>
                                <div className="flex flex-col gap-1" style={heatStyle}>
                                  <span>{display}</span>
                                  {['Value', 'NOI', 'Occupancy'].includes(metric) && numericVal !== null && stat && stat.max !== stat.min ? (
                                    <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full ${metric === 'NOI' ? 'bg-info' : 'bg-success'} rounded-full`}
                                        style={{ width: `${Math.max(6, (numericVal / stat.max) * 100)}%` }}
                                      />
                                    </div>
                                  ) : null}
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-3 text-xs text-text-secondary">
                    Alerts include active items from the last 90 days; shading highlights best/worst per metric.
                  </div>
                </div>
              </Card>
            )}

            {/* Side-by-Side Comparison Modal */}
          {showComparisonModal && comparisonProperties.length > 1 && (
            <div
              className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center px-4"
              role="dialog"
              aria-modal="true"
              aria-label="Property comparison modal"
              onClick={() => setShowComparisonModal(false)}
            >
              <div
                ref={comparisonModalRef}
                className="bg-surface rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <div>
                      <div className="text-sm text-text-secondary">Side-by-Side Comparison</div>
                      <div className="text-xl font-semibold text-text-primary">{comparisonProperties.length} properties</div>
                    </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setShowComparisonModal(false)} aria-label="Close comparison dialog">Close</Button>
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Download className="w-4 h-4" />}
                      aria-label="Export comparison table as CSV"
                        onClick={() => {
                          const header = ['Metric', ...comparisonProperties.map((p) => p.property_code || p.property_name)];
                          const rows = [
                            ['Value', ...comparisonProperties.map((p) => {
                              const m = propertyMetricsMap.get(p.id);
                              return m?.total_assets ? `$${(m.total_assets / 1_000_000).toFixed(1)}M` : '—';
                            })],
                            ['NOI', ...comparisonProperties.map((p) => {
                              const m = propertyMetricsMap.get(p.id);
                              return m?.net_operating_income ? `$${(m.net_operating_income / 1_000).toFixed(1)}K` : '—';
                            })],
                            ['DSCR', ...comparisonProperties.map((p) => {
                              const m = propertyMetricsMap.get(p.id);
                              return m?.dscr ? m.dscr.toFixed(2) : '—';
                            })],
                            ['LTV', ...comparisonProperties.map((p) => {
                              const m = propertyMetricsMap.get(p.id);
                              return m?.ltv_ratio ? `${(m.ltv_ratio * 100).toFixed(0)}%` : '—';
                            })],
                            ['Occupancy', ...comparisonProperties.map((p) => {
                              const m = propertyMetricsMap.get(p.id);
                              return m?.occupancy_rate ? `${m.occupancy_rate.toFixed(0)}%` : '—';
                            })],
                          ];
                          const csv = [header, ...rows].map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
                          try {
                            // Download CSV
                            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                            const url = URL.createObjectURL(blob);
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = 'property-comparison.csv';
                            link.click();
                            URL.revokeObjectURL(url);

                            // Copy to clipboard as a convenience
                            if (navigator?.clipboard?.writeText) {
                              navigator.clipboard.writeText(csv).catch(() => {});
                            }
                            alert('Comparison exported as CSV (also copied to clipboard when permitted).');
                          } catch (err) {
                            console.error('Failed to export comparison', err);
                            alert('Export failed. Please try again.');
                          }
                        }}
                      >
                        Export
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label="Copy comparison summary to clipboard"
                        onClick={() => {
                          const summary = comparisonProperties.map((p) => {
                            const m = propertyMetricsMap.get(p.id);
                            return `${p.property_name} (${p.property_code}) — Value ${m?.total_assets ? `$${(m.total_assets / 1_000_000).toFixed(1)}M` : '—'}, NOI ${m?.net_operating_income ? `$${(m.net_operating_income / 1_000).toFixed(1)}K` : '—'}, DSCR ${m?.dscr ?? '—'}`;
                          }).join('\n');
                          if (navigator?.clipboard?.writeText) {
                            navigator.clipboard.writeText(summary).catch(() => {});
                          }
                        }}
                      >
                        Copy Summary
                      </Button>
                  </div>
                </div>
                  <div className="p-6 overflow-auto max-h-[75vh]">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                      {comparisonProperties.map((p) => {
                        const m = propertyMetricsMap.get(p.id);
                        const value = m?.total_assets || 0;
                        const noi = m?.net_operating_income || m?.net_income || 0;
                        const occ = m?.occupancy_rate || 0;
                        const dscr = m?.dscr ?? null;
                        const ltv = m?.ltv_ratio ?? null;
                        const capRate = value > 0 ? (noi / value) * 100 : null;
                        const docCount = availableDocuments.filter((d) => d.property_code === p.property_code).length;
                        const trend = (m?.noi_trend || []).slice(-8);
                        const noiDelta = trend.length >= 2 ? trend[trend.length - 1] - trend[trend.length - 2] : null;
                        const sparkMax = Math.max(...trend, 1);
                        return (
                          <Card key={p.id} className="p-4 border border-border">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="text-lg font-semibold text-text-primary">{p.property_name}</div>
                                <div className="text-sm text-text-secondary">{p.property_code} • {p.city}, {p.state}</div>
                              </div>
                              <div className="text-sm text-text-secondary">
                                <div className="font-semibold text-text-primary">${(value / 1_000_000).toFixed(1)}M</div>
                                <div>NOI ${(noi / 1_000).toFixed(1)}K</div>
                              </div>
                            </div>
                            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                              <div className="p-2 rounded-lg bg-background">
                                <div className="text-xs text-text-secondary">DSCR</div>
                                <div className="font-semibold text-text-primary">{dscr !== null ? dscr.toFixed(2) : '—'}</div>
                              </div>
                              <div className="p-2 rounded-lg bg-background">
                                <div className="text-xs text-text-secondary">LTV</div>
                                <div className="font-semibold text-text-primary">{ltv !== null ? `${(ltv * 100).toFixed(0)}%` : '—'}</div>
                              </div>
                              <div className="p-2 rounded-lg bg-background">
                                <div className="text-xs text-text-secondary">Cap Rate</div>
                                <div className="font-semibold text-text-primary">{capRate !== null ? `${capRate.toFixed(1)}%` : '—'}</div>
                              </div>
                              <div className="p-2 rounded-lg bg-background">
                                <div className="text-xs text-text-secondary">Docs</div>
                                <div className="font-semibold text-text-primary">{docCount}</div>
                              </div>
                              <div className="col-span-2">
                                <div className="flex justify-between text-xs text-text-secondary">
                                  <span>Occupancy</span>
                                  <span className="font-semibold text-text-primary">{occ.toFixed(0)}%</span>
                                </div>
                                <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden mt-1">
                                  <div
                                    className="h-full bg-info rounded-full"
                                    style={{ width: `${Math.min(occ, 100)}%` }}
                                  />
                                </div>
                              </div>
                              <div className="col-span-2">
                                <div className="flex items-center justify-between text-xs text-text-secondary">
                                  <span>NOI Trend</span>
                                  {docCount > 0 && (
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-border text-[11px]">
                                      <FileText className="w-3 h-3" /> {docCount} docs
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-end gap-1 mt-1 h-10">
                                  {trend.length > 0 ? trend.map((val: number, i: number) => {
                                    const height = (val / sparkMax) * 100;
                                    return (
                                      <span key={i} className="flex-1 bg-info rounded-sm" style={{ height: `${Math.max(height, 6)}%` }} />
                                    );
                                  }) : (
                                    <span className="text-xs text-text-secondary">No trend data</span>
                                  )}
                                </div>
                                {noiDelta !== null && (
                                  <div className={`mt-1 text-xs font-medium ${noiDelta >= 0 ? 'text-success' : 'text-danger'}`}>
                                    {noiDelta >= 0 ? '↑' : '↓'} {Math.abs(noiDelta).toFixed(1)} (last period)
                                  </div>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr>
                            <th className="text-left py-2 pr-4 font-semibold text-text-secondary">Metric</th>
                            {comparisonProperties.map((p) => (
                              <th key={p.id} className="text-left py-2 pr-4 font-semibold text-text-primary">
                                {p.property_code || p.property_name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {['Value', 'NOI', 'DSCR', 'LTV', 'Occupancy'].map((metric) => (
                            <tr key={metric} className="border-t border-border">
                              <td className="py-2 pr-4 font-medium text-text-primary">{metric}</td>
                              {comparisonProperties.map((p) => {
                                const m = propertyMetricsMap.get(p.id);
                                let display = '—';
                                switch (metric) {
                                  case 'Value':
                                    display = m?.total_assets ? `$${(m.total_assets / 1_000_000).toFixed(1)}M` : '—';
                                    break;
                                  case 'NOI':
                                    display = m?.net_operating_income ? `$${(m.net_operating_income / 1_000).toFixed(1)}K` : '—';
                                    break;
                                  case 'DSCR':
                                    display = m?.dscr ? m.dscr.toFixed(2) : '—';
                                    break;
                                  case 'LTV':
                                    display = m?.ltv_ratio ? `${(m.ltv_ratio * 100).toFixed(0)}%` : '—';
                                    break;
                                  case 'Occupancy':
                                    display = m?.occupancy_rate ? `${m.occupancy_rate.toFixed(0)}%` : '—';
                                    break;
                                }
                                return (
                                  <td key={p.id} className="py-2 pr-4 text-text-secondary">
                                    {display}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Map View */}
            {viewMode === 'map' && (
              <div className="h-[calc(100vh-300px)]">
                <PropertyMap
                  properties={filteredProperties}
                  selectedProperty={selectedProperty}
                  onPropertySelect={setSelectedProperty}
                  height={700}
                />
              </div>
            )}
          </div>

          {/* Right Panel - Asset Details (70%) */}
          <div className="lg:col-span-7">
            {selectedProperty ? (
              <div className="space-y-6">
                {/* Property Header */}
                <Card className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <Building2 className="w-6 h-6 shrink-0" />
                        <InlineEdit
                          className="inline-edit-heading w-full"
                          displayClassName="w-full text-left"
                          inputClassName="w-full"
                          value={selectedProperty.property_name}
                          placeholder="Property name"
                          activation="double-click"
                          onSave={handlePropertyNameSave}
                        />
                      </div>
                      <p className="text-text-secondary mt-1">
                        {selectedProperty.property_code} • {selectedProperty.city}, {selectedProperty.state}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        variant="primary" 
                        size="sm" 
                        icon={<Edit className="w-4 h-4" />}
                        onClick={() => {
                          setEditingProperty(selectedProperty);
                          setShowCreateModal(true);
                        }}
                      >
                        Edit
                      </Button>
                      <Button 
                        className="bg-red-50 border-red-200 hover:bg-red-100/80 text-danger" 
                        size="sm" 
                        icon={<Trash2 className="w-4 h-4" />}
                        onClick={() => setPropertyToDelete(selectedProperty)}
                      >
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
                          <div className="w-32">
                            <Select
                              value={selectedYear.toString()}
                              onChange={(val) => setSelectedYear(parseInt(val))}
                              options={[2023, 2024, 2025, 2026, 2027].map(year => ({ value: year.toString(), label: year.toString() }))}
                            />
                          </div>
                          <div className="w-40">
                            <Select
                              value={selectedMonth.toString()}
                              onChange={(val) => setSelectedMonth(parseInt(val))}
                              options={Array.from({ length: 12 }, (_, i) => i + 1).map(month => ({
                                value: month.toString(),
                                label: new Date(2000, month - 1).toLocaleString('default', { month: 'long' })
                              }))}
                            />
                          </div>
                        </div>
                      </div>
                    </Card>

                    {/* Key Metrics */}
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Key Metrics</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard
                          title="Purchase Price"
                          value={`$${(((metrics?.value || costs?.initialBuying || 0)) / 1_000_000).toFixed(2)}M`}
                          loading={metricsLoading}
                          comparison="Original basis"
                        />
                        <MetricCard
                          title="Current Value"
                          value={`$${(((metrics?.value || 0)) / 1_000_000).toFixed(2)}M`}
                          loading={metricsLoading}
                          comparison="Latest valuation"
                          status="info"
                        />
                        <MetricCard
                          title="Hold Period"
                          value={
                            selectedProperty?.acquisition_date
                              ? (() => {
                                  const acqDate = new Date(selectedProperty.acquisition_date);
                                  const now = new Date();
                                  const months = (now.getFullYear() - acqDate.getFullYear()) * 12 + (now.getMonth() - acqDate.getMonth());
                                  return `${months} mo`;
                                })()
                              : 'N/A'
                          }
                          loading={metricsLoading}
                        />
                        <MetricCard
                          title="Cap Rate"
                          value={
                            metrics?.capRate !== null && metrics?.capRate !== undefined
                              ? `${metrics.capRate.toFixed(2)}%`
                              : metrics?.value && metrics?.noi
                                ? `${((metrics.noi / metrics.value) * 100).toFixed(2)}%`
                                : 'N/A'
                          }
                          loading={metricsLoading}
                          status="success"
                          comparison="NOI / Value"
                        />
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
                              ${((metrics?.noi || 0) / 1000).toFixed(1)}K / ${(((metrics?.noi || 0) * 1.25) / 1000).toFixed(1)}K target
                            </span>
                          </div>
                          <ProgressBar
                            value={metrics?.noi && metrics.noi > 0 ? ((metrics.noi / (metrics.noi * 1.25)) * 100) : 0}
                            max={100}
                            className="bg-green-50 border-green-200"
                            height="md"
                          />
                        </div>
                        <div>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm text-text-secondary">DSCR</span>
                            <span className="text-sm font-medium">
                              {(metrics?.dscr !== null && metrics?.dscr !== undefined) ? metrics.dscr.toFixed(2) : '0.00'} / 1.25 min
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
                            className="bg-green-50 border-green-200"
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
                            <div className="text-lg font-semibold">${(costs.initialBuying / 1000000).toFixed(2)}M</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Other Costs</div>
                            <div className="text-lg font-semibold">${(costs.other / 1000).toFixed(0)}K</div>
                          </div>
                          <div>
                            <div className="text-sm text-text-secondary">Total Annual Operating Expenses</div>
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
                          <div className="w-32">
                            <Select
                              value={selectedYear.toString()}
                              onChange={(val) => {
                                setSelectedYear(parseInt(val));
                                if (selectedProperty) {
                                  loadFinancialStatements(selectedProperty.property_code);
                                }
                              }}
                              options={[2023, 2024, 2025, 2026].map(year => ({ value: year.toString(), label: year.toString() }))}
                            />
                          </div>
                          <div className="w-40">
                            <Select
                              value={selectedMonth.toString()}
                              onChange={(val) => {
                                setSelectedMonth(parseInt(val));
                                if (selectedProperty) {
                                  loadFinancialStatements(selectedProperty.property_code);
                                }
                              }}
                              options={Array.from({ length: 12 }, (_, i) => i + 1).map(month => ({
                                value: month.toString(),
                                label: new Date(2000, month - 1).toLocaleString('default', { month: 'long' })
                              }))}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Statement Type Cards */}
                      <div className="grid grid-cols-4 gap-4 mb-6">
                        <Card
                          variant={selectedStatement === 'income' ? 'outlined' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'income' ? 'ring-2 ring-info' : ''}`}
                          onClick={async () => {
                            setSelectedStatement('income');
                            if (availableDocuments.length > 0) {
                              loadFinancialDocumentData('income_statement', availableDocuments);
                            } else if (selectedProperty) {
                              const docs = await loadAvailableDocuments(selectedProperty.property_code);
                              loadFinancialDocumentData('income_statement', docs);
                            }
                          }}
                          hoverable
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              // Trigger click logic if needed, but for now we just satisfy a11y
                            }
                          }}
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
                          variant={selectedStatement === 'balance' ? 'outlined' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'balance' ? 'ring-2 ring-info' : ''}`}
                          onClick={async () => {
                            setSelectedStatement('balance');
                            if (availableDocuments.length > 0) {
                              loadFinancialDocumentData('balance_sheet', availableDocuments);
                            } else if (selectedProperty) {
                              const docs = await loadAvailableDocuments(selectedProperty.property_code);
                              loadFinancialDocumentData('balance_sheet', docs);
                            }
                          }}
                          hoverable
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              // Trigger click logic if needed, but for now we just satisfy a11y
                            }
                          }}
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
                          variant={selectedStatement === 'cashflow' ? 'outlined' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'cashflow' ? 'ring-2 ring-info' : ''}`}
                          onClick={async () => {
                            setSelectedStatement('cashflow');
                            if (availableDocuments.length > 0) {
                              loadFinancialDocumentData('cash_flow', availableDocuments);
                            } else if (selectedProperty) {
                              const docs = await loadAvailableDocuments(selectedProperty.property_code);
                              loadFinancialDocumentData('cash_flow', docs);
                            }
                          }}
                          hoverable
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              // Trigger click logic if needed, but for now we just satisfy a11y
                            }
                          }}
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">💸</div>
                            <div className="font-semibold">Cash Flow</div>
                            <div className="text-sm text-text-secondary mt-1">
                              {selectedYear} - {new Date(2000, selectedMonth - 1).toLocaleString('default', { month: 'short' })}
                            </div>
                          </div>
                        </Card>
                        <Card
                          variant={selectedStatement === 'mortgage' ? 'outlined' : 'default'}
                          className={`p-4 cursor-pointer transition-all ${selectedStatement === 'mortgage' ? 'ring-2 ring-info' : ''}`}
                          onClick={async () => {
                            setSelectedStatement('mortgage');
                            if (availableDocuments.length > 0) {
                              loadFinancialDocumentData('mortgage_statement', availableDocuments);
                            } else if (selectedProperty) {
                              const docs = await loadAvailableDocuments(selectedProperty.property_code);
                              loadFinancialDocumentData('mortgage_statement', docs);
                            }
                          }}
                          hoverable
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              // Trigger click logic if needed, but for now we just satisfy a11y
                            }
                          }}
                        >
                          <div className="text-center">
                            <div className="text-2xl mb-2">🏦</div>
                            <div className="font-semibold">Mortgage Statement</div>
                            <div className="text-sm text-text-secondary mt-1">
                              {selectedYear} - {new Date(2000, selectedMonth - 1).toLocaleString('default', { month: 'short' })}
                            </div>
                          </div>
                        </Card>
                      </div>

                      {/* Mortgage Metrics Section */}
                      {selectedProperty && (
                        <div className="mb-6">
                          <h3 className="text-lg font-semibold mb-4">🏦 Mortgage Metrics</h3>
                          <MortgageMetricsWidget
                            propertyId={selectedProperty.id}
                            periodYear={selectedYear}
                            periodMonth={selectedMonth}
                          />
                        </div>
                      )}

                      {/* Financial Data Display */}
                      {selectedStatement === 'mortgage' ? (
                        /* Mortgage statement view - show detailed mortgage data */
                        <MortgageStatementDetails
                          propertyId={selectedProperty?.id || 0}
                          periodYear={selectedYear}
                          periodMonth={selectedMonth}
                        />
                      ) : loadingDocumentData ? (
                        <div className="text-center py-8">
                          <div className="text-text-secondary mb-2">Loading complete financial document data...</div>
                          <div className="text-xs text-text-tertiary">Fetching all line items with zero data loss</div>
                        </div>
                      ) : financialData && financialData.items && financialData.items.length > 0 ? (
                        /* Show detailed line items table */
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
                          {/* Summary view - Click button to load detailed data */}
                          <Card className="p-4 bg-info-light/10 border-info">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-info text-xl">ℹ️</span>
                                <div>
                                  <div className="font-semibold">Summary View</div>
                                  <div className="text-sm text-text-secondary">
                                    Click below to view all {financialStatements.balance_sheet?.total_line_items || 'detailed'} line items
                                  </div>
                                </div>
                              </div>
                              <button
                                onClick={async () => {
                                  if (!selectedProperty) return;

                                  const docTypeMap = {
                                    'income': 'income_statement' as const,
                                    'balance': 'balance_sheet' as const,
                                    'cashflow': 'cash_flow' as const,
                                    'mortgage': 'mortgage_statement' as const
                                  };

                                  console.log('Button clicked - loading detailed data for:', selectedStatement);

                                  // Ensure documents are loaded first
                                  let docs = availableDocuments;
                                  if (docs.length === 0) {
                                    console.log('Loading available documents first...');
                                    docs = await loadAvailableDocuments(selectedProperty.property_code);
                                  }

                                  console.log('Documents available:', docs.length);
                                  // Load detailed data with the documents
                                  await loadFinancialDocumentData(docTypeMap[selectedStatement], docs);
                                }}
                                disabled={loadingDocumentData}
                                className="px-4 py-2 bg-info text-white rounded-lg hover:bg-info/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {loadingDocumentData ? 'Loading...' : 'Load Detailed View'}
                              </button>
                            </div>
                          </Card>

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
                                    ${(financialStatements.income_statement.total_expenses || financialStatements.income_statement.total_operating_expenses || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                                      {/* Backend returns operating_margin as percentage (already × 100), so display as-is */}
                                      {typeof financialStatements.income_statement.operating_margin === 'number'
                                        ? financialStatements.income_statement.operating_margin.toFixed(1)
                                        : '0.0'}%
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
                        {/* Executive Summary - Top Priority */}
                        <Card variant="glass" className="p-8 mb-6">
                          <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                              <Sparkles className="w-6 h-6 text-premium" />
                              <h2 className="text-2xl font-bold">Executive Market Summary</h2>
                            </div>
                            <Button
                              variant="primary"
                              onClick={() => {
                                if (selectedProperty) {
                                  window.location.hash = `market-intelligence/${selectedProperty.property_code}`;
                                }
                              }}
                            >
                              Full Market Dashboard
                            </Button>
                          </div>

                          {/* Key Performance Indicators - Most Critical Metrics */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
                            {/* Performance vs Market */}
                            <div className="text-center p-6 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border-2 border-blue-200">
                              <div className="text-sm font-semibold text-blue-700 mb-2">PERFORMANCE VS MARKET</div>
                              <div className="text-4xl font-bold mb-2">
                                {marketIntel.yourCapRate > 0 && marketIntel.marketCapRate > 0 ? (
                                  <span className={marketIntel.yourCapRate > marketIntel.marketCapRate ? 'text-green-600' : 'text-orange-600'}>
                                    {marketIntel.yourCapRate > marketIntel.marketCapRate ? '+' : ''}
                                    {((marketIntel.yourCapRate - marketIntel.marketCapRate) / marketIntel.marketCapRate * 100).toFixed(1)}%
                                  </span>
                                ) : 'N/A'}
                              </div>
                              <div className="text-xs text-blue-600">
                                Your Cap: {marketIntel.yourCapRate}% vs Market: {marketIntel.marketCapRate}%
                              </div>
                            </div>

                            {/* Market Position */}
                            <div className="text-center p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border-2 border-purple-200">
                              <div className="text-sm font-semibold text-purple-700 mb-2">LOCATION QUALITY</div>
                              <div className="text-4xl font-bold mb-2">
                                <span className={
                                  locationScore >= 8 ? 'text-green-600' :
                                  locationScore >= 6 ? 'text-blue-600' :
                                  locationScore >= 4 ? 'text-orange-600' : 'text-red-600'
                                }>
                                  {marketIntel.locationScore !== null ? `${marketIntel.locationScore}/10` : 'N/A'}
                                </span>
                              </div>
                              <div className="text-xs text-purple-600">
                                {marketIntel.locationScore !== null
                                  ? (locationScore >= 8 ? 'Premium Location' :
                                     locationScore >= 6 ? 'Strong Location' :
                                     locationScore >= 4 ? 'Average Location' : 'Below Average')
                                  : 'Data unavailable'}
                              </div>
                            </div>

                            {/* Growth Potential */}
                            <div className="text-center p-6 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border-2 border-green-200">
                              <div className="text-sm font-semibold text-green-700 mb-2">RENT GROWTH POTENTIAL</div>
                              <div className="text-4xl font-bold mb-2">
                                {marketIntel.rentGrowth !== null ? (
                                  <span className={marketIntel.rentGrowth >= 5 ? 'text-green-600' : marketIntel.rentGrowth >= 2 ? 'text-blue-600' : 'text-orange-600'}>
                                    +{marketIntel.rentGrowth}%
                                  </span>
                                ) : (
                                  <span className="text-gray-400">N/A</span>
                                )}
                              </div>
                              <div className="text-xs text-green-600">
                                {marketIntel.rentGrowth !== null
                                  ? `Market YoY Growth`
                                  : 'Insufficient data'}
                              </div>
                            </div>
                          </div>

                          {/* AI Strategic Insights - Executive Level */}
                          {marketIntel.aiInsights.length > 0 && (
                            <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded-r-lg">
                              <div className="flex items-center gap-2 mb-3">
                                <Sparkles className="w-5 h-5 text-indigo-600" />
                                <h4 className="font-bold text-indigo-900">Strategic Recommendation</h4>
                              </div>
                              <div className="text-sm text-indigo-800 font-medium">
                                {marketIntel.aiInsights[0]}
                              </div>
                            </div>
                          )}
                        </Card>

                        {/* Market Comparison - Secondary Priority */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                          {/* Competitive Position */}
                          <Card className="p-6">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                              <TrendingUp className="w-5 h-5 text-success" />
                              Competitive Position
                            </h3>
                            <div className="space-y-4">
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <span className="text-sm font-medium">Your Cap Rate</span>
                                <span className="text-lg font-bold text-blue-600">{marketIntel.yourCapRate}%</span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <span className="text-sm font-medium">Market Average</span>
                                <span className="text-lg font-bold">{marketIntel.marketCapRate}%</span>
                              </div>
                              {marketIntel.rentGrowth !== null && (
                                <>
                                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                    <span className="text-sm font-medium">Your Rent Growth</span>
                                    <span className={`text-lg font-bold ${marketIntel.yourRentGrowth >= marketIntel.rentGrowth ? 'text-green-600' : 'text-orange-600'}`}>
                                      +{marketIntel.yourRentGrowth}%
                                    </span>
                                  </div>
                                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                    <span className="text-sm font-medium">Market Rent Growth</span>
                                    <span className="text-lg font-bold">+{marketIntel.rentGrowth}%</span>
                                  </div>
                                </>
                              )}
                            </div>
                          </Card>

                          {/* Market Demographics - Decision Context */}
                          <Card className="p-6">
                            <h3 className="text-lg font-semibold mb-4">Market Demographics</h3>
                            {marketIntel.demographics.dataSource && (
                              <div className="text-xs text-text-secondary mb-3">
                                Source: {marketIntel.demographics.dataSource}
                              </div>
                            )}
                            <div className="space-y-4">
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <span className="text-sm font-medium">Population Density</span>
                                <span className="text-lg font-bold">
                                  {marketIntel.demographics.population !== null
                                    ? marketIntel.demographics.population.toLocaleString()
                                    : 'N/A'}
                                </span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <span className="text-sm font-medium">Median Income</span>
                                <span className="text-lg font-bold">
                                  {marketIntel.demographics.medianIncome !== null
                                    ? `$${marketIntel.demographics.medianIncome.toLocaleString()}`
                                    : 'N/A'}
                                </span>
                              </div>
                              <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <span className="text-sm font-medium">Economic Base</span>
                                <span className="text-sm font-semibold">
                                  {marketIntel.demographics.employmentType || 'N/A'}
                                </span>
                              </div>
                            </div>
                          </Card>
                        </div>

                        {/* Comparable Properties - Supporting Detail */}
                        <Card className="p-6">
                          <h3 className="text-lg font-semibold mb-4">Competitive Set (2-mile radius)</h3>
                          <div className="space-y-3">
                            {marketIntel.comparables.length > 0 ? (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {marketIntel.comparables.map((comp, i) => (
                                  <div key={i} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                                    <div className="flex items-center justify-between mb-3">
                                      <div className="font-semibold text-gray-900">{comp.name}</div>
                                      <div className="text-xs text-gray-500 bg-white px-2 py-1 rounded">{comp.distance} mi</div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                      <div className="bg-white p-2 rounded text-center">
                                        <div className="text-xs text-gray-500">Cap Rate</div>
                                        <div className="text-lg font-bold text-blue-600">{comp.capRate}%</div>
                                      </div>
                                      <div className="bg-white p-2 rounded text-center">
                                        <div className="text-xs text-gray-500">Occupancy</div>
                                        <div className="text-lg font-bold text-green-600">{comp.occupancy}%</div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="text-text-secondary text-center py-8 bg-gray-50 rounded-lg">
                                No comparable properties identified within 2-mile radius
                              </div>
                            )}
                          </div>
                        </Card>

                        {/* Additional AI Insights - If More Available */}
                        {marketIntel.aiInsights.length > 1 && (
                          <Card className="bg-blue-50 border-blue-200 p-6 mt-6">
                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                              <Sparkles className="w-5 h-5 text-info" />
                              Additional Market Insights
                            </h3>
                            <div className="space-y-3">
                              {marketIntel.aiInsights.slice(1).map((insight, i) => (
                                <div key={i} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                                  <span className="text-info text-xl">💡</span>
                                  <span className="text-sm flex-1 text-gray-700">{insight}</span>
                                </div>
                              ))}
                            </div>
                          </Card>
                        )}
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
                    {/* All Tenants Table */}
                    <Card className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold">All Tenants</h3>
                        {tenantDetails.length > 0 && (
                          <div className="text-sm text-text-secondary">
                            Period: {tenantDetails[0]?.period_year}/{String(tenantDetails[0]?.period_month).padStart(2, '0')} • Total: {tenantDetails.length} tenants
                          </div>
                        )}
                      </div>
                      {loadingTenants ? (
                        <div className="py-8 text-center text-text-secondary">Loading tenant data...</div>
                      ) : tenantDetails.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border bg-premium-light/10">
                                <th className="text-left py-3 px-4 font-semibold">Unit #</th>
                                <th className="text-left py-3 px-4 font-semibold">Tenant Name</th>
                                <th className="text-left py-3 px-4 font-semibold">Tenant Code</th>
                                <th className="text-left py-3 px-4 font-semibold">Lease Type</th>
                                <th className="text-left py-3 px-4 font-semibold">Lease Start</th>
                                <th className="text-left py-3 px-4 font-semibold">Lease End</th>
                                <th className="text-right py-3 px-4 font-semibold">Term (Months)</th>
                                <th className="text-right py-3 px-4 font-semibold">Remaining (Yrs)</th>
                                <th className="text-right py-3 px-4 font-semibold">Sq Ft</th>
                                <th className="text-right py-3 px-4 font-semibold">Monthly Rent</th>
                                <th className="text-right py-3 px-4 font-semibold">Rent/SqFt</th>
                                <th className="text-right py-3 px-4 font-semibold">Annual Rent</th>
                                <th className="text-right py-3 px-4 font-semibold">Annual Rent/SqFt</th>
                                <th className="text-right py-3 px-4 font-semibold">Gross Rent</th>
                                <th className="text-right py-3 px-4 font-semibold">Security Deposit</th>
                                <th className="text-right py-3 px-4 font-semibold">LOC Amount</th>
                                <th className="text-right py-3 px-4 font-semibold">CAM Reimb.</th>
                                <th className="text-right py-3 px-4 font-semibold">Tax Reimb.</th>
                                <th className="text-right py-3 px-4 font-semibold">Insurance Reimb.</th>
                                <th className="text-right py-3 px-4 font-semibold">Tenancy (Yrs)</th>
                                <th className="text-right py-3 px-4 font-semibold">Recoveries/SF</th>
                                <th className="text-right py-3 px-4 font-semibold">Misc/SF</th>
                                <th className="text-left py-3 px-4 font-semibold">Occupancy</th>
                                <th className="text-left py-3 px-4 font-semibold">Lease Status</th>
                                <th className="text-left py-3 px-4 font-semibold">Notes</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tenantDetails.map((tenant) => (
                                <tr key={tenant.id} className="border-b border-border/50 hover:bg-premium-light/5">
                                  <td className="py-2 px-4 font-medium">{tenant.unit_number || '-'}</td>
                                  <td className="py-2 px-4">{tenant.tenant_name || '-'}</td>
                                  <td className="py-2 px-4 text-text-secondary">{tenant.tenant_code || '-'}</td>
                                  <td className="py-2 px-4">{tenant.lease_type || '-'}</td>
                                  <td className="py-2 px-4">{tenant.lease_start_date || '-'}</td>
                                  <td className="py-2 px-4">{tenant.lease_end_date || '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.lease_term_months || '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.remaining_lease_years ? tenant.remaining_lease_years.toFixed(2) : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.unit_area_sqft ? tenant.unit_area_sqft.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.monthly_rent ? `$${tenant.monthly_rent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.monthly_rent_per_sqft ? `$${tenant.monthly_rent_per_sqft.toFixed(2)}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_rent ? `$${tenant.annual_rent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_rent_per_sqft ? `$${tenant.annual_rent_per_sqft.toFixed(2)}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.gross_rent ? `$${tenant.gross_rent.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.security_deposit ? `$${tenant.security_deposit.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.loc_amount ? `$${tenant.loc_amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_cam_reimbursement ? `$${tenant.annual_cam_reimbursement.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_tax_reimbursement ? `$${tenant.annual_tax_reimbursement.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_insurance_reimbursement ? `$${tenant.annual_insurance_reimbursement.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.tenancy_years ? tenant.tenancy_years.toFixed(2) : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_recoveries_per_sf ? `$${tenant.annual_recoveries_per_sf.toFixed(2)}` : '-'}</td>
                                  <td className="text-right py-2 px-4">{tenant.annual_misc_per_sf ? `$${tenant.annual_misc_per_sf.toFixed(2)}` : '-'}</td>
                                  <td className="py-2 px-4">
                                    <span className={`px-2 py-1 rounded text-xs ${
                                      tenant.occupancy_status === 'occupied' ? 'bg-success-light text-success' :
                                      tenant.occupancy_status === 'vacant' ? 'bg-warning-light text-warning' :
                                      'bg-text-secondary/20 text-text-secondary'
                                    }`}>
                                      {tenant.occupancy_status || '-'}
                                    </span>
                                  </td>
                                  <td className="py-2 px-4">
                                    <span className={`px-2 py-1 rounded text-xs ${
                                      tenant.lease_status === 'active' ? 'bg-info-light text-info' :
                                      tenant.lease_status === 'expired' ? 'bg-warning-light text-warning' :
                                      'bg-text-secondary/20 text-text-secondary'
                                    }`}>
                                      {tenant.lease_status || '-'}
                                    </span>
                                  </td>
                                  <td className="py-2 px-4 text-text-secondary text-xs max-w-xs truncate" title={tenant.notes || ''}>
                                    {tenant.notes || '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="py-8 text-center text-text-secondary">
                          No tenant data available for this property.
                        </div>
                      )}
                    </Card>

                    {/* Tenant Mix Summary */}
                    {unitInfo && tenantMix.length > 0 && (
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
                              {tenantMix.map((mix, index) => (
                                <tr key={index} className="border-b border-border/50 last:border-0">
                                  <td className="py-2 px-4">{mix.tenantType}</td>
                                  <td className="text-right py-2 px-4">{mix.unitCount}</td>
                                  <td className="text-right py-2 px-4">{mix.totalSqft.toLocaleString()}</td>
                                  <td className="text-right py-2 px-4">${(mix.totalRevenue / 12).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                  <td className="py-2 px-4">{mix.occupancyPct.toFixed(0)}% occupied</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </Card>
                    )}

                    {/* AI Tenant Matching */}
                    {tenantMatches.length > 0 && (
                      <Card className="bg-green-50 border-green-200 p-6">
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
                                <Button className="bg-green-50 border-green-200" size="sm">Contact Tenant</Button>
                                <Button variant="primary" size="sm">Schedule Tour</Button>
                                <Button className="bg-blue-50 border-blue-200" size="sm">View Profile</Button>
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
                <h3 className="text-xl font-semibold mb-2">
                  {properties.length === 0 ? 'No Properties Found' : 'No Property Selected'}
                </h3>
                <p className="text-text-secondary mb-4">
                  {properties.length === 0
                    ? 'Add a property to start managing your portfolio.'
                    : 'Select a property from the list to view details.'}
                </p>
                <div className="flex justify-center gap-2">
                  {filtersApplied && properties.length > 0 && (
                    <Button variant="ghost" onClick={handleClearFilters}>
                      Clear Filters
                    </Button>
                  )}
                  <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => window.location.hash = 'add-property'}>
                    Add Property
                  </Button>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Advanced Filter Modal */}
      {showAdvancedFilter && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAdvancedFilter(false)}>
          <Card className="max-w-2xl w-full m-4 p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Filter className="w-5 h-5" /> Advanced Filters
            </h2>
            <div className="space-y-4">
               <div className="grid grid-cols-2 gap-4">
                  <Input 
                    label="Min NOI ($)" 
                    placeholder="e.g. 50000" 
                    value={tempFilters.minNOI}
                    onChange={(e) => setTempFilters({...tempFilters, minNOI: e.target.value})}
                    type="number"
                  />
                  <Input 
                    label="Min Occupancy (%)" 
                    placeholder="e.g. 90" 
                    value={tempFilters.minOccupancy}
                    onChange={(e) => setTempFilters({...tempFilters, minOccupancy: e.target.value})}
                    type="number"
                  />
               </div>
               <div className="grid grid-cols-2 gap-4">
                  <Input 
                    label="Min Units" 
                    placeholder="e.g. 10" 
                    value={tempFilters.minUnits}
                    onChange={(e) => setTempFilters({...tempFilters, minUnits: e.target.value})}
                    type="number"
                  />
                  <Input 
                    label="Max LTV (%)" 
                    placeholder="e.g. 75" 
                    value={tempFilters.maxLTV}
                    onChange={(e) => setTempFilters({...tempFilters, maxLTV: e.target.value})}
                    type="number"
                  />
               </div>
               <div>
                  <label className="block text-sm font-medium mb-1">Property Tags</label>
                  <div className="flex flex-wrap gap-2">
                     {['Distressed', 'Value Add', 'Stabilized', 'Student Housing'].map(tag => (
                        <div 
                          key={tag} 
                          onClick={() => toggleTag(tag)}
                          className={`px-3 py-1 border rounded-full text-sm cursor-pointer transition-colors ${
                              tempFilters.tags.includes(tag) 
                              ? 'bg-primary text-white border-primary' 
                              : 'bg-surface hover:bg-surface-hover text-text-secondary'
                          }`}
                        >
                          {tag}
                        </div>
                     ))}
                  </div>
               </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
               <Button variant="ghost" onClick={() => setShowAdvancedFilter(false)}>Cancel</Button>
               <Button variant="primary" onClick={handleApplyAdvancedFilters}>Apply Filters</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Comparison Modal */}
      {showComparisonModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowComparisonModal(false)}>
           <Card className="max-w-6xl w-full max-h-[90vh] overflow-y-auto m-4 p-6" onClick={(e) => e.stopPropagation()}>
             <div className="flex justify-between items-center mb-6">
               <h2 className="text-2xl font-bold flex items-center gap-2">
                 <Sparkles className="w-6 h-6 text-info" /> Property Comparison
               </h2>
               <Button variant="ghost" onClick={() => setShowComparisonModal(false)}>Close</Button>
             </div>
             <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr>
                      <th className="text-left py-2 pr-4 font-semibold text-text-secondary">Metric</th>
                      {comparisonProperties.map((p) => (
                        <th key={p.id} className="text-left py-2 pr-4 font-semibold text-text-primary">
                          {p.property_code || p.property_name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {['Value', 'NOI', 'DSCR', 'LTV', 'Occupancy', 'Cap Rate', 'Docs', 'Alerts'].map((metric) => (
                      <tr key={metric} className="border-t border-border">
                        <td className="py-2 pr-4 font-medium text-text-primary">{metric}</td>
                        {comparisonProperties.map((p) => {
                          const m = propertyMetricsMap.get(p.id);
                          const value = m?.total_assets || 0;
                          const noi = m?.net_operating_income || m?.net_income || 0;
                          const dscr = m?.dscr ?? null;
                          const ltv = m?.ltv_ratio ?? null;
                          const occ = m?.occupancy_rate ?? null;
                          const capRate = value > 0 ? (noi / value) * 100 : null;
                          const docs = availableDocuments.filter((d) => d.property_code === p.property_code).length;
                          const alerts = alertCounts.get(p.id) ?? 0;

                          let display = '—';
                          switch (metric) {
                            case 'Value': display = value ? `$${(value / 1_000_000).toFixed(1)}M` : '—'; break;
                            case 'NOI': display = noi ? `$${(noi / 1_000).toFixed(1)}K` : '—'; break;
                            case 'DSCR': display = dscr !== null ? dscr.toFixed(2) : '—'; break;
                            case 'LTV': display = ltv !== null ? `${(ltv * 100).toFixed(0)}%` : '—'; break;
                            case 'Occupancy': display = occ !== null ? `${occ.toFixed(0)}%` : '—'; break;
                            case 'Cap Rate': display = capRate !== null ? `${capRate.toFixed(1)}%` : '—'; break;
                            case 'Docs': display = `${docs}`; break;
                            case 'Alerts': display = `${alerts}`; break;
                          }

                          const statMap: Record<string, { min: number; max: number }> = {
                            'Value': comparisonStats.value,
                            'NOI': comparisonStats.noi,
                            'DSCR': comparisonStats.dscr,
                            'Occupancy': comparisonStats.occupancy,
                            'Cap Rate': comparisonStats.capRate,
                            'Docs': comparisonStats.docs,
                            'Alerts': comparisonStats.alerts,
                            'LTV': comparisonStats.ltv,
                          };
                          const invertHeat = metric === 'LTV' || metric === 'Alerts';
                          const stat = statMap[metric];
                          let heatStyle: React.CSSProperties = {};
                          const numericVal = metric === 'Value' ? value
                            : metric === 'NOI' ? noi
                            : metric === 'DSCR' ? dscr
                            : metric === 'Occupancy' ? occ
                            : metric === 'Cap Rate' ? capRate
                            : metric === 'Docs' ? docs
                            : metric === 'Alerts' ? alerts
                            : metric === 'LTV' ? ltv
                            : null;
                          if (stat && numericVal !== null && stat.max !== stat.min) {
                            const ratio = (numericVal - stat.min) / (stat.max - stat.min);
                            const intensity = Math.max(0.08, Math.min(0.4, invertHeat ? 0.4 - ratio * 0.3 : 0.1 + ratio * 0.3));
                            heatStyle = { backgroundColor: `rgba(34,197,94,${intensity})` };
                             if (invertHeat && numericVal >= stat.max * 0.9) heatStyle = { backgroundColor: 'rgba(239,68,68,0.2)' }; // Critical Red
                          }

                          return (
                            <td key={p.id} className="py-2 pr-4 text-text-secondary">
                              <div className="flex flex-col gap-1 p-2 rounded" style={heatStyle}>
                                <span>{display}</span>
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
             </div>
           </Card>
        </div>
      )}

      {/* Modals */}
      {showCreateModal && (
        <PropertyFormModal
          property={editingProperty || undefined}
          onClose={() => {
            setShowCreateModal(false);
            setEditingProperty(null);
          }}
          onSuccess={() => {
            setShowCreateModal(false);
            setEditingProperty(null);
            loadProperties();
          }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {propertyToDelete && (
        <DeletePropertyModal
          property={propertyToDelete}
          onClose={() => setPropertyToDelete(null)}
          onSuccess={() => {
            // Remove from local state
            setProperties(prev => prev.filter(p => p.id !== propertyToDelete.id));
            
            // Select first available or null logic
            // We need to act on the *next* state, but here we calculate based on current
            const remaining = properties.filter(p => p.id !== propertyToDelete.id);
            setSelectedProperty(remaining.length > 0 ? remaining[0] : null);
            
            setPropertyToDelete(null);
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
      // Ensure property_code is uppercase and matches format
      const normalizedCode = formData.property_code.toUpperCase().trim();
      const codePattern = /^[A-Z]{2,5}\d{3}$/;
      
      if (!codePattern.test(normalizedCode)) {
        setError('Property code must be 2-5 uppercase letters followed by 3 digits (e.g., ESP001, TES121)');
        setLoading(false);
        return;
      }

      const submitData = {
        ...formData,
        property_code: normalizedCode
      };

      if (isEditing && property) {
        await propertyService.updateProperty(property.id, submitData);
      } else {
        await propertyService.createProperty(submitData);
      }
      onSuccess();
    } catch (err: any) {
      setError(formatErrorMessage(err) || 'Operation failed');
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
              <Input
                label="Property Code"
                required
                value={formData.property_code}
                onChange={(e) => {
                  const value = e.target.value.toUpperCase().replace(/\s/g, '');
                  setFormData({ ...formData, property_code: value });
                }}
                disabled={isEditing}
                placeholder="ESP001"
                helperText="Format: 2-5 uppercase letters followed by 3 digits"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="Property Name"
                required
                value={formData.property_name}
                onChange={(e) => setFormData({ ...formData, property_name: e.target.value })}
                fullWidth
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <Select
                label="Property Type"
                value={formData.property_type}
                onChange={(val) => setFormData({ ...formData, property_type: val })}
                options={[
                  { value: 'Retail', label: 'Retail' },
                  { value: 'Office', label: 'Office' },
                  { value: 'Industrial', label: 'Industrial' },
                  { value: 'Mixed Use', label: 'Mixed Use' },
                  { value: 'Multifamily', label: 'Multifamily' },
                  { value: 'Commercial', label: 'Commercial' },
                ]}
                placeholder="Select type..."
              />
            </div>

            <div>
              <Input
                label="Total Area (sqft)"
                type="number"
                value={formData.total_area_sqft || ''}
                onChange={(e) => setFormData({ ...formData, total_area_sqft: e.target.value ? Number(e.target.value) : undefined })}
                min={0}
                fullWidth
              />
            </div>
          </div>

          <div className="mb-4">
            <Input
              label="Address"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              fullWidth
            />
          </div>

          <div className="grid grid-cols-4 gap-4 mb-4">
            <div>
              <Input
                label="City"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                fullWidth
              />
            </div>

            <div>
              <Input
                label="State"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                maxLength={2}
                placeholder="NC"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="ZIP Code"
                value={formData.zip_code}
                onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                fullWidth
              />
            </div>

            <div>
              <Input
                label="Country"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                placeholder="USA"
                fullWidth
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <Input
                label="Acquisition Date"
                type="date"
                value={formData.acquisition_date}
                onChange={(e) => setFormData({ ...formData, acquisition_date: e.target.value })}
                fullWidth
              />
            </div>

            <div>
              <Select
                label="Status"
                value={formData.status}
                onChange={(val) => setFormData({ ...formData, status: val })}
                options={[
                  { value: 'active', label: 'Active' },
                  { value: 'sold', label: 'Sold' },
                  { value: 'under_contract', label: 'Under Contract' },
                ]}
              />
            </div>
          </div>

          <div className="mb-4">
            <Input
              label="Ownership Structure"
              value={formData.ownership_structure}
              onChange={(e) => setFormData({ ...formData, ownership_structure: e.target.value })}
              placeholder="LLC, Partnership, etc."
              fullWidth
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
            <Button className="bg-red-50 border-red-200" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={loading} loading={loading}>
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Delete Confirmation Modal Component
function DeletePropertyModal({
  property,
  onClose,
  onSuccess,
}: {
  property: Property;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDelete = async () => {
    setLoading(true);
    setError('');
    try {
      await propertyService.deleteProperty(property.property_code);
      onSuccess();
    } catch (err: any) {
      console.error('Delete error:', err);
      if (err?.status === 401) {
        setError('Session expired. Redirecting to login...');
        setTimeout(() => logout(), 1500); // Give user a moment to see the message
      } else if (err?.status === 403) {
         setError('Access Denied: You do not have permission to delete this property.');
      } else {
         setError(err?.message || 'Failed to delete property. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto w-full h-full p-4" onClick={onClose} aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div className="bg-surface rounded-xl p-6 max-w-md w-full mx-auto shadow-2xl scale-100 transform transition-transform" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-danger flex items-center gap-2" id="modal-title">
             <Trash2 className="w-5 h-5" /> Delete Property
          </h2>
          <button className="text-text-secondary hover:text-text-primary text-xl" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="relative">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-danger rounded-lg text-sm flex items-start gap-2 animate-in fade-in slide-in-from-top-2 duration-200">
                <span className="mt-0.5">⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <div className="mb-6">
              <p className="text-text-primary mb-2">
                Are you sure you want to delete <span className="font-semibold text-text-primary bg-surface-hover px-1 rounded">{property.property_name}</span>?
              </p>
              <p className="text-sm text-text-secondary bg-warning-light/30 p-3 rounded-lg border border-warning/20">
                <strong className="text-warning-dark block mb-1">Warning:</strong>
                This action cannot be undone. All associated data including financial records, tenant information, and documents will be permanently removed.
              </p>
            </div>

            <div className="flex gap-3 justify-end pt-2">
              <Button variant="ghost" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button 
                className="bg-danger text-white hover:bg-danger-hover border-danger focus:ring-danger/30" 
                onClick={handleDelete} 
                disabled={loading} 
                loading={loading}
              >
                {loading ? 'Deleting...' : 'Delete Property'}
              </Button>
            </div>
        </div>
      </div>
    </div>
  );
}
