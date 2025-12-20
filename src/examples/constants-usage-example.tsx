/**
 * Frontend Constants Usage Examples
 *
 * This file demonstrates how to use the centralized constants module
 * in your React components for consistent formatting and configuration.
 */

import {
  API_CONFIG,
  FINANCIAL_THRESHOLDS,
  CHART_COLORS,
  formatCurrency,
  formatPercentage,
  getDSCRColor,
  getOccupancyColor,
  getSeverityColor,
  NLQ_EXAMPLE_QUERIES,
} from '../config/constants';

// ==================== API Configuration Example ====================

export function ApiExample() {
  const fetchMetrics = async (propertyId: number) => {
    // Use centralized API_CONFIG instead of hardcoded URLs
    const response = await fetch(
      `${API_CONFIG.BASE_URL}/api/v1/metrics/${propertyId}`,
      {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      }
    );
    return response.json();
  };

  return null;
}

// ==================== Currency Formatting Example ====================

export function FinancialMetricsCard({ noi, revenue }: { noi: number; revenue: number }) {
  return (
    <div>
      {/* Compact format ($1.2M) */}
      <h3>NOI: {formatCurrency(noi, true)}</h3>

      {/* Full format ($1,234,567.00) */}
      <p>Revenue: {formatCurrency(revenue, false)}</p>
    </div>
  );
}

// ==================== DSCR Color Coding Example ====================

export function DSCRIndicator({ dscr }: { dscr: number }) {
  const color = getDSCRColor(dscr);

  return (
    <div style={{ color }}>
      DSCR: {dscr.toFixed(2)}
      {/* Color will be:
          - Green if dscr >= 1.50 (Excellent)
          - Blue if dscr >= 1.25 (Good)
          - Amber if dscr >= 1.10 (Warning)
          - Red if dscr < 1.10 (Critical)
      */}
    </div>
  );
}

// ==================== Occupancy Color Coding Example ====================

export function OccupancyBadge({ occupancy }: { occupancy: number }) {
  const color = getOccupancyColor(occupancy);

  return (
    <span style={{ backgroundColor: color, color: 'white', padding: '4px 8px', borderRadius: '4px' }}>
      {formatPercentage(occupancy, 1)}
      {/* Color will be:
          - Green if occupancy >= 95% (Excellent)
          - Blue if occupancy >= 90% (Good)
          - Amber if occupancy >= 85% (Warning)
          - Red if occupancy < 85% (Critical)
      */}
    </span>
  );
}

// ==================== Alert Severity Colors Example ====================

export function AlertCard({ severity, message }: { severity: string; message: string }) {
  const color = getSeverityColor(severity);

  return (
    <div style={{ borderLeft: `4px solid ${color}`, padding: '12px' }}>
      <span style={{ color, fontWeight: 'bold' }}>{severity}</span>
      <p>{message}</p>
    </div>
  );
}

// ==================== Threshold Checking Example ====================

export function VarianceAnalysis({ variance }: { variance: number }) {
  let status: string;
  let color: string;

  if (Math.abs(variance) >= FINANCIAL_THRESHOLDS.VARIANCE_URGENT_PCT) {
    status = 'URGENT';
    color = CHART_COLORS.URGENT;
  } else if (Math.abs(variance) >= FINANCIAL_THRESHOLDS.VARIANCE_CRITICAL_PCT) {
    status = 'CRITICAL';
    color = CHART_COLORS.CRITICAL;
  } else if (Math.abs(variance) >= FINANCIAL_THRESHOLDS.VARIANCE_WARNING_PCT) {
    status = 'WARNING';
    color = CHART_COLORS.WARNING_SEVERITY;
  } else {
    status = 'NORMAL';
    color = CHART_COLORS.NORMAL;
  }

  return (
    <div style={{ color }}>
      Variance: {formatPercentage(variance, 1)} - {status}
    </div>
  );
}

// ==================== NLQ Example Queries Usage ====================

export function NLQExamples() {
  const handleExampleClick = (query: string) => {
    // Execute the NLQ query
    console.log('Executing query:', query);
  };

  return (
    <div>
      <h3>Example Queries:</h3>
      {NLQ_EXAMPLE_QUERIES.map((query, index) => (
        <button
          key={index}
          onClick={() => handleExampleClick(query)}
          style={{ display: 'block', margin: '4px 0' }}
        >
          {query}
        </button>
      ))}
    </div>
  );
}

// ==================== Chart Configuration Example ====================

export function ChartExample({ data }: { data: any[] }) {
  return (
    <div>
      {/* Use consistent colors from constants */}
      <div style={{ color: CHART_COLORS.PRIMARY }}>Primary Data</div>
      <div style={{ color: CHART_COLORS.SUCCESS }}>Positive Trend</div>
      <div style={{ color: CHART_COLORS.WARNING }}>Needs Attention</div>
      <div style={{ color: CHART_COLORS.DANGER }}>Critical Issue</div>
    </div>
  );
}

// ==================== Complete Property Card Example ====================

export function PropertyCard({
  property,
  metrics,
}: {
  property: { name: string; code: string };
  metrics: {
    noi: number;
    revenue: number;
    dscr: number;
    occupancy: number;
  };
}) {
  return (
    <div style={{ border: '1px solid #ddd', padding: '16px', borderRadius: '8px' }}>
      <h2>{property.name}</h2>
      <p style={{ color: '#666' }}>{property.code}</p>

      <div style={{ marginTop: '16px' }}>
        <div>
          <strong>NOI:</strong> {formatCurrency(metrics.noi, true)}
        </div>
        <div>
          <strong>Revenue:</strong> {formatCurrency(metrics.revenue, true)}
        </div>

        <div style={{ marginTop: '12px' }}>
          <span style={{ color: getDSCRColor(metrics.dscr) }}>
            <strong>DSCR:</strong> {metrics.dscr.toFixed(2)}
          </span>
        </div>

        <div style={{ marginTop: '8px' }}>
          <strong>Occupancy:</strong>{' '}
          <span style={{ color: getOccupancyColor(metrics.occupancy) }}>
            {formatPercentage(metrics.occupancy, 1)}
          </span>
        </div>
      </div>

      {/* Threshold-based warnings */}
      {metrics.dscr < FINANCIAL_THRESHOLDS.DSCR_WARNING && (
        <div
          style={{
            marginTop: '12px',
            padding: '8px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '4px',
          }}
        >
          ⚠️ DSCR below threshold ({FINANCIAL_THRESHOLDS.DSCR_WARNING})
        </div>
      )}

      {metrics.occupancy < FINANCIAL_THRESHOLDS.OCCUPANCY_WARNING && (
        <div
          style={{
            marginTop: '12px',
            padding: '8px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '4px',
          }}
        >
          ⚠️ Occupancy below threshold ({FINANCIAL_THRESHOLDS.OCCUPANCY_WARNING}%)
        </div>
      )}
    </div>
  );
}

// ==================== API Error Handling with Retry Example ====================

export async function robustApiCall<T>(endpoint: string): Promise<T> {
  const { TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY } = API_CONFIG;

  for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);

      const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
        credentials: 'include',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        return await response.json();
      }

      // If not ok but not our last attempt, retry
      if (attempt < RETRY_ATTEMPTS - 1) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * (attempt + 1)));
        continue;
      }

      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    } catch (error) {
      if (attempt === RETRY_ATTEMPTS - 1) {
        throw error;
      }
      // Wait before retry with exponential backoff
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY * Math.pow(2, attempt)));
    }
  }

  throw new Error('Max retries exceeded');
}

// ==================== Benefits of Using Constants ====================

/*
 * BENEFITS:
 *
 * 1. CONSISTENCY
 *    - Same thresholds across all components
 *    - Same colors for same meanings
 *    - Same formatting rules
 *
 * 2. MAINTAINABILITY
 *    - Change threshold in one place, applies everywhere
 *    - Easy to adjust colors for branding
 *    - Central location for all configuration
 *
 * 3. TYPE SAFETY
 *    - IntelliSense for all constants
 *    - Compile-time checking
 *    - No magic numbers or strings
 *
 * 4. ALIGNMENT WITH BACKEND
 *    - Same thresholds as backend
 *    - Consistent business logic
 *    - No discrepancies between frontend/backend
 *
 * 5. EASY TESTING
 *    - Mock constants for unit tests
 *    - Test edge cases at exact thresholds
 *    - Predictable behavior
 */
