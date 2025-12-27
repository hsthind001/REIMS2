import { useState, useEffect } from 'react';
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
  TrendingUp
} from 'lucide-react';
import { Card, Button, ProgressBar } from '../components/design-system';
import { PropertyMap } from '../components/PropertyMap';
import { propertyService } from '../lib/property';
import { reportsService } from '../lib/reports';
import { documentService } from '../lib/document';
import { financialDataService } from '../lib/financial_data';
import { DocumentUpload } from '../components/DocumentUpload';
import { MortgageMetricsWidget } from '../components/mortgage/MortgageMetricsWidget';
import { exportPropertyListToCSV, exportPropertyListToExcel } from '../lib/exportUtils';
import type { Property, PropertyCreate, DocumentUpload as DocumentUploadType } from '../types/api';
import type { FinancialDataItem, FinancialDataResponse } from '../lib/financial_data';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

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
  const [propertyDscrMap, setPropertyDscrMap] = useState<Map<number, number | null>>(new Map());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [financialData, setFinancialData] = useState<FinancialDataResponse | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentUploadType[]>([]);
  const [loadingDocumentData, setLoadingDocumentData] = useState(false);
  const [tenantMix, setTenantMix] = useState<any[]>([]);
  const [tenantDetails, setTenantDetails] = useState<any[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');

  useEffect(() => {
    loadProperties();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadPropertyDetails(selectedProperty.id);
      loadFinancialStatements(selectedProperty.property_code);
      loadTenantMix(selectedProperty.id);
      loadTenantDetails(selectedProperty.id);
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
        
        // Fetch DSCR for all properties using the actual API endpoint
        const dscrMap = new Map<number, number | null>();
        const dec2024PeriodIdMap: Record<string, number> = {
          'ESP001': 2,
          'HMND001': 4,
          'TCSH001': 9,
          'WEND001': 6
        };
        
        // Fetch DSCR for each property in parallel
        const dscrPromises = props.map(async (prop) => {
          try {
            const periodIdToUse = dec2024PeriodIdMap[prop.property_code] || metricsMap.get(prop.id)?.period_id;
            const periodIdParam = periodIdToUse ? `?financial_period_id=${periodIdToUse}` : '';
            
            const dscrResponse = await fetch(`${API_BASE_URL}/risk-alerts/properties/${prop.id}/dscr/calculate${periodIdParam}`, {
              method: 'POST',
              credentials: 'include'
            });
            
            if (dscrResponse.ok) {
              const dscrData = await dscrResponse.json();
              if (dscrData.success && dscrData.dscr !== null && dscrData.dscr !== undefined) {
                dscrMap.set(prop.id, dscrData.dscr);
                return;
              }
            }
            // If API fails, set to null (don't show DSCR)
            dscrMap.set(prop.id, null);
          } catch (err) {
            console.error(`Failed to fetch DSCR for ${prop.property_code}:`, err);
            dscrMap.set(prop.id, null);
          }
        });
        
        await Promise.all(dscrPromises);
        setPropertyDscrMap(dscrMap);
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
        const metricsRes = await fetch(`${API_BASE_URL}/metrics/summary?limit=100`, {
          credentials: 'include'
        });
        const metricsData = metricsRes.ok ? await metricsRes.json() : [];
        // Match by property_code since API returns property_code, not property_id
        propertyMetric = metricsData.find((m: any) => m.property_code === currentProperty.property_code) || propertyMetricFromMap;
      }
      
      if (propertyMetric) {
        // Get DSCR and LTV from metrics summary (already calculated by backend)
        let dscr: number | null = propertyMetric.dscr !== null && propertyMetric.dscr !== undefined ? propertyMetric.dscr : null;
        let ltv: number | null = propertyMetric.ltv_ratio !== null && propertyMetric.ltv_ratio !== undefined ? propertyMetric.ltv_ratio : null;
        let capRate: number | null = null;

        try {
          // Only fetch cap rate (DSCR and LTV are already in metrics summary)
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
              variant="info"
              icon={<Download className="w-4 h-4" />}
              onClick={() => exportPropertyListToCSV(properties)}
              size="sm"
            >
              CSV
            </Button>
            <Button
              variant="info"
              icon={<Download className="w-4 h-4" />}
              onClick={() => exportPropertyListToExcel(properties)}
              size="sm"
            >
              Excel
            </Button>
            <Button variant="primary" icon={<Plus className="w-4 h-4" />} onClick={() => setShowCreateModal(true)}>
              Add Property
            </Button>
          </div>
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

            {/* Property Cards (List View) */}
            {viewMode === 'list' && (
            <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
              {sortedProperties.map((property) => {
                const isSelected = selectedProperty?.id === property.id;
                // Get this property's metrics from the map
                const propertyMetric = propertyMetricsMap.get(property.id);
                // Use selected property's detailed metrics if this is the selected property, otherwise use summary metrics
                const displayMetrics = isSelected && metrics ? metrics : null;
                const displayValue = displayMetrics?.value || propertyMetric?.total_assets || 0;
                // Use net_operating_income (NOI) instead of net_income for consistency with Command Center
                const displayNoi = displayMetrics?.noi || propertyMetric?.net_operating_income || propertyMetric?.net_income || 0;
                const displayOccupancy = displayMetrics?.occupancy || propertyMetric?.occupancy_rate || 0;
                // Use DSCR from API (propertyDscrMap) if available, otherwise use selected property's detailed metrics
                const displayDscr = displayMetrics?.dscr || propertyDscrMap.get(property.id) || null;
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
                          <span className="font-medium">${(displayNoi / 1000).toFixed(1)}K</span>
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
                          <div className="text-xl font-bold">${((metrics?.value || costs?.initialBuying || 0) / 1000000).toFixed(2)}M</div>
                        </div>
                        <div>
                          <div className="text-sm text-text-secondary">Current Value</div>
                          <div className="text-xl font-bold">${((metrics?.value || 0) / 1000000).toFixed(2)}M</div>
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
                          <div className="text-xl font-bold">
                            {metrics?.capRate !== null && metrics?.capRate !== undefined 
                              ? `${metrics.capRate.toFixed(2)}%` 
                              : metrics?.value && metrics?.noi 
                                ? `${((metrics.noi / metrics.value) * 100).toFixed(2)}%`
                                : 'N/A'}
                          </div>
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
                              ${((metrics?.noi || 0) / 1000).toFixed(1)}K / ${(((metrics?.noi || 0) * 1.25) / 1000).toFixed(1)}K target
                            </span>
                          </div>
                          <ProgressBar
                            value={metrics?.noi && metrics.noi > 0 ? ((metrics.noi / (metrics.noi * 1.25)) * 100) : 0}
                            max={100}
                            variant="success"
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
                        <Card variant="premium" className="p-8 mb-6">
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
                                  marketIntel.locationScore >= 8 ? 'text-green-600' :
                                  marketIntel.locationScore >= 6 ? 'text-blue-600' :
                                  marketIntel.locationScore >= 4 ? 'text-orange-600' : 'text-red-600'
                                }>
                                  {marketIntel.locationScore !== null ? `${marketIntel.locationScore}/10` : 'N/A'}
                                </span>
                              </div>
                              <div className="text-xs text-purple-600">
                                {marketIntel.locationScore >= 8 ? 'Premium Location' :
                                 marketIntel.locationScore >= 6 ? 'Strong Location' :
                                 marketIntel.locationScore >= 4 ? 'Average Location' : 'Below Average'}
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
                          <Card variant="info" className="p-6 mt-6">
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
                onChange={(e) => {
                  // Auto-convert to uppercase and remove any spaces
                  const value = e.target.value.toUpperCase().replace(/\s/g, '');
                  setFormData({ ...formData, property_code: value });
                }}
                required
                disabled={isEditing}
                pattern="[A-Z]{2,5}[0-9]{3}"
                title="Format: 2-5 uppercase letters followed by 3 digits (e.g., ESP001, TES121)"
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                placeholder="ESP001"
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

