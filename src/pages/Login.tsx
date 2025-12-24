import { useEffect } from 'react'
import { useLocation, useNavigate, type Location } from 'react-router-dom'
import '../App.css'
import { LoginForm } from '../components/LoginForm'
import { useAuth } from '../components/AuthContext'

export default function LoginPage() {
  const { isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!loading && isAuthenticated) {
      const redirectTo = (location.state as { from?: Location })?.from?.pathname || '/'
      navigate(redirectTo, { replace: true })
    }
  }, [isAuthenticated, loading, navigate, location])

  if (loading) {
    return (
      <div className="app" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#0f172a' }}>Loading...</div>
          <div style={{ color: '#64748b' }}>Checking your session</div>
        </div>
      </div>
    )
  }

  return (
    <div className="app" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '520px', padding: '2rem' }}>
        <LoginForm />
      </div>
    </div>
  )
}
