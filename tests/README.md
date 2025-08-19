# MemeVerse Test Suite

This directory contains comprehensive tests for the MemeVerse application.

## Test Structure

- `conftest.py` - pytest configuration and fixtures
- `test_database_service.py` - Database connection tests
- `test_user_service.py` - User service tests
- `test_auth_blueprint.py` - Authentication blueprint tests
- `test_models.py` - Data model tests
- `test_feed_service.py` - Feed service tests
- `test_like_service.py` - Like service tests
- `test_tag_service.py` - Tag service tests
- `test_media_service.py` - Media service tests
- `test_integration.py` - Integration tests
- `test_utils.py` - Utility function tests
- `requirements.txt` - Test dependencies
- `run_tests.py` - Test runner script

## Running Tests

### Basic Test Run

```bash
python tests/run_tests.py
```

### Run Tests with Coverage

```bash
python tests/run_tests.py --coverage
```

### Run Tests with pytest directly

```bash
python -m pytest tests/ -v
```

## Test Dependencies

Install test dependencies:

```bash
pip install -r tests/requirements.txt
```

## Test Database Cleanup

The test suite automatically cleans up after each test run:
- New users created during tests are removed
- New memes created during tests are removed
- Database state is restored to its initial state

This ensures that tests don't interfere with each other and that the database remains clean.

## Environment Variables

The tests use the same environment variables as the main application:
- `POSTGREST_USERNAME` - Database username
- `POSTGREST_PASSWORD` - Database password

These are loaded from the `.env` file in the project root.

## Test Suite Features

### 1. Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies to focus on the logic being tested
- Cover edge cases and error conditions

### 2. Integration Tests
- Test the interaction between different components
- Verify that services work together correctly
- Test database operations with real data

### 3. Database Cleanup
- Automatic cleanup of test data after each test
- Ensures tests don't interfere with each other
- Maintains database integrity

### 4. Mock Services
- Mock external services to avoid dependencies
- Simulate different scenarios and edge cases
- Ensure tests run consistently

## Writing New Tests

### 1. Test Structure
Follow the existing pattern:
- Use pytest for test framework
- Use async/await for async tests
- Use fixtures for setup/teardown

### 2. Database Tests
- Use the db_pool fixture for database access
- Always clean up test data
- Handle exceptions gracefully

### 3. Mocking
- Use unittest.mock for mocking
- Mock external services and dependencies
- Focus on testing the logic, not the dependencies

## Common Test Patterns

### 1. Service Tests
```python
@pytest.mark.asyncio
async def test_service_method(db_pool):
    # Setup
    service = MyService(db_pool)
    
    # Test
    result = await service.method()
    
    # Assert
    assert result is not None
```

### 2. Integration Tests
```python
@pytest.mark.asyncio
async def test_integration_flow(db_pool):
    # Setup multiple services
    service1 = Service1(db_pool)
    service2 = Service2(db_pool)
    
    # Test the flow
    result1 = await service1.method()
    result2 = await service2.method(result1)
    
    # Assert
    assert result2 is expected_value
```

## Troubleshooting

### 1. Database Connection Issues
- Verify .env file contains correct credentials
- Ensure database server is running
- Check network connectivity to database server

### 2. Test Failures
- Run individual test files to isolate issues
- Check test output for specific error messages
- Verify test data setup and cleanup

### 3. Performance Issues
- Use mocking to avoid slow external services
- Limit database operations in tests
- Use appropriate test scope (function vs session)
