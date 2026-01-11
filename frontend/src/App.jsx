/**
 * Main App Component
 *
 * REIMS Application with NLQ Integration
 */

import React, { useMemo, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Button, Drawer, Grid, Layout, Menu, theme } from 'antd';
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
const { useBreakpoint } = Grid;

function AppLayout() {
  const location = useLocation();
  const screens = useBreakpoint();
  const { token } = theme.useToken();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const isMobile = !screens.md;

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/property')) {
      return 'properties';
    }
    if (location.pathname.startsWith('/nlq')) {
      return 'nlq';
    }
    return 'dashboard';
  }, [location.pathname]);

  const menuItems = useMemo(
    () => [
      {
        key: 'dashboard',
        icon: <DashboardOutlined />,
        label: <Link to="/">Dashboard</Link>
      },
      {
        key: 'properties',
        icon: <HomeOutlined />,
        label: <Link to="/property/ESP">Property Details</Link>
      },
      {
        key: 'nlq',
        icon: <SearchOutlined />,
        label: <Link to="/nlq">NLQ Search</Link>
      }
    ],
    []
  );

  const layoutStyle = {
    minHeight: '100vh',
    '--app-header-height': `${token.controlHeight * 2}px`,
    '--app-horizontal-padding': `${token.controlHeightLG * 1.25}px`,
    '--app-logo-gap': `${token.marginXL}px`,
    '--app-content-padding': `${token.paddingLG}px`,
    '--app-content-gap': `${token.marginMD}px`
  };

  return (
    <Layout style={layoutStyle}>
      <Header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-left">
            <Button
              className="app-menu-button"
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setIsDrawerOpen(true)}
              aria-label="Open navigation menu"
            />
            <div className="app-logo">REIMS</div>
          </div>
          {!isMobile && (
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={[selectedKey]}
              items={menuItems}
              className="app-menu"
            />
          )}
        </div>
      </Header>

      <Drawer
        title="Navigation"
        placement="left"
        onClose={() => setIsDrawerOpen(false)}
        open={isDrawerOpen}
        className="app-drawer"
        bodyStyle={{ padding: token.paddingLG }}
      >
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={() => setIsDrawerOpen(false)}
        />
      </Drawer>

      <Content className="app-content">
        <div className="app-content-inner">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/property/:propertyCode" element={<PropertyDetails />} />
            <Route path="/nlq" element={<NLQPage />} />
          </Routes>
        </div>
      </Content>

      <Footer style={{ textAlign: 'center' }}>
        REIMS ©2025 - Real Estate Investment Management System
      </Footer>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;

