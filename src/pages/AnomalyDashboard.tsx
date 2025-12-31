/**
 * Enhanced Anomaly Detection Dashboard
 * World-class anomaly detection with ML, XAI, active learning, and portfolio intelligence
 */
import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Search, Eye, AlertCircle, Brain, RefreshCw, FileText } from 'lucide-react'
import { anomaliesService, type Anomaly, type UncertainAnomaly } from '../lib/anomalies'
import { LearnedPatternsList } from '../components/anomalies/LearnedPatternsList'
import { BatchReprocessingForm } from '../components/anomalies/BatchReprocessingForm'

type TabType = 'all' | 'uncertain' | 'batch' | 'patterns'

export default function AnomalyDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('all')
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [uncertainAnomalies, setUncertainAnomalies] = useState<UncertainAnomaly[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [propertyId, setPropertyId] = useState<number | null>(null)

  useEffect(() => {
    if (activeTab === 'all') {
      loadAnomalies()
    } else if (activeTab === 'uncertain') {
      loadUncertainAnomalies()
    }
  }, [activeTab, severityFilter, propertyId])

  const loadAnomalies = async () => {
    setLoading(true)
    try {
      const data = await anomaliesService.getAnomalies({
        severity: severityFilter || undefined,
        property_id: propertyId || undefined,
      })
      setAnomalies(data)
    } catch (error) {
      console.error('Failed to load anomalies:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadUncertainAnomalies = async () => {
    setLoading(true)
    try {
      const data = await anomaliesService.getUncertainAnomalies(50)
      setUncertainAnomalies(data)
    } catch (error) {
      console.error('Failed to load uncertain anomalies:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetails = (anomalyId: number) => {
    window.location.hash = `anomaly-details?anomaly_id=${anomalyId}`
  }

  const handleExport = async (format: 'csv' | 'excel' | 'json') => {
    setExporting(true)
    try {
      let blob: Blob | any
      let filename: string

      if (format === 'csv') {
        blob = await anomaliesService.exportAnomaliesCSV({
          property_ids: propertyId ? [propertyId] : undefined,
          severity: severityFilter || undefined,
        })
        filename = `anomalies_export_${new Date().toISOString().split('T')[0]}.csv`
      } else if (format === 'excel') {
        blob = await anomaliesService.exportAnomaliesExcel({
          property_ids: propertyId ? [propertyId] : undefined,
          severity: severityFilter || undefined,
        })
        filename = `anomalies_export_${new Date().toISOString().split('T')[0]}.xlsx`
      } else {
        const data = await anomaliesService.exportAnomaliesJSON({
          property_ids: propertyId ? [propertyId] : undefined,
          severity: severityFilter || undefined,
        })
        blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        filename = `anomalies_export_${new Date().toISOString().split('T')[0]}.json`
      }

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Failed to export anomalies:', error)
      alert('Failed to export anomalies. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const filteredAnomalies = anomalies.filter((anomaly) => {
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase()
      return (
        anomaly.account_code?.toLowerCase().includes(searchLower) ||
        anomaly.field_name?.toLowerCase().includes(searchLower) ||
        anomaly.message?.toLowerCase().includes(searchLower) ||
        anomaly.anomaly_type?.toLowerCase().includes(searchLower)
      )
    }
    return true
  })

  const chartData = filteredAnomalies.reduce((acc: any, anomaly: Anomaly) => {
    acc[anomaly.anomaly_type] = (acc[anomaly.anomaly_type] || 0) + 1
    return acc
  }, {})

  const chartDataArray = Object.entries(chartData).map(([type, count]) => ({
    type: type.replace(/_/g, ' '),
    count,
  }))

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Anomaly Detection Dashboard</h1>
            <p className="text-gray-600 mt-2">World-class ML-powered anomaly detection with XAI and active learning</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <select
                defaultValue=""
                onChange={(e) => {
                  const format = e.target.value as 'csv' | 'excel' | 'json'
                  if (format) {
                    handleExport(format)
                    e.target.value = '' // Reset select
                  }
                }}
                disabled={exporting}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Export...</option>
                <option value="csv">Export CSV</option>
                <option value="excel">Export Excel</option>
                <option value="json">Export JSON</option>
              </select>
            </div>
            <button
              onClick={() => (activeTab === 'all' ? loadAnomalies() : loadUncertainAnomalies())}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
            >
              <RefreshCw size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'all', label: 'All Anomalies', icon: AlertCircle },
            { id: 'uncertain', label: 'Uncertain (Need Feedback)', icon: Brain },
            { id: 'batch', label: 'Batch Reprocessing', icon: FileText },
            { id: 'patterns', label: 'Learned Patterns', icon: Brain },
          ].map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`
                  flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Batch Reprocessing Tab */}
      {activeTab === 'batch' && (
        <BatchReprocessingForm />
      )}

      {/* Learned Patterns Tab */}
      {activeTab === 'patterns' && propertyId && (
        <LearnedPatternsList propertyId={propertyId} />
      )}

      {/* All Anomalies & Uncertain Anomalies Tabs */}
      {(activeTab === 'all' || activeTab === 'uncertain') && (
        <>
          {/* Filters */}
          <div className="mb-6 flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Search anomalies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Total Anomalies</div>
              <div className="text-3xl font-bold text-gray-900">
                {activeTab === 'all' ? filteredAnomalies.length : uncertainAnomalies.length}
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Critical</div>
              <div className="text-3xl font-bold text-red-600">
                {(activeTab === 'all' ? filteredAnomalies : uncertainAnomalies).filter(
                  (a) => a.severity === 'critical'
                ).length}
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">High</div>
              <div className="text-3xl font-bold text-orange-600">
                {(activeTab === 'all' ? filteredAnomalies : uncertainAnomalies).filter(
                  (a) => a.severity === 'high'
                ).length}
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Medium</div>
              <div className="text-3xl font-bold text-yellow-600">
                {(activeTab === 'all' ? filteredAnomalies : uncertainAnomalies).filter(
                  (a) => a.severity === 'medium'
                ).length}
              </div>
            </div>
          </div>

          {/* Chart */}
          {activeTab === 'all' && chartDataArray.length > 0 && (
            <div className="bg-white p-6 rounded-lg shadow mb-6">
              <h2 className="text-xl font-semibold mb-4">Anomaly Distribution by Type</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartDataArray}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="type" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Anomaly Table */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                  {activeTab === 'uncertain' && (
                    <>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uncertainty</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days Since</th>
                    </>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Detected</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={activeTab === 'uncertain' ? 8 : 7} className="px-6 py-8 text-center text-gray-500">
                      Loading anomalies...
                    </td>
                  </tr>
                ) : (activeTab === 'all' ? filteredAnomalies : uncertainAnomalies).length === 0 ? (
                  <tr>
                    <td colSpan={activeTab === 'uncertain' ? 8 : 7} className="px-6 py-8 text-center text-gray-500">
                      No anomalies found
                    </td>
                  </tr>
                ) : (
                  (activeTab === 'all' ? filteredAnomalies : uncertainAnomalies).map((anomaly) => (
                    <tr key={anomaly.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {anomaly.anomaly_type?.replace(/_/g, ' ') || 'N/A'}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            anomaly.severity === 'critical'
                              ? 'bg-red-100 text-red-800'
                              : anomaly.severity === 'high'
                              ? 'bg-orange-100 text-orange-800'
                              : anomaly.severity === 'medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {anomaly.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">{anomaly.account_code}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {anomaly.actual_value
                          ? new Intl.NumberFormat('en-US', {
                              style: 'currency',
                              currency: 'USD',
                            }).format(anomaly.actual_value)
                          : 'N/A'}
                      </td>
                      {activeTab === 'uncertain' && 'uncertainty_score' in anomaly && (
                        <>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {anomaly.confidence ? `${Math.round(anomaly.confidence * 100)}%` : 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {anomaly.uncertainty_score ? anomaly.uncertainty_score.toFixed(2) : 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {anomaly.days_since_detection || 0} days
                          </td>
                        </>
                      )}
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {new Date(anomaly.detected_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleViewDetails(anomaly.id)}
                          className="text-blue-600 hover:text-blue-700 flex items-center gap-1 text-sm font-medium"
                        >
                          <Eye size={16} />
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

    </div>
  )
}
