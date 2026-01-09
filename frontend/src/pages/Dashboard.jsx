/**
 * Dashboard Page
 *
 * Main dashboard with NLQ Search integration (Option 1: Simple Search)
 */

import React, { useState } from 'react';
import { Row, Col, Card, Statistic, Select, Alert } from 'antd';
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  HomeOutlined
} from '@ant-design/icons';
import NLQSearchBar from '../components/NLQSearchBar';
import './Dashboard.css';

const { Option } = Select;

const Dashboard = () => {
  const [selectedProperty, setSelectedProperty] = useState('ESP');

  // Mock data - replace with real API calls
  const properties = [
    { code: 'ESP', name: 'Esperanza', id: 1 },
    { code: 'OAK', name: 'Oakland Plaza', id: 2 },
    { code: 'PIN', name: 'Pinecrest', id: 3 },
    { code: 'MAP', name: 'Maple Grove', id: 4 }
  ];

  const stats = {
    totalRevenue: 1250000,
    totalExpenses: 850000,
    netIncome: 400000,
    properties: 4
  };

  return (
    <div className="dashboard-container page-content">
      <div className="dashboard-header">
        <h1>📊 Dashboard</h1>
        <p>Real Estate Investment Management System</p>
      </div>

      {/* Property Selector */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle">
          <Col>
            <label style={{ marginRight: 12, fontWeight: 600 }}>
              Select Property:
            </label>
          </Col>
          <Col>
            <Select
              value={selectedProperty}
              onChange={setSelectedProperty}
              style={{ width: 250 }}
              size="large"
            >
              <Option value="ALL">All Properties</Option>
              {properties.map(prop => (
                <Option key={prop.code} value={prop.code}>
                  {prop.name} ({prop.code})
                </Option>
              ))}
            </Select>
          </Col>
        </Row>
      </Card>

      {/* Key Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Revenue"
              value={stats.totalRevenue}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="YTD"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Expenses"
              value={stats.totalExpenses}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="YTD"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Net Income"
              value={stats.netIncome}
              precision={2}
              prefix={<RiseOutlined />}
              suffix="YTD"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Properties"
              value={stats.properties}
              prefix={<HomeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* OPTION 1: Simple NLQ Search Bar */}
      <Alert
        message="🎯 Option 1: Simple Search Integration"
        description="Ask questions about your financial data in natural language"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <NLQSearchBar
        propertyCode={selectedProperty !== 'ALL' ? selectedProperty : null}
        propertyId={
          selectedProperty !== 'ALL'
            ? properties.find(p => p.code === selectedProperty)?.id
            : null
        }
      />

      {/* Additional Dashboard Content */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="Recent Activity" bordered={false}>
            <p>• Cash position updated for ESP - Nov 2025</p>
            <p>• New tenant lease signed - OAK</p>
            <p>• DSCR calculation completed - PIN</p>
            <p>• Monthly report generated - All properties</p>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Quick Actions" bordered={false}>
            <p>✓ View financial statements</p>
            <p>✓ Calculate metrics</p>
            <p>✓ Generate reports</p>
            <p>✓ Review audit trail</p>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
