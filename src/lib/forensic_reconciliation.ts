/**
 * Forensic Reconciliation API Client
 * 
 * Provides functions to interact with forensic reconciliation endpoints
 */

import { api } from './api';

export interface ForensicReconciliationSession {
  id: number;
  property_id: number;
  period_id: number;
  session_type: string;
  status: string;
  auditor_id?: number;
  started_at: string | null;
  completed_at: string | null;
  summary?: {
    total_matches?: number;
    exact_matches?: number;
    fuzzy_matches?: number;
    calculated_matches?: number;
    inferred_matches?: number;
    discrepancies?: number;
    health_score?: number;
    approved?: number;
    pending_review?: number;
  };
  notes?: string;
}

export interface ForensicMatch {
  id: number;
  session_id: number;
  source_document_type: string;
  source_record_id: number;
  source_account_code?: string;
  source_account_name?: string;
  source_amount?: number;
  target_document_type: string;
  target_record_id: number;
  target_account_code?: string;
  target_account_name?: string;
  target_amount?: number;
  match_type: 'exact' | 'fuzzy' | 'calculated' | 'inferred';
  confidence_score: number;
  amount_difference?: number;
  amount_difference_percent?: number;
  match_algorithm?: string;
  relationship_type?: string;
  relationship_formula?: string;
  status: 'pending' | 'approved' | 'rejected' | 'modified';
  exception_tier?: 'tier_0_auto_close' | 'tier_1_auto_suggest' | 'tier_2_route' | 'tier_3_escalate';
  reviewed_by?: number;
  reviewed_at?: string;
  review_notes?: string;
  created_at?: string;
  source_coordinates?: any;
  target_coordinates?: any;
  reasons?: string[];
  prior_period_amount?: number;
}

export interface ForensicDiscrepancy {
  id: number;
  session_id: number;
  match_id?: number;
  discrepancy_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  exception_tier?: 'tier_0_auto_close' | 'tier_1_auto_suggest' | 'tier_2_route' | 'tier_3_escalate';
  source_value?: number;
  target_value?: number;
  expected_value?: number;
  actual_value?: number;
  difference?: number;
  difference_percent?: number;
  description: string;
  suggested_resolution?: string;
  status: 'open' | 'investigating' | 'resolved' | 'accepted';
  resolved_by?: number;
  resolved_at?: string;
  resolution_notes?: string;
  created_at?: string;
}

export interface ReconciliationDashboard {
  session_id?: number;
  session_status?: string;
  started_at?: string;
  summary?: any;
  matches?: {
    total: number;
    by_status: Record<string, number>;
    by_type: Record<string, number>;
  };
  discrepancies?: {
    total: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
  };
  recent_activity?: any[];
}

export interface SessionCreateRequest {
  property_id: number;
  period_id: number;
  session_type?: string;
  auditor_id?: number;
}

export interface RunReconciliationRequest {
  use_exact?: boolean;
  use_fuzzy?: boolean;
  use_calculated?: boolean;
  use_inferred?: boolean;
  use_rules?: boolean;
}

export interface ApproveMatchRequest {
  notes?: string;
}

export interface RejectMatchRequest {
  reason: string;
}

export interface ResolveDiscrepancyRequest {
  resolution_notes: string;
  new_value?: number;
}

export interface CalculatedRuleEvaluation {
  rule_id: string;
  rule_name: string;
  description?: string | null;
  formula: string;
  severity: string;
  status: 'PASS' | 'FAIL' | 'SKIPPED';
  expected_value?: number | null;
  actual_value?: number | null;
  difference?: number | null;
  difference_percent?: number | null;
  tolerance_absolute?: number | null;
  tolerance_percent?: number | null;
  message?: string | null;
}

export interface CalculatedRuleEvaluationResponse {
  property_id: number;
  period_id: number;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  rules: CalculatedRuleEvaluation[];
}

export const forensicReconciliationService = {
  /**
   * Create a new forensic reconciliation session
   */
  async createSession(request: SessionCreateRequest): Promise<ForensicReconciliationSession> {
    return api.post('/forensic-reconciliation/sessions', request);
  },

  /**
   * Get session details
   */
  async getSession(sessionId: number): Promise<ForensicReconciliationSession> {
    return api.get(`/forensic-reconciliation/sessions/${sessionId}`);
  },

  /**
   * Run reconciliation for a session
   */
  async runReconciliation(
    sessionId: number,
    request?: RunReconciliationRequest
  ): Promise<any> {
    return api.post(`/forensic-reconciliation/sessions/${sessionId}/run`, request || {});
  },

  /**
   * Get matches for a session
   */
  async getMatches(
    sessionId: number,
    filters?: {
      match_type?: string;
      status?: string;
      min_confidence?: number;
    }
  ): Promise<{ session_id: number; total: number; matches: ForensicMatch[] }> {
    const params = new URLSearchParams();
    if (filters?.match_type) params.append('match_type', filters.match_type);
    if (filters?.status) params.append('status_filter', filters.status);
    if (filters?.min_confidence !== undefined) params.append('min_confidence', filters.min_confidence.toString());
    
    const queryString = params.toString();
    const url = `/forensic-reconciliation/sessions/${sessionId}/matches${queryString ? `?${queryString}` : ''}`;
    return api.get(url);
  },

  /**
   * Get discrepancies for a session
   */
  async getDiscrepancies(
    sessionId: number,
    filters?: {
      severity?: string;
      status?: string;
    }
  ): Promise<{ session_id: number; total: number; discrepancies: ForensicDiscrepancy[] }> {
    const params = new URLSearchParams();
    if (filters?.severity) params.append('severity', filters.severity);
    if (filters?.status) params.append('status_filter', filters.status);
    
    const queryString = params.toString();
    const url = `/forensic-reconciliation/sessions/${sessionId}/discrepancies${queryString ? `?${queryString}` : ''}`;
    return api.get(url);
  },

  /**
   * Approve a match
   */
  async approveMatch(matchId: number, request?: ApproveMatchRequest): Promise<any> {
    return api.post(`/forensic-reconciliation/matches/${matchId}/approve`, request || {});
  },

  /**
   * Reject a match
   */
  async rejectMatch(matchId: number, request: RejectMatchRequest): Promise<any> {
    return api.post(`/forensic-reconciliation/matches/${matchId}/reject`, request);
  },

  /**
   * Resolve a discrepancy
   */
  async resolveDiscrepancy(discrepancyId: number, request: ResolveDiscrepancyRequest): Promise<any> {
    return api.post(`/forensic-reconciliation/discrepancies/${discrepancyId}/resolve`, request);
  },

  /**
   * Get specific calculated rule detail
   */
  async getCalculatedRuleDetail(ruleId: string, propertyId: number, periodId: number): Promise<any> {
    return api.get(`/forensic-reconciliation/calculated-rules/detail/${ruleId}/${propertyId}/${periodId}`);
  },

  /**
   * Evaluate calculated rules for a property and period
   */
  async evaluateCalculatedRules(propertyId: number, periodId: number): Promise<CalculatedRuleEvaluationResponse> {
    return api.get(`/forensic-reconciliation/calculated-rules/evaluate/${propertyId}/${periodId}`);
  },


  /**
   * Update calculated rule definition (creates new version)
   */
  async updateCalculatedRule(ruleId: string, ruleData: any): Promise<any> {
    // Backend uses versioning - POSTing with existing rule_id creates new version
    const payload = {
      rule_id: ruleId,
      rule_name: ruleData.name,
      formula: ruleData.formula,
      description: ruleData.description,
      tolerance_absolute: ruleData.threshold || 0.01,
      tolerance_percent: null,
      materiality_threshold: null,
      severity: 'medium',
      property_scope: null, // Apply to all properties
      doc_scope: { all: true }, // Apply to all document types
      failure_explanation_template: null,
      effective_date: new Date().toISOString().split('T')[0], // Today
      expires_at: null // No expiration
    };
    
    return api.post('/forensic-reconciliation/calculated-rules', payload);
  },

  /**
   * Get dashboard data
   */
  async getDashboard(propertyId: number, periodId: number): Promise<ReconciliationDashboard> {
    return api.get(`/forensic-reconciliation/dashboard/${propertyId}/${periodId}`);
  },

  /**
   * Get health score
   */
  async getHealthScore(propertyId: number, periodId: number): Promise<any> {
    return api.get(`/forensic-reconciliation/health-score/${propertyId}/${periodId}`);
  },

  /**
   * Complete a session
   */
  async completeSession(sessionId: number): Promise<any> {
    return api.post(`/forensic-reconciliation/sessions/${sessionId}/complete`);
  },

  /**
   * Validate matches and calculate health score
   */
  async validateSession(sessionId: number): Promise<any> {
    return api.post(`/forensic-reconciliation/sessions/${sessionId}/validate`);
  },

  /**
   * Check data availability for reconciliation
   */
  async checkDataAvailability(propertyId: number, periodId: number): Promise<{
    document_uploads: Record<string, boolean>;
    extracted_data: Record<string, { count: number; has_data: boolean }>;
    key_accounts: Record<string, boolean>;
    total_records: number;
    can_reconcile: boolean;
    recommendations: string[];
  }> {
    return api.get(`/forensic-reconciliation/data-availability/${propertyId}/${periodId}`);
  },

  /**
   * Classify match into exception tier
   */
  async classifyMatchTier(matchId: number, autoResolve: boolean = true): Promise<any> {
    return api.post(`/forensic-reconciliation/matches/${matchId}/classify-tier?auto_resolve=${autoResolve}`);
  },

  /**
   * Get suggested fix for tier 1 match
   */
  async suggestMatchFix(matchId: number): Promise<any> {
    return api.post(`/forensic-reconciliation/matches/${matchId}/suggest-fix`);
  },

  /**
   * Bulk classify matches into tiers
   */
  async bulkClassifyTiers(matchIds: number[], autoResolve: boolean = true): Promise<any> {
    return api.post(`/forensic-reconciliation/matches/bulk-tier`, { match_ids: matchIds, auto_resolve: autoResolve });
  },

  /**
   * Get health score with persona
   */
  async getHealthScoreWithPersona(propertyId: number, periodId: number, persona: string = 'controller'): Promise<any> {
    return api.get(`/forensic-reconciliation/health-score/${propertyId}/${periodId}?persona=${persona}`);
  },

  /**
   * Get health score trend
   */
  async getHealthScoreTrend(propertyId: number, periods: number = 6): Promise<any> {
    return api.get(`/forensic-reconciliation/health-score/${propertyId}/trend?periods=${periods}`);
  },

  /**
   * Get health score configuration
   */
  async getHealthScoreConfig(persona: string): Promise<any> {
    return api.get(`/forensic-reconciliation/health-score-configs/${persona}`);
  },

  /**
   * Update health score configuration
   */
  async updateHealthScoreConfig(persona: string, config: any): Promise<any> {
    return api.put(`/forensic-reconciliation/health-score-configs/${persona}`, config);
  },
};
