/**
 * Market Intelligence TypeScript Interfaces
 *
 * Auto-generated interfaces for market intelligence API responses
 * Last updated: December 25, 2025
 */

// ============================================================================
// Data Lineage & Metadata
// ============================================================================

export interface DataLineage {
  source: string;
  vintage: string;
  confidence: number;
  fetched_at: string;
  extra_metadata?: Record<string, any>;
}

export interface TaggedData<T> {
  data: T;
  lineage: DataLineage;
}

// ============================================================================
// Demographics
// ============================================================================

export interface HousingUnits {
  single_family: number;
  multifamily_2_4: number;
  multifamily_5_9: number;
  multifamily_10_19: number;
  multifamily_20_49: number;
  multifamily_50_plus: number;
}

export interface Geography {
  state_fips: string;
  county_fips: string;
  tract: string;
}

export interface DemographicsData {
  population: number;
  median_household_income: number;
  median_home_value: number;
  median_gross_rent: number;
  unemployment_rate: number;
  median_age: number;
  college_educated_pct: number;
  housing_units: HousingUnits;
  geography: Geography;
}

export type Demographics = TaggedData<DemographicsData>;

// ============================================================================
// Economic Indicators
// ============================================================================

export interface EconomicIndicatorValue {
  value: number | null;
  date: string;
}

export interface EconomicIndicatorsData {
  gdp_growth?: EconomicIndicatorValue;
  unemployment_rate?: EconomicIndicatorValue;
  inflation_rate?: EconomicIndicatorValue;
  fed_funds_rate?: EconomicIndicatorValue;
  mortgage_rate_30y?: EconomicIndicatorValue;
  recession_probability?: EconomicIndicatorValue;
  msa_unemployment?: EconomicIndicatorValue;
  msa_gdp?: EconomicIndicatorValue;
}

export type EconomicIndicators = TaggedData<EconomicIndicatorsData>;

// ============================================================================
// Location Intelligence (Phase 2)
// ============================================================================

export interface Amenities {
  grocery_stores_1mi: number;
  restaurants_1mi: number;
  schools_2mi: number;
  hospitals_5mi: number;
  parks_1mi: number;
}

export interface TransitAccess {
  bus_stops_0_5mi: number;
  subway_stations_1mi: number;
  commute_time_downtown_min: number;
}

export interface LocationIntelligenceData {
  walk_score: number;
  transit_score: number;
  bike_score: number;
  amenities: Amenities;
  transit_access: TransitAccess;
  crime_index: number;
  school_rating_avg: number;
}

export type LocationIntelligence = TaggedData<LocationIntelligenceData>;

// ============================================================================
// ESG Assessment (Phase 3)
// ============================================================================

export interface EnvironmentalRisk {
  flood_risk_score: number;
  flood_zone: string;
  wildfire_risk_score: number;
  earthquake_risk_score: number;
  climate_risk_composite: number;
  energy_efficiency_rating: string;
  emissions_intensity_kg_co2_sqft: number;
}

export interface SocialRisk {
  crime_score: number;
  school_quality_score: number;
  income_inequality_gini: number;
  diversity_index: number;
  community_health_score: number;
}

export interface GovernanceRisk {
  zoning_compliance_score: number;
  permit_history_score: number;
  tax_delinquency_risk: string;
  legal_issues_count: number;
  regulatory_risk_score: number;
}

export interface ESGAssessmentData {
  environmental: EnvironmentalRisk;
  social: SocialRisk;
  governance: GovernanceRisk;
  composite_esg_score: number;
  esg_grade: string;
}

export type ESGAssessment = TaggedData<ESGAssessmentData>;

// ============================================================================
// Forecasts (Phase 4)
// ============================================================================

export interface ForecastResult {
  predicted_rent?: number;
  predicted_occupancy?: number;
  predicted_cap_rate?: number;
  predicted_value?: number;
  change_pct?: number;
  change_bps?: number;
  confidence_interval_95: [number, number];
  model: string;
  r_squared?: number;
  accuracy?: number;
  mae?: number;
}

export interface ForecastsData {
  rent_forecast_12mo?: ForecastResult;
  occupancy_forecast_12mo?: ForecastResult;
  cap_rate_forecast_12mo?: ForecastResult;
  value_forecast_12mo?: ForecastResult;
}

export type Forecasts = TaggedData<ForecastsData>;

// ============================================================================
// Competitive Analysis (Phase 5)
// ============================================================================

export interface SubmarketPosition {
  rent_percentile: number;
  occupancy_percentile: number;
  quality_percentile: number;
  value_percentile: number;
}

export interface CompetitiveThreat {
  property_name: string;
  distance_mi: number;
  threat_score: number;
  advantages: string[];
  disadvantages: string[];
}

export interface SubmarketTrends {
  rent_growth_3yr_cagr: number;
  occupancy_trend: string;
  new_supply_pipeline_units: number;
  absorption_rate_units_per_mo: number;
  months_of_supply: number;
}

export interface CompetitiveAnalysisData {
  submarket_position: SubmarketPosition;
  competitive_threats: CompetitiveThreat[];
  submarket_trends: SubmarketTrends;
}

export type CompetitiveAnalysis = TaggedData<CompetitiveAnalysisData>;

// ============================================================================
// Comparables (Phase 5)
// ============================================================================

export interface Adjustments {
  age_adjustment_pct: number;
  location_adjustment_pct: number;
  amenities_adjustment_pct: number;
  size_adjustment_pct: number;
}

export interface Comparable {
  property_name: string;
  distance_mi: number;
  similarity_score: number;
  rent_psf: number;
  occupancy_rate: number;
  cap_rate: number;
  year_built: number;
  units: number;
  adjustments: Adjustments;
  adjusted_rent_psf: number;
}

export interface MarketRentEstimate {
  mean_rent_psf: number;
  median_rent_psf: number;
  std_dev: number;
  confidence: number;
  sample_size: number;
}

export interface ComparablesData {
  comparables: Comparable[];
  market_rent_estimate: MarketRentEstimate;
}

export type Comparables = TaggedData<ComparablesData>;

// ============================================================================
// AI Insights (Phase 6)
// ============================================================================

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface InvestmentRecommendation {
  recommendation: 'BUY' | 'HOLD' | 'SELL';
  confidence_score: number;
  rationale: string;
  key_factors: string[];
}

export interface AIInsightsData {
  swot_analysis: SWOTAnalysis;
  investment_recommendation: InvestmentRecommendation;
  risk_assessment: string;
  opportunities: string[];
  market_trend_synthesis: string;
}

export type AIInsights = TaggedData<AIInsightsData>;

// ============================================================================
// Complete Market Intelligence
// ============================================================================

export interface MarketIntelligence {
  property_code: string;
  property_id: number;
  demographics: Demographics | null;
  economic_indicators: EconomicIndicators | null;
  location_intelligence: LocationIntelligence | null;
  esg_assessment: ESGAssessment | null;
  forecasts: Forecasts | null;
  competitive_analysis: CompetitiveAnalysis | null;
  comparables: Comparables | null;
  ai_insights: AIInsights | null;
  last_refreshed: string | null;
  refresh_status: 'success' | 'partial' | 'failure' | null;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface DemographicsResponse {
  property_code: string;
  demographics: Demographics;
  last_refreshed: string;
}

export interface EconomicIndicatorsResponse {
  property_code: string;
  economic_indicators: EconomicIndicators;
  last_refreshed: string;
}

export interface LocationIntelligenceResponse {
  property_code: string;
  location_intelligence: LocationIntelligence;
  last_refreshed: string;
}

export interface ESGAssessmentResponse {
  property_code: string;
  esg_assessment: ESGAssessment;
  last_refreshed: string;
}

export interface ForecastsResponse {
  property_code: string;
  forecasts: Forecasts;
  last_refreshed: string;
}

export interface CompetitiveAnalysisResponse {
  property_code: string;
  competitive_analysis: CompetitiveAnalysis;
  last_refreshed: string;
}

export interface AIInsightsResponse {
  property_code: string;
  ai_insights: AIInsights;
  last_refreshed: string;
}

export interface RefreshResponse {
  property_code: string;
  status: 'success' | 'partial' | 'failure';
  refreshed: string[];
  errors: Array<{
    category: string;
    error: string;
  }>;
  last_refreshed: string;
}

export interface LineageRecord {
  id: number;
  source: string;
  category: string;
  vintage: string | null;
  fetched_at: string;
  status: 'success' | 'partial' | 'failure';
  confidence: number | null;
  records_fetched: number | null;
  error: string | null;
}

export interface LineageResponse {
  property_code: string;
  category: string | null;
  total_records: number;
  lineage: LineageRecord[];
}

export interface StatisticsResponse {
  total_active_properties: number;
  properties_with_market_intelligence: number;
  coverage: {
    demographics: number;
    economic_indicators: number;
  };
  coverage_percentage: {
    demographics: number;
    economic: number;
  };
  data_pulls_last_30_days: number;
}

// ============================================================================
// Geocoding
// ============================================================================

export interface AddressDetails {
  house_number?: string;
  road?: string;
  city?: string;
  state?: string;
  postcode?: string;
  country?: string;
}

export interface GeocodedLocation {
  latitude: number;
  longitude: number;
  formatted_address: string;
  address_details: AddressDetails;
  importance: number;
}

// ============================================================================
// API Request Parameters
// ============================================================================

export interface RefreshRequest {
  categories?: Array<
    'demographics' |
    'economic' |
    'location' |
    'esg' |
    'forecasts' |
    'competitive' |
    'comparables' |
    'insights'
  >;
}

export interface EconomicIndicatorsRequest {
  msa_code?: string;
  refresh?: boolean;
}

export interface DemographicsRequest {
  refresh?: boolean;
}

export interface LocationIntelligenceRequest {
  refresh?: boolean;
}

export interface ESGAssessmentRequest {
  refresh?: boolean;
}

export interface ForecastsRequest {
  refresh?: boolean;
}

export interface CompetitiveAnalysisRequest {
  refresh?: boolean;
}

export interface AIInsightsRequest {
  refresh?: boolean;
}

export interface LineageRequest {
  category?: string;
  limit?: number;
}

// ============================================================================
// Forecast Model Types
// ============================================================================

export type ModelType = 'prophet' | 'arima' | 'xgboost' | 'lstm' | 'ensemble';
export type ForecastTarget = 'rent' | 'occupancy' | 'cap_rate' | 'value' | 'expenses';

export interface ForecastModel {
  id: number;
  property_id: number | null;
  model_type: ModelType;
  forecast_target: ForecastTarget;
  forecast_horizon_months: number;
  r_squared: number | null;
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  accuracy: number | null;
  is_active: boolean;
  version: string | null;
  trained_at: string;
  last_used_at: string | null;
}

// ============================================================================
// Helper Types
// ============================================================================

export type DataCategory =
  | 'demographics'
  | 'economic'
  | 'location'
  | 'esg'
  | 'forecasts'
  | 'competitive'
  | 'comparables'
  | 'insights';

export type RefreshStatus = 'success' | 'partial' | 'failure';

export type FetchStatus = 'success' | 'partial' | 'failure';

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Extract the data portion from a TaggedData type
 */
export type ExtractData<T> = T extends TaggedData<infer U> ? U : never;

/**
 * Check if market intelligence data is available
 */
export function hasData<T>(data: T | null): data is T {
  return data !== null;
}

/**
 * Get confidence level description
 */
export function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 90) return 'high';
  if (confidence >= 70) return 'medium';
  return 'low';
}

/**
 * Format data vintage for display
 */
export function formatVintage(vintage: string): string {
  // Handle different vintage formats: "2021", "2024-Q3", "2024-11"
  if (vintage.includes('-Q')) {
    return vintage; // Quarter format
  }
  if (vintage.includes('-') && vintage.length > 5) {
    const [year, month] = vintage.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${monthNames[parseInt(month) - 1]} ${year}`;
  }
  return vintage; // Year format
}

/**
 * Check if data needs refresh (older than 24 hours)
 */
export function needsRefresh(lastRefreshed: string | null): boolean {
  if (!lastRefreshed) return true;
  const refreshedDate = new Date(lastRefreshed);
  const now = new Date();
  const hoursDiff = (now.getTime() - refreshedDate.getTime()) / (1000 * 60 * 60);
  return hoursDiff > 24;
}

/**
 * Get ESG grade color
 */
export function getESGGradeColor(grade: string): string {
  const letter = grade.charAt(0);
  switch (letter) {
    case 'A': return '#10b981'; // green
    case 'B': return '#3b82f6'; // blue
    case 'C': return '#f59e0b'; // yellow
    case 'D': return '#ef4444'; // red
    default: return '#6b7280'; // gray
  }
}
