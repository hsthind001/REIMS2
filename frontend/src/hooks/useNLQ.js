/**
 * useNLQ Hook - React hook for Natural Language Query functionality
 *
 * Provides state management and methods for NLQ queries
 *
 * @example
 * const { query, loading, error, result } = useNLQ();
 *
 * const handleSearch = async () => {
 *   await query("What was cash position in November 2025?", { property_code: "ESP" });
 * };
 */

import { useState, useCallback } from 'react';
import nlqService from '../services/nlqService';

export const useNLQ = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  /**
   * Execute NLQ query
   * @param {string} question - Natural language question
   * @param {object} context - Optional context (property_code, property_id)
   * @param {number} userId - Optional user ID
   * @returns {Promise} Query result
   */
  const query = useCallback(async (question, context = null, userId = 1) => {
    setLoading(true);
    setError(null);

    try {
      const response = await nlqService.query(question, context, userId);
      setResult(response);
      return response;
    } catch (err) {
      const errorMessage = err.message || 'Query failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Parse temporal expression
   * @param {string} temporalQuery - Query with temporal expression
   * @returns {Promise} Parsed temporal info
   */
  const parseTemporal = useCallback(async (temporalQuery) => {
    setLoading(true);
    setError(null);

    try {
      const response = await nlqService.parseTemporal(temporalQuery);
      return response;
    } catch (err) {
      const errorMessage = err.message || 'Temporal parsing failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Get all formulas
   * @param {string} category - Optional category filter
   * @returns {Promise} Formulas list
   */
  const getFormulas = useCallback(async (category = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await nlqService.getFormulas(category);
      return response;
    } catch (err) {
      const errorMessage = err.message || 'Failed to load formulas';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Calculate metric
   * @param {string} metric - Metric name
   * @param {object} params - Calculation parameters
   * @returns {Promise} Calculation result
   */
  const calculateMetric = useCallback(async (metric, params) => {
    setLoading(true);
    setError(null);

    try {
      const response = await nlqService.calculateMetric(metric, params);
      return response;
    } catch (err) {
      const errorMessage = err.message || 'Calculation failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    // Methods
    query,
    parseTemporal,
    getFormulas,
    calculateMetric,
    reset,

    // State
    loading,
    error,
    result
  };
};

export default useNLQ;
