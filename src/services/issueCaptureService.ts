import { apiClient } from '../lib/apiClient';

interface CaptureIssueRequest {
  error_message: string;
  issue_category: 'frontend' | 'backend' | 'extraction' | 'validation' | 'ml_ai';
  severity?: 'critical' | 'error' | 'warning' | 'info';
  context?: Record<string, any>;
  upload_id?: number;
  document_type?: string;
  property_id?: number;
  period_id?: number;
}

class IssueCaptureService {
  /**
   * Capture a frontend error
   */
  async captureError(
    error: Error,
    context?: Record<string, any>
  ): Promise<boolean> {
    try {
      const request: CaptureIssueRequest = {
        error_message: error.message,
        issue_category: 'frontend',
        severity: 'error',
        context: {
          ...context,
          stack: error.stack,
          userAgent: navigator.userAgent,
          url: window.location.href,
          timestamp: new Date().toISOString()
        }
      };

      await apiClient.post('/self-learning/capture-issue', request);
      return true;
    } catch (e) {
      console.error('Failed to capture error:', e);
      return false;
    }
  }

  /**
   * Capture an API error
   */
  async captureApiError(
    endpoint: string,
    method: string,
    statusCode: number,
    errorMessage: string,
    context?: Record<string, any>
  ): Promise<boolean> {
    try {
      const request: CaptureIssueRequest = {
        error_message: `API Error: ${method} ${endpoint} returned ${statusCode}: ${errorMessage}`,
        issue_category: 'backend',
        severity: statusCode >= 500 ? 'error' : 'warning',
        context: {
          ...context,
          endpoint,
          method,
          statusCode,
          url: window.location.href,
          timestamp: new Date().toISOString()
        }
      };

      await apiClient.post('/self-learning/capture-issue', request);
      return true;
    } catch (e) {
      console.error('Failed to capture API error:', e);
      return false;
    }
  }

  /**
   * Capture a UI/rendering issue
   */
  async captureUIIssue(
    issueDescription: string,
    component?: string,
    context?: Record<string, any>
  ): Promise<boolean> {
    try {
      const request: CaptureIssueRequest = {
        error_message: `UI Issue: ${issueDescription}`,
        issue_category: 'frontend',
        severity: 'warning',
        context: {
          ...context,
          component,
          url: window.location.href,
          timestamp: new Date().toISOString()
        }
      };

      await apiClient.post('/self-learning/capture-issue', request);
      return true;
    } catch (e) {
      console.error('Failed to capture UI issue:', e);
      return false;
    }
  }

  /**
   * Get pre-flight warnings before an operation
   */
  async getPreflightWarnings(
    operation: 'upload' | 'extraction',
    params: {
      document_type?: string;
      property_code?: string;
      filename?: string;
      file_size?: number;
      context?: Record<string, any>;
    }
  ): Promise<{
    warnings: string[];
      auto_fixes: any[];
      should_proceed: boolean;
    }> {
    try {
      return await apiClient.post('/self-learning/preflight-check', {
        operation,
        ...params
      });
    } catch (e) {
      console.error('Failed to get preflight warnings:', e);
      return {
        warnings: [],
        auto_fixes: [],
        should_proceed: true
      };
    }
  }
}

// Create singleton instance
export const issueCaptureService = new IssueCaptureService();

// Global error handler
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    issueCaptureService.captureError(
      new Error(event.message),
      {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }
    );
  });

  window.addEventListener('unhandledrejection', (event) => {
    issueCaptureService.captureError(
      new Error(event.reason?.message || 'Unhandled promise rejection'),
      {
        reason: event.reason
      }
    );
  });
}

export default issueCaptureService;
