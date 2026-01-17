/**
 * Download Utility Functions
 *
 * Centralized utilities for downloading files in the browser.
 * Replaces direct DOM manipulation patterns with reusable functions.
 */

/**
 * Download a Blob as a file
 *
 * @param blob - The Blob to download
 * @param filename - The filename for the downloaded file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    // Always revoke the URL to free memory
    URL.revokeObjectURL(url);
  }
}

/**
 * Download text content as a file
 *
 * @param content - The text content to download
 * @param filename - The filename for the downloaded file
 * @param mimeType - The MIME type (default: 'text/plain')
 */
export function downloadText(
  content: string,
  filename: string,
  mimeType: string = 'text/plain'
): void {
  const blob = new Blob([content], { type: mimeType });
  downloadBlob(blob, filename);
}

/**
 * Download JSON data as a file
 *
 * @param data - The data to serialize to JSON
 * @param filename - The filename for the downloaded file (should end with .json)
 * @param prettyPrint - Whether to pretty-print the JSON (default: true)
 */
export function downloadJSON(
  data: unknown,
  filename: string,
  prettyPrint: boolean = true
): void {
  const content = prettyPrint
    ? JSON.stringify(data, null, 2)
    : JSON.stringify(data);
  downloadText(content, filename, 'application/json');
}

/**
 * Download CSV data as a file
 *
 * @param data - Array of objects to convert to CSV
 * @param filename - The filename for the downloaded file (should end with .csv)
 * @param headers - Optional custom headers (uses object keys if not provided)
 */
export function downloadCSV<T extends Record<string, unknown>>(
  data: T[],
  filename: string,
  headers?: string[]
): void {
  if (data.length === 0) {
    console.warn('downloadCSV: No data to export');
    return;
  }

  const csvHeaders = headers || Object.keys(data[0]);

  const escapeCSV = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    const str = String(value);
    // Escape quotes and wrap in quotes if contains comma, quote, or newline
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const csvRows = [
    csvHeaders.join(','),
    ...data.map((row) =>
      csvHeaders.map((header) => escapeCSV(row[header])).join(',')
    ),
  ];

  const csvContent = csvRows.join('\n');
  downloadText(csvContent, filename, 'text/csv;charset=utf-8;');
}

/**
 * Download data from a URL (fetch and download)
 *
 * @param url - The URL to fetch
 * @param filename - The filename for the downloaded file
 * @param options - Optional fetch options
 */
export async function downloadFromURL(
  url: string,
  filename: string,
  options?: RequestInit
): Promise<void> {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  }
  const blob = await response.blob();
  downloadBlob(blob, filename);
}

/**
 * Generate a timestamped filename
 *
 * @param baseName - The base name for the file (without extension)
 * @param extension - The file extension (e.g., 'csv', 'json')
 * @returns Filename with timestamp (e.g., 'report-2026-01-16T12-30-45.csv')
 */
export function generateTimestampedFilename(
  baseName: string,
  extension: string
): string {
  const timestamp = new Date()
    .toISOString()
    .replace(/[:.]/g, '-')
    .slice(0, 19);
  return `${baseName}-${timestamp}.${extension}`;
}
