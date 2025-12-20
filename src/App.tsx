import { useState, lazy, Suspense, useEffect } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './components/AuthContext'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'

// Lazy load pages for better initial bundle size
const CommandCenter = lazy(() => import('./pages/CommandCenter'))
const PortfolioHub = lazy(() => import('./pages/PortfolioHub'))
const FinancialCommand = lazy(() => import('./pages/FinancialCommand'))
const DataControlCenter = lazy(() => import('./pages/DataControlCenter'))
const AdminHub = lazy(() => import('./pages/AdminHub'))
const RiskManagement = lazy(() => import('./pages/RiskManagement'))
const AlertRules = lazy(() => import('./pages/AlertRules'))
const BulkImport = lazy(() => import('./pages/BulkImport'))
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'))
const NotificationCenter = lazy(() => import('./components/notifications/NotificationCenter'))

// Loading fallback component
const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>Loading...</div>
      <div style={{ color: 'var(--text-muted)' }}>Please wait</div>
    </div>
  </div>
)

type Page = 'dashboard' | 'properties' | 'reports' | 'operations' | 'users' | 'risk' | 'login' | 'register'

function AppContent() {
  console.log('🎨 AppContent: Component rendering');
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [hashRoute, setHashRoute] = useState<string>('')
  const { user, logout, isAuthenticated, loading } = useAuth()

  console.log('🎨 AppContent: Auth state - loading:', loading, 'isAuthenticated:', isAuthenticated);

  // Handle hash-based routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) // Remove the #
      setHashRoute(hash)
      // If navigating to bulk-import, ensure we're on operations page
      if (hash === 'bulk-import' && currentPage !== 'operations') {
        setCurrentPage('operations')
      }
      // If navigating to review-queue, ensure we're on operations page
      if (hash === 'review-queue' && currentPage !== 'operations') {
        setCurrentPage('operations')
      }
      // If navigating to alert-rules, ensure we're on risk page
      if (hash === 'alert-rules' && currentPage !== 'risk') {
        setCurrentPage('risk')
      }
    }

    // Check initial hash
    handleHashChange()

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [currentPage])

  // Show loading state while checking authentication
  if (loading) {
    console.log('🎨 AppContent: Showing loading state');
    return (
      <div className="app" style={{ minHeight: '100vh', backgroundColor: '#f8fafc' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh', 
          flexDirection: 'column',
          backgroundColor: '#ffffff',
          padding: '2rem'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem', color: '#0f172a' }}>Loading...</div>
          <div style={{ color: '#64748b' }}>Initializing application</div>
        </div>
      </div>
    )
  }

  const renderPage = () => {
    // Show login/register if not authenticated
    if (!isAuthenticated) {
      if (currentPage === 'register') {
        return <RegisterForm />
      }
      return <LoginForm />
    }

    // Show app pages if authenticated (with lazy loading)
    const PageComponent = () => {
      switch (currentPage) {
        case 'dashboard':
          return <CommandCenter />
        case 'properties':
          return <PortfolioHub />
        case 'reports':
          return <FinancialCommand />
        case 'operations':
          return <DataControlCenter />
        case 'users':
          return <AdminHub />
        case 'risk':
          // Check if hash route is alert-rules
          if (hashRoute === 'alert-rules') {
            return <AlertRules />
          }
          return <RiskManagement />
        default:
          return <CommandCenter />
      }
    }

    return (
      <Suspense fallback={<PageLoader />}>
        <PageComponent />
      </Suspense>
    )
  }

  const handleLogout = async () => {
    try {
      await logout()
      setCurrentPage('login')
    } catch (err) {
      console.error('Logout failed:', err)
    }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <button 
            className="menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
          <h1 className="app-title">REIMS 2.0</h1>
          <span className="app-subtitle">Real Estate Investment Management System</span>
        </div>
        <div className="header-right">
          {isAuthenticated ? (
            <>
              <NotificationCenter />
              <span className="user-info">👤 {user?.username}</span>
              <button className="btn-logout" onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <>
              <button 
                className={`btn-link ${currentPage === 'login' ? 'active' : ''}`}
                onClick={() => setCurrentPage('login')}
              >
                Login
              </button>
              <button 
                className={`btn-link ${currentPage === 'register' ? 'active' : ''}`}
                onClick={() => setCurrentPage('register')}
              >
                Register
              </button>
            </>
          )}
          <span className="status-indicator">●</span>
          <span className="status-text">Online</span>
        </div>
      </header>

      <div className="main-container">
        {/* Sidebar - 5 Strategic Pages Only */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="nav-menu">
            <button
              className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentPage('dashboard')}
            >
              <span className="nav-icon">📊</span>
              {sidebarOpen && <span className="nav-text">Command Center</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'properties' ? 'active' : ''}`}
              onClick={() => setCurrentPage('properties')}
            >
              <span className="nav-icon">🏢</span>
              {sidebarOpen && <span className="nav-text">Portfolio Hub</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'reports' ? 'active' : ''}`}
              onClick={() => setCurrentPage('reports')}
            >
              <span className="nav-icon">💰</span>
              {sidebarOpen && <span className="nav-text">Financial Command</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'operations' ? 'active' : ''}`}
              onClick={() => setCurrentPage('operations')}
            >
              <span className="nav-icon">🔧</span>
              {sidebarOpen && <span className="nav-text">Data Control Center</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'users' ? 'active' : ''}`}
              onClick={() => setCurrentPage('users')}
            >
              <span className="nav-icon">⚙️</span>
              {sidebarOpen && <span className="nav-text">Admin Hub</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'risk' ? 'active' : ''}`}
              onClick={() => setCurrentPage('risk')}
            >
              <span className="nav-icon">🛡️</span>
              {sidebarOpen && <span className="nav-text">Risk Management</span>}
            </button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="content">
          {hashRoute === 'bulk-import' ? (
            <Suspense fallback={<PageLoader />}>
              <BulkImport />
            </Suspense>
          ) : hashRoute === 'review-queue' ? (
            <Suspense fallback={<PageLoader />}>
              <ReviewQueue />
            </Suspense>
          ) : (
            renderPage()
          )}
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
