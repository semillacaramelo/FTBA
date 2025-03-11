# Testing Strategy

This document outlines the testing approach for the FTBA system, including test types, test infrastructure, and best practices.

## Testing Objectives

The FTBA testing strategy aims to:

1. **Verify Correctness**: Ensure that system components work as expected
2. **Validate Integration**: Confirm that components interact correctly
3. **Ensure Performance**: Verify that the system meets performance requirements
4. **Verify API Integration**: Confirm correct interaction with external APIs
5. **Test Error Handling**: Validate robustness in error scenarios
6. **Validate Configuration**: Ensure configuration handling works properly

## Test Types

### Unit Tests

Unit tests focus on individual components in isolation:

- Located in `tests/` directory with `test_` prefix
- Test individual classes and functions
- Use pytest for test discovery and execution
- Employ mocking for external dependencies

Example unit test:
```python
async def test_agent_initialization(message_broker):
    """Test agent initialization"""
    agent = TestAgent("test_agent", message_broker)
    await agent.setup()
    
    assert agent.agent_id == "test_agent"
    assert not agent._running
    assert agent._message_broker is message_broker
```

### Integration Tests

Integration tests verify the interaction between system components:

- Test communication between agents
- Validate message broker functionality
- Test data flow through the system
- Verify configuration loading and validation

Example integration test:
```python
async def test_technical_analysis_risk_management_integration():
    """Test integration between technical analysis and risk management agents"""
    # Setup
    message_broker = MessageBroker()
    ta_agent = TechnicalAnalysisAgent("ta_agent", message_broker)
    risk_agent = RiskManagementAgent("risk_agent", message_broker)
    
    # Start agents
    await ta_agent.start()
    await risk_agent.start()
    
    # Inject test data
    await ta_agent.inject_test_signal(signal_data)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Verify risk agent received and processed the signal
    assert risk_agent.last_processed_signal is not None
    assert risk_agent.last_processed_signal.symbol == signal_data["symbol"]
```

### API Integration Tests

These tests verify correct interaction with external APIs:

- Test Deriv API client functionality
- Validate error handling for API failures
- Test reconnection logic
- Verify proper mapping between system concepts and API-specific entities

Example API test:
```python
async def test_deriv_api_buy_contract(mock_deriv_api):
    """Test buying a contract through the Deriv API"""
    # Setup mock response
    mock_deriv_api.set_buy_response({
        "buy": {
            "contract_id": "123456789",
            "longcode": "Win payout if EUR/USD rises",
            "purchase_time": 1234567890,
            "buy_price": 10.0
        }
    })
    
    # Create client and execute request
    client = DerivApiClient(app_id="12345")
    result = await client.buy_contract("proposal_id_123", 10.0)
    
    # Verify result
    assert result["contract_id"] == "123456789"
    assert result["buy_price"] == 10.0
```

### System Tests

System tests validate the entire system end-to-end:

- Test complete workflow from market data to trade execution
- Validate system startup and shutdown sequences
- Test recovery from various error scenarios
- Verify logging and monitoring functionality

Example system test:
```python
async def test_complete_trading_workflow():
    """Test the complete trading workflow from signal to execution"""
    # Initialize the system with test configuration
    config = load_test_config()
    system = await initialize_system(config)
    
    # Inject test market data
    await inject_test_market_data(system)
    
    # Wait for processing
    await asyncio.sleep(1.0)
    
    # Verify that a trade was proposed, approved, and executed
    trade_execution_agent = system.agents["trade_execution"]
    assert len(trade_execution_agent.executed_trades) > 0
    
    # Validate the trade details
    trade = trade_execution_agent.executed_trades[0]
    assert trade.symbol == "EUR/USD"
    assert trade.status == TradeStatus.EXECUTED
```

### Performance Tests

Performance tests verify that the system meets performance requirements:

- Measure message processing throughput
- Evaluate resource usage under load
- Test handling of large data volumes
- Benchmark critical operations

Example performance test:
```python
async def test_message_broker_throughput():
    """Test message broker throughput"""
    # Setup
    message_broker = MessageBroker()
    receivers = [TestAgent(f"receiver_{i}", message_broker) for i in range(10)]
    sender = TestAgent("sender", message_broker)
    
    # Subscribe to test message type
    for receiver in receivers:
        await receiver.subscribe_to([MessageType.TEST])
    
    # Measure time to process 1000 messages
    start_time = time.time()
    
    for i in range(1000):
        await sender.send_message(MessageType.TEST, {"data": i})
    
    # Wait for processing
    await asyncio.sleep(1.0)
    
    end_time = time.time()
    
    # Calculate throughput
    throughput = 1000 / (end_time - start_time)
    
    # Verify meets minimum throughput requirement
    assert throughput >= 500  # messages per second
```

### Security Tests

Security tests validate that the system follows security best practices:

- Test input validation and sanitization
- Verify API token handling
- Test access control mechanisms
- Validate error message security

Example security test:
```python
def test_api_token_handling():
    """Test secure handling of API tokens"""
    # Test that tokens are not logged
    with captured_logs() as logs:
        client = DerivApiClient(app_id="12345", token="secret_token")
        # Trigger some logging
        client.log_connection_attempt()
        
    # Verify token is not in logs
    assert "secret_token" not in logs.getvalue()
```

## Test Infrastructure

### Test Runner

The `run_tests.py` script provides the main entry point for running tests:

```python
def run_tests(pattern: Optional[str] = None) -> bool:
    """
    Run the test suite.
    
    Args:
        pattern: Optional pattern to filter tests
        
    Returns:
        True if all tests passed, False otherwise
    """
```

Usage:
```bash
# Run all tests
python run_tests.py

# Run tests matching a pattern
python run_tests.py --pattern "test_api"

# List available tests
python run_tests.py --list
```

### Mock Objects

Common mock objects for testing:

#### Message Broker

```python
@pytest.fixture
async def message_broker():
    """Create a message broker for testing"""
    broker = MessageBroker()
    yield broker
```

#### Test Agent

```python
class TestAgent(Agent):
    """Test agent implementation for unit tests"""
    
    def __init__(self, agent_id, message_broker):
        super().__init__(agent_id, message_broker)
        self.messages_received = []
        
    async def setup(self):
        """Initialize the agent"""
        pass
        
    async def process_cycle(self):
        """Main processing cycle"""
        await asyncio.sleep(0.01)
        
    async def handle_message(self, message):
        """Handle incoming messages"""
        self.messages_received.append(message)
```

#### MockResponse

```python
class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status=200, json_data=None, raise_error=None):
        self.status = status
        self._json_data = json_data
        self._raise_error = raise_error
        
    async def json(self):
        """Return mock JSON data"""
        if self._raise_error:
            raise self._raise_error
        return self._json_data
        
    def raise_for_status(self):
        """Simulate raise_for_status method"""
        if self.status >= 400:
            raise ClientResponseError(self.status, f"HTTP Error {self.status}")
```

### Test Configuration

The test suite uses specialized configuration for testing:

```python
def get_test_config():
    """Get a configuration for testing"""
    return {
        "system": {
            "log_level": "DEBUG",
            "data_directory": "./test_data",
        },
        "market_data": {
            "provider": "simulation",
            "symbols": ["EUR/USD"],
        },
        "risk_management": {
            "max_account_risk_percent": 1.0,
        },
        # More test configuration...
    }
```

## Test Data

### Market Data

The test suite includes sample market data for testing:

- Located in `tests/test_data/market_data/`
- Includes various symbols and timeframes
- Contains both normal and edge case scenarios
- Used for technical analysis and signal generation testing

### Simulated API Responses

The tests include simulated API responses for testing API clients:

- Located in `tests/test_data/api_responses/`
- Covers both success and error scenarios
- Includes various contract types and symbols
- Used for testing API client error handling

## Testing Practices

### Test Isolation

- Each test runs in isolation
- Tests clean up after themselves
- No test should depend on the results of another test
- Use fixtures to create isolated test environments

### Asynchronous Testing

- Use asyncio for testing async functions
- Use pytest-asyncio for running async tests
- Properly handle awaitables in test functions
- Use timeouts to prevent tests from hanging

Example:
```python
@pytest.mark.asyncio
async def test_async_functionality():
    """Test an asynchronous function"""
    result = await async_function()
    assert result is not None
```

### Mocking External Dependencies

- Use unittest.mock or pytest-mock for mocking
- Mock API responses for testing API clients
- Mock time for testing time-dependent functionality
- Use dependency injection to facilitate mocking

Example:
```python
def test_function_with_mock(mocker):
    """Test a function with mocked dependencies"""
    # Create mock
    mock_dependency = mocker.MagicMock()
    mock_dependency.method.return_value = "mocked_result"
    
    # Call function with mock
    result = function_under_test(dependency=mock_dependency)
    
    # Verify result
    assert result == "expected_result"
    
    # Verify mock was called correctly
    mock_dependency.method.assert_called_once_with("expected_arg")
```

### Error Scenario Testing

- Test both happy path and error scenarios
- Verify proper error handling
- Test recovery mechanisms
- Ensure errors are logged appropriately

Example:
```python
async def test_api_client_handles_timeout_error(mocker):
    """Test API client handles timeout errors correctly"""
    # Setup mock to raise timeout error
    mock_session = mocker.MagicMock()
    mock_session.get.side_effect = asyncio.TimeoutError()
    
    # Create client with mock session
    client = APIClient(base_url="https://example.com")
    client._session = mock_session
    
    # Call method and verify it handles the error
    with pytest.raises(APIError) as excinfo:
        await client.get("/endpoint")
    
    # Verify error message
    assert "timeout" in str(excinfo.value).lower()
```

## Trade Test Mode

The system includes a special trade test mode for verifying Deriv API integration:

- Run with `--tradetest` command-line option
- Executes one CALL and one PUT test trade
- Uses Deriv demo account
- Logs detailed information about trade execution

This mode is useful for:
- Verifying Deriv API credentials
- Testing the trade execution flow
- Debugging API integration issues
- Confirming system functionality in a production-like environment

## Test Coverage

The testing strategy aims for comprehensive coverage:

- **Horizontal Coverage**: All system components are tested
- **Vertical Coverage**: All layers of the system are tested (from low-level functions to high-level workflows)
- **Scenario Coverage**: Various scenarios and edge cases are tested
- **Code Coverage**: Target at least 80% line coverage

## Continuous Integration

The tests are designed to run in CI environments:

- Fast execution for rapid feedback
- No dependence on real external services (using mocks)
- Comprehensive test reporting
- Code coverage tracking

## Test Failure Investigation

When a test fails:

1. **Review the Test Output**: Understand what failed and why
2. **Check Recent Changes**: Look for relevant code changes
3. **Reproduce Locally**: Try to reproduce the failure locally
4. **Add Debug Logging**: Add additional logging to identify the issue
5. **Fix the Issue**: Address the root cause of the failure
6. **Add a Regression Test**: Ensure the issue doesn't recur

## Future Test Enhancements

Planned enhancements to the testing strategy:

1. **Property-Based Testing**: Add property-based tests for more thorough testing
2. **Chaos Testing**: Introduce random failures to test resilience
3. **Fuzzing**: Add fuzz testing for input validation
4. **Performance Regression Testing**: Track performance metrics over time
5. **Expanded API Testing**: Add more comprehensive API test scenarios