/**
 * Metrics Source Service
 * 
 * Service for retrieving source document information for metric values
 * Used for PDF source navigation feature
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

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

    const response = await fetch(
      `${API_BASE_URL}/metrics/${propertyId}/source?${params.toString()}`,
      {
        credentials: 'include',
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        // Source not found - this is OK for calculated metrics
        return null;
      }
      throw new Error(`Failed to get metric source: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
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

    const url = `${API_BASE_URL}/pdf-viewer/${uploadId}${params.toString() ? `?${params.toString()}` : ''}`;
    
    const response = await fetch(url, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Failed to get PDF viewer data: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting PDF viewer data:', error);
    return null;
  }
}

