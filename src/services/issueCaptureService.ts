/**
 * Issue Capture Service
 * 
 * Captures frontend errors and issues for the self-learning system.
 */

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
  private apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  }

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

      const response = await fetch(`${this.apiBaseUrl}/self-learning/capture-issue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(request)
      });

      return response.ok;
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

      const response = await fetch(`${this.apiBaseUrl}/self-learning/capture-issue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(request)
      });

      return response.ok;
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

      const response = await fetch(`${this.apiBaseUrl}/self-learning/capture-issue`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(request)
      });

      return response.ok;
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
      const response = await fetch(`${this.apiBaseUrl}/self-learning/preflight-check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          operation,
          ...params
        })
      });

      if (response.ok) {
        return await response.json();
      }

      return {
        warnings: [],
        auto_fixes: [],
        should_proceed: true
      };
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

