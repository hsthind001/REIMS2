/**
 * Match Info Tooltip Component
 * 
 * Shows detailed breakdown of extraction and matching confidence
 * with visual indicators and match strategy information
 */

import { useState } from 'react'

interface MatchInfoTooltipProps {
  extractionConfidence: number
  matchConfidence: number
  matchStrategy: string
  matchStrategyLabel: string
  matchStrategyDescription: string
  severity: 'critical' | 'warning' | 'excellent'
}

export function MatchInfoTooltip({
  extractionConfidence,
  matchConfidence,
  matchStrategy,
  matchStrategyLabel,
  matchStrategyDescription,
  severity
}: MatchInfoTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)

  const getStatusLabel = () => {
    if (severity === 'critical') return 'Needs Review'
    if (severity === 'warning') return 'Acceptable'
    return 'High Quality'
  }

  const getStatusColor = () => {
    if (severity === 'critical') return '#dc2626'
    if (severity === 'warning') return '#f59e0b'
    return '#10b981'
  }

  const getConfidenceBar = (confidence: number) => {
    const percentage = Math.min(100, Math.max(0, confidence))
    let color = '#10b981'
    if (percentage < 85) color = '#dc2626'
    else if (percentage < 95) color = '#f59e0b'
    
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div style={{
          width: '100px',
          height: '8px',
          backgroundColor: '#e5e7eb',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${percentage}%`,
            height: '100%',
            backgroundColor: color,
            transition: 'width 0.3s ease'
          }} />
        </div>
        <span style={{ fontSize: '0.875rem', fontWeight: 600, minWidth: '45px' }}>
          {confidence.toFixed(1)}%
        </span>
      </div>
    )
  }

  return (
    <div 
      className="match-info-tooltip-wrapper"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      {/* Trigger Icon */}
      <button
        className="tooltip-trigger"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'help',
          padding: '0.25rem',
          fontSize: '1rem',
          opacity: 0.7,
          transition: 'opacity 0.2s'
        }}
        onMouseEnter={() => setIsOpen(true)}
        onFocus={() => setIsOpen(true)}
      >
        ℹ️
      </button>

      {/* Tooltip Content */}
      {isOpen && (
        <div
          className="match-info-tooltip-content"
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginTop: '0.5rem',
            width: '300px',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
            padding: '1rem',
            zIndex: 1000,
            fontSize: '0.875rem'
          }}
        >
          {/* Title */}
          <div style={{
            fontWeight: 700,
            fontSize: '0.9375rem',
            marginBottom: '0.75rem',
            color: '#1f2937'
          }}>
            Quality Breakdown
          </div>

          {/* Extraction Confidence */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '0.25rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Extraction
            </div>
            {getConfidenceBar(extractionConfidence)}
          </div>

          {/* Match Confidence */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '0.25rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Matching
            </div>
            {getConfidenceBar(matchConfidence)}
          </div>

          {/* Divider */}
          <div style={{
            height: '1px',
            backgroundColor: '#e5e7eb',
            margin: '0.75rem 0'
          }} />

          {/* Match Strategy */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '0.25rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Strategy
            </div>
            <div style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              color: '#1f2937',
              marginBottom: '0.125rem'
            }}>
              {matchStrategyLabel}
            </div>
            <div style={{
              fontSize: '0.75rem',
              color: '#6b7280',
              lineHeight: '1.4'
            }}>
              {matchStrategyDescription}
            </div>
          </div>

          {/* Status */}
          <div>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '0.25rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Status
            </div>
            <div style={{
              display: 'inline-block',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              backgroundColor: `${getStatusColor()}15`,
              color: getStatusColor(),
              fontSize: '0.8125rem',
              fontWeight: 600
            }}>
              {getStatusLabel()}
            </div>
          </div>

          {/* Arrow */}
          <div style={{
            position: 'absolute',
            top: '-6px',
            left: '50%',
            width: '12px',
            height: '12px',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRight: 'none',
            borderBottom: 'none',
            transform: 'translateX(-50%) rotate(45deg)'
          }} />
        </div>
      )}
    </div>
  )
}
