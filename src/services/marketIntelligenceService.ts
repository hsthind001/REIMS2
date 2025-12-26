/**
 * Market Intelligence Service
 *
 * Service layer for interacting with market intelligence API endpoints
 */

import axios from 'axios';
import type {
  MarketIntelligence,
  DemographicsResponse,
  EconomicIndicatorsResponse,
  LocationIntelligenceResponse,
  ESGAssessmentResponse,
  ForecastsResponse,
  CompetitiveAnalysisResponse,
  AIInsightsResponse,
  RefreshResponse,
  LineageResponse,
  StatisticsResponse,
  RefreshRequest,
  EconomicIndicatorsRequest,
  DemographicsRequest,
  LocationIntelligenceRequest,
  ESGAssessmentRequest,
  ForecastsRequest,
  CompetitiveAnalysisRequest,
  AIInsightsRequest,
  LineageRequest,
} from '../types/market-intelligence';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * Get system-wide market intelligence statistics
 */
export async function getStatistics(): Promise<StatisticsResponse> {
  const response = await axios.get(`${API_V1}/market-intelligence/statistics`);
  return response.data;
}

/**
 * Get complete market intelligence for a property
 */
export async function getMarketIntelligence(propertyCode: string): Promise<MarketIntelligence> {
  const response = await axios.get(`${API_V1}/properties/${propertyCode}/market-intelligence`);
  return response.data;
}

/**
 * Get demographics data for a property
 */
export async function getDemographics(
  propertyCode: string,
  options?: DemographicsRequest
): Promise<DemographicsResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/demographics`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get economic indicators for a property
 */
export async function getEconomicIndicators(
  propertyCode: string,
  options?: EconomicIndicatorsRequest
): Promise<EconomicIndicatorsResponse> {
  const params = new URLSearchParams();
  if (options?.msa_code) params.append('msa_code', options.msa_code);
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/economic`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get location intelligence for a property
 */
export async function getLocationIntelligence(
  propertyCode: string,
  options?: LocationIntelligenceRequest
): Promise<LocationIntelligenceResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/location`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get ESG assessment for a property
 */
export async function getESGAssessment(
  propertyCode: string,
  options?: ESGAssessmentRequest
): Promise<ESGAssessmentResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/esg`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get predictive forecasts for a property
 */
export async function getForecasts(
  propertyCode: string,
  options?: ForecastsRequest
): Promise<ForecastsResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/forecasts`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get competitive analysis for a property
 */
export async function getCompetitiveAnalysis(
  propertyCode: string,
  options?: CompetitiveAnalysisRequest
): Promise<CompetitiveAnalysisResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/competitive`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get AI-powered insights for a property
 */
export async function getAIInsights(
  propertyCode: string,
  options?: AIInsightsRequest
): Promise<AIInsightsResponse> {
  const params = new URLSearchParams();
  if (options?.refresh) params.append('refresh', 'true');

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/insights`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Refresh market intelligence data
 */
export async function refreshMarketIntelligence(
  propertyCode: string,
  request?: RefreshRequest
): Promise<RefreshResponse> {
  const params = new URLSearchParams();
  if (request?.categories) {
    request.categories.forEach(cat => params.append('categories', cat));
  }

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/refresh`;
  const response = await axios.post(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Get data lineage (audit trail) for a property
 */
export async function getDataLineage(
  propertyCode: string,
  options?: LineageRequest
): Promise<LineageResponse> {
  const params = new URLSearchParams();
  if (options?.category) params.append('category', options.category);
  if (options?.limit) params.append('limit', options.limit.toString());

  const url = `${API_V1}/properties/${propertyCode}/market-intelligence/lineage`;
  const response = await axios.get(params.toString() ? `${url}?${params}` : url);
  return response.data;
}

/**
 * Check if market intelligence data needs refresh
 */
export function needsRefresh(lastRefreshed: string | null): boolean {
  if (!lastRefreshed) return true;
  const refreshedDate = new Date(lastRefreshed);
  const now = new Date();
  const hoursDiff = (now.getTime() - refreshedDate.getTime()) / (1000 * 60 * 60);
  return hoursDiff > 24;
}

/**
 * Format currency value
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format percentage value
 */
export function formatPercentage(value: number | null | undefined, decimals: number = 1): string {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format number with commas
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Get confidence level badge color
 */
export function getConfidenceBadgeColor(confidence: number): string {
  if (confidence >= 90) return 'green';
  if (confidence >= 70) return 'yellow';
  return 'red';
}

/**
 * Format vintage for display
 */
export function formatVintage(vintage: string): string {
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
