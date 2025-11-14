import { useState } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './components/AuthContext'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import Dashboard from './pages/Dashboard'
import Properties from './pages/Properties'
import Documents from './pages/Documents'
import Reports from './pages/Reports'
import Reconciliation from './pages/Reconciliation'
import Alerts from './pages/Alerts'
import AnomalyDashboard from './pages/AnomalyDashboard'
import PerformanceMonitoring from './pages/PerformanceMonitoring'
import UserManagement from './pages/UserManagement'
import PropertyIntelligence from './pages/PropertyIntelligence'
import TenantOptimizer from './pages/TenantOptimizer'
import NaturalLanguageQuery from './pages/NaturalLanguageQuery'
import RiskManagement from './pages/RiskManagement'
import VarianceAnalysis from './pages/VarianceAnalysis'
import DocumentSummarization from './pages/DocumentSummarization'
import BulkImport from './pages/BulkImport'

type Page = 'dashboard' | 'properties' | 'documents' | 'reports' | 'reconciliation' | 'alerts' | 'anomalies' | 'performance' | 'users' | 'property-intel' | 'tenant-optimizer' | 'nlq' | 'risk' | 'variance' | 'doc-summary' | 'bulk-import' | 'login' | 'register'

function AppContent() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout, isAuthenticated } = useAuth()

  const renderPage = () => {
    // Show login/register if not authenticated
    if (!isAuthenticated) {
      if (currentPage === 'register') {
        return <RegisterForm />
      }
      return <LoginForm />
    }

    // Show app pages if authenticated
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'properties':
        return <Properties />
      case 'documents':
        return <Documents />
      case 'reports':
        return <Reports />
      case 'reconciliation':
        return <Reconciliation />
      case 'alerts':
        return <Alerts />
      case 'anomalies':
        return <AnomalyDashboard />
      case 'performance':
        return <PerformanceMonitoring />
      case 'users':
        return <UserManagement />
      case 'property-intel':
        return <PropertyIntelligence />
      case 'tenant-optimizer':
        return <TenantOptimizer />
      case 'nlq':
        return <NaturalLanguageQuery />
      case 'risk':
        return <RiskManagement />
      case 'variance':
        return <VarianceAnalysis />
      case 'doc-summary':
        return <DocumentSummarization />
      case 'bulk-import':
        return <BulkImport />
      default:
        return <Dashboard />
    }
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
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="nav-menu">
            <button
              className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentPage('dashboard')}
            >
              <span className="nav-icon">📊</span>
              {sidebarOpen && <span className="nav-text">Dashboard</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'properties' ? 'active' : ''}`}
              onClick={() => setCurrentPage('properties')}
            >
              <span className="nav-icon">🏢</span>
              {sidebarOpen && <span className="nav-text">Properties</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'documents' ? 'active' : ''}`}
              onClick={() => setCurrentPage('documents')}
            >
              <span className="nav-icon">📄</span>
              {sidebarOpen && <span className="nav-text">Documents</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'reports' ? 'active' : ''}`}
              onClick={() => setCurrentPage('reports')}
            >
              <span className="nav-icon">📈</span>
              {sidebarOpen && <span className="nav-text">Reports</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'reconciliation' ? 'active' : ''}`}
              onClick={() => setCurrentPage('reconciliation')}
            >
              <span className="nav-icon">🔄</span>
              {sidebarOpen && <span className="nav-text">Reconciliation</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'alerts' ? 'active' : ''}`}
              onClick={() => setCurrentPage('alerts')}
            >
              <span className="nav-icon">🔔</span>
              {sidebarOpen && <span className="nav-text">Alerts</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'anomalies' ? 'active' : ''}`}
              onClick={() => setCurrentPage('anomalies')}
            >
              <span className="nav-icon">⚠️</span>
              {sidebarOpen && <span className="nav-text">Anomalies</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'performance' ? 'active' : ''}`}
              onClick={() => setCurrentPage('performance')}
            >
              <span className="nav-icon">📈</span>
              {sidebarOpen && <span className="nav-text">Performance</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'users' ? 'active' : ''}`}
              onClick={() => setCurrentPage('users')}
            >
              <span className="nav-icon">👥</span>
              {sidebarOpen && <span className="nav-text">Users</span>}
            </button>

            {sidebarOpen && <div className="nav-divider">AI & Intelligence</div>}

            <button
              className={`nav-item ${currentPage === 'property-intel' ? 'active' : ''}`}
              onClick={() => setCurrentPage('property-intel')}
            >
              <span className="nav-icon">🔍</span>
              {sidebarOpen && <span className="nav-text">Property Intel</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'tenant-optimizer' ? 'active' : ''}`}
              onClick={() => setCurrentPage('tenant-optimizer')}
            >
              <span className="nav-icon">🎯</span>
              {sidebarOpen && <span className="nav-text">Tenant Optimizer</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'nlq' ? 'active' : ''}`}
              onClick={() => setCurrentPage('nlq')}
            >
              <span className="nav-icon">💬</span>
              {sidebarOpen && <span className="nav-text">Ask AI</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'doc-summary' ? 'active' : ''}`}
              onClick={() => setCurrentPage('doc-summary')}
            >
              <span className="nav-icon">📄</span>
              {sidebarOpen && <span className="nav-text">Doc Summary</span>}
            </button>

            {sidebarOpen && <div className="nav-divider">Risk & Analytics</div>}

            <button
              className={`nav-item ${currentPage === 'risk' ? 'active' : ''}`}
              onClick={() => setCurrentPage('risk')}
            >
              <span className="nav-icon">🛡️</span>
              {sidebarOpen && <span className="nav-text">Risk Management</span>}
            </button>
            <button
              className={`nav-item ${currentPage === 'variance' ? 'active' : ''}`}
              onClick={() => setCurrentPage('variance')}
            >
              <span className="nav-icon">📊</span>
              {sidebarOpen && <span className="nav-text">Variance Analysis</span>}
            </button>

            {sidebarOpen && <div className="nav-divider">Data Management</div>}

            <button
              className={`nav-item ${currentPage === 'bulk-import' ? 'active' : ''}`}
              onClick={() => setCurrentPage('bulk-import')}
            >
              <span className="nav-icon">📂</span>
              {sidebarOpen && <span className="nav-text">Bulk Import</span>}
            </button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="content">
          {renderPage()}
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
