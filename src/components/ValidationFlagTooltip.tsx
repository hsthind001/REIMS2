/**
 * Validation Flag Tooltip Component
 * 
 * Shows detailed breakdown of validation issues for rent roll records
 * with visual indicators and specific field-level problems
 */

import { useState } from 'react'

interface ValidationFlag {
  severity: string
  field: string
  message: string
  expected?: string
  actual?: string
}

interface ValidationFlagTooltipProps {
  validationScore: number
  flags: ValidationFlag[]
  criticalCount: number
  warningCount: number
  infoCount: number
}

export function ValidationFlagTooltip({
  validationScore,
  flags,
  criticalCount,
  warningCount,
  infoCount
}: ValidationFlagTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)

  const getStatusLabel = () => {
    if (criticalCount > 0) return 'Critical Issues'
    if (warningCount > 0) return 'Warnings'
    if (validationScore >= 99) return 'Excellent'
    return 'Acceptable'
  }

  const getStatusColor = () => {
    if (criticalCount > 0) return '#dc2626'
    if (warningCount > 0) return '#f59e0b'
    return '#10b981'
  }

  const getValidationBar = (score: number) => {
    const percentage = Math.min(100, Math.max(0, score))
    let color = '#10b981'
    if (percentage < 95) color = '#dc2626'
    else if (percentage < 99) color = '#f59e0b'
    
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div style={{
          width: '120px',
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
        <span style={{ fontSize: '0.875rem', fontWeight: 600, minWidth: '50px' }}>
          {score.toFixed(1)}%
        </span>
      </div>
    )
  }

  const getSeverityIcon = (severity: string) => {
    if (severity === 'CRITICAL') return '⚠️'
    if (severity === 'WARNING') return '⚡'
    return 'ℹ️'
  }

  return (
    <div 
      className="validation-flag-tooltip-wrapper"
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
          className="validation-flag-tooltip-content"
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginTop: '0.5rem',
            width: '320px',
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
            Validation Summary
          </div>

          {/* Validation Score */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '0.25rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Quality Score
            </div>
            {getValidationBar(validationScore)}
          </div>

          {/* Flag Counts */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '0.5rem',
              fontSize: '0.75rem'
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, color: '#dc2626' }}>{criticalCount}</div>
                <div style={{ color: '#6b7280' }}>Critical</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, color: '#f59e0b' }}>{warningCount}</div>
                <div style={{ color: '#6b7280' }}>Warnings</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, color: '#6b7280' }}>{infoCount}</div>
                <div style={{ color: '#9ca3af' }}>Info</div>
              </div>
            </div>
          </div>

          {/* Validation Issues */}
          {flags.length > 0 && (
            <>
              <div style={{
                height: '1px',
                backgroundColor: '#e5e7eb',
                margin: '0.75rem 0'
              }} />
              
              <div style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#6b7280',
                marginBottom: '0.5rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Issues Detected
              </div>
              
              <div style={{
                maxHeight: '150px',
                overflowY: 'auto',
                fontSize: '0.8125rem'
              }}>
                {flags.slice(0, 5).map((flag, idx) => (
                  <div key={idx} style={{
                    padding: '0.375rem',
                    marginBottom: '0.25rem',
                    backgroundColor: flag.severity === 'CRITICAL' ? '#fef2f2' : flag.severity === 'WARNING' ? '#fffbeb' : '#f9fafb',
                    borderRadius: '0.25rem',
                    borderLeft: `3px solid ${flag.severity === 'CRITICAL' ? '#dc2626' : flag.severity === 'WARNING' ? '#f59e0b' : '#6b7280'}`
                  }}>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '0.375rem' }}>
                      <span>{getSeverityIcon(flag.severity)}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, marginBottom: '0.125rem' }}>
                          {flag.field || 'General'}
                        </div>
                        <div style={{ color: '#6b7280', fontSize: '0.75rem', lineHeight: '1.4' }}>
                          {flag.message}
                        </div>
                        {flag.expected && flag.actual && (
                          <div style={{ fontSize: '0.6875rem', color: '#9ca3af', marginTop: '0.125rem' }}>
                            Expected: {flag.expected} | Actual: {flag.actual}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {flags.length > 5 && (
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', textAlign: 'center', marginTop: '0.25rem' }}>
                    +{flags.length - 5} more issues
                  </div>
                )}
              </div>
            </>
          )}

          {/* Status */}
          <div style={{ marginTop: '0.75rem' }}>
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
            transform: 'translateX(-50%) rotate(45deg)',
            width: '12px',
            height: '12px',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRight: 'none',
            borderBottom: 'none'
          }} />
        </div>
      )}
    </div>
  )
}

