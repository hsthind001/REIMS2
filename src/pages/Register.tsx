import { useState } from 'react'
import '../App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface RegisterProps {
  onRegisterSuccess?: () => void
}

export default function Register({ onRegisterSuccess }: RegisterProps) {
  const [formData, setFormData] = useState({
    email: '',
    full_name: '',
    password: '',
    confirm_password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters')
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: formData.email,
          full_name: formData.full_name,
          password: formData.password
        })
      })

      if (response.ok) {
        setSuccess(true)
        if (onRegisterSuccess) {
          setTimeout(() => {
            onRegisterSuccess()
          }, 2000)
        }
      } else {
        const data = await response.json()
        throw new Error(data.detail || 'Registration failed')
      }
    } catch (err) {
      console.error('Registration error:', err)
      setError(err instanceof Error ? err.message : 'Registration failed')
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
          📝 Register for REIMS2
        </h1>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {success && (
          <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
            <span>✅</span>
            <span>Registration successful! Redirecting...</span>
          </div>
        )}

        {!success && (
          <form onSubmit={handleRegister}>
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="full_name">Full Name</label>
              <input
                id="full_name"
                type="text"
                className="form-input"
                placeholder="John Doe"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="john.doe@reims.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="Minimum 6 characters"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                minLength={6}
              />
            </div>

            <div className="form-group" style={{ marginBottom: '2rem' }}>
              <label htmlFor="confirm_password">Confirm Password</label>
              <input
                id="confirm_password"
                type="password"
                className="form-input"
                placeholder="Re-enter password"
                value={formData.confirm_password}
                onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                required
                minLength={6}
              />
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{ width: '100%' }}
            >
              {loading ? '🔄 Creating Account...' : '🚀 Register'}
            </button>
          </form>
        )}

        <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <p>Already have an account? Use the Login page.</p>
        </div>
      </div>
    </div>
  )
}
