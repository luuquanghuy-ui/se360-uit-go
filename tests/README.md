# UIT-Go Testing Guide

## Test Structure

```
tests/
├── README.md              # This file
├── smoke_test.py          # Post-deployment smoke tests
├── test_userservice.py    # UserService unit tests
└── requirements.txt       # Test dependencies
```

## Running Tests

### 1. Unit Tests (Local)

```bash
# Install dependencies
pip install pytest requests fastapi httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_userservice.py -v

# Run with coverage
pytest tests/ --cov=UserService --cov-report=html
```

### 2. Smoke Tests (After Deployment)

```bash
# Install dependencies
pip install requests

# Run smoke tests against production
python tests/smoke_test.py

# Run smoke tests against local
BASE_URL=http://localhost:8000 python tests/smoke_test.py
```

### 3. Integration Tests (Docker Compose)

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
sleep 10

# Run integration tests
pytest tests/ --base-url=http://localhost:8000

# Stop services
docker-compose down
```

## GitHub Actions

Tests run automatically on:
- **Pull Requests**: All unit tests
- **Push to main**: Full CI/CD pipeline (test → build → deploy → smoke test)

### Manual Test Run

Go to GitHub Actions → "Run Tests Only" → "Run workflow"

## Writing New Tests

### Unit Test Template

```python
import pytest
from fastapi.testclient import TestClient

class TestFeature:
    def test_something(self):
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = some_function(input_data)

        # Assert
        assert result == expected_value
```

### Smoke Test Template

```python
def test_new_feature() -> bool:
    """Test description"""
    try:
        response = requests.get(f"{BASE_URL}/endpoint")
        if response.status_code == 200:
            log_test("Feature: SUCCESS", "pass")
            return True
        else:
            log_test("Feature: FAILED", "fail")
            return False
    except Exception as e:
        log_test(f"Feature: FAILED - {e}", "fail")
        return False
```

## Test Coverage Goals

- **Unit Tests**: > 80% code coverage
- **Integration Tests**: All major user flows
- **Smoke Tests**: All critical endpoints after deploy

## Continuous Testing

```bash
# Watch mode for development
pytest-watch tests/

# Run tests on file change
pytest --looponfail tests/
```

## Troubleshooting

### Tests fail locally but pass in CI
- Check Python version (should be 3.11)
- Check environment variables
- Check database connections

### Smoke tests fail after deployment
- Check pod logs: `kubectl logs -f deployment/userservice -n uitgo`
- Check pod status: `kubectl get pods -n uitgo`
- Verify health checks: `curl http://4.144.174.255/health`

### Database connection errors
- Ensure services can reach databases
- Check credentials in secrets
- Verify network policies

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [GitHub Actions docs](https://docs.github.com/en/actions)
