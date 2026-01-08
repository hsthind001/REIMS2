/**
 * NLQ Service - API client for Natural Language Query system
 *
 * Provides methods to interact with the NLQ backend:
 * - Query natural language questions
 * - Parse temporal expressions
 * - Get formulas and calculations
 * - Health checks
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class NLQService {
  /**
   * Send natural language query
   * @param {string} question - Natural language question
   * @param {object} context - Optional context (property_id, property_code, user_id)
   * @param {number} userId - User ID (default: 1)
   * @returns {Promise} Query response with answer, data, metadata, confidence
   *
   * @example
   * const result = await nlqService.query(
   *   "What was cash position in November 2025?",
   *   { property_code: "ESP" }
   * );
   */
  async query(question, context = null, userId = 1) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/nlq/query`, {
        question,
        context,
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('NLQ query error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Parse temporal expression from natural language
   * @param {string} query - Query with temporal expression
   * @returns {Promise} Parsed temporal information
   *
   * @example
   * const temporal = await nlqService.parseTemporal("last 3 months");
   * // Returns: { has_temporal: true, filters: { start_date, end_date }, ... }
   */
  async parseTemporal(query) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/nlq/temporal/parse`, {
        query
      });
      return response.data;
    } catch (error) {
      console.error('Temporal parse error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Get all available formulas
   * @param {string} category - Optional category filter (liquidity, mortgage, etc.)
   * @returns {Promise} List of formulas
   *
   * @example
   * const formulas = await nlqService.getFormulas("mortgage");
   */
  async getFormulas(category = null) {
    try {
      const params = category ? { category } : {};
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/formulas`, { params });
      return response.data;
    } catch (error) {
      console.error('Get formulas error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Get specific formula details
   * @param {string} metric - Formula metric name (e.g., 'dscr', 'current_ratio')
   * @returns {Promise} Formula details
   *
   * @example
   * const formula = await nlqService.getFormula("dscr");
   */
  async getFormula(metric) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/formulas/${metric}`);
      return response.data;
    } catch (error) {
      console.error('Get formula error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Calculate specific metric for a property/period
   * @param {string} metric - Metric name (dscr, current_ratio, etc.)
   * @param {object} params - Calculation parameters
   * @param {number} params.property_id - Property ID
   * @param {number} params.year - Year
   * @param {number} params.month - Month
   * @returns {Promise} Calculation result
   *
   * @example
   * const result = await nlqService.calculateMetric("dscr", {
   *   property_id: 1,
   *   year: 2025,
   *   month: 11
   * });
   */
  async calculateMetric(metric, params) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/nlq/calculate/${metric}`,
        params
      );
      return response.data;
    } catch (error) {
      console.error('Calculate metric error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Health check for NLQ system
   * @returns {Promise} System health status
   *
   * @example
   * const health = await nlqService.healthCheck();
   * console.log(health.status); // "healthy"
   */
  async healthCheck() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/health`);
      return response.data;
    } catch (error) {
      console.error('Health check error:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Handle API errors
   * @private
   */
  _handleError(error) {
    if (error.response) {
      // Server responded with error
      return new Error(error.response.data.error || error.response.data.detail || 'Server error');
    } else if (error.request) {
      // Request made but no response
      return new Error('No response from server. Please check if the NLQ service is running.');
    } else {
      // Other errors
      return new Error(error.message || 'Unknown error');
    }
  }
}

// Export singleton instance
export default new NLQService();
