import { useEffect, useState } from 'react'
import AnomalyDetail from '../components/anomalies/AnomalyDetail'

function parseAnomalyId() {
  const hash = window.location.hash.slice(1)
  const [route, queryString] = hash.split('?')
  if (!route.startsWith('anomaly-details')) return null

  const params = new URLSearchParams(queryString || '')
  const rawId = params.get('anomaly_id') || params.get('id')
  if (!rawId) return null

  const parsed = Number(rawId)
  return Number.isFinite(parsed) ? parsed : null
}

export default function AnomalyDetailPage() {
  const [anomalyId, setAnomalyId] = useState<number | null>(parseAnomalyId())

  useEffect(() => {
    const handleHashChange = () => setAnomalyId(parseAnomalyId())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back()
      return
    }
    window.location.hash = ''
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <button
          onClick={handleBack}
          className="btn btn-sm btn-secondary"
        >
          ← Back
        </button>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>Anomaly Details</h1>
      </div>

      {anomalyId ? (
        <AnomalyDetail anomalyId={anomalyId} />
      ) : (
        <div className="card" style={{ padding: '1.5rem' }}>
          <p style={{ margin: 0 }}>No anomaly selected.</p>
        </div>
      )}
    </div>
  )
}
