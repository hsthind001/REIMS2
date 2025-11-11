/**
 * Quality Badge Component
 * 
 * Displays quality severity level with color-coded badges
 * Supports detailed mode showing extraction vs match confidence breakdown
 */

interface QualityBadgeProps {
  severity: 'critical' | 'warning' | 'info' | 'excellent'
  count?: number
  showIcon?: boolean
  detailed?: boolean
  extractionConfidence?: number
  matchConfidence?: number
}

export function QualityBadge({ 
  severity, 
  count, 
  showIcon = true,
  detailed = false,
  extractionConfidence,
  matchConfidence
}: QualityBadgeProps) {
  const icons = {
    critical: '⚠️',
    warning: '⚡',
    info: 'ℹ️',
    excellent: '✓'
  }
  
  const labels = {
    critical: 'Critical',
    warning: 'Warning',
    info: 'Info',
    excellent: 'Excellent'
  }
  
  // Detailed mode: show confidence breakdown
  if (detailed && extractionConfidence !== undefined && matchConfidence !== undefined) {
    return (
      <span className={`quality-badge ${severity} detailed`}>
        {showIcon && <span>{icons[severity]}</span>}
        <span className="badge-label">{labels[severity]}</span>
        <span className="badge-details">
          <span className="extraction-conf" title="Extraction Confidence">
            E:{extractionConfidence.toFixed(0)}%
          </span>
          <span className="separator">|</span>
          <span className="match-conf" title="Match Confidence">
            M:{matchConfidence.toFixed(0)}%
          </span>
        </span>
        {count !== undefined && count > 0 && (
          <span className="badge-count">({count})</span>
        )}
      </span>
    )
  }
  
  // Standard mode
  return (
    <span className={`quality-badge ${severity}`}>
      {showIcon && <span>{icons[severity]}</span>}
      <span>{labels[severity]}</span>
      {count !== undefined && count > 0 && (
        <span className="badge-count">({count})</span>
      )}
    </span>
  )
}

