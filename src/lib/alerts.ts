/**
 * Alert Service
 * API client for alert management
 */
import { ApiClient } from './api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const apiClient = new ApiClient(API_BASE_URL);

export interface Alert {
  id: number;
  property_id: number;
  financial_period_id?: number;
  alert_type: string;
  severity: string;
  status: string;
  title: string;
  description?: string;
  threshold_value?: number;
  actual_value?: number;
  threshold_unit?: string;
  assigned_committee: string;
  requires_approval?: boolean;
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  dismissed_at?: string;
  acknowledged_by?: number;
  resolved_by?: number;
  dismissed_by?: number;
  resolution_notes?: string;
  dismissal_reason?: string;
  alert_metadata?: any;
  related_metric?: string;
  br_id?: string;
  priority_score?: number;
  correlation_group_id?: number;
  escalation_level?: number;
  escalated_at?: string;
  related_alert_ids?: number[];
  alert_tags?: string[];
  performance_impact?: string;
  created_at: string;
  updated_at?: string;
}

export interface AlertSummary {
  success: boolean;
  period_days: number;
  total_alerts: number;
  active_alerts: number;
  critical_active: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  property_id?: number;
}

export interface AlertTrend {
  date: string;
  count: number;
}

export interface AlertTrendsResponse {
  success: boolean;
  period_days: number;
  trends: AlertTrend[];
  total_alerts: number;
  property_id?: number;
}

export interface AlertAnalytics {
  success: boolean;
  period_days: number;
  total_alerts: number;
  resolved_count: number;
  average_resolution_hours?: number;
  type_frequency: Record<string, number>;
  property_distribution?: Record<number, number>;
  property_id?: number;
}

export class AlertService {
  /**
   * Get all alerts with optional filtering
   */
  static async getAlerts(params?: {
    status?: string;
    severity?: string;
    alert_type?: string;
    property_id?: number;
    committee?: string;
    limit?: number;
  }): Promise<{ success: boolean; alerts: Alert[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.alert_type) queryParams.append('alert_type', params.alert_type);
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.committee) queryParams.append('committee', params.committee);
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const response = await apiClient.get(`/risk-alerts?${queryParams.toString()}`);
    return response;
  }

  /**
   * Get a specific alert by ID
   */
  static async getAlert(alertId: number): Promise<Alert> {
    const response = await apiClient.get(`/risk-alerts/alerts/${alertId}`);
    return response;
  }

  /**
   * Acknowledge an alert
   */
  static async acknowledgeAlert(
    alertId: number,
    acknowledgedBy: number,
    notes?: string
  ): Promise<{ success: boolean; alert: Alert }> {
    const response = await apiClient.post(`/risk-alerts/alerts/${alertId}/acknowledge`, {
      acknowledged_by: acknowledgedBy,
      notes
    });
    return response;
  }

  /**
   * Resolve an alert
   */
  static async resolveAlert(
    alertId: number,
    resolvedBy: number,
    resolutionNotes: string
  ): Promise<{ success: boolean; alert: Alert }> {
    const response = await apiClient.post(`/risk-alerts/alerts/${alertId}/resolve`, {
      resolved_by: resolvedBy,
      resolution_notes: resolutionNotes
    });
    return response;
  }

  /**
   * Dismiss an alert
   */
  static async dismissAlert(
    alertId: number,
    dismissedBy: number,
    dismissalReason: string
  ): Promise<{ success: boolean; alert: Alert }> {
    const response = await apiClient.post(`/risk-alerts/alerts/${alertId}/dismiss`, {
      dismissed_by: dismissedBy,
      dismissal_reason: dismissalReason
    });
    return response;
  }

  /**
   * Bulk acknowledge alerts
   */
  static async bulkAcknowledge(
    alertIds: number[],
    acknowledgedBy: number,
    notes?: string
  ): Promise<{ success: boolean; acknowledged: number; total_requested: number }> {
    const response = await apiClient.post('/risk-alerts/bulk-acknowledge', {
      alert_ids: alertIds,
      acknowledged_by: acknowledgedBy,
      notes
    });
    return response;
  }

  /**
   * Get alert summary for dashboard
   */
  static async getSummary(params?: {
    property_id?: number;
    days?: number;
  }): Promise<AlertSummary> {
    const queryParams = new URLSearchParams();
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());

    const response = await apiClient.get(`/risk-alerts/summary?${queryParams.toString()}`);
    return response;
  }

  /**
   * Get alert trends
   */
  static async getTrends(params?: {
    property_id?: number;
    days?: number;
  }): Promise<AlertTrendsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());

    const response = await apiClient.get(`/risk-alerts/trends?${queryParams.toString()}`);
    return response;
  }

  /**
   * Get alert analytics
   */
  static async getAnalytics(params?: {
    property_id?: number;
    days?: number;
  }): Promise<AlertAnalytics> {
    const queryParams = new URLSearchParams();
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());

    const response = await apiClient.get(`/risk-alerts/analytics?${queryParams.toString()}`);
    return response;
  }

  /**
   * Get related alerts
   */
  static async getRelatedAlerts(alertId: number): Promise<{
    success: boolean;
    alert_id: number;
    related_alerts: Alert[];
    total: number;
  }> {
    const response = await apiClient.get(`/risk-alerts/${alertId}/related`);
    return response;
  }

  /**
   * Escalate an alert
   */
  static async escalateAlert(
    alertId: number,
    reason: string,
    targetCommittee?: string
  ): Promise<{ success: boolean; alert: Alert; escalation_level: number }> {
    const response = await apiClient.post(`/risk-alerts/${alertId}/escalate`, {
      reason,
      target_committee: targetCommittee
    });
    return response;
  }

  /**
   * Get dashboard summary (legacy endpoint)
   */
  static async getDashboardSummary(): Promise<{
    success: boolean;
    total_critical_alerts: number;
    total_active_alerts: number;
    total_active_locks: number;
    properties_with_good_dscr: number;
    summary: any;
  }> {
    const response = await apiClient.get('/risk-alerts/dashboard/summary');
    return response;
  }
}
