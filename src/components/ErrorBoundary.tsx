/**
 * Error Boundary Component
 * 
 * Catches React errors and displays friendly error message
 * instead of blank page
 */

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { extractErrorMessage } from '../utils/errorHandling';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details to console for debugging
    console.error('🔴 React Error Boundary caught an error:');
    console.error('Error:', error);
    console.error('Error Info:', errorInfo);
    console.error('Component Stack:', errorInfo.componentStack);
    
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          maxWidth: '800px',
          margin: '100px auto'
        }}>
          <h1 style={{ color: '#dc2626', fontSize: '32px', marginBottom: '20px' }}>
            ⚠️ Application Error
          </h1>
          
          <div style={{
            background: '#fee',
            border: '1px solid #fcc',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '20px',
            textAlign: 'left'
          }}>
            <h2 style={{ fontSize: '18px', marginBottom: '10px' }}>Error Details:</h2>
            <pre style={{
              background: '#fff',
              padding: '10px',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '14px'
            }}>
              {extractErrorMessage(this.state.error, 'Unknown error occurred')}
            </pre>
          </div>

          {this.state.errorInfo && (
            <details style={{ marginBottom: '20px', textAlign: 'left' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
                Component Stack Trace
              </summary>
              <pre style={{
                background: '#f5f5f5',
                padding: '10px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                marginTop: '10px'
              }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}

          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              background: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            🔄 Reload Application
          </button>

          <div style={{ marginTop: '20px', fontSize: '14px', color: '#666' }}>
            <p>If this error persists:</p>
            <ol style={{ textAlign: 'left', maxWidth: '500px', margin: '10px auto' }}>
              <li>Check browser console (F12) for more details</li>
              <li>Try clearing browser cache (Ctrl + Shift + Delete)</li>
              <li>Restart backend services: <code>docker compose restart</code></li>
            </ol>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}


