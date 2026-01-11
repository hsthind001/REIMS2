/**
 * Dashboard Page
 *
 * Main dashboard with NLQ Search integration (Option 1: Simple Search)
 */

import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Select,
  Alert,
  List,
  Timeline,
  Button,
  Tag,
  Space
} from 'antd';
import {
  DollarOutlined,
  RiseOutlined,
  HomeOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined
} from '@ant-design/icons';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';
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

  const kpiCards = [
    {
      key: 'revenue',
      title: 'Total Revenue',
      value: stats.totalRevenue,
      precision: 2,
      prefix: <DollarOutlined />,
      suffix: 'YTD',
      valueStyle: { color: '#3f8600' },
      trend: 'up',
      delta: '+8.2%',
      label: 'vs last month',
      spark: [6, 7, 8, 7, 9]
    },
    {
      key: 'expenses',
      title: 'Total Expenses',
      value: stats.totalExpenses,
      precision: 2,
      prefix: <DollarOutlined />,
      suffix: 'YTD',
      valueStyle: { color: '#cf1322' },
      trend: 'down',
      delta: '-3.4%',
      label: 'vs last month',
      spark: [8, 7, 6, 6, 5]
    },
    {
      key: 'noi',
      title: 'Net Income',
      value: stats.netIncome,
      precision: 2,
      prefix: <RiseOutlined />,
      suffix: 'YTD',
      valueStyle: { color: '#3f8600' },
      trend: 'up',
      delta: '+5.1%',
      label: 'vs last month',
      spark: [5, 6, 7, 7, 8]
    },
    {
      key: 'properties',
      title: 'Properties',
      value: stats.properties,
      prefix: <HomeOutlined />,
      trend: 'flat',
      delta: '0',
      label: 'net adds',
      spark: [4, 4, 4, 4, 4]
    }
  ];

  const activityItems = [
    {
      title: 'Cash position updated for ESP',
      description: 'November close posted to treasury',
      time: 'Today, 9:30 AM'
    },
    {
      title: 'New tenant lease signed - OAK',
      description: '36-month lease finalized with 3.5% escalator',
      time: 'Yesterday'
    },
    {
      title: 'DSCR calculation completed - PIN',
      description: 'DSCR improved to 1.42 for Q3',
      time: '2 days ago'
    },
    {
      title: 'Monthly report generated - All properties',
      description: 'Portfolio performance deck published',
      time: 'Last week'
    }
  ];

  const quickActions = [
    {
      title: 'View financial statements',
      description: 'Income statement, balance sheet, cash flow',
      action: 'Open statements'
    },
    {
      title: 'Calculate key metrics',
      description: 'NOI, DSCR, occupancy, rent growth',
      action: 'Run metrics'
    },
    {
      title: 'Generate reports',
      description: 'Investor-ready summaries and exports',
      action: 'Create report'
    },
    {
      title: 'Review audit trail',
      description: 'Track approvals and data changes',
      action: 'View audit'
    }
  ];

  const chartData = [
    { month: 'Apr', revenue: 920, noi: 310 },
    { month: 'May', revenue: 980, noi: 330 },
    { month: 'Jun', revenue: 1040, noi: 360 },
    { month: 'Jul', revenue: 990, noi: 340 },
    { month: 'Aug', revenue: 1120, noi: 390 },
    { month: 'Sep', revenue: 1180, noi: 410 }
  ];

  const trendIcon = trend => {
    if (trend === 'up') return <ArrowUpOutlined />;
    if (trend === 'down') return <ArrowDownOutlined />;
    return <MinusOutlined />;
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
      <Row gutter={[16, 16]} className="dashboard-section">
        {kpiCards.map(card => (
          <Col key={card.key} xs={24} sm={12} lg={6}>
            <Card className="dashboard-card">
              <Statistic
                title={card.title}
                value={card.value}
                precision={card.precision}
                prefix={card.prefix}
                suffix={card.suffix}
                valueStyle={card.valueStyle}
              />
              <div className="kpi-trend">
                <Space size={8} align="center">
                  <span className={`trend-icon ${card.trend}`}>
                    {trendIcon(card.trend)}
                  </span>
                  <span className={`trend-delta ${card.trend}`}>
                    {card.delta}
                  </span>
                  <span className="trend-label">{card.label}</span>
                </Space>
                <div className="trend-spark">
                  {card.spark.map((value, index) => (
                    <span
                      key={`${card.key}-${index}`}
                      className="spark-bar"
                      style={{ height: `${value + 4}px` }}
                    />
                  ))}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        title={<span className="section-title">Portfolio Momentum</span>}
        className="dashboard-card dashboard-section"
        bordered={false}
      >
        <div className="chart-header">
          <div>
            <h3>Revenue & NOI Trend</h3>
            <p>Rolling six-month performance snapshot</p>
          </div>
          <Space>
            <Tag color="green">Revenue</Tag>
            <Tag color="blue">NOI</Tag>
          </Space>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="revenue" stroke="#52c41a" strokeWidth={2} />
              <Line type="monotone" dataKey="noi" stroke="#1890ff" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

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
      <Row gutter={[16, 16]} className="dashboard-section">
        <Col xs={24} lg={12}>
          <Card
            title={<span className="section-title">Recent Activity</span>}
            className="dashboard-card"
            bordered={false}
          >
            <Timeline
              items={activityItems.map(item => ({
                children: (
                  <div className="activity-item">
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.description}</p>
                    </div>
                    <Tag color="default">{item.time}</Tag>
                  </div>
                )
              }))}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<span className="section-title">Quick Actions</span>}
            className="dashboard-card"
            bordered={false}
          >
            <List
              itemLayout="horizontal"
              dataSource={quickActions}
              renderItem={item => (
                <List.Item
                  actions={[
                    <Button key={item.action} type="primary" size="small">
                      {item.action}
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={item.title}
                    description={item.description}
                  />
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
