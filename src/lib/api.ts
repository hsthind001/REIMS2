import { apiClient } from './apiClient';

export { ApiClient, ApiError } from './apiClient';

// Primary shared client
export const api = apiClient;

// Hook-friendly accessor for React components
export function useApi() {
  return apiClient;
}
