/**
 * Dashboard Page
 *
 * Main dashboard with NLQ Search integration (Option 1: Simple Search)
 */

import React, { useState } from 'react';
import { Row, Col, Card, Statistic, Select, Alert, List, Timeline, Button, Tag } from 'antd';
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  HomeOutlined,
  FileTextOutlined,
  CalculatorOutlined,
  BarChartOutlined,
  AuditOutlined
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
    properties: 4,
    totalRevenueDelta: 0.062,
    totalExpensesDelta: -0.041,
    netIncomeDelta: 0.089,
    propertiesDelta: 1
  };

  const chartSeries = [38, 52, 47, 61, 58, 70, 64, 76, 68, 82, 73, 88];

  const formatDelta = (delta, format = 'percent') => {
    if (format === 'count') {
      return `${Math.abs(delta)}`;
    }
    return `${Math.abs(delta * 100).toFixed(1)}%`;
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
            <div className="kpi-delta kpi-positive">
              <RiseOutlined />
              <span>
                {formatDelta(stats.totalRevenueDelta)} vs prior period
              </span>
            </div>
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
            <div className="kpi-delta kpi-negative">
              <FallOutlined />
              <span>
                {formatDelta(stats.totalExpensesDelta)} vs prior period
              </span>
            </div>
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
            <div className="kpi-delta kpi-positive">
              <RiseOutlined />
              <span>
                {formatDelta(stats.netIncomeDelta)} vs prior period
              </span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Properties"
              value={stats.properties}
              prefix={<HomeOutlined />}
            />
            <div className="kpi-delta kpi-positive">
              <RiseOutlined />
              <span>
                {formatDelta(stats.propertiesDelta, 'count')} vs prior period
              </span>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24}>
          <Card className="compact-chart-card">
            <div className="compact-chart-header">
              <div>
                <h3>Portfolio Performance Trend</h3>
                <p>Last 12 months, rolling net operating income</p>
              </div>
              <Tag color="green">+8.2% YTD</Tag>
            </div>
            <div className="compact-chart">
              {chartSeries.map((value, index) => (
                <span
                  key={`chart-bar-${index}`}
                  className="compact-chart-bar"
                  style={{ height: `${value}%` }}
                />
              ))}
            </div>
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
            <Timeline
              items={[
                {
                  color: 'green',
                  children: 'Cash position updated for ESP — Nov 2025'
                },
                {
                  color: 'blue',
                  children: 'New tenant lease signed — OAK'
                },
                {
                  color: 'purple',
                  children: 'DSCR calculation completed — PIN'
                },
                {
                  color: 'gray',
                  children: 'Monthly report generated — All properties'
                }
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Quick Actions" bordered={false}>
            <List
              dataSource={[
                {
                  label: 'View financial statements',
                  icon: <FileTextOutlined />
                },
                { label: 'Calculate metrics', icon: <CalculatorOutlined /> },
                { label: 'Generate reports', icon: <BarChartOutlined /> },
                { label: 'Review audit trail', icon: <AuditOutlined /> }
              ]}
              renderItem={item => (
                <List.Item className="quick-action-item">
                  <Button icon={item.icon} type="primary" block>
                    {item.label}
                  </Button>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
