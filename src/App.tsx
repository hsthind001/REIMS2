import { useState, lazy, Suspense, useEffect } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './components/AuthContext'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import { Button } from './components/ui/Button'
import { useTheme } from './hooks/useTheme'
import { routes } from './config/routes'
import { CommandPalette } from './components/CommandPalette'
import './components/CommandPalette.css'
import { ToastProvider } from './hooks/ToastContext'
import { propertyService } from './lib/property'
import { documentService } from './lib/document'

// Lazy load pages for better initial bundle size
const InsightsHub = lazy(() => import('./pages/InsightsHub'))
const Properties = lazy(() => import('./pages/Properties'))
const Financials = lazy(() => import('./pages/Financials'))
const QualityControl = lazy(() => import('./pages/QualityControl'))
const Administration = lazy(() => import('./pages/Administration'))
const RiskIntelligence = lazy(() => import('./pages/RiskIntelligence'))
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
const AnomalyDashboard = lazy(() => import('./pages/AnomalyDashboard'))

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
  const { theme, toggle } = useTheme()
  const [isPaletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')

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

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isCommandK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      if (isCommandK) {
        e.preventDefault();
        setPaletteOpen(prev => !prev);
      }
      if (e.key === 'Escape' && isPaletteOpen) {
        e.preventDefault();
        setPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isPaletteOpen]);
  const [propertyCommands, setPropertyCommands] = useState<any[]>([]);
  const [docCommands, setDocCommands] = useState<any[]>([]);
  const [propertySource, setPropertySource] = useState<any[]>([]);
  const [docSource, setDocSource] = useState<any[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    const loadPropertyCommands = async () => {
      if (!isPaletteOpen || !isAuthenticated) return;
      try {
        const props = await propertyService.getAllProperties({ limit: 50, signal: controller.signal });
        const sorted = props.sort((a, b) => a.property_name.localeCompare(b.property_name));
        setPropertySource(sorted);
      } catch (err) {
        if ((err as any)?.name !== 'AbortError') {
          console.error('Failed to load properties for command palette', err);
        }
      }
    };
    loadPropertyCommands();
    return () => controller.abort();
  }, [isPaletteOpen, isAuthenticated]);

  useEffect(() => {
    const controller = new AbortController();
    const loadDocCommands = async () => {
      if (!isPaletteOpen || !isAuthenticated) return;
      try {
        const docs = await documentService.getDocuments({ limit: 20, signal: controller.signal });
        const items = docs.items || [];
        setDocSource(items);
      } catch (err) {
        if ((err as any)?.name !== 'AbortError') {
          console.error('Failed to load documents for command palette', err);
        }
      }
    };
    loadDocCommands();
    return () => controller.abort();
  }, [isPaletteOpen, isAuthenticated]);

  useEffect(() => {
    const t = setTimeout(() => {
      const q = paletteQuery.toLowerCase();
      const filteredProps = propertySource
        .filter((p) =>
          !q ||
          p.property_name.toLowerCase().includes(q) ||
          p.property_code.toLowerCase().includes(q) ||
          (p.city || '').toLowerCase().includes(q)
        )
        .slice(0, 50)
        .map((p) => ({
          id: `prop-${p.id}`,
          label: `${p.property_name} (${p.property_code}) • ${p.city || 'Unknown'}, ${p.state || ''}`.trim(),
          section: 'Properties',
          handler: () => {
            setCurrentPage('properties');
            window.location.hash = `market-intelligence/${p.property_code}`;
          }
        }));
      setPropertyCommands(filteredProps);

      const filteredDocs = docSource
        .filter((d: any) =>
          !q ||
          d.file_name.toLowerCase().includes(q) ||
          (d.property_code || '').toLowerCase().includes(q) ||
          (d.document_type || '').toLowerCase().includes(q)
        )
        .slice(0, 20)
        .map((d: any) => ({
          id: `doc-${d.id}`,
          label: `${d.file_name} • ${d.property_code || 'Unknown'} (${d.document_type})`,
          section: 'Documents',
          handler: () => {
            window.location.hash = 'bulk-import';
            setHashRoute('bulk-import');
          }
        }));
      setDocCommands(filteredDocs);
    }, 200);

    return () => clearTimeout(t);
  }, [paletteQuery, propertySource, docSource]);

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
          return <InsightsHub />
        case 'properties':
          return <Properties />
        case 'reports':
          return <Financials />
        case 'operations':
          return <QualityControl />
        case 'users':
          return <Administration />
        case 'risk':
          // Check if hash route is alert-rules
          if (hashRoute === 'alert-rules') {
            return <AlertRules />
          }
          return <RiskIntelligence />
        default:
          return <InsightsHub />
      }
    }

    return (
      <Suspense fallback={<PageLoader />}>
        <PageComponent />
      </Suspense>
    )
  }

  const commandActions = [
    { id: 'nav-dashboard', label: 'Go to Insights Hub', section: 'Navigation', shortcut: 'Ctrl/Cmd + 1', handler: () => setCurrentPage('dashboard') },
    { id: 'nav-properties', label: 'Go to Properties', section: 'Navigation', shortcut: 'Ctrl/Cmd + 2', handler: () => setCurrentPage('properties') },
    { id: 'nav-financials', label: 'Go to Financials', section: 'Navigation', shortcut: 'Ctrl/Cmd + 3', handler: () => setCurrentPage('reports') },
    { id: 'nav-quality', label: 'Go to Quality Control', section: 'Navigation', shortcut: 'Ctrl/Cmd + 4', handler: () => setCurrentPage('operations') },
    { id: 'nav-admin', label: 'Go to Administration', section: 'Navigation', shortcut: 'Ctrl/Cmd + 5', handler: () => setCurrentPage('users') },
    { id: 'nav-risk', label: 'Go to Risk Intelligence', section: 'Navigation', shortcut: 'Ctrl/Cmd + 6', handler: () => setCurrentPage('risk') },
    { id: 'nav-ai', label: 'Open AI Assistant', section: 'Navigation', shortcut: 'Ctrl/Cmd + 7', handler: () => { window.location.hash = 'nlq-search'; setHashRoute('nlq-search'); } },
    { id: 'nav-financials-variance', label: 'Open Variance Analysis', section: 'Financials', handler: () => { setCurrentPage('reports'); window.location.hash = 'variance'; setHashRoute('variance'); } },
    { id: 'nav-financials-statements', label: 'Open Financial Statements', section: 'Financials', handler: () => { setCurrentPage('reports'); window.location.hash = 'statements'; setHashRoute('statements'); } },
    { id: 'nav-financials-coa', label: 'Open Chart of Accounts', section: 'Financials', handler: () => { setCurrentPage('reports'); window.location.hash = 'chart-of-accounts'; setHashRoute('chart-of-accounts'); } },
    { id: 'nav-risk-anomalies', label: 'Open Risk Anomalies', section: 'Risk', handler: () => { setCurrentPage('risk'); window.location.hash = 'anomalies'; setHashRoute('anomalies'); } },
    { id: 'theme-toggle', label: theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode', section: 'Theme', shortcut: 'Ctrl/Cmd + J', handler: toggle },
    { id: 'refresh-dashboard', label: 'Refresh Insights Hub', section: 'Actions', handler: () => { setCurrentPage('dashboard'); window.location.reload(); } },
    { id: 'goto-docs', label: 'Upload Documents', section: 'Actions', shortcut: '/', handler: () => { window.location.hash = 'bulk-import'; setHashRoute('bulk-import'); } },
    { id: 'goto-alerts', label: 'View Alerts Rules', section: 'Actions', handler: () => { window.location.hash = 'alert-rules'; setHashRoute('alert-rules'); setCurrentPage('risk'); } },
    { id: 'goto-compare', label: 'Open Properties Comparison', section: 'Actions', handler: () => { setCurrentPage('properties'); window.location.hash = 'compare'; } },
  ];
  const combinedActions = [...commandActions, ...propertyCommands, ...docCommands];

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
      <a href="#main-content" className="skip-link">Skip to main content</a>
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
          <Button
            variant="ghost"
            size="sm"
            onClick={toggle}
            aria-label="Toggle theme"
          >
            {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
          </Button>
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
        {/* Sidebar - driven by route map */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="nav-menu">
            {routes.map((route) => {
              const isActive =
                (route.path === '/' && currentPage === 'dashboard') ||
                (route.path === '/properties' && currentPage === 'properties') ||
                (route.path === '/financials' && currentPage === 'reports') ||
                (route.path === '/quality' && currentPage === 'operations') ||
                (route.path === '/admin' && currentPage === 'users') ||
                (route.path === '/risk' && currentPage === 'risk') ||
                (route.path === '/ai' && hashRoute === 'nlq-search');

              const handleClick = () => {
                switch (route.path) {
                  case '/':
                    setCurrentPage('dashboard');
                    break;
                  case '/properties':
                    setCurrentPage('properties');
                    break;
                  case '/financials':
                    setCurrentPage('reports');
                    break;
                  case '/quality':
                    setCurrentPage('operations');
                    break;
                  case '/admin':
                    setCurrentPage('users');
                    break;
                  case '/risk':
                    setCurrentPage('risk');
                    break;
                  case '/ai':
                    window.location.hash = 'nlq-search';
                    break;
                  default:
                    setCurrentPage('dashboard');
                }
              };

              const iconMap: Record<string, string> = {
                dashboard: '📊',
                building: '🏢',
                finance: '💰',
                check: '🔧',
                settings: '⚙️',
                shield: '🛡️',
                bot: '💬',
              };

              return (
                <button
                  key={route.path}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={handleClick}
                >
                  <span className="nav-icon">{iconMap[route.icon] || '•'}</span>
                  {sidebarOpen && <span className="nav-text">{route.label}</span>}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="content" id="main-content">
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
          ) : hashRoute === 'anomaly-dashboard' ? (
            <Suspense fallback={<PageLoader />}>
              <AnomalyDashboard />
            </Suspense>
          ) : (
            renderPage()
          )}
        </main>
      </div>

      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setPaletteOpen(false)}
        actions={combinedActions}
        sectionsOrder={['Navigation', 'Actions', 'Properties', 'Documents', 'Theme', 'General']}
        onQueryChange={(q) => setPaletteQuery(q)}
      />
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
