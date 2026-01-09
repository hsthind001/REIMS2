/**
 * NLQ Dedicated Page
 *
 * Standalone page for natural language queries with enhanced features
 */

import React, { useState } from 'react';
import { Row, Col, Card, Tabs, Select, Button, Space, Tag } from 'antd';
import {
  SearchOutlined,
  QuestionCircleOutlined,
  CalculatorOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import NLQSearchBar from '../components/NLQSearchBar';
import './NLQPage.css';

const { TabPane } = Tabs;
const { Option } = Select;

const NLQPage = () => {
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [queryHistory, setQueryHistory] = useState([
    { query: "What was cash position in November 2025?", timestamp: "2 minutes ago" },
    { query: "How is DSCR calculated?", timestamp: "5 minutes ago" },
    { query: "Show revenue for Q4 2025", timestamp: "10 minutes ago" }
  ]);

  const properties = [
    { code: 'ESP', name: 'Esperanza', id: 1 },
    { code: 'OAK', name: 'Oakland Plaza', id: 2 },
    { code: 'PIN', name: 'Pinecrest', id: 3 },
    { code: 'MAP', name: 'Maple Grove', id: 4 }
  ];

  const exampleQueries = {
    'Financial Data': [
      "What was the cash position in November 2025?",
      "Show me total revenue for Q4 2025",
      "What are total assets for property ESP?",
      "Show operating expenses for last month",
      "Compare net income YTD vs last year"
    ],
    'Formulas & Calculations': [
      "How is DSCR calculated?",
      "What is the formula for Current Ratio?",
      "Explain NOI calculation",
      "Calculate DSCR for property ESP in November 2025",
      "What is the benchmark for good DSCR?"
    ],
    'Temporal Queries': [
      "Show data for last 3 months",
      "Compare Q4 2025 vs Q4 2024",
      "Year to date revenue",
      "Month to date expenses",
      "Between August and December 2025"
    ],
    'Audit & History': [
      "Who changed cash position in November 2025?",
      "Show me audit history for property ESP",
      "What was modified last week?",
      "List all changes by user John Doe"
    ]
  };

  const handleExampleClick = (query) => {
    // This would trigger the search
    console.log("Example query:", query);
  };

  return (
    <div className="nlq-page-container page-content">
      <div className="nlq-page-header">
        <h1><SearchOutlined /> Natural Language Query</h1>
        <p>Ask questions about your financial data in plain English</p>
      </div>

      <Row gutter={[16, 16]}>
        {/* Main Search Area */}
        <Col xs={24} lg={16}>
          <Card>
            {/* Property Selector */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ marginRight: 12, fontWeight: 600 }}>
                Filter by Property (Optional):
              </label>
              <Select
                value={selectedProperty}
                onChange={setSelectedProperty}
                style={{ width: 250 }}
                placeholder="All Properties"
                allowClear
              >
                {properties.map(prop => (
                  <Option key={prop.code} value={prop.code}>
                    {prop.name} ({prop.code})
                  </Option>
                ))}
              </Select>
            </div>

            {/* NLQ Search Bar */}
            <NLQSearchBar
              propertyCode={selectedProperty}
              propertyId={
                selectedProperty
                  ? properties.find(p => p.code === selectedProperty)?.id
                  : null
              }
            />
          </Card>

          {/* Query History */}
          <Card
            title={<span><HistoryOutlined /> Recent Queries</span>}
            style={{ marginTop: 16 }}
          >
            {queryHistory.map((item, index) => (
              <div key={index} className="history-item">
                <Button
                  type="link"
                  onClick={() => handleExampleClick(item.query)}
                  style={{ padding: 0 }}
                >
                  {item.query}
                </Button>
                <span className="history-timestamp">{item.timestamp}</span>
              </div>
            ))}
          </Card>
        </Col>

        {/* Examples & Help */}
        <Col xs={24} lg={8}>
          <Card title={<span><QuestionCircleOutlined /> Example Queries</span>}>
            <Tabs defaultActiveKey="1" tabPosition="top" size="small">
              {Object.entries(exampleQueries).map(([category, queries], idx) => (
                <TabPane tab={category} key={String(idx + 1)}>
                  <div className="example-queries">
                    {queries.map((query, qIdx) => (
                      <Button
                        key={qIdx}
                        type="text"
                        size="small"
                        onClick={() => handleExampleClick(query)}
                        className="example-query-button"
                      >
                        💡 {query}
                      </Button>
                    ))}
                  </div>
                </TabPane>
              ))}
            </Tabs>
          </Card>

          <Card
            title={<span><CalculatorOutlined /> Supported Features</span>}
            style={{ marginTop: 16 }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Tag color="blue">✓ Temporal Queries (10+ types)</Tag>
              <Tag color="green">✓ 50+ Financial Formulas</Tag>
              <Tag color="purple">✓ Multi-Statement Analysis</Tag>
              <Tag color="orange">✓ Audit Trail Queries</Tag>
              <Tag color="cyan">✓ Comparative Analysis</Tag>
              <Tag color="magenta">✓ Natural Language</Tag>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default NLQPage;
