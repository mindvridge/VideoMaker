# Testing Guide

Comprehensive guide for testing the AI Video Generation application.

## Table of Contents
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)

## Quick Start

### Install Test Dependencies

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Run all tests
make test

# Or directly with pytest
cd backend
pytest
```

### Run Specific Tests

```bash
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run API tests
pytest -m api

# Run security tests
pytest -m security

# Run a specific test file
pytest tests/test_api_endpoints.py

# Run a specific test
pytest tests/test_api_endpoints.py::TestBasicEndpoints::test_root_endpoint
```

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_api_endpoints.py    # API endpoint tests
├── test_models.py           # Model manager tests
├── test_storage.py          # S3 storage tests
├── test_tasks.py            # Celery task tests
└── test_security.py         # Security tests (CORS, rate limiting)
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, multiple components)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.celery` - Celery task tests
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.slow` - Slow running tests

## Running Tests

### Basic Commands

```bash
# Run all tests with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run with parallel execution (faster)
pytest -n auto

# Run only failed tests from last run
pytest --lf

# Run tests and stop on first failure
pytest -x
```

### Using Make Commands

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run linting
make lint

# Format code
make format
```

### Environment-Specific Tests

```bash
# Development environment (default)
ENVIRONMENT=development pytest

# Staging environment
ENVIRONMENT=staging pytest

# Production-like tests
ENVIRONMENT=production pytest
```

## Test Coverage

### Viewing Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Requirements

- **Minimum coverage**: 70%
- **Target coverage**: 85%
- **Critical modules**: 90%+ (API, security)

### Current Coverage

Check the latest coverage report:
```bash
pytest --cov=app --cov-report=term-missing
```

## Writing Tests

### Test Fixtures

Use fixtures from `conftest.py`:

```python
def test_example(client, mock_redis, sample_video_request):
    """Example test using fixtures."""
    response = client.post("/api/generate", json=sample_video_request)
    assert response.status_code == 200
```

### Available Fixtures

- `client` - FastAPI test client
- `mock_redis` - Fake Redis instance
- `mock_s3` - Mocked S3 client
- `mock_celery_task` - Mocked Celery task
- `sample_video_request` - Sample request data
- `sample_task_result` - Sample task result
- `temp_video_file` - Temporary video file
- `temp_image_file` - Temporary image file

### Mocking Examples

#### Mock External Services

```python
from unittest.mock import patch

@patch("app.main.generate_video_task")
def test_with_mocked_task(mock_task, client):
    mock_task.apply_async.return_value.id = "test-123"
    response = client.post("/api/generate", json={...})
    assert response.status_code == 200
```

#### Mock S3 Operations

```python
def test_upload(mock_s3, storage):
    result = storage.upload_video("/path/to/video.mp4")
    assert result["success"] is True
```

### Test Organization

#### Unit Tests

Test individual components in isolation:

```python
@pytest.mark.unit
class TestModelManager:
    def test_initialization(self):
        manager = GPUModelManager()
        assert manager.models == {}
```

#### Integration Tests

Test multiple components together:

```python
@pytest.mark.integration
class TestVideoGenerationFlow:
    def test_full_flow(self, client, mock_s3):
        # Submit task
        response = client.post("/api/generate", json={...})
        task_id = response.json()["task_id"]

        # Check status
        status = client.get(f"/api/status/{task_id}")
        assert status.json()["status"] == "pending"
```

#### API Tests

Test API endpoints:

```python
@pytest.mark.api
def test_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
```

### Best Practices

1. **Descriptive Test Names**
   ```python
   # Good
   def test_generate_video_with_invalid_model_returns_400()

   # Bad
   def test_video()
   ```

2. **Arrange-Act-Assert Pattern**
   ```python
   def test_example():
       # Arrange - Set up test data
       request = {"model_type": "wan-2.2-t2v", ...}

       # Act - Execute the code
       response = client.post("/api/generate", json=request)

       # Assert - Verify results
       assert response.status_code == 200
   ```

3. **Use Fixtures for Setup**
   ```python
   @pytest.fixture
   def video_request():
       return {"model_type": "wan-2.2-t2v", "prompt": "test"}

   def test_with_fixture(video_request):
       # Use video_request
       pass
   ```

4. **Test Edge Cases**
   ```python
   def test_empty_prompt():
       """Test with empty prompt."""

   def test_extremely_long_prompt():
       """Test with very long prompt."""

   def test_special_characters():
       """Test with special characters."""
   ```

5. **Mock External Dependencies**
   - Always mock S3, GPU models, external APIs
   - Use `fakeredis` for Redis
   - Use `moto` for AWS services

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Every push to `main`, `develop`, or `claude/**` branches
- Every pull request

### CI Pipeline Stages

1. **Backend Tests**
   - Install dependencies
   - Run linting (flake8, black, isort)
   - Run tests with coverage
   - Upload coverage to Codecov

2. **Frontend Tests**
   - Install dependencies
   - Run linting
   - Type checking
   - Build test

3. **Docker Build**
   - Build backend image
   - Build frontend image

4. **Security Scan**
   - Trivy vulnerability scan
   - Python security check (safety, bandit)

### Local CI Simulation

Run the same checks locally:

```bash
# Backend checks
cd backend
flake8 app/
black --check app/
isort --check app/
pytest --cov=app

# Frontend checks
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest -s

# Very verbose
pytest -vv

# Show local variables on failure
pytest -l
```

### Debug Specific Test

```bash
# Run with debugger
pytest --pdb tests/test_api_endpoints.py::test_specific

# Drop into debugger on failure
pytest --pdb -x
```

### View Logs

```bash
# Show log output
pytest --log-cli-level=DEBUG
```

## Performance Testing

### Load Tests

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py
```

### Benchmarking

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmark tests
pytest tests/test_performance.py --benchmark-only
```

## Test Data

### Fixtures Location

- `conftest.py` - Shared fixtures
- `fixtures/` - Sample data files (if needed)

### Generating Test Data

```python
@pytest.fixture
def sample_data():
    """Generate sample test data."""
    return {
        "field1": "value1",
        "field2": "value2"
    }
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure app is in PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Redis Connection**
   ```bash
   # Use fakeredis (automatic in tests)
   # Or start real Redis:
   docker run -d -p 6379:6379 redis:7-alpine
   ```

3. **Coverage Not Generated**
   ```bash
   # Ensure pytest-cov is installed
   pip install pytest-cov
   ```

4. **Tests Hanging**
   ```bash
   # Set timeout
   pytest --timeout=300
   ```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)
