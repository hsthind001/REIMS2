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
const FullFinancialData = lazy(() => import('./pages/FullFinancialData'))
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'))
const WorkflowLocks = lazy(() => import('./pages/WorkflowLocks'))
const NotificationCenter = lazy(() => import('./components/notifications/NotificationCenter'))
const ForensicReconciliation = lazy(() => import('./pages/ForensicReconciliation'))
const MarketIntelligenceDashboard = lazy(() => import('./pages/MarketIntelligenceDashboard'))
const AnomalyDetailPage = lazy(() => import('./pages/AnomalyDetailPage'))

// Forensic Audit Framework Pages
const ForensicAuditDashboard = lazy(() => import('./pages/ForensicAuditDashboard'))
const MathIntegrityDashboard = lazy(() => import('./pages/MathIntegrityDashboard'))
const PerformanceBenchmarkDashboard = lazy(() => import('./pages/PerformanceBenchmarkDashboard'))
const FraudDetectionDashboard = lazy(() => import('./pages/FraudDetectionDashboard'))
const CovenantComplianceDashboard = lazy(() => import('./pages/CovenantComplianceDashboard'))
const ReconciliationResultsDashboard = lazy(() => import('./pages/ReconciliationResultsDashboard'))
const TenantRiskDashboard = lazy(() => import('./pages/TenantRiskDashboard'))
const CollectionsQualityDashboard = lazy(() => import('./pages/CollectionsQualityDashboard'))
const DocumentCompletenessDashboard = lazy(() => import('./pages/DocumentCompletenessDashboard'))
const AuditHistoryDashboard = lazy(() => import('./pages/AuditHistoryDashboard'))
const NaturalLanguageQueryNew = lazy(() => import('./pages/NaturalLanguageQueryNew'))

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
      // Extract route name (before query params)
      const routeName = hash.split('?')[0]
      setHashRoute(hash)
      // If navigating to bulk-import, ensure we're on operations page
      if (routeName === 'bulk-import' && currentPage !== 'operations') {
        setCurrentPage('operations')
      }
      // If navigating to review-queue, ensure we're on operations page
      if (routeName === 'review-queue' && currentPage !== 'operations') {
        setCurrentPage('operations')
      }
      // If navigating to workflow-locks, ensure we're on risk page
      if (routeName === 'workflow-locks' && currentPage !== 'risk') {
        setCurrentPage('risk')
      }
      // If navigating to alert-rules, ensure we're on risk page
      if (routeName === 'alert-rules' && currentPage !== 'risk') {
        setCurrentPage('risk')
      }
      // If navigating to reports, ensure we're on reports page
      if (routeName === 'reports' && currentPage !== 'reports') {
        setCurrentPage('reports')
      }
      if (routeName === 'financial-data' && currentPage !== 'reports') {
        setCurrentPage('reports')
      }
      // If navigating to forensic-reconciliation, ensure we're on operations page
      if (routeName === 'forensic-reconciliation' && currentPage !== 'operations') {
        setCurrentPage('operations')
      }
      // If navigating to market-intelligence, ensure we're on properties page
      if (routeName.startsWith('market-intelligence') && currentPage !== 'properties') {
        setCurrentPage('properties')
      }
      if (routeName.startsWith('anomaly-details') && currentPage !== 'risk') {
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
          {hashRoute.startsWith('financial-data') ? (
            <Suspense fallback={<PageLoader />}>
              <FullFinancialData />
            </Suspense>
          ) : hashRoute === 'bulk-import' ? (
            <Suspense fallback={<PageLoader />}>
              <BulkImport />
            </Suspense>
          ) : hashRoute.startsWith('review-queue') ? (
            <Suspense fallback={<PageLoader />}>
              <ReviewQueue />
            </Suspense>
          ) : hashRoute === 'workflow-locks' ? (
            <Suspense fallback={<PageLoader />}>
              <WorkflowLocks />
            </Suspense>
          ) : hashRoute === 'forensic-reconciliation' ? (
            <Suspense fallback={<PageLoader />}>
              <ForensicReconciliation />
            </Suspense>
          ) : hashRoute.startsWith('market-intelligence/') ? (
            <Suspense fallback={<PageLoader />}>
              <MarketIntelligenceDashboard />
            </Suspense>
          ) : hashRoute.startsWith('anomaly-details') ? (
            <Suspense fallback={<PageLoader />}>
              <AnomalyDetailPage />
            </Suspense>
          ) : hashRoute === 'forensic-audit-dashboard' ? (
            <Suspense fallback={<PageLoader />}>
              <ForensicAuditDashboard />
            </Suspense>
          ) : hashRoute === 'math-integrity' ? (
            <Suspense fallback={<PageLoader />}>
              <MathIntegrityDashboard />
            </Suspense>
          ) : hashRoute === 'performance-benchmarking' ? (
            <Suspense fallback={<PageLoader />}>
              <PerformanceBenchmarkDashboard />
            </Suspense>
          ) : hashRoute === 'fraud-detection' ? (
            <Suspense fallback={<PageLoader />}>
              <FraudDetectionDashboard />
            </Suspense>
          ) : hashRoute === 'covenant-compliance' ? (
            <Suspense fallback={<PageLoader />}>
              <CovenantComplianceDashboard />
            </Suspense>
          ) : hashRoute === 'reconciliation-results' ? (
            <Suspense fallback={<PageLoader />}>
              <ReconciliationResultsDashboard />
            </Suspense>
          ) : hashRoute === 'tenant-risk' ? (
            <Suspense fallback={<PageLoader />}>
              <TenantRiskDashboard />
            </Suspense>
          ) : hashRoute === 'collections-quality' ? (
            <Suspense fallback={<PageLoader />}>
              <CollectionsQualityDashboard />
            </Suspense>
          ) : hashRoute === 'document-completeness' ? (
            <Suspense fallback={<PageLoader />}>
              <DocumentCompletenessDashboard />
            </Suspense>
          ) : hashRoute === 'audit-history' ? (
            <Suspense fallback={<PageLoader />}>
              <AuditHistoryDashboard />
            </Suspense>
          ) : hashRoute === 'nlq-search' ? (
            <Suspense fallback={<PageLoader />}>
              <NaturalLanguageQueryNew />
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
