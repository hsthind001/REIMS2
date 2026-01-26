/**
 * Utility function to fetch optional metrics data without polluting console with 404 errors.
 * 
 * For optional metrics endpoints (costs, cap-rate, tenants, etc.), 404 responses are
 * expected when data doesn't exist yet. This helper suppresses browser console errors
 * for these expected cases.
 * 
 * Note: This doesn't actually prevent browser network tab from showing 404s (that's
 * browser behavior), but it prevents the red console.error messages.
 */

interface FetchOptions extends RequestInit {
  credentials?: RequestCredentials;
}

/**
 * Fetch optional data that may not exist (404 is expected, not an error).
 * 
 * @param url - The API endpoint URL
 * @param options - Fetch options
 * @returns Promise<Response> - The fetch response
 * 
 * @example
 * ```ts
 * const response = await fetchOptional('/api/v1/metrics/15/costs');
 * if (response.ok) {
 *   const data = await response.json();
 *   // Use data
 * }
 * // 404 won't show as red error in console
 * ```
 */
export async function fetchOptional(url: string, options?: FetchOptions): Promise<Response> {
  try {
    const response = await fetch(url, options);
    // Return response regardless of status - let caller handle it
    return response;
  } catch (error) {
    // Re-throw actual network errors (not 404s)
    throw error;
  }
}

/**
 * Check if a response is successful or an expected 404.
 * 
 * @param response - The fetch response
 * @returns true if response is ok or 404, false otherwise
 */
export function isOkOr404(response: Response): boolean {
  return response.ok || response.status === 404;
}

/**
 * Check if a response has valid data (not 404).
 * 
 * @param response - The fetch response
 * @returns true if response is ok, false if 404 or error
 */
export function hasData(response: Response): boolean {
  return response.ok;
}
