import { useEffect, useMemo, useState } from 'react'
import {
  getAllAccountsWithThresholds,
  getDefaultThreshold,
  setDefaultThreshold,
  saveThreshold,
  deleteThreshold,
  type AccountWithThreshold
} from '../../lib/anomalyThresholds'
import { RefreshCw, Save, Search, Settings, Undo2 } from 'lucide-react'

type DocOption = {
  value: string
  label: string
}

function toPercent(value?: number | null): number {
  if (value === undefined || value === null) return 0
  return Number(value) * 100
}

function toDecimalPercent(value: number): number {
  return value / 100
}

export default function ValueSetupPanel() {
  const [accounts, setAccounts] = useState<AccountWithThreshold[]>([])
  const [search, setSearch] = useState('')
  const [defaultThreshold, setDefaultThresholdState] = useState<number>(1) // percent view
  const [loading, setLoading] = useState(false)
  const [savingDefault, setSavingDefault] = useState(false)
  const [rowSaving, setRowSaving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<Record<string, number>>({})

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [defaultResp, accountsResp] = await Promise.all([
        getDefaultThreshold(),
        getAllAccountsWithThresholds(),
      ])
      setDefaultThresholdState(toPercent(defaultResp.default_threshold))
      setAccounts(accountsResp || [])
    } catch (err: any) {
      setError(err?.message || 'Failed to load value setup data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filteredAccounts = useMemo(() => {
    if (!search) return accounts
    const query = search.toLowerCase()
    return accounts.filter(
      (acc) =>
        acc.account_code?.toLowerCase().includes(query) ||
        acc.account_name?.toLowerCase().includes(query)
    )
  }, [accounts, search])

  const handleSaveDefault = async () => {
    setSavingDefault(true)
    setError(null)
    setSuccess(null)
    try {
      await setDefaultThreshold(toDecimalPercent(defaultThreshold))
      setSuccess('Global default threshold updated')
      // Refresh accounts so default column reflects the new value
      await loadData()
    } catch (err: any) {
      setError(err?.message || 'Failed to update default threshold')
    } finally {
      setSavingDefault(false)
    }
  }

  const handleSaveRow = async (account: AccountWithThreshold) => {
    const percentVal = editValues[account.account_code] ?? toPercent(account.threshold_value ?? account.default_threshold)
    const decimalVal = toDecimalPercent(percentVal)
    setRowSaving(account.account_code)
    setError(null)
    setSuccess(null)
    try {
      const updated = await saveThreshold(
        account.account_code,
        account.account_name,
        decimalVal,
        true
      )
      setAccounts(prev =>
        prev.map(acc =>
          acc.account_code === account.account_code
            ? { ...acc, threshold_value: Number(updated.threshold_value), is_custom: true }
            : acc
        )
      )
      setSuccess(`Saved threshold for ${account.account_code}`)
    } catch (err: any) {
      setError(err?.message || `Failed to save ${account.account_code}`)
    } finally {
      setRowSaving(null)
    }
  }

  const handleResetRow = async (account: AccountWithThreshold) => {
    setRowSaving(account.account_code)
    setError(null)
    setSuccess(null)
    try {
      await deleteThreshold(account.account_code)
      setAccounts(prev =>
        prev.map(acc =>
          acc.account_code === account.account_code
            ? { ...acc, threshold_value: null, is_custom: false }
            : acc
        )
      )
      setEditValues(prev => {
        const next = { ...prev }
        delete next[account.account_code]
        return next
      })
      setSuccess(`Reset ${account.account_code} to default`)
    } catch (err: any) {
      setError(err?.message || `Failed to reset ${account.account_code}`)
    } finally {
      setRowSaving(null)
    }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ margin: 0 }}>Value Setup — Anomaly Thresholds</h3>
          <p style={{ color: '#6b7280', margin: 0 }}>
            Set the global default threshold (percent of account value) and override specific accounts.
            Defaults apply when no custom threshold is defined.
          </p>
        </div>
        <button
          onClick={loadData}
          className="btn btn-secondary btn-sm"
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      {(error || success) && (
        <div className={`alert ${error ? 'alert-error' : 'alert-success'}`} style={{ marginBottom: '1rem' }}>
          {error || success}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1rem',
          alignItems: 'flex-start',
          marginBottom: '1rem',
          flexWrap: 'wrap'
        }}
      >
        <div className="card" style={{ border: '1px solid #e5e7eb', boxShadow: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Settings size={18} />
            <strong>Global Default Threshold</strong>
          </div>
          <label style={{ display: 'block', color: '#6b7280', marginBottom: '0.35rem' }}>Percent of account value</label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="number"
              min={0}
              step={0.01}
              value={defaultThreshold}
              onChange={(e) => setDefaultThresholdState(parseFloat(e.target.value))}
              className="form-input"
              style={{ maxWidth: '140px' }}
            />
            <span style={{ color: '#6b7280' }}>%</span>
            <button
              onClick={handleSaveDefault}
              className="btn btn-primary btn-sm"
              disabled={savingDefault}
              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Save size={16} />
              Save
            </button>
          </div>
        </div>

        <div className="card" style={{ border: '1px solid #e5e7eb', boxShadow: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Settings size={18} />
            <strong>Filters</strong>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: '1 1 260px' }}>
              <Search size={14} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
              <input
                type="text"
                placeholder="Search account code or name"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '28px', width: '100%' }}
              />
            </div>
          </div>
          <p style={{ color: '#6b7280', marginTop: '0.5rem', marginBottom: 0 }}>
            Showing thresholds across all documents. Use search to narrow results.
          </p>
        </div>
      </div>

      <div className="table-responsive" style={{ maxHeight: '520px', overflow: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ position: 'sticky', top: 0, background: '#fff' }}>Account Code</th>
              <th style={{ position: 'sticky', top: 0, background: '#fff' }}>Account Name</th>
              <th style={{ position: 'sticky', top: 0, background: '#fff', width: '160px' }}>Threshold (%)</th>
              <th style={{ position: 'sticky', top: 0, background: '#fff', width: '160px' }}>Status</th>
              <th style={{ position: 'sticky', top: 0, background: '#fff', width: '160px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '1rem' }}>Loading thresholds...</td>
              </tr>
            )}
            {!loading && filteredAccounts.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '1rem', color: '#6b7280' }}>
                  No accounts found for the selected filter.
                </td>
              </tr>
            )}
            {!loading && filteredAccounts.map(account => {
              const currentPercent = editValues[account.account_code] ?? toPercent(account.threshold_value ?? account.default_threshold)
              return (
                <tr key={account.account_code}>
                  <td style={{ whiteSpace: 'nowrap', fontWeight: 600 }}>{account.account_code}</td>
                  <td>{account.account_name}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <input
                        type="number"
                        step={0.01}
                        min={0}
                        value={currentPercent}
                        onChange={(e) =>
                          setEditValues(prev => ({
                            ...prev,
                            [account.account_code]: parseFloat(e.target.value)
                          }))
                        }
                        className="form-input"
                        style={{ maxWidth: '120px' }}
                      />
                      <span style={{ color: '#6b7280' }}>%</span>
                    </div>
                  </td>
                  <td>
                    {account.is_custom ? (
                      <span className="badge bg-green-100 text-green-700">Custom</span>
                    ) : (
                      <span className="badge bg-gray-100 text-gray-700">Default ({toPercent(account.default_threshold).toFixed(2)}%)</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleSaveRow(account)}
                        disabled={rowSaving === account.account_code}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <Save size={14} />
                        Save
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleResetRow(account)}
                        disabled={rowSaving === account.account_code || !account.is_custom}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                        title="Reset to global default"
                      >
                        <Undo2 size={14} />
                        Reset
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
