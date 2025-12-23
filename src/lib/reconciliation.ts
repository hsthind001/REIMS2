/**
 * Reconciliation API Client
 * 
 * Provides functions to interact with reconciliation endpoints
 */

import { api } from './api';

export interface ReconciliationSession {
  id: number;
  property_code: string;
  property_name: string;
  period_year: number;
  period_month: number;
  document_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  summary?: {
    total_records: number;
    matches: number;
    differences: number;
    missing_in_db: number;
    missing_in_pdf: number;
    match_rate: number;
  };
}

export interface ComparisonRecord {
  id?: number; // Difference ID from backend
  account_code: string;
  account_name: string;
  pdf_value: number | null;
  db_value: number | null;
  difference: number | null;
  difference_percent: number | null;
  match_status: 'exact' | 'tolerance' | 'mismatch' | 'missing_pdf' | 'missing_db';
  confidence_score?: number;
  needs_review: boolean;
  flags?: string[];
  priority?: number;
  severity?: string;
  // Extended fields for rent roll reconciliation
  rent_roll_fields?: {
    tenant_code?: string;
    lease_type?: string;
    lease_start_date?: string;
    lease_end_date?: string;
    lease_term_months?: number;
    tenancy_years?: number;
    unit_area_sqft?: number;
    monthly_rent_per_sqft?: number;
    annual_rent?: number;
    annual_rent_per_sqft?: number;
    annual_recoveries_per_sf?: number;
    annual_misc_per_sf?: number;
    security_deposit?: number;
    loc_amount?: number;
    occupancy_status?: string;
    lease_status?: string;
  };
}

export interface ComparisonData {
  session_id: number;
  property: {
    id: number;
    code: string;
    name: string;
  };
  period: {
    id: number;
    year: number;
    month: number;
  };
  document_type: string;
  pdf_url: string | null;
  comparison: {
    total_records: number;
    matches: number;
    differences: number;
    missing_in_db: number;
    missing_in_pdf: number;
    records: ComparisonRecord[];
  };
}

export interface ResolutionRequest {
  action: 'accept_pdf' | 'accept_db' | 'manual_entry' | 'ignore';
  new_value?: number;
  reason: string;
}

export interface BulkResolveRequest {
  difference_ids: number[];
  action: 'accept_pdf' | 'accept_db' | 'ignore';
}

export const reconciliationService = {
  /**
   * Start a new reconciliation session
   */
  async startSession(
    propertyCode: string,
    year: number,
    month: number,
    docType: string
  ): Promise<ReconciliationSession> {
    return await api.post<ReconciliationSession>('/reconciliation/session', {
      property_code: propertyCode,
      period_year: year,
      period_month: month,
      document_type: docType
    });
  },

  /**
   * Get comparison data between PDF and database
   */
  async getComparison(
    propertyCode: string,
    year: number,
    month: number,
    docType: string
  ): Promise<ComparisonData> {
    return await api.get<ComparisonData>('/reconciliation/compare', {
      property_code: propertyCode,
      year,
      month,
      doc_type: docType
    });
  },

  /**
   * Get MinIO presigned URL for PDF viewing
   */
  async getPdfUrl(
    propertyCode: string,
    year: number,
    month: number,
    docType: string
  ): Promise<string> {
    const response = await api.get<{pdf_url: string}>('/reconciliation/pdf-url', {
      property_code: propertyCode,
      year,
      month,
      doc_type: docType
    });
    return response.pdf_url;
  },

  /**
   * Resolve a single difference
   */
  async resolveDifference(
    differenceId: number,
    resolution: ResolutionRequest
  ): Promise<{ success: boolean; message: string }> {
    return await api.post<{ success: boolean; message: string }>(`/reconciliation/resolve/${differenceId}`, resolution);
  },

  /**
   * Bulk resolve multiple differences
   */
  async bulkResolve(request: BulkResolveRequest): Promise<{
    success: number;
    failed: number;
    total: number;
  }> {
    return await api.post<{success: number; failed: number; total: number}>('/reconciliation/bulk-resolve', request);
  },

  /**
   * Get list of reconciliation sessions
   */
  async getSessions(propertyCode?: string, limit: number = 50): Promise<{
    sessions: ReconciliationSession[];
    total: number;
  }> {
    const params: any = { limit };
    if (propertyCode) {
      params.property_code = propertyCode;
    }
    return await api.get<{sessions: ReconciliationSession[]; total: number}>('/reconciliation/sessions', params);
  },

  /**
   * Get session details with differences
   */
  async getSessionDetails(sessionId: number): Promise<{
    session: ReconciliationSession;
    differences: ComparisonRecord[];
  }> {
    return await api.get<{session: ReconciliationSession; differences: ComparisonRecord[]}>(`/reconciliation/sessions/${sessionId}`);
  },

  /**
   * Mark session as complete
   */
  async completeSession(sessionId: number): Promise<{ success: boolean; message: string }> {
    return await api.put<{ success: boolean; message: string }>(`/reconciliation/sessions/${sessionId}/complete`);
  },

  /**
   * Generate reconciliation report
   */
  async generateReport(
    sessionId: number,
    format: 'excel' | 'pdf' = 'excel'
  ): Promise<Blob> {
    // Note: Blob download needs special handling
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/reconciliation/report/${sessionId}?format=${format}`;
    const response = await fetch(url, {
      credentials: 'include'
    });
    return await response.blob();
  }
};

export default reconciliationService;

