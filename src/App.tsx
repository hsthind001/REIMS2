import { useState } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './components/AuthContext'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import Dashboard from './pages/Dashboard'
import Properties from './pages/Properties'
import Documents from './pages/Documents'
import Reports from './pages/Reports'

type Page = 'dashboard' | 'properties' | 'documents' | 'reports' | 'login' | 'register'

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
