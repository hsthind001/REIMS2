import { useState } from 'react'
import '../App.css'
import { useAuth } from '../components/AuthContext'
import { ApiError } from '../lib/apiClient'

interface LoginProps {
  onLoginSuccess?: () => void
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { login } = useAuth()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await login(formData)
      if (onLoginSuccess) {
        onLoginSuccess()
      }
    } catch (err: any) {
      console.error('Login error:', err)
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError('Invalid email or password')
        } else if (err.category === 'network' || err.category === 'timeout') {
          setError('Network error or server unavailable. Please check if the backend server is running.')
        } else {
          setError(err.message || 'Login failed')
        }
      } else {
        setError(err?.message || 'Invalid email or password')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container" style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '80vh'
    }}>
      <div className="card" style={{ maxWidth: '500px', width: '100%' }}>
        <h1 className="page-title" style={{ textAlign: 'center', marginBottom: '2rem' }}>
          🔐 Login to REIMS2
        </h1>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="admin@reims.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          <div className="form-group" style={{ marginBottom: '2rem' }}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              placeholder="Enter your password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: '100%' }}
          >
            {loading ? '🔄 Logging in...' : '🚀 Login'}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <p>Contact your administrator for credentials</p>
        </div>
      </div>
    </div>
  )
}
