/**
 * Safe Error Display Component
 * 
 * A React component that safely displays error messages, ensuring
 * they are always rendered as strings, never as objects.
 * 
 * This prevents "Objects are not valid as a React child" errors.
 */

import { extractErrorMessage } from '../utils/errorHandling';
import type { ErrorLike } from '../utils/errorHandling';

interface SafeErrorDisplayProps {
  /**
   * The error to display. Can be any error-like value.
   * Will be safely converted to a string.
   */
  error: ErrorLike;
  
  /**
   * Fallback message if error cannot be extracted
   */
  fallback?: string;
  
  /**
   * CSS class name for the error container
   */
  className?: string;
  
  /**
   * Whether to show as an alert (with styling)
   */
  alert?: boolean;
  
  /**
   * Alert variant: 'error', 'warning', 'info'
   */
  variant?: 'error' | 'warning' | 'info';
}

/**
 * Safely displays an error message, converting any error format to a string.
 * 
 * @example
 * ```tsx
 * // Safe - handles any error format
 * <SafeErrorDisplay error={apiError} />
 * 
 * // With styling
 * <SafeErrorDisplay error={err} alert variant="error" />
 * ```
 */
export function SafeErrorDisplay({
  error,
  fallback = "An error occurred",
  className = "",
  alert = false,
  variant = "error"
}: SafeErrorDisplayProps) {
  const message = extractErrorMessage(error, fallback);
  
  if (alert) {
    const alertClass = `alert alert-${variant}`;
    return (
      <div className={`${alertClass} ${className}`.trim()}>
        {message}
      </div>
    );
  }
  
  return (
    <span className={className}>
      {message}
    </span>
  );
}

/**
 * Hook version for inline use
 */
export function useSafeErrorMessage(error: ErrorLike, fallback: string = "An error occurred"): string {
  return extractErrorMessage(error, fallback);
}

