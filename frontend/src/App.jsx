/**
 * Main App Component
 *
 * REIMS Application with NLQ Integration
 */

import React, { useMemo, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Drawer, Button } from 'antd';
import {
  DashboardOutlined,
  HomeOutlined,
  SearchOutlined,
  MenuOutlined
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import PropertyDetails from './pages/PropertyDetails';
import NLQPage from './pages/NLQPage';
import './App.css';

const { Header, Content, Footer } = Layout;

const navItems = [
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: 'Dashboard',
    to: '/'
  },
  {
    key: 'properties',
    icon: <HomeOutlined />,
    label: 'Property Details',
    to: '/property/ESP'
  },
  {
    key: 'nlq',
    icon: <SearchOutlined />,
    label: 'NLQ Search',
    to: '/nlq'
  }
];

const AppLayout = () => {
  const location = useLocation();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const selectedKeys = useMemo(() => {
    if (location.pathname.startsWith('/property')) {
      return ['properties'];
    }
    if (location.pathname.startsWith('/nlq')) {
      return ['nlq'];
    }
    return ['dashboard'];
  }, [location.pathname]);

  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [location.pathname]);

  const renderMenu = (mode, onClick) => (
    <Menu
      theme="dark"
      mode={mode}
      selectedKeys={selectedKeys}
      onClick={onClick}
      className={`app-menu app-menu-${mode}`}
    >
      {navItems.map(item => (
        <Menu.Item key={item.key} icon={item.icon}>
          <Link to={item.to}>{item.label}</Link>
        </Menu.Item>
      ))}
    </Menu>
  );

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="app-header-inner">
          <div className="app-logo">REIMS</div>
          <nav className="app-nav-desktop">
            {renderMenu('horizontal')}
          </nav>
          <Button
            type="text"
            icon={<MenuOutlined />}
            className="app-mobile-trigger"
            onClick={() => setIsMobileNavOpen(true)}
            aria-label="Open navigation menu"
          />
        </div>
      </Header>
      <Drawer
        placement="right"
        open={isMobileNavOpen}
        onClose={() => setIsMobileNavOpen(false)}
        className="app-mobile-drawer"
      >
        {renderMenu('inline', () => setIsMobileNavOpen(false))}
      </Drawer>

      <Content className="app-content">
        <div className="app-content-card">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/property/:propertyCode" element={<PropertyDetails />} />
            <Route path="/nlq" element={<NLQPage />} />
          </Routes>
        </div>
      </Content>

      <Footer className="app-footer">
        REIMS ©2025 - Real Estate Investment Management System
      </Footer>
    </Layout>
  );
};

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
