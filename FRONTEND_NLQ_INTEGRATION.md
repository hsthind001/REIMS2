# Frontend Integration Guide - REIMS NLQ System

## 🎯 Overview

This guide shows how to integrate the NLQ (Natural Language Query) system into your React frontend.

---

## 📋 Table of Contents

1. [Quick Integration](#quick-integration)
2. [API Endpoints](#api-endpoints)
3. [React Components](#react-components)
4. [Complete Example](#complete-example)
5. [Advanced Features](#advanced-features)

---

## 🚀 Quick Integration

### Step 1: Create API Service

Create `frontend/src/services/nlqService.js`:

```javascript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class NLQService {
  /**
   * Send natural language query
   * @param {string} question - Natural language question
   * @param {object} context - Optional context (property_id, property_code)
   * @param {number} userId - User ID
   */
  async query(question, context = null, userId = 1) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/nlq/query`, {
        question,
        context,
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('NLQ query error:', error);
      throw error;
    }
  }

  /**
   * Parse temporal expression
   * @param {string} query - Query with temporal expression
   */
  async parseTemporal(query) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/nlq/temporal/parse`, {
        query
      });
      return response.data;
    } catch (error) {
      console.error('Temporal parse error:', error);
      throw error;
    }
  }

  /**
   * Get all available formulas
   * @param {string} category - Optional category filter
   */
  async getFormulas(category = null) {
    try {
      const params = category ? { category } : {};
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/formulas`, { params });
      return response.data;
    } catch (error) {
      console.error('Get formulas error:', error);
      throw error;
    }
  }

  /**
   * Get specific formula details
   * @param {string} metric - Formula metric name (e.g., 'dscr', 'current_ratio')
   */
  async getFormula(metric) {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/formulas/${metric}`);
      return response.data;
    } catch (error) {
      console.error('Get formula error:', error);
      throw error;
    }
  }

  /**
   * Calculate specific metric
   * @param {string} metric - Metric name
   * @param {object} params - Calculation parameters
   */
  async calculateMetric(metric, params) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/nlq/calculate/${metric}`,
        params
      );
      return response.data;
    } catch (error) {
      console.error('Calculate metric error:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/nlq/health`);
      return response.data;
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  }
}

export default new NLQService();
```

### Step 2: Create React Hook

Create `frontend/src/hooks/useNLQ.js`:

```javascript
import { useState } from 'react';
import nlqService from '../services/nlqService';

export const useNLQ = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const query = async (question, context = null) => {
    setLoading(true);
    setError(null);

    try {
      const response = await nlqService.query(question, context);
      setResult(response);
      return response;
    } catch (err) {
      setError(err.message || 'Query failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setResult(null);
    setError(null);
  };

  return {
    query,
    loading,
    error,
    result,
    reset
  };
};
```

---

## 📡 API Endpoints

### 1. Main Query Endpoint

**POST** `/api/v1/nlq/query`

**Request:**
```json
{
  "question": "What was the cash position in November 2025?",
  "context": {
    "property_code": "ESP",
    "property_id": 1
  },
  "user_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "answer": "The cash position for property ESP in November 2025 was $156,438.52.",
  "data": [
    {
      "property_code": "ESP",
      "year": 2025,
      "month": 11,
      "amount": 156438.52
    }
  ],
  "metadata": {
    "temporal_info": {
      "has_temporal": true,
      "temporal_type": "absolute",
      "normalized_expression": "November 2025"
    }
  },
  "confidence_score": 0.92,
  "execution_time_ms": 1523
}
```

### 2. Temporal Parse Endpoint

**POST** `/api/v1/nlq/temporal/parse`

**Request:**
```json
{
  "query": "last 3 months"
}
```

**Response:**
```json
{
  "has_temporal": true,
  "temporal_type": "relative",
  "filters": {
    "start_date": "2025-10-01",
    "end_date": "2026-01-01"
  },
  "normalized_expression": "Last 3 Months"
}
```

### 3. Formulas Endpoint

**GET** `/api/v1/nlq/formulas?category=mortgage`

**Response:**
```json
{
  "success": true,
  "count": 4,
  "category": "mortgage",
  "formulas": {
    "dscr": {
      "name": "Debt Service Coverage Ratio",
      "formula": "NOI / Annual Debt Service",
      "category": "mortgage",
      "benchmark": {
        "excellent": "> 1.5",
        "good": "1.25 - 1.5"
      }
    }
  }
}
```

### 4. Calculate Metric Endpoint

**POST** `/api/v1/nlq/calculate/dscr`

**Request:**
```json
{
  "property_id": 1,
  "year": 2025,
  "month": 11
}
```

**Response:**
```json
{
  "success": true,
  "metric": "dscr",
  "value": 1.45,
  "benchmark": "good",
  "calculation_details": {
    "noi": 145000,
    "annual_debt_service": 100000
  }
}
```

---

## 🎨 React Components

### Option 1: Simple Search Bar

Create `frontend/src/components/NLQSearchBar.jsx`:

```jsx
import React, { useState } from 'react';
import { useNLQ } from '../hooks/useNLQ';
import { Card, Input, Button, Spin, Alert } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const NLQSearchBar = ({ propertyCode = null }) => {
  const [question, setQuestion] = useState('');
  const { query, loading, error, result } = useNLQ();

  const handleSearch = async () => {
    if (!question.trim()) return;

    const context = propertyCode ? { property_code: propertyCode } : null;
    await query(question, context);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Card title="Ask a Question" style={{ marginBottom: 20 }}>
      <Input.Search
        placeholder="Ask anything... (e.g., What was cash position in November 2025?)"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyPress={handleKeyPress}
        onSearch={handleSearch}
        loading={loading}
        enterButton={
          <Button type="primary" icon={<SearchOutlined />}>
            Ask
          </Button>
        }
        size="large"
      />

      {loading && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Spin size="large" tip="Thinking..." />
        </div>
      )}

      {error && (
        <Alert
          type="error"
          message="Error"
          description={error}
          style={{ marginTop: 20 }}
          closable
        />
      )}

      {result && !loading && (
        <Card
          type="inner"
          style={{ marginTop: 20 }}
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Answer</span>
              <span style={{ fontSize: 12, fontWeight: 'normal' }}>
                Confidence: {(result.confidence_score * 100).toFixed(0)}%
                {' • '}
                {result.execution_time_ms}ms
              </span>
            </div>
          }
        >
          <div style={{ whiteSpace: 'pre-wrap' }}>{result.answer}</div>

          {result.data && result.data.length > 0 && (
            <div style={{ marginTop: 15 }}>
              <strong>Data:</strong>
              <pre style={{ background: '#f5f5f5', padding: 10, borderRadius: 4 }}>
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      )}
    </Card>
  );
};

export default NLQSearchBar;
```

**Usage:**
```jsx
import NLQSearchBar from './components/NLQSearchBar';

function App() {
  return (
    <div>
      <NLQSearchBar propertyCode="ESP" />
    </div>
  );
}
```

### Option 2: Chat Interface

Create `frontend/src/components/NLQChat.jsx`:

```jsx
import React, { useState } from 'react';
import { useNLQ } from '../hooks/useNLQ';
import { Card, Input, Button, List, Avatar, Spin } from 'antd';
import { UserOutlined, RobotOutlined, SendOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const NLQChat = ({ propertyCode = null }) => {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const { query, loading } = useNLQ();

  const handleSend = async () => {
    if (!question.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: question,
      timestamp: new Date()
    };
    setMessages([...messages, userMessage]);

    const currentQuestion = question;
    setQuestion('');

    // Get answer
    try {
      const context = propertyCode ? { property_code: propertyCode } : null;
      const response = await query(currentQuestion, context);

      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.answer,
        data: response.data,
        metadata: response.metadata,
        confidence: response.confidence_score,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: `Sorry, I encountered an error: ${err.message}`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  return (
    <Card title="NLQ Chat Assistant" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
        <List
          dataSource={messages}
          renderItem={(message) => (
            <List.Item style={{ border: 'none', padding: '12px 0' }}>
              <List.Item.Meta
                avatar={
                  <Avatar
                    icon={message.type === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: message.type === 'user' ? '#1890ff' : '#52c41a'
                    }}
                  />
                }
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{message.type === 'user' ? 'You' : 'AI Assistant'}</span>
                    <span style={{ fontSize: 12, color: '#999' }}>
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                }
                description={
                  <div>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                    {message.confidence && (
                      <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                        Confidence: {(message.confidence * 100).toFixed(0)}%
                      </div>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
        {loading && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin tip="Thinking..." />
          </div>
        )}
      </div>

      <Input.Search
        placeholder="Ask a question..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onSearch={handleSend}
        onPressEnter={handleSend}
        enterButton={
          <Button type="primary" icon={<SendOutlined />} loading={loading}>
            Send
          </Button>
        }
        disabled={loading}
      />
    </Card>
  );
};

export default NLQChat;
```

### Option 3: Formula Explorer

Create `frontend/src/components/FormulaExplorer.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import nlqService from '../services/nlqService';
import { Card, Collapse, Tag, Descriptions, Button, message } from 'antd';
import { CalculatorOutlined } from '@ant-design/icons';

const { Panel } = Collapse;

const FormulaExplorer = ({ propertyId = null }) => {
  const [formulas, setFormulas] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFormulas();
  }, []);

  const loadFormulas = async () => {
    try {
      const response = await nlqService.getFormulas();
      setFormulas(response.formulas || {});
    } catch (error) {
      message.error('Failed to load formulas');
    } finally {
      setLoading(false);
    }
  };

  const handleCalculate = async (metricKey) => {
    if (!propertyId) {
      message.warning('Please select a property first');
      return;
    }

    try {
      const result = await nlqService.calculateMetric(metricKey, {
        property_id: propertyId,
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1
      });

      message.success(`${metricKey.toUpperCase()}: ${result.value}`);
    } catch (error) {
      message.error('Calculation failed');
    }
  };

  return (
    <Card title="Formula Explorer" loading={loading}>
      <Collapse accordion>
        {Object.entries(formulas).map(([key, formula]) => (
          <Panel
            key={key}
            header={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{formula.name}</span>
                <Tag color={formula.critical ? 'red' : 'blue'}>{formula.category}</Tag>
              </div>
            }
          >
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Formula">
                <code>{formula.formula}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Explanation">
                {formula.explanation}
              </Descriptions.Item>
              {formula.benchmark && (
                <Descriptions.Item label="Benchmarks">
                  {Object.entries(formula.benchmark).map(([level, value]) => (
                    <div key={level}>
                      <Tag color={level === 'excellent' ? 'green' : level === 'good' ? 'blue' : 'orange'}>
                        {level}
                      </Tag>
                      {value}
                    </div>
                  ))}
                </Descriptions.Item>
              )}
            </Descriptions>

            {propertyId && (
              <Button
                type="primary"
                icon={<CalculatorOutlined />}
                onClick={() => handleCalculate(key)}
                style={{ marginTop: 12 }}
              >
                Calculate Now
              </Button>
            )}
          </Panel>
        ))}
      </Collapse>
    </Card>
  );
};

export default FormulaExplorer;
```

---

## 🎯 Complete Example

### Full Integration in Dashboard

Create `frontend/src/pages/NLQDashboard.jsx`:

```jsx
import React, { useState } from 'react';
import { Layout, Row, Col, Select, Tabs } from 'antd';
import NLQSearchBar from '../components/NLQSearchBar';
import NLQChat from '../components/NLQChat';
import FormulaExplorer from '../components/FormulaExplorer';

const { Content } = Layout;
const { TabPane } = Tabs;

const NLQDashboard = () => {
  const [selectedProperty, setSelectedProperty] = useState('ESP');

  return (
    <Layout style={{ minHeight: '100vh', padding: 24 }}>
      <Content>
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <div style={{ marginBottom: 16 }}>
              <label>Select Property: </label>
              <Select
                value={selectedProperty}
                onChange={setSelectedProperty}
                style={{ width: 200, marginLeft: 8 }}
              >
                <Select.Option value="ESP">Esperanza (ESP)</Select.Option>
                <Select.Option value="OAK">Oakland (OAK)</Select.Option>
                <Select.Option value="PIN">Pinecrest (PIN)</Select.Option>
              </Select>
            </div>
          </Col>

          <Col span={24}>
            <Tabs defaultActiveKey="search">
              <TabPane tab="Quick Search" key="search">
                <NLQSearchBar propertyCode={selectedProperty} />
              </TabPane>

              <TabPane tab="Chat Interface" key="chat">
                <NLQChat propertyCode={selectedProperty} />
              </TabPane>

              <TabPane tab="Formula Explorer" key="formulas">
                <FormulaExplorer propertyId={1} />
              </TabPane>
            </Tabs>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default NLQDashboard;
```

### Add to Your Routes

In `frontend/src/App.js`:

```jsx
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import NLQDashboard from './pages/NLQDashboard';

function App() {
  return (
    <Router>
      <Routes>
        {/* Your existing routes */}
        <Route path="/nlq" element={<NLQDashboard />} />
      </Routes>
    </Router>
  );
}
```

---

## 🚀 Advanced Features

### 1. Add to Existing Pages

**Example: Add NLQ to Property Details Page**

```jsx
import NLQSearchBar from '../components/NLQSearchBar';

const PropertyDetailsPage = ({ propertyCode }) => {
  return (
    <div>
      {/* Existing property details */}

      {/* Add NLQ search */}
      <NLQSearchBar propertyCode={propertyCode} />
    </div>
  );
};
```

### 2. Add Quick Actions

```jsx
const QuickQuestions = ({ propertyCode, onQuestionClick }) => {
  const questions = [
    `What was cash position for ${propertyCode} last month?`,
    `Calculate DSCR for ${propertyCode}`,
    `Show revenue YTD for ${propertyCode}`,
    `How is NOI calculated?`
  ];

  return (
    <div>
      <h4>Quick Questions:</h4>
      {questions.map((q, i) => (
        <Button
          key={i}
          type="link"
          onClick={() => onQuestionClick(q)}
          style={{ display: 'block', marginBottom: 8 }}
        >
          {q}
        </Button>
      ))}
    </div>
  );
};
```

### 3. Add to Navigation

```jsx
// In your navigation menu
<Menu.Item key="nlq" icon={<SearchOutlined />}>
  <Link to="/nlq">Ask Questions</Link>
</Menu.Item>
```

### 4. Voice Input (Optional)

```jsx
import { AudioOutlined } from '@ant-design/icons';

const VoiceInput = ({ onResult }) => {
  const startListening = () => {
    const recognition = new window.webkitSpeechRecognition();
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
    };
    recognition.start();
  };

  return (
    <Button icon={<AudioOutlined />} onClick={startListening}>
      Voice Input
    </Button>
  );
};
```

---

## 📦 Installation

### Required npm packages:

```bash
cd frontend

# If not already installed
npm install axios react-markdown
```

### Optional packages:

```bash
# For better markdown rendering
npm install remark-gfm

# For syntax highlighting in code blocks
npm install react-syntax-highlighter
```

---

## ⚙️ Environment Configuration

Create `frontend/.env`:

```bash
REACT_APP_API_URL=http://localhost:8000
```

For production:

```bash
REACT_APP_API_URL=https://your-production-domain.com
```

---

## 🎨 Styling

### Custom Styles

Create `frontend/src/styles/nlq.css`:

```css
.nlq-search-bar {
  max-width: 800px;
  margin: 0 auto;
}

.nlq-result {
  background: #f9f9f9;
  border-left: 4px solid #1890ff;
  padding: 16px;
  margin-top: 16px;
  border-radius: 4px;
}

.nlq-confidence-high {
  color: #52c41a;
}

.nlq-confidence-medium {
  color: #faad14;
}

.nlq-confidence-low {
  color: #f5222d;
}

.nlq-chat-message {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

---

## 🧪 Testing Your Integration

### 1. Test the API Connection

```jsx
// In your component
useEffect(() => {
  nlqService.healthCheck()
    .then(health => console.log('NLQ Health:', health))
    .catch(err => console.error('NLQ not available:', err));
}, []);
```

### 2. Test Example Queries

```javascript
const testQueries = [
  "What was cash position in November 2025?",
  "How is DSCR calculated?",
  "Show revenue for Q4 2025",
  "Calculate current ratio for ESP"
];
```

### 3. Check Response Structure

```javascript
const handleQuery = async (question) => {
  const response = await nlqService.query(question);

  console.log('Success:', response.success);
  console.log('Answer:', response.answer);
  console.log('Data:', response.data);
  console.log('Confidence:', response.confidence_score);
  console.log('Time:', response.execution_time_ms + 'ms');
};
```

---

## 🎯 Example Use Cases

### 1. Dashboard Widget

```jsx
<Card title="Quick Insights">
  <NLQSearchBar
    propertyCode={currentProperty}
    placeholder="Ask about this property..."
  />
</Card>
```

### 2. Report Builder

```jsx
<Modal title="Ask AI" visible={showNLQ}>
  <NLQChat propertyCode={reportProperty} />
</Modal>
```

### 3. Help/Support

```jsx
<Drawer title="AI Assistant" visible={showHelp}>
  <NLQSearchBar placeholder="How can I help you?" />
</Drawer>
```

---

## 🚀 Next Steps

1. **Try it out:**
   - Copy the components to your frontend
   - Add to your existing pages
   - Test with example queries

2. **Customize:**
   - Match your UI design
   - Add property-specific context
   - Customize result display

3. **Enhance:**
   - Add voice input
   - Add query history
   - Add favorites/bookmarks
   - Add export functionality

---

## 📞 Support

If you encounter issues:

1. Check backend is running: `http://localhost:8000/api/v1/nlq/health`
2. Check CORS settings in backend
3. Check browser console for errors
4. Verify API_BASE_URL is correct

---

**You're all set! The NLQ system is now accessible from your React frontend.** 🎉
