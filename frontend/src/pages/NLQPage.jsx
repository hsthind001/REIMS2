/**
 * NLQ Dedicated Page
 *
 * Standalone page for natural language queries with enhanced features
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Row, Col, Card, Tabs, Select, Button, Space, Tag, Divider } from 'antd';
import {
  SearchOutlined,
  QuestionCircleOutlined,
  CalculatorOutlined,
  HistoryOutlined,
  PushpinOutlined,
  PushpinFilled,
  StarOutlined,
  StarFilled,
  DeleteOutlined
} from '@ant-design/icons';
import NLQSearchBar from '../components/NLQSearchBar';
import './NLQPage.css';

const { TabPane } = Tabs;
const { Option } = Select;

const NLQPage = () => {
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [activeQuery, setActiveQuery] = useState('');
  const [queryHistory, setQueryHistory] = useState([
    {
      id: 'seed-1',
      query: "What was cash position in November 2025?",
      timestamp: "2 minutes ago",
      pinned: true,
      favorite: true
    },
    {
      id: 'seed-2',
      query: "How is DSCR calculated?",
      timestamp: "5 minutes ago",
      pinned: false,
      favorite: false
    },
    {
      id: 'seed-3',
      query: "Show revenue for Q4 2025",
      timestamp: "10 minutes ago",
      pinned: false,
      favorite: false
    }
  ]);

  const storageKey = 'nlq-query-history-v1';

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          const normalized = parsed.map((item, index) => ({
            id: item.id ?? `stored-${index}-${Date.now()}`,
            query: item.query,
            timestamp: item.timestamp ?? new Date().toLocaleString(),
            pinned: Boolean(item.pinned),
            favorite: Boolean(item.favorite)
          }));
          setQueryHistory(normalized);
        }
      } catch (err) {
        console.warn('Failed to parse NLQ history storage', err);
      }
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(queryHistory));
  }, [queryHistory]);

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
    setActiveQuery(query);
  };

  const handleQuerySubmit = (query) => {
    setQueryHistory((prev) => {
      const existing = prev.find((item) => item.query === query);
      const timestamp = new Date().toLocaleString();
      if (existing) {
        return [
          { ...existing, timestamp },
          ...prev.filter((item) => item.query !== query)
        ];
      }

      const entry = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        query,
        timestamp,
        pinned: false,
        favorite: false
      };
      return [entry, ...prev];
    });
  };

  const togglePinned = (id) => {
    setQueryHistory((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, pinned: !item.pinned } : item
      )
    );
  };

  const toggleFavorite = (id) => {
    setQueryHistory((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, favorite: !item.favorite } : item
      )
    );
  };

  const removeHistoryItem = (id) => {
    setQueryHistory((prev) => prev.filter((item) => item.id !== id));
  };

  const historySections = useMemo(() => {
    const pinned = queryHistory.filter((item) => item.pinned);
    const recent = queryHistory.filter((item) => !item.pinned);
    return { pinned, recent };
  }, [queryHistory]);

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
              quickPrompts={[
                "Summarize cash flow trends",
                "Show latest NOI",
                "Compare Q4 revenue vs Q3"
              ]}
              externalQuestion={activeQuery}
              onQuerySubmit={handleQuerySubmit}
            />
          </Card>
        </Col>

        {/* Examples & Help */}
        <Col xs={24} lg={8}>
          <Card
            title={<span><HistoryOutlined /> Query History</span>}
            className="nlq-history-panel"
          >
            {queryHistory.length === 0 ? (
              <div className="history-empty">
                <p>No saved questions yet.</p>
                <span>Run a search to build your history.</span>
              </div>
            ) : (
              <>
                {historySections.pinned.length > 0 && (
                  <div className="history-section">
                    <span className="history-section-title">Pinned</span>
                    {historySections.pinned.map((item) => (
                      <div key={item.id} className="history-item">
                        <Button
                          type="link"
                          onClick={() => handleExampleClick(item.query)}
                          className="history-query"
                        >
                          {item.query}
                        </Button>
                        <div className="history-actions">
                          <Button
                            type="text"
                            size="small"
                            onClick={() => togglePinned(item.id)}
                            icon={<PushpinFilled />}
                          />
                          <Button
                            type="text"
                            size="small"
                            onClick={() => toggleFavorite(item.id)}
                            icon={item.favorite ? <StarFilled /> : <StarOutlined />}
                          />
                          <Button
                            type="text"
                            size="small"
                            onClick={() => removeHistoryItem(item.id)}
                            icon={<DeleteOutlined />}
                          />
                        </div>
                        <span className="history-timestamp">{item.timestamp}</span>
                      </div>
                    ))}
                    <Divider className="history-divider" />
                  </div>
                )}
                <div className="history-section">
                  <span className="history-section-title">Recent</span>
                  {historySections.recent.map((item) => (
                    <div key={item.id ?? item.query} className="history-item">
                      <Button
                        type="link"
                        onClick={() => handleExampleClick(item.query)}
                        className="history-query"
                      >
                        {item.query}
                      </Button>
                      <div className="history-actions">
                        <Button
                          type="text"
                          size="small"
                          onClick={() => togglePinned(item.id)}
                          icon={<PushpinOutlined />}
                        />
                        <Button
                          type="text"
                          size="small"
                          onClick={() => toggleFavorite(item.id)}
                          icon={item.favorite ? <StarFilled /> : <StarOutlined />}
                        />
                        <Button
                          type="text"
                          size="small"
                          onClick={() => removeHistoryItem(item.id)}
                          icon={<DeleteOutlined />}
                        />
                      </div>
                      <span className="history-timestamp">
                        {item.favorite && <StarFilled className="history-favorite" />} {item.timestamp}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>

          <Card title={<span><QuestionCircleOutlined /> Example Queries</span>} style={{ marginTop: 16 }}>
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
