/**
 * Rules Service - API client for calculated forensic rules
 *
 * Provides:
 * - List active calculated rules
 * - Evaluate rules for a property/period
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class RulesService {
  async listCalculatedRules(propertyId = null) {
    try {
      const params = propertyId ? { property_id: propertyId } : {};
      const response = await axios.get(`${API_BASE_URL}/api/v1/forensic-reconciliation/calculated-rules`, { params });
      return response.data;
    } catch (error) {
      console.error('List calculated rules error:', error);
      throw this._handleError(error);
    }
  }

  async evaluateCalculatedRules(propertyId, periodId) {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/v1/forensic-reconciliation/calculated-rules/evaluate/${propertyId}/${periodId}`
      );
      return response.data;
    } catch (error) {
      console.error('Evaluate calculated rules error:', error);
      throw this._handleError(error);
    }
  }

  _handleError(error) {
    if (error.response) {
      return new Error(error.response.data.error || error.response.data.detail || 'Server error');
    } else if (error.request) {
      return new Error('No response from server. Ensure backend is running and API URL is correct.');
    }
    return new Error(error.message || 'Unknown error');
  }
}

export default new RulesService();
