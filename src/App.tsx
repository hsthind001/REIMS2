import { useState, lazy, Suspense } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  Outlet,
  useNavigate,
  useLocation,
} from 'react-router-dom'
import './App.css'
import { AuthProvider, useAuth } from './components/AuthContext'
import LoginPage from './pages/Login'
import RegisterPage from './pages/Register'

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
const WorkflowLocks = lazy(() => import('./pages/WorkflowLocks'))
const NotificationCenter = lazy(() => import('./components/notifications/NotificationCenter'))
const ForensicReconciliation = lazy(() => import('./pages/ForensicReconciliation'))
const Reconciliation = lazy(() => import('./pages/Reconciliation'))

// Loading fallback component
const PageLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>Loading...</div>
      <div style={{ color: 'var(--text-muted)' }}>Please wait</div>
    </div>
  </div>
)

function LoadingScreen() {
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

function ProtectedLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await logout()
      navigate('/login')
    } catch (err) {
      console.error('Logout failed:', err)
    }
  }

  const navItems = [
    { to: '/', label: 'Command Center', icon: '📊', end: true },
    { to: '/properties', label: 'Portfolio Hub', icon: '🏢' },
    { to: '/reports', label: 'Financial Command', icon: '💰' },
    { to: '/operations', label: 'Data Control Center', icon: '🔧' },
    { to: '/users', label: 'Admin Hub', icon: '⚙️' },
    { to: '/risk', label: 'Risk Management', icon: '🛡️' },
  ]

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <button
            className="menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
          <h1 className="app-title">REIMS 2.0</h1>
          <span className="app-subtitle">Real Estate Investment Management System</span>
        </div>
        <div className="header-right">
          <Suspense fallback={<div style={{ width: '1.5rem', height: '1.5rem' }} />}>
            <NotificationCenter />
          </Suspense>
          <span className="user-info">👤 {user?.username}</span>
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
          <span className="status-indicator">●</span>
          <span className="status-text">Online</span>
        </div>
      </header>

      <div className="main-container">
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="nav-menu">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {sidebarOpen && <span className="nav-text">{item.label}</span>}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="content">
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <LoadingScreen />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <ProtectedLayout />
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route index element={<CommandCenter />} />
            <Route path="/dashboard" element={<CommandCenter />} />
            <Route path="/properties" element={<PortfolioHub />} />
            <Route path="/reports" element={<FinancialCommand />} />
            <Route path="/operations" element={<DataControlCenter />} />
            <Route path="/operations/bulk-import" element={<BulkImport />} />
            <Route path="/operations/review-queue" element={<ReviewQueue />} />
            <Route path="/operations/reconciliation" element={<Reconciliation />} />
            <Route path="/operations/forensic-reconciliation" element={<ForensicReconciliation />} />
            <Route path="/users" element={<AdminHub />} />
            <Route path="/risk" element={<RiskManagement />} />
            <Route path="/risk/alert-rules" element={<AlertRules />} />
            <Route path="/risk/workflow-locks" element={<WorkflowLocks />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
