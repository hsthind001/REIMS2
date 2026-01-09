/**
 * NLQ Service - Complete Natural Language Query System
 *
 * Integrates with the comprehensive NLQ backend with:
 * - Temporal query support (10+ types)
 * - 50+ financial formulas
 * - Multi-agent orchestration
 * - Audit trail queries
 * - Reconciliation queries
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

export interface NLQQueryRequest {
  question: string;
  context?: {
    property_code?: string;
    property_id?: number;
    user_id?: number;
  };
  user_id?: number;
}

export interface NLQQueryResponse {
  success: boolean;
  answer: string;
  data?: any[];
  metadata?: {
    temporal_info?: {
      has_temporal: boolean;
      temporal_type?: string;
      filters?: Record<string, any>;
      normalized_expression?: string;
    };
    intent?: {
      primary_domain?: string;
      agent?: string;
    };
    agents_used?: string[];
    subqueries?: string[];
  };
  confidence_score: number;
  execution_time_ms?: number;
  query?: string;
  error?: string;
}

export interface TemporalParseResponse {
  has_temporal: boolean;
  temporal_type?: string;
  filters?: {
    year?: number;
    month?: number;
    start_date?: string;
    end_date?: string;
  };
  normalized_expression?: string;
}

export interface Formula {
  name: string;
  formula: string;
  explanation?: string;
  category: string;
  benchmark?: Record<string, string>;
  interpretation?: string;
  critical?: boolean;
  inputs?: string[];
}

export interface FormulasResponse {
  success: boolean;
  count: number;
  category?: string;
  formulas: Record<string, Formula>;
}

export interface CalculateMetricRequest {
  property_id: number;
  year: number;
  month: number;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  system: string;
  capabilities: string[];
  agents: string[];
  features: Record<string, boolean>;
}

class NLQService {
  /**
   * Execute natural language query
   */
  async query(request: NLQQueryRequest): Promise<NLQQueryResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.error || 'Query failed');
      }

      return await response.json();
    } catch (error) {
      console.error('NLQ query error:', error);
      throw error;
    }
  }

  /**
   * Parse temporal expression
   */
  async parseTemporal(query: string): Promise<TemporalParseResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/temporal/parse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error('Temporal parse failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Temporal parse error:', error);
      throw error;
    }
  }

  /**
   * Get all formulas or filter by category
   */
  async getFormulas(category?: string): Promise<FormulasResponse> {
    try {
      const url = category
        ? `${API_BASE_URL}/nlq/formulas?category=${category}`
        : `${API_BASE_URL}/nlq/formulas`;

      const response = await fetch(url, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch formulas');
      }

      return await response.json();
    } catch (error) {
      console.error('Get formulas error:', error);
      throw error;
    }
  }

  /**
   * Get specific formula details
   */
  async getFormula(metric: string): Promise<{ success: boolean; formula: Formula }> {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/formulas/${metric}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Formula not found');
      }

      return await response.json();
    } catch (error) {
      console.error('Get formula error:', error);
      throw error;
    }
  }

  /**
   * Calculate specific metric
   */
  async calculateMetric(
    metric: string,
    params: CalculateMetricRequest
  ): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/calculate/${metric}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error('Calculation failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Calculate metric error:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/nlq/health`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Health check failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const nlqService = new NLQService();
export default nlqService;
