/**
 * Quality Alert Component
 * 
 * Shows post-upload quality summary with actionable buttons
 */

import { QualityBadge } from './QualityBadge'

interface QualityMetrics {
  total_records: number
  matched_records: number
  match_rate: number
  avg_confidence: number
  needs_review_count: number
  critical_count: number
  warning_count: number
  severity_level: 'critical' | 'warning' | 'info' | 'excellent'
  match_strategy_breakdown?: Record<string, number>
}

interface QualityAlertProps {
  severity: 'critical' | 'warning' | 'info' | 'excellent'
  metrics: QualityMetrics
  uploadId: number
  propertyCode: string
  documentType?: string
  onViewDetails: () => void
  onDismiss: () => void
}

export function QualityAlert({ 
  severity, 
  metrics, 
  uploadId, 
  propertyCode,
  documentType,
  onViewDetails,
  onDismiss 
}: QualityAlertProps) {
  
  const isRentRoll = documentType === 'rent_roll'
  
  const getMessage = () => {
    if (severity === 'critical') {
      return {
        title: '⚠️ Critical Quality Issues Detected',
        description: `${metrics.critical_count} critical items need immediate review`
      }
    } else if (severity === 'warning') {
      return {
        title: '⚡ Quality Warnings',
        description: `${metrics.warning_count} items may need review`
      }
    } else if (severity === 'excellent') {
      return {
        title: '✅ Excellent Quality',
        description: 'All data extracted with high confidence'
      }
    } else {
      return {
        title: 'ℹ️ Extraction Complete',
        description: 'Data extracted successfully'
      }
    }
  }
  
  const message = getMessage()
  
  return (
    <div className={`quality-modal ${severity}`}>
      <div className="modal-header">
        <h2>{message.title}</h2>
        <button onClick={onDismiss} className="close-btn">×</button>
      </div>
      
      <div className="modal-body">
        <p className="modal-description">{message.description}</p>
        
        <div className="quality-stats">
          <div className="stat-row">
            <span className="stat-label">Property:</span>
            <span className="stat-value">{propertyCode}</span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Total Records:</span>
            <span className="stat-value">{metrics.total_records}</span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">Match Rate:</span>
            <span className="stat-value">
              {metrics.match_rate.toFixed(1)}% ({metrics.matched_records}/{metrics.total_records})
            </span>
          </div>
          
          <div className="stat-row">
            <span className="stat-label">{isRentRoll ? 'Avg Validation Score:' : 'Avg Confidence:'}</span>
            <span className="stat-value">{metrics.avg_confidence.toFixed(1)}%</span>
          </div>
          
          {metrics.needs_review_count > 0 && (
            <>
              <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #e5e7eb' }} />
              
              <div className="stat-row">
                <span className="stat-label">Needs Review:</span>
                <span className="stat-value highlight">{metrics.needs_review_count} items</span>
              </div>
              
              {metrics.critical_count > 0 && (
                <div className="stat-row">
                  <span className="stat-label">Critical:</span>
                  <span className="stat-value critical-text">{metrics.critical_count} items</span>
                </div>
              )}
              
              {metrics.warning_count > 0 && (
                <div className="stat-row">
                  <span className="stat-label">Warnings:</span>
                  <span className="stat-value warning-text">{metrics.warning_count} items</span>
                </div>
              )}
            </>
          )}
          
          {/* Match Strategy Breakdown */}
          {metrics.match_strategy_breakdown && Object.keys(metrics.match_strategy_breakdown).length > 0 && (
            <>
              <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #e5e7eb' }} />
              
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="stat-label" style={{ fontWeight: 600 }}>Match Strategies:</span>
              </div>
              
              {Object.entries(metrics.match_strategy_breakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([strategy, count]) => (
                  <div key={strategy} className="stat-row" style={{ fontSize: '0.8125rem' }}>
                    <span className="stat-label">{strategy.replace(/_/g, ' ')}:</span>
                    <span className="stat-value">{count} items</span>
                  </div>
                ))}
            </>
          )}
        </div>
        
        <div className="modal-actions">
          {metrics.needs_review_count > 0 && (
            <button 
              onClick={onViewDetails} 
              className="btn-primary"
            >
              Review Items
            </button>
          )}
          <button onClick={onDismiss} className="btn-secondary">
            {metrics.needs_review_count > 0 ? 'Review Later' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  )
}

