/**
 * Confidence Indicator Component
 * 
 * Displays field-level confidence scores with color-coded visual indicator
 * Shows extraction engine information and conflict details in tooltip
 */

import { useState } from 'react';

export interface ConfidenceIndicatorProps {
  /** Confidence score between 0 and 1 (e.g., 0.85 for 85%) */
  confidence: number;
  /** Name of the extraction engine used */
  engine?: string;
  /** Whether there are conflicting values from multiple engines */
  hasConflicts?: boolean;
  /** List of conflicting values with their engines and confidences */
  conflictingValues?: Array<{
    engine: string;
    value: any;
    confidence: number;
  }>;
  /** Additional warnings or messages */
  warnings?: string[];
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show percentage label */
  showLabel?: boolean;
  /** Custom className for styling */
  className?: string;
}

/**
 * Get color based on confidence score
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.95) return '#10b981'; // green-500 - Excellent
  if (confidence >= 0.85) return '#84cc16'; // lime-500 - Good
  if (confidence >= 0.70) return '#eab308'; // yellow-500 - Fair
  if (confidence >= 0.50) return '#f97316'; // orange-500 - Low
  return '#ef4444'; // red-500 - Critical
}

/**
 * Get label based on confidence score
 */
function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.95) return 'Excellent';
  if (confidence >= 0.85) return 'Good';
  if (confidence >= 0.70) return 'Fair';
  if (confidence >= 0.50) return 'Low';
  return 'Critical';
}

/**
 * Get size-specific dimensions
 */
function getSizeDimensions(size: 'sm' | 'md' | 'lg') {
  const dimensions = {
    sm: { height: '6px', fontSize: '0.75rem', padding: '0.25rem' },
    md: { height: '8px', fontSize: '0.875rem', padding: '0.5rem' },
    lg: { height: '12px', fontSize: '1rem', padding: '0.75rem' }
  };
  return dimensions[size];
}

export function ConfidenceIndicator({
  confidence,
  engine,
  hasConflicts = false,
  conflictingValues = [],
  warnings = [],
  size = 'md',
  showLabel = true,
  className = ''
}: ConfidenceIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  
  // Normalize confidence to 0-1 range
  const normalizedConfidence = Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(normalizedConfidence * 100);
  
  const color = getConfidenceColor(normalizedConfidence);
  const label = getConfidenceLabel(normalizedConfidence);
  const dimensions = getSizeDimensions(size);
  
  // Determine if needs review
  const needsReview = normalizedConfidence < 0.70 || hasConflicts || warnings.length > 0;
  
  return (
    <div 
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Main container */}
      <div className="flex items-center gap-2">
        {/* Confidence bar */}
        <div 
          className="relative bg-gray-200 rounded-full overflow-hidden"
          style={{ 
            width: size === 'sm' ? '100px' : size === 'md' ? '150px' : '200px',
            height: dimensions.height
          }}
        >
          {/* Filled portion */}
          <div
            className="absolute top-0 left-0 h-full transition-all duration-300 ease-in-out rounded-full"
            style={{
              width: `${percentage}%`,
              backgroundColor: color
            }}
          />
        </div>
        
        {/* Label */}
        {showLabel && (
          <div className="flex items-center gap-1">
            <span 
              className="font-medium"
              style={{ 
                color: color,
                fontSize: dimensions.fontSize
              }}
            >
              {percentage}%
            </span>
            <span 
              className="text-gray-600"
              style={{ fontSize: dimensions.fontSize }}
            >
              {label}
            </span>
          </div>
        )}
        
        {/* Warning/Conflict Indicator */}
        {needsReview && (
          <span className="text-yellow-600" title="Needs Review">
            ⚠️
          </span>
        )}
        
        {hasConflicts && (
          <span className="text-orange-600" title="Has Conflicts">
            ⚡
          </span>
        )}
      </div>
      
      {/* Tooltip */}
      {showTooltip && (
        <div 
          className="absolute z-50 bottom-full left-0 mb-2 w-80 bg-gray-900 text-white text-sm rounded-lg shadow-lg"
          style={{ padding: dimensions.padding }}
        >
          {/* Confidence Details */}
          <div className="mb-2">
            <div className="font-semibold mb-1">Confidence Score</div>
            <div className="flex justify-between items-center">
              <span>{percentage}% - {label}</span>
              {engine && (
                <span className="text-gray-400 text-xs">Engine: {engine}</span>
              )}
            </div>
          </div>
          
          {/* Conflict Information */}
          {hasConflicts && conflictingValues.length > 0 && (
            <div className="mb-2 border-t border-gray-700 pt-2">
              <div className="font-semibold mb-1 text-orange-400">
                ⚡ Conflicting Values Detected
              </div>
              {conflictingValues.map((conflict, idx) => (
                <div key={idx} className="text-xs ml-2 mb-1">
                  <span className="text-gray-400">{conflict.engine}:</span>{' '}
                  <span className="text-white">{String(conflict.value)}</span>{' '}
                  <span className="text-green-400">({Math.round(conflict.confidence * 100)}%)</span>
                </div>
              ))}
            </div>
          )}
          
          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="border-t border-gray-700 pt-2">
              <div className="font-semibold mb-1 text-yellow-400">
                ⚠️ Warnings ({warnings.length})
              </div>
              {warnings.map((warning, idx) => (
                <div key={idx} className="text-xs ml-2 text-gray-300">
                  • {warning}
                </div>
              ))}
            </div>
          )}
          
          {/* Review Recommendation */}
          {needsReview && (
            <div className="border-t border-gray-700 pt-2 mt-2">
              <div className="text-xs text-yellow-300">
                📋 Manual review recommended
              </div>
            </div>
          )}
          
          {/* Tooltip arrow */}
          <div 
            className="absolute top-full left-4 w-0 h-0"
            style={{
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '6px solid #111827'
            }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Compact version for inline display (no label, smaller)
 */
export function ConfidenceIndicatorCompact({
  confidence,
  engine,
  hasConflicts,
  conflictingValues,
  warnings,
  className = ''
}: Omit<ConfidenceIndicatorProps, 'size' | 'showLabel'>) {
  return (
    <ConfidenceIndicator
      confidence={confidence}
      engine={engine}
      hasConflicts={hasConflicts}
      conflictingValues={conflictingValues}
      warnings={warnings}
      size="sm"
      showLabel={false}
      className={className}
    />
  );
}

/**
 * Badge version with just the percentage and color
 */
export function ConfidenceBadge({
  confidence,
  className = ''
}: Pick<ConfidenceIndicatorProps, 'confidence' | 'className'>) {
  const normalizedConfidence = Math.max(0, Math.min(1, confidence));
  const percentage = Math.round(normalizedConfidence * 100);
  const color = getConfidenceColor(normalizedConfidence);
  const label = getConfidenceLabel(normalizedConfidence);
  
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className}`}
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}`
      }}
      title={`${percentage}% - ${label}`}
    >
      {percentage}%
    </span>
  );
}

