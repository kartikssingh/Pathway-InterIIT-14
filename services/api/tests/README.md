# Test Suite

This directory contains all tests for the backend application, organized by test type.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_db_connection.py         # Database connection tests
│   └── test_fastapi_db.py            # FastAPI database session tests
│
├── integration/             # Integration tests for API endpoints
│   ├── test_auth_api.py              # Authentication API tests
│   ├── test_dashboard_api.py         # Dashboard API tests
│   └── test_alert_classification.py  # Alert classification API tests
│
├── load/                    # Load and performance tests
│   └── (placeholder for future load tests)
│
└── e2e/                     # End-to-end tests
    └── (placeholder for future e2e tests)
```

## Test Types

### Unit Tests (`unit/`)
Tests for individual components in isolation:
- Database connection and session management
- Individual service functions
- Model validations
- Utility functions

### Integration Tests (`integration/`)
Tests for API endpoints and component interactions:
- API endpoint responses
- Database queries through API
- Authentication flows
- Multi-component interactions

### Load Tests (`load/`)
Performance and stress tests:
- API endpoint performance under load
- Database query optimization
- Concurrent user simulation
- Resource usage monitoring

### End-to-End Tests (`e2e/`)
Complete user workflow tests:
- Full user journeys
- Multi-step processes
- Cross-module functionality

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test type
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Load tests
pytest tests/load/

# E2E tests
pytest tests/e2e/
```

### Run specific test file
```bash
pytest tests/integration/test_auth_api.py
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Test Guidelines

1. **Unit Tests**: Should be fast, isolated, and not depend on external services
2. **Integration Tests**: Can use database and external APIs, but should clean up after themselves
3. **Load Tests**: Should be run separately, not in CI pipeline
4. **E2E Tests**: Should cover critical user paths and be maintainable

## Future Improvements

- [ ] Add pytest fixtures for common test setups
- [ ] Add conftest.py for shared configurations
- [ ] Implement proper test database setup/teardown
- [ ] Add load testing scenarios
- [ ] Create comprehensive e2e test suite
