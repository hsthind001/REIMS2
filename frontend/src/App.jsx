/**
 * Main App Component
 *
 * REIMS Application with NLQ Integration
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  HomeOutlined,
  SearchOutlined,
  CalculatorOutlined
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import PropertyDetails from './pages/PropertyDetails';
import NLQPage from './pages/NLQPage';
import './App.css';

const { Header, Content, Footer } = Layout;

function App() {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ position: 'fixed', zIndex: 1, width: '100%' }}>
          <div className="logo" style={{ float: 'left', color: 'white', fontSize: '20px', fontWeight: 'bold', marginRight: '50px' }}>
            REIMS
          </div>
          <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['dashboard']}>
            <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
              <Link to="/">Dashboard</Link>
            </Menu.Item>
            <Menu.Item key="properties" icon={<HomeOutlined />}>
              <Link to="/property/ESP">Property Details</Link>
            </Menu.Item>
            <Menu.Item key="nlq" icon={<SearchOutlined />}>
              <Link to="/nlq">NLQ Search</Link>
            </Menu.Item>
          </Menu>
        </Header>

        <Content style={{ padding: '0 50px', marginTop: 64 }}>
          <div style={{ background: '#fff', padding: 24, minHeight: 'calc(100vh - 134px)', marginTop: 16 }}>
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
    </Router>
  );
}

export default App;
