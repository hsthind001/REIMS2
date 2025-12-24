/**
 * Alert Rules Service
 * API client for alert rule management
 */
import { ApiClient } from './api';

const apiClient = new ApiClient();

export interface AlertRule {
  id: number;
  rule_name: string;
  description?: string;
  rule_type: string;
  field_name: string;
  condition: string;
  threshold_value?: number;
  severity: string;
  is_active: boolean;
  rule_expression?: any;
  severity_mapping?: any;
  cooldown_period?: number;
  rule_dependencies?: any;
  property_specific: boolean;
  property_id?: number;
  rule_template_id?: number;
  execution_count?: number;
  last_triggered_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface AlertRuleTemplate {
  id: string;
  name: string;
  description: string;
  rule_type: string;
  field_name: string;
  condition: string;
  default_threshold: number;
  default_severity: string;
  severity_mapping?: any;
  assigned_committee: string;
  alert_type: string;
}

export interface RuleTestRequest {
  property_id: number;
  period_id: number;
  rule_config?: any;
}

export class AlertRuleService {
  /**
   * Get all alert rules
   */
  static async getRules(params?: {
    property_id?: number;
    is_active?: boolean;
    rule_type?: string;
    limit?: number;
    skip?: number;
  }): Promise<AlertRule[]> {
    const queryParams = new URLSearchParams();
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());
    if (params?.rule_type) queryParams.append('rule_type', params.rule_type);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.skip) queryParams.append('skip', params.skip.toString());

    const response = await apiClient.get(`/alert-rules?${queryParams.toString()}`);
    return response;
  }

  /**
   * Get a specific rule by ID
   */
  static async getRule(ruleId: number): Promise<AlertRule> {
    const response = await apiClient.get(`/alert-rules/${ruleId}`);
    return response;
  }

  /**
   * Create a new alert rule
   */
  static async createRule(rule: Partial<AlertRule>): Promise<AlertRule> {
    const response = await apiClient.post('/alert-rules', rule);
    return response;
  }

  /**
   * Update an alert rule
   */
  static async updateRule(ruleId: number, updates: Partial<AlertRule>): Promise<AlertRule> {
    const response = await apiClient.put(`/alert-rules/${ruleId}`, updates);
    return response;
  }

  /**
   * Delete an alert rule
   */
  static async deleteRule(ruleId: number): Promise<void> {
    await apiClient.delete(`/alert-rules/${ruleId}`);
  }

  /**
   * Test a rule against data
   */
  static async testRule(ruleId: number, testRequest: RuleTestRequest): Promise<{
    success: boolean;
    rule_id: number;
    property_id: number;
    period_id: number;
    result: any;
  }> {
    const response = await apiClient.post(`/alert-rules/${ruleId}/test`, testRequest);
    return response;
  }

  /**
   * Get all rule templates
   */
  static async getTemplates(): Promise<{
    success: boolean;
    templates: AlertRuleTemplate[];
    total: number;
  }> {
    const response = await apiClient.get('/alert-rules/templates/list');
    return response;
  }

  /**
   * Get a specific template
   */
  static async getTemplate(templateId: string): Promise<{
    success: boolean;
    template: AlertRuleTemplate;
  }> {
    const response = await apiClient.get(`/alert-rules/templates/${templateId}`);
    return response;
  }

  /**
   * Create rule from template
   */
  static async createFromTemplate(
    templateId: string,
    params?: {
      property_id?: number;
      threshold_override?: number;
    }
  ): Promise<AlertRule> {
    const queryParams = new URLSearchParams();
    if (params?.property_id) queryParams.append('property_id', params.property_id.toString());
    if (params?.threshold_override) queryParams.append('threshold_override', params.threshold_override.toString());

    const response = await apiClient.post(
      `/alert-rules/templates/${templateId}/create?${queryParams.toString()}`
    );
    return response;
  }

  /**
   * Activate a rule
   */
  static async activateRule(ruleId: number): Promise<AlertRule> {
    const response = await apiClient.post(`/alert-rules/${ruleId}/activate`);
    return response;
  }

  /**
   * Deactivate a rule
   */
  static async deactivateRule(ruleId: number): Promise<AlertRule> {
    const response = await apiClient.post(`/alert-rules/${ruleId}/deactivate`);
    return response;
  }
}
