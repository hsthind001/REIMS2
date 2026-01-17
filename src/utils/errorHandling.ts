/**
 * Error Handling Utilities
 * 
 * Provides safe, intelligent error handling to prevent React rendering errors
 * and ensure all errors are properly converted to displayable strings.
 * 
 * This prevents the "Objects are not valid as a React child" error class.
 */

/**
 * Type definitions for various error formats
 */
export type ErrorLike = 
  | string
  | Error
  | { message?: string; detail?: string | object; error?: string; [key: string]: any }
  | null
  | undefined;

export interface ApiError {
  message: string;
  status?: number;
  detail?: string | object;
  [key: string]: any;
}

/**
 * Safely extracts a string message from any error-like value.
 * 
 * This function is intelligent enough to handle:
 * - Plain strings
 * - Error objects
 * - API error objects with nested structures
 * - Objects with message/detail/error properties
 * - Null/undefined values
 * 
 * @param error - Any error-like value
 * @param fallback - Fallback message if error cannot be extracted (default: "An error occurred")
 * @returns A safe string that can be rendered in React
 * 
 * @example
 * ```tsx
 * // Safe to use in JSX
 * <div>{extractErrorMessage(err)}</div>
 * 
 * // Handles all formats
 * extractErrorMessage("Simple string") // "Simple string"
 * extractErrorMessage(new Error("Error message")) // "Error message"
 * extractErrorMessage({ message: "API error" }) // "API error"
 * extractErrorMessage({ detail: { message: "Nested" } }) // "Nested"
 * extractErrorMessage(null) // "An error occurred"
 * ```
 */
export function extractErrorMessage(error: ErrorLike, fallback: string = "An error occurred"): string {
  // Handle null/undefined
  if (error === null || error === undefined) {
    return fallback;
  }

  // Handle plain strings
  if (typeof error === "string") {
    return error.trim() || fallback;
  }

  // Handle Error objects
  if (error instanceof Error) {
    return error.message || error.toString() || fallback;
  }

  // Handle objects
  if (typeof error === "object") {
    // Try message property first (most common)
    if (error.message) {
      if (typeof error.message === "string") {
        return error.message.trim() || fallback;
      }
      // If message is an object, recursively extract
      if (typeof error.message === "object") {
        const nested = extractErrorMessage(error.message, fallback);
        if (nested !== fallback) {
          return nested;
        }
      }
    }

    // Try error property
    if (error.error) {
      if (typeof error.error === "string") {
        return error.error.trim() || fallback;
      }
      if (typeof error.error === "object") {
        const nested = extractErrorMessage(error.error, fallback);
        if (nested !== fallback) {
          return nested;
        }
      }
    }

    // Try detail property (common in API errors)
    if (error.detail) {
      if (typeof error.detail === "string") {
        return error.detail.trim() || fallback;
      }
      // If detail is an object, try to extract message from it
      if (typeof error.detail === "object") {
        // Special handling for password_errors array
        if (Array.isArray((error.detail as any).password_errors)) {
          const errors = (error.detail as any).password_errors;
          const mainMsg = (error.detail as any).message || "";
          return mainMsg 
            ? `${mainMsg}: ${errors.join(", ")}`
            : errors.join(", ");
        }

        const detailMessage = extractErrorMessage(error.detail, "");
        if (detailMessage) {
          return detailMessage;
        }
      }
    }

    // Try msg property (alternative naming)
    if (error.msg && typeof error.msg === "string") {
      return error.msg.trim() || fallback;
    }

    // Last resort: try to stringify (but limit length for safety)
    try {
      const stringified = JSON.stringify(error);
      // Limit to 200 chars to avoid huge error messages
      return stringified.length > 200 
        ? stringified.substring(0, 200) + "..."
        : stringified;
    } catch {
      // If stringify fails, use fallback
      return fallback;
    }
  }

  // Fallback for any other type
  try {
    return String(error);
  } catch {
    return fallback;
  }
}

/**
 * Validates that a value is a safe string for React rendering.
 * 
 * @param value - Value to validate
 * @returns true if value is a non-empty string
 */
export function isSafeString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/**
 * Converts any value to a safe string for React rendering.
 * 
 * @param value - Value to convert
 * @param fallback - Fallback if conversion fails
 * @returns Safe string for rendering
 */
export function toSafeString(value: unknown, fallback: string = ""): string {
  if (isSafeString(value)) {
    return value;
  }
  
  if (value === null || value === undefined) {
    return fallback;
  }
  
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return fallback;
    }
  }
  
  return String(value) || fallback;
}

/**
 * Type guard to check if an error is an API error object.
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === "object" &&
    error !== null &&
    ("message" in error || "detail" in error || "error" in error)
  );
}

/**
 * Extracts error message from API error responses.
 * Handles FastAPI error format: { detail: string | object }
 */
export function extractApiErrorMessage(error: unknown, fallback: string = "API request failed"): string {
  if (isApiError(error)) {
    return extractErrorMessage(error, fallback);
  }
  
  // Handle unknown type by casting to ErrorLike
  return extractErrorMessage(error as ErrorLike, fallback);
}

/**
 * Runtime validation: Ensures a value can be safely rendered in React.
 * Throws a descriptive error if the value is not safe.
 * 
 * Use this in development to catch unsafe values early.
 */
export function assertSafeForRender(value: unknown, context: string = "render"): void {
  // Use Vite's import.meta.env instead of process.env
  const isDev = import.meta.env.DEV;
  
  if (isDev) {
    // Allow primitives
    if (value === null || value === undefined) {
      return; // null/undefined are safe (won't render)
    }
    
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return; // Primitives are safe
    }
    
    // Objects and arrays are NOT safe to render directly
    if (typeof value === "object") {
      console.error(
        `⚠️ [Error Handling] Unsafe value detected in ${context}:`,
        value,
        "\nUse extractErrorMessage() or toSafeString() to convert to a safe string."
      );
      // In development, we can throw to catch issues early
      // In production, we'll just log
      if (isDev) {
        throw new Error(
          `Cannot render object directly in ${context}. ` +
          `Use extractErrorMessage() or toSafeString() to convert to a string.`
        );
      }
    }
  }
}

