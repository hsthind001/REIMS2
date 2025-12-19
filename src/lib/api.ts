/**
 * API Client
 * 
 * Centralized API communication layer with error handling,
 * type safety, and session management
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export interface ApiError {
  message: string;
  status: number;
  detail?: string | any;
}

export class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL + API_PREFIX;
  }

  /**
   * Generic request handler with error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      credentials: 'include', // Important for session cookies
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, defaultOptions);

      // Handle non-OK responses
      if (!response.ok) {
        let error: ApiError;
        
        try {
          const errorData = await response.json();
          error = {
            message: errorData.detail || errorData.message || 'An error occurred',
            status: response.status,
            detail: errorData,
          };
        } catch {
          error = {
            message: response.statusText || 'An error occurred',
            status: response.status,
          };
        }
        
        throw error;
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      if ((error as ApiError).status) {
        throw error; // Re-throw API errors
      }
      
      // Network or other errors
      throw {
        message: 'Network error or server unavailable',
        status: 0,
        detail: error,
      } as ApiError;
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
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
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Upload file (multipart/form-data)
   */
  async uploadFile<T>(
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
        // Extract message from detail - handle both string and object cases
        let errorMessage = 'Upload failed';
        if (errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (typeof errorData.detail === 'object') {
            // If detail is an object, try to extract a message
            errorMessage = errorData.detail.message || errorData.detail.error || 'Upload failed';
          }
        } else if (errorData.message) {
          errorMessage = typeof errorData.message === 'string' ? errorData.message : 'Upload failed';
        }
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

