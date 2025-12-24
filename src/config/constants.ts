/**
 * Frontend Configuration Constants
 *
 * Centralizes all configuration values and constants
 * to improve maintainability and prevent hardcoding
 */

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
} as const;

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 1000,
  PAGE_SIZE_OPTIONS: [25, 50, 100, 200, 500],
} as const;

// Financial Thresholds (should match backend)
export const FINANCIAL_THRESHOLDS = {
  // DSCR
  DSCR_EXCELLENT: 1.50,
  DSCR_GOOD: 1.25,
  DSCR_WARNING: 1.10,
  DSCR_CRITICAL: 1.00,

  // Occupancy
  OCCUPANCY_EXCELLENT: 95.0,
  OCCUPANCY_GOOD: 90.0,
  OCCUPANCY_WARNING: 85.0,
  OCCUPANCY_CRITICAL: 80.0,

  // Variance
  VARIANCE_WARNING_PCT: 10.0,
  VARIANCE_CRITICAL_PCT: 25.0,
  VARIANCE_URGENT_PCT: 50.0,

  // Liquidity
  CURRENT_RATIO_MINIMUM: 1.5,
  QUICK_RATIO_MINIMUM: 1.0,
} as const;

// Chart Colors
export const CHART_COLORS = {
  PRIMARY: '#3b82f6', // blue-500
  SUCCESS: '#10b981', // green-500
  WARNING: '#f59e0b', // amber-500
  DANGER: '#ef4444', // red-500
  INFO: '#6366f1', // indigo-500
  SECONDARY: '#8b5cf6', // violet-500

  // Variance colors
  FAVORABLE: '#10b981',
  UNFAVORABLE: '#ef4444',
  NEUTRAL: '#6b7280',

  // Severity colors
  NORMAL: '#10b981',
  WARNING_SEVERITY: '#f59e0b',
  CRITICAL: '#ef4444',
  URGENT: '#dc2626',
} as const;

// Date Formats
export const DATE_FORMATS = {
  DISPLAY: 'MMM DD, YYYY',
  DISPLAY_LONG: 'MMMM DD, YYYY',
  DISPLAY_WITH_TIME: 'MMM DD, YYYY h:mm A',
  ISO: 'YYYY-MM-DD',
  MONTH_YEAR: 'MMM YYYY',
  YEAR: 'YYYY',
} as const;

// Number Formats
export const NUMBER_FORMATS = {
  CURRENCY_NO_DECIMALS: {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  },
  CURRENCY: {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  },
  PERCENTAGE: {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  },
  PERCENTAGE_NO_DECIMALS: {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  },
  DECIMAL_2: {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  },
} as const;

// File Upload
export const FILE_UPLOAD = {
  MAX_SIZE_MB: 50,
  MAX_SIZE_BYTES: 50 * 1024 * 1024,
  ACCEPTED_TYPES: {
    PDF: '.pdf',
    EXCEL: '.xlsx,.xls',
    WORD: '.docx,.doc',
    CSV: '.csv',
    IMAGE: '.jpg,.jpeg,.png',
  },
  CHUNK_SIZE_BYTES: 1024 * 1024, // 1MB chunks
} as const;

// Document Types
export const DOCUMENT_TYPES = {
  BALANCE_SHEET: 'Balance Sheet',
  INCOME_STATEMENT: 'Income Statement',
  CASH_FLOW: 'Cash Flow Statement',
  RENT_ROLL: 'Rent Roll',
  MORTGAGE_STATEMENT: 'Mortgage Statement',
  OTHER: 'Other',
} as const;

// Account Code Ranges
export const ACCOUNT_CODES = {
  REVENUE: { START: '4000', END: '4999', PREFIX: '4' },
  OPERATING_EXPENSE: { START: '5000', END: '5999', PREFIX: '5' },
  ADDITIONAL_EXPENSE: { START: '6000', END: '6999', PREFIX: '6' },
  MORTGAGE_INTEREST: { START: '7000', END: '7999', PREFIX: '7' },
  DEPRECIATION: { START: '8000', END: '8999', PREFIX: '8' },
} as const;

// Alert Severities
export const ALERT_SEVERITIES = {
  INFO: 'INFO',
  WARNING: 'WARNING',
  CRITICAL: 'CRITICAL',
  URGENT: 'URGENT',
} as const;

// Alert Types
export const ALERT_TYPES = {
  VARIANCE_BREACH: 'VARIANCE_BREACH',
  DSCR_BREACH: 'DSCR_BREACH',
  OCCUPANCY_BREACH: 'OCCUPANCY_BREACH',
  LIQUIDITY_BREACH: 'LIQUIDITY_BREACH',
  STATISTICAL_ANOMALY: 'STATISTICAL_ANOMALY',
  DATA_QUALITY: 'DATA_QUALITY',
} as const;

// Special Unit Types (excluded from occupancy)
export const SPECIAL_UNIT_TYPES = [
  'COMMON',
  'ATM',
  'LAND',
  'SIGN',
  'STORAGE',
  'MECH',
  'ELEC',
] as const;

// Review Queue Filters
export const REVIEW_FILTERS = {
  PENDING: 'pending',
  REVIEWED: 'reviewed',
  ALL: 'all',
} as const;

// Export Types
export const EXPORT_TYPES = {
  PDF: 'pdf',
  EXCEL: 'excel',
  CSV: 'csv',
} as const;

// Report Types
export const REPORT_TYPES = {
  FINANCIAL_SUMMARY: 'financial_summary',
  VARIANCE_ANALYSIS: 'variance_analysis',
  PORTFOLIO_OVERVIEW: 'portfolio_overview',
  PROPERTY_PERFORMANCE: 'property_performance',
  RENT_ROLL_SUMMARY: 'rent_roll_summary',
} as const;

// NLQ Example Queries
export const NLQ_EXAMPLE_QUERIES = [
  'What is the total NOI for all properties in 2024?',
  'Show me properties with DSCR below 1.25',
  'Which properties have the highest occupancy rate?',
  'What is the average cap rate across all retail properties?',
  'List properties with rent growth above 5% last year',
  'Show me all properties in California with NOI over $1M',
  'What are the top 3 performing properties by NOI?',
  'Which tenants are expiring in the next 6 months?',
  'What is the total debt across all properties?',
  'Show properties with negative cash flow',
] as const;

// Cache Keys
export const CACHE_KEYS = {
  USER: 'user',
  PROPERTIES: 'properties',
  FINANCIAL_PERIODS: 'financial_periods',
  METRICS: 'metrics',
} as const;

// Cache TTLs (milliseconds)
export const CACHE_TTLS = {
  USER: 15 * 60 * 1000, // 15 minutes
  PROPERTIES: 60 * 60 * 1000, // 1 hour
  FINANCIAL_PERIODS: 60 * 60 * 1000, // 1 hour
  METRICS: 5 * 60 * 1000, // 5 minutes
} as const;

// WebSocket Events
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  DOCUMENT_PROCESSED: 'document_processed',
  METRICS_UPDATED: 'metrics_updated',
  ALERT_CREATED: 'alert_created',
  TASK_COMPLETED: 'task_completed',
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_PREFERENCES: 'user_preferences',
  SELECTED_PROPERTY: 'selected_property',
  THEME: 'theme',
} as const;

// Feature Flags
export const FEATURES = {
  NLQ_ENABLED: import.meta.env.VITE_FEATURE_NLQ === 'true',
  AI_FEATURES_ENABLED: import.meta.env.VITE_FEATURE_AI === 'true',
  BULK_IMPORT_ENABLED: import.meta.env.VITE_FEATURE_BULK_IMPORT === 'true',
  ADVANCED_ANALYTICS_ENABLED: import.meta.env.VITE_FEATURE_ANALYTICS === 'true',
} as const;

// Helper Functions
export const formatCurrency = (value: number | null | undefined, compact = false): string => {
  if (value === null || value === undefined) return 'N/A';

  if (compact && Math.abs(value) >= 1000) {
    const suffixes = ['', 'K', 'M', 'B'];
    const tier = Math.log10(Math.abs(value)) / 3 | 0;
    const suffix = suffixes[tier];
    const scale = Math.pow(10, tier * 3);
    const scaled = value / scale;
    return `$${scaled.toFixed(1)}${suffix}`;
  }

  return new Intl.NumberFormat('en-US', NUMBER_FORMATS.CURRENCY).format(value);
};

export const formatPercentage = (value: number | null | undefined, decimals = 1): string => {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(decimals)}%`;
};

export const formatNumber = (value: number | null | undefined, decimals = 0): string => {
  if (value === null || value === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

export const getDSCRColor = (dscr: number | null | undefined): string => {
  if (!dscr) return CHART_COLORS.NEUTRAL;
  if (dscr >= FINANCIAL_THRESHOLDS.DSCR_EXCELLENT) return CHART_COLORS.SUCCESS;
  if (dscr >= FINANCIAL_THRESHOLDS.DSCR_GOOD) return CHART_COLORS.INFO;
  if (dscr >= FINANCIAL_THRESHOLDS.DSCR_WARNING) return CHART_COLORS.WARNING;
  return CHART_COLORS.DANGER;
};

export const getOccupancyColor = (occupancy: number | null | undefined): string => {
  if (!occupancy) return CHART_COLORS.NEUTRAL;
  if (occupancy >= FINANCIAL_THRESHOLDS.OCCUPANCY_EXCELLENT) return CHART_COLORS.SUCCESS;
  if (occupancy >= FINANCIAL_THRESHOLDS.OCCUPANCY_GOOD) return CHART_COLORS.INFO;
  if (occupancy >= FINANCIAL_THRESHOLDS.OCCUPANCY_WARNING) return CHART_COLORS.WARNING;
  return CHART_COLORS.DANGER;
};

export const getSeverityColor = (severity: string): string => {
  switch (severity.toUpperCase()) {
    case ALERT_SEVERITIES.NORMAL:
      return CHART_COLORS.NORMAL;
    case ALERT_SEVERITIES.WARNING:
      return CHART_COLORS.WARNING_SEVERITY;
    case ALERT_SEVERITIES.CRITICAL:
      return CHART_COLORS.CRITICAL;
    case ALERT_SEVERITIES.URGENT:
      return CHART_COLORS.URGENT;
    default:
      return CHART_COLORS.NEUTRAL;
  }
};
