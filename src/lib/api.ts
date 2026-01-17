/**
 * API Client
 * 
 * Centralized API communication layer with error handling,
 * type safety, and session management
 */

import { extractErrorMessage } from '../utils/errorHandling';
import { useAuthStore } from '../store/authStore';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export interface ApiError {
  message: string;
  status: number;
  detail?: string | any;
  category?: 'network' | 'auth' | 'server' | 'client' | 'unknown';
  retryable?: boolean;
}

export type ErrorCategory = 'network' | 'auth' | 'server' | 'client' | 'unknown';

export class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL + API_PREFIX;
  }

  /**
   * Categorize error and determine if retryable
   */
  private categorizeError(status: number, error?: any): { category: ErrorCategory; retryable: boolean; message: string } {
    if (status === 0) {
      return {
        category: 'network',
        retryable: true,
        message: 'Network error - please check your connection and try again'
      };
    }
    
    if (status >= 500) {
      return {
        category: 'server',
        retryable: true,
        message: 'Server error - please try again in a moment'
      };
    }
    
    if (status === 401 || status === 403) {
      return {
        category: 'auth',
        retryable: false,
        message: 'Authentication required - please log in again'
      };
    }
    
    if (status >= 400 && status < 500) {
      return {
        category: 'client',
        retryable: false,
        message: 'Invalid request - please check your input'
      };
    }
    
    return {
      category: 'unknown',
      retryable: false,
      message: 'An unexpected error occurred'
    };
  }

  /**
   * Get user-friendly error message
   */
  private getUserFriendlyMessage(error: ApiError): string {
    if (error.message && error.message !== 'An error occurred') {
      return error.message;
    }
    
    const categorized = this.categorizeError(error.status, error.detail);
    return categorized.message;
  }

  /**
   * Generic request handler with error handling and retry logic
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestInit = {},
    retries: number = 2
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      credentials: 'include', // Important for session cookies
      redirect: 'follow', // Follow redirects (307 from FastAPI trailing slash)
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Inject Organization ID if available
    const currentOrg = useAuthStore.getState().currentOrganization;
    if (currentOrg) {
        // @ts-ignore
        defaultOptions.headers['X-Organization-ID'] = currentOrg.id.toString();
    }

    let lastError: ApiError | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, defaultOptions);

        // Handle non-OK responses
        if (!response.ok) {
          let error: ApiError;
          
            try {
            const errorData = await response.json();
            const categorized = this.categorizeError(response.status, errorData);
            error = {
              message: extractErrorMessage(errorData.detail || errorData.message || categorized.message),
              status: response.status,
              detail: errorData,
              category: categorized.category,
              retryable: categorized.retryable,
            };
          } catch {
            const categorized = this.categorizeError(response.status);
            error = {
              message: categorized.message,
              status: response.status,
              category: categorized.category,
              retryable: categorized.retryable,
            };
          }
          
          // If not retryable or last attempt, throw error
          if (!error.retryable || attempt === retries) {
            error.message = this.getUserFriendlyMessage(error);
            throw error;
          }
          
          // Wait before retry (exponential backoff)
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
          lastError = error;
          continue;
        }

        // Handle 204 No Content
        if (response.status === 204) {
          return {} as T;
        }

        return await response.json();
      } catch (error) {
        if ((error as ApiError).status !== undefined) {
          // API error - check if retryable
          const apiError = error as ApiError;
          if (!apiError.retryable || attempt === retries) {
            apiError.message = this.getUserFriendlyMessage(apiError);
            throw apiError;
          }
          lastError = apiError;
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
          continue;
        }
        
        // Network or other errors
        const networkError: ApiError = {
          message: 'Network error or server unavailable',
          status: 0,
          detail: error,
          category: 'network',
          retryable: true,
        };
        
        if (attempt === retries) {
          networkError.message = this.getUserFriendlyMessage(networkError);
          throw networkError;
        }
        
        lastError = networkError;
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }

    // Should never reach here, but TypeScript needs it
    if (lastError) {
      lastError.message = this.getUserFriendlyMessage(lastError);
      throw lastError;
    }
    
    throw {
      message: 'Request failed after retries',
      status: 0,
      category: 'unknown',
      retryable: false,
    } as ApiError;
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, params?: Record<string, any>): Promise<T> {
    let url = endpoint;
    
    if (params) {
      const queryString = new URLSearchParams(
        Object.entries(params)
          .filter(([_, v]) => v !== undefined && v !== null)
          .map(([k, v]) => [k, String(v)])
      ).toString();
      
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    return this.request<T>(url, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Upload file (multipart/form-data)
   */
  async uploadFile<T = any>(
    endpoint: string,
    formData: FormData
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        body: formData,
        // Don't set Content-Type - let browser set it with boundary
      });

      if (!response.ok) {
        const errorData = await response.json();
        // Use intelligent error extraction utility
        const errorMessage = extractErrorMessage(errorData.detail || errorData, 'Upload failed');
        throw {
          message: errorMessage,
          status: response.status,
          detail: errorData,
        } as ApiError;
      }

      return await response.json();
    } catch (error) {
      if ((error as ApiError).status) {
        throw error;
      }
      
      throw {
        message: 'Upload failed',
        status: 0,
        detail: error,
      } as ApiError;
    }
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export hook for React components
export function useApi() {
  return api;
}
