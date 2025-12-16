# Testing Guide for REIMS2 NLQ/RAG System

## Overview

Comprehensive unit tests for the NLQ/RAG system components, including:
- Hallucination Detector
- Citation Extractor
- RAG Retrieval Service
- Structured Logging
- Correlation ID Middleware

## Test Structure

```
backend/tests/
├── conftest.py                    # Shared fixtures
├── services/
│   ├── test_hallucination_detector.py
│   ├── test_citation_extractor.py
│   └── test_rag_retrieval_service.py (to be added)
└── README_TESTING.md              # This file
```

## Running Tests

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Test File
```bash
pytest tests/services/test_hallucination_detector.py
```

### Run Specific Test Class
```bash
pytest tests/services/test_hallucination_detector.py::TestClaimExtraction
```

### Run Specific Test
```bash
pytest tests/services/test_hallucination_detector.py::TestClaimExtraction::test_should_extract_currency_claims
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Only Unit Tests (Skip Integration)
```bash
pytest -m "not integration"
```

### Run Only Fast Tests (Skip Slow)
```bash
pytest -m "not slow"
```

## Test Coverage

Target: **>80% code coverage**

Current coverage can be viewed by running:
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Test Categories

### Unit Tests
- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Fast execution (< 1 second per test)

### Integration Tests
- Test components working together
- May use real database (test DB)
- Marked with `@pytest.mark.integration`

### Performance Tests
- Test performance requirements
- Verify timeouts and resource usage
- Marked with `@pytest.mark.slow` if needed

## Fixtures

### Common Fixtures (in conftest.py)
- `db_session`: In-memory SQLite database session
- `mock_user`: Mock user object

### Service-Specific Fixtures
- `mock_db`: Mock database session
- `hallucination_detector`: HallucinationDetector instance
- `citation_extractor`: CitationExtractor instance
- `sample_claims`: Sample claim objects
- `sample_chunks`: Sample document chunks
- `sample_sql_queries`: Sample SQL queries
- `sample_sql_results`: Sample SQL results

## Test Patterns

### 1. Happy Path Tests
```python
def test_should_extract_currency_claims(self, hallucination_detector):
    """Test extraction of currency values"""
    text = "The NOI was $1,234,567.89"
    claims = hallucination_detector._extract_claims(text)
    assert len(claims) > 0
```

### 2. Edge Case Tests
```python
def test_should_handle_empty_text(self, hallucination_detector):
    """Test that empty text returns no claims"""
    claims = hallucination_detector._extract_claims("")
    assert len(claims) == 0
```

### 3. Error Handling Tests
```python
def test_should_handle_database_error_gracefully(self, hallucination_detector, mock_db):
    """Test graceful handling of database errors"""
    mock_db.query.side_effect = SQLAlchemyError("Database error")
    result = hallucination_detector.detect_hallucinations("Test")
    assert result is not None
```

### 4. Parametrized Tests
```python
@pytest.mark.parametrize("answer,expected_claims", [
    ("$1,234,567.89", 1),
    ("85.5%", 1),
    ("No numbers", 0),
])
def test_should_extract_claims_for_various_formats(self, hallucination_detector, answer, expected_claims):
    result = hallucination_detector.detect_hallucinations(answer)
    assert result['total_claims'] >= expected_claims
```

### 5. Performance Tests
```python
def test_should_complete_detection_quickly(self, hallucination_detector):
    """Test that detection completes within timeout"""
    start_time = time.time()
    result = hallucination_detector.detect_hallucinations("Test")
    duration = time.time() - start_time
    assert duration < 0.1  # < 100ms
```

## Mocking External Dependencies

### Database
```python
mock_db = Mock(spec=Session)
mock_db.query.return_value.filter.return_value.all.return_value = [sample_data]
```

### External APIs
```python
with patch('app.services.embedding_service.OpenAI') as mock_openai:
    mock_openai.return_value.embeddings.create.return_value = Mock(data=[Mock(embedding=[0.1]*1536)])
```

### Configuration
```python
with patch('app.services.hallucination_detector.hallucination_config') as mock_config:
    mock_config.CURRENCY_TOLERANCE_PERCENT = 5.0
```

## Test Data

### Sample Claims
- Currency: `$1,234,567.89`, `$2.5M`, `$500K`
- Percentage: `85.5%`, `12.5 percent`
- Ratio: `DSCR 1.25`, `1.5x coverage`
- Date: `Q3 2024`, `December 2024`, `2024-12-01`

### Sample Chunks
```python
{
    'chunk_id': 1,
    'chunk_text': 'The NOI was $1,234,567.89',
    'document_type': 'income_statement',
    'metadata': {'page': 2, 'line': 15}
}
```

## Edge Cases Covered

1. **Empty Inputs**: Empty strings, None values
2. **Very Long Inputs**: >10,000 characters
3. **Special Characters**: Unicode, emojis, special symbols
4. **Invalid Data Types**: Wrong types, None values
5. **Concurrent Requests**: Thread safety
6. **API Failures**: Network errors, timeouts
7. **Database Errors**: Connection failures, query errors
8. **Security**: ReDoS protection, input validation

## Continuous Integration

Tests should be run in CI/CD pipeline:
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml
    
- name: Check coverage
  run: |
    coverage report --fail-under=80
```

## Best Practices

1. **Descriptive Test Names**: Use `test_should_[action]_when_[condition]` format
2. **One Assertion Per Test**: Focus on single behavior
3. **Arrange-Act-Assert**: Clear test structure
4. **Use Fixtures**: Reuse common setup
5. **Mock External Dependencies**: Isolate unit under test
6. **Test Edge Cases**: Cover boundary conditions
7. **Performance Tests**: Verify timeouts and resource usage
8. **Documentation**: Explain test purpose in docstrings

## Troubleshooting

### Tests Failing
1. Check test database is set up correctly
2. Verify mocks are configured properly
3. Check for import errors
4. Review test output for specific failures

### Coverage Below 80%
1. Identify untested code paths
2. Add tests for edge cases
3. Test error handling paths
4. Test all branches in conditionals

### Slow Tests
1. Use mocks instead of real database
2. Mark slow tests with `@pytest.mark.slow`
3. Run only fast tests during development
4. Optimize test data setup

## Next Steps

1. Add tests for RAGRetrievalService
2. Add tests for structured logging
3. Add tests for correlation ID middleware
4. Add integration tests with real database
5. Add performance benchmarks
6. Add load tests for concurrent requests

