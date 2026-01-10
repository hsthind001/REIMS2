/**
 * Property Details Page
 *
 * Property information with NLQ Search integration (Option 2: Card Integration)
 */

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Row, Col, Card, Descriptions, Tabs, Table, Tag, Alert, InputNumber, Button, Space, Typography } from 'antd';
import {
  HomeOutlined,
  DollarOutlined,
  CalculatorOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import NLQSearchBar from '../components/NLQSearchBar';
import rulesService from '../services/rulesService';
import './PropertyDetails.css';

const { TabPane } = Tabs;

const PropertyDetails = () => {
  const { propertyCode } = useParams();
  const [property, setProperty] = useState(null);
  const [rules, setRules] = useState([]);
  const [ruleResults, setRuleResults] = useState([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [periodId, setPeriodId] = useState(1);
  const [ruleSummary, setRuleSummary] = useState({ total: 0, failed: 0, passed: 0, skipped: 0 });
  const { Text } = Typography;

  useEffect(() => {
    // Mock data - replace with real API call
    const mockProperties = {
      ESP: {
        id: 1,
        code: 'ESP',
        name: 'Esperanza',
        address: '123 Main Street',
        city: 'Los Angeles',
        state: 'CA',
        zip: '90001',
        type: 'Multi-Family',
        units: 120,
        squareFeet: 95000,
        yearBuilt: 2018,
        purchasePrice: 15000000,
        currentValue: 18500000
      },
      OAK: {
        id: 2,
        code: 'OAK',
        name: 'Oakland Plaza',
        address: '456 Oak Avenue',
        city: 'Oakland',
        state: 'CA',
        zip: '94601',
        type: 'Commercial',
        units: 15,
        squareFeet: 45000,
        yearBuilt: 2015,
        purchasePrice: 8000000,
        currentValue: 9200000
      },
      PIN: {
        id: 3,
        code: 'PIN',
        name: 'Pinecrest',
        address: '789 Pine Road',
        city: 'San Diego',
        state: 'CA',
        zip: '92101',
        type: 'Multi-Family',
        units: 80,
        squareFeet: 65000,
        yearBuilt: 2020,
        purchasePrice: 12000000,
        currentValue: 13800000
      }
    };

    setProperty(mockProperties[propertyCode] || mockProperties.ESP);
  }, [propertyCode]);

  useEffect(() => {
    const loadRules = async () => {
      if (!property) return;
      setRulesLoading(true);
      try {
        const data = await rulesService.listCalculatedRules(property.id);
        setRules(data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setRulesLoading(false);
      }
    };
    loadRules();
  }, [property]);

  const evaluateRules = async () => {
    if (!property || !periodId) return;
    setResultsLoading(true);
    try {
      const data = await rulesService.evaluateCalculatedRules(property.id, periodId);
      setRuleResults(data?.rules || []);
      setRuleSummary({
        total: data?.total || 0,
        failed: data?.failed || 0,
        passed: data?.passed || 0,
        skipped: data?.skipped || 0
      });
    } catch (err) {
      console.error(err);
    } finally {
      setResultsLoading(false);
    }
  };

  const financialData = [
    {
      key: '1',
      metric: 'Monthly Revenue',
      value: '$125,000',
      change: '+5.2%',
      trend: 'up'
    },
    {
      key: '2',
      metric: 'Monthly Expenses',
      value: '$85,000',
      change: '-2.1%',
      trend: 'down'
    },
    {
      key: '3',
      metric: 'NOI',
      value: '$40,000',
      change: '+8.5%',
      trend: 'up'
    },
    {
      key: '4',
      metric: 'DSCR',
      value: '1.45',
      change: '+0.05',
      trend: 'up'
    }
  ];

  const columns = [
    {
      title: 'Metric',
      dataIndex: 'metric',
      key: 'metric',
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      render: (text) => <span style={{ fontSize: 16 }}>{text}</span>
    },
    {
      title: 'Change',
      dataIndex: 'change',
      key: 'change',
      render: (text, record) => (
        <Tag color={record.trend === 'up' ? 'green' : 'red'}>
          {text}
        </Tag>
      )
    }
  ];

  if (!property) {
    return <div>Loading...</div>;
  }

  const ruleColumns = [
    { title: 'Rule ID', dataIndex: 'rule_id', key: 'rule_id' },
    { title: 'Name', dataIndex: 'rule_name', key: 'rule_name' },
    { title: 'Severity', dataIndex: 'severity', key: 'severity',
      render: (sev) => <Tag color={sev === 'critical' ? 'red' : sev === 'warning' ? 'orange' : 'blue'}>{sev}</Tag>
    },
    { title: 'Formula', dataIndex: 'formula', key: 'formula' },
    { title: 'Tolerance', key: 'tolerance',
      render: (_, record) => (
        <span>
          {record.tolerance_absolute !== null && record.tolerance_absolute !== undefined ? `±${record.tolerance_absolute}` : '-'}
          {record.tolerance_percent ? ` / ${record.tolerance_percent}%` : ''}
        </span>
      )
    }
  ];

  const ruleResultColumns = [
    { title: 'Rule ID', dataIndex: 'rule_id', key: 'rule_id' },
    { title: 'Name', dataIndex: 'rule_name', key: 'rule_name' },
    { title: 'Status', dataIndex: 'status', key: 'status',
      render: (status) => {
        const color = status === 'PASS' ? 'green' : status === 'FAIL' ? 'red' : 'default';
        return <Tag color={color}>{status}</Tag>;
      }
    },
    { title: 'Severity', dataIndex: 'severity', key: 'severity',
      render: (sev) => <Tag color={sev === 'critical' ? 'red' : sev === 'warning' ? 'orange' : 'blue'}>{sev}</Tag>
    },
    { title: 'Difference', dataIndex: 'difference', key: 'difference',
      render: (diff) => {
        if (diff === null || diff === undefined) return '-';
        return typeof diff === 'number' ? diff.toFixed(2) : diff;
      } },
    { title: 'Message', dataIndex: 'message', key: 'message', render: (msg) => msg || '-' }
  ];

  return (
    <div className="property-details-container page-content">
      {/* Property Header */}
      <div className="property-header">
        <h1>
          <HomeOutlined /> {property.name} ({property.code})
        </h1>
        <p>{property.address}, {property.city}, {property.state} {property.zip}</p>
      </div>

      <Row gutter={[16, 16]}>
        {/* Property Information */}
        <Col xs={24} lg={12}>
          <Card title="Property Information" bordered={false}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Property Code">{property.code}</Descriptions.Item>
              <Descriptions.Item label="Type">{property.type}</Descriptions.Item>
              <Descriptions.Item label="Units">{property.units}</Descriptions.Item>
              <Descriptions.Item label="Square Feet">{property.squareFeet.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="Year Built">{property.yearBuilt}</Descriptions.Item>
              <Descriptions.Item label="Purchase Price">
                ${property.purchasePrice.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Current Value">
                ${property.currentValue.toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Financial Metrics */}
        <Col xs={24} lg={12}>
          <Card title="Key Financial Metrics" bordered={false}>
            <Table
              dataSource={financialData}
              columns={columns}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* OPTION 2: NLQ Search in Card */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Alert
            message="🎯 Option 2: Card Integration"
            description="Ask questions about this specific property's financial data"
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Card
            title={
              <span>
                <CalculatorOutlined /> Ask Questions About {property.name}
              </span>
            }
            bordered={false}
            style={{ background: 'var(--color-surface-subtle)' }}
          >
            <NLQSearchBar
              propertyCode={property.code}
              propertyId={property.id}
            />
          </Card>
        </Col>
      </Row>

      {/* Additional Tabs */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card>
            <Tabs defaultActiveKey="1">
              <TabPane tab="Financial Statements" key="1">
                <p>Balance Sheet, Income Statement, Cash Flow</p>
              </TabPane>
              <TabPane tab="Rent Roll" key="2">
                <p>Unit details, Occupancy, Lease information</p>
              </TabPane>
              <TabPane tab="Maintenance" key="3">
                <p>Work orders, Repairs, Capital expenditures</p>
              </TabPane>
              <TabPane tab="Documents" key="4">
                <p>Leases, Contracts, Reports</p>
              </TabPane>
              <TabPane tab="Rules" key="5">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space align="center">
                    <Text strong>Period ID:</Text>
                    <InputNumber min={1} value={periodId} onChange={setPeriodId} />
                    <Button type="primary" onClick={evaluateRules} loading={resultsLoading}>
                      Evaluate Rules
                    </Button>
                    <Text type="secondary">
                      Summary: {ruleSummary.passed} pass / {ruleSummary.failed} fail / {ruleSummary.skipped} skipped
                    </Text>
                  </Space>

                  <Card title="Active Calculated Rules" size="small">
                    <Table
                      dataSource={rules.map((r) => ({ key: r.id || r.rule_id, ...r }))}
                      columns={ruleColumns}
                      loading={rulesLoading}
                      pagination={{ pageSize: 10 }}
                      size="small"
                      scroll={{ x: true }}
                    />
                  </Card>

                  <Card title="Rule Evaluation Results" size="small">
                    <Table
                      dataSource={ruleResults.map((r, idx) => ({ key: `${r.rule_id}-${idx}`, ...r }))}
                      columns={ruleResultColumns}
                      loading={resultsLoading}
                      pagination={{ pageSize: 10 }}
                      size="small"
                      scroll={{ x: true }}
                    />
                  </Card>
                </Space>
              </TabPane>
            </Tabs>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PropertyDetails;
