/**
 * Metrics Source Service
 * 
 * Service for retrieving source document information for metric values
 * Used for PDF source navigation feature
 */

import { apiClient, ApiError } from './apiClient';

export interface MetricSourceResponse {
  upload_id: number;
  document_type: string;
  file_name: string;
  page_number: number | null;
  extraction_x0: number | null;
  extraction_y0: number | null;
  extraction_x1: number | null;
  extraction_y1: number | null;
  pdf_url: string | null;
  has_coordinates: boolean;
}

export interface PDFViewerResponse {
  upload_id: number;
  file_name: string;
  pdf_url: string;
  page_number: number | null;
  highlight_coords: {
    page: number;
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  } | null;
  has_highlight: boolean;
}

/**
 * Map metric types to account codes for source lookup
 */
export function getAccountCodeForMetric(metricType: string): string | null {
  const metricToAccountMap: Record<string, string> = {
    'total_assets': '1999-0000',
    'property_value': '1999-0000',
    'net_operating_income': 'net_operating_income', // Special handling needed
    'noi': 'net_operating_income',
    'occupancy_rate': 'occupancy_rate', // Special handling needed
  };
  
  return metricToAccountMap[metricType.toLowerCase()] || null;
}

/**
 * Get source document information for a metric value
 */
export async function getMetricSource(
  propertyId: number,
  metricType: string,
  periodId?: number
): Promise<MetricSourceResponse | null> {
  try {
    const accountCode = getAccountCodeForMetric(metricType);
    
    if (!accountCode) {
      console.warn(`No account code mapping for metric type: ${metricType}`);
      return null;
    }

    const params = new URLSearchParams({
      account_code: accountCode,
      metric_type: metricType,
    });
    
    if (periodId) {
      params.append('period_id', periodId.toString());
    }

    const data = await apiClient.get<MetricSourceResponse>(`/metrics/${propertyId}/source`, Object.fromEntries(params));
    return data;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    console.error('Error getting metric source:', error);
    return null;
  }
}

/**
 * Get PDF viewer data with highlight coordinates
 */
export async function getPDFViewerData(
  uploadId: number,
  highlightPage?: number,
  highlightCoords?: { x0: number; y0: number; x1: number; y1: number }
): Promise<PDFViewerResponse | null> {
  try {
    const params = new URLSearchParams();
    
    if (highlightPage) {
      params.append('highlight_page', highlightPage.toString());
    }
    
    if (highlightCoords) {
      params.append('highlight_x0', highlightCoords.x0.toString());
      params.append('highlight_y0', highlightCoords.y0.toString());
      params.append('highlight_x1', highlightCoords.x1.toString());
      params.append('highlight_y1', highlightCoords.y1.toString());
    }

    const data = await apiClient.get<PDFViewerResponse>(`/pdf-viewer/${uploadId}`, Object.fromEntries(params));
    return data;
  } catch (error) {
    console.error('Error getting PDF viewer data:', error);
    return null;
  }
}
