# System Architecture

This document provides a detailed overview of the FTBA system architecture, explaining how the different components interact to create a cohesive multi-agent trading system.

## Architectural Overview

The FTBA system is built on a multi-agent architecture with event-driven communication. This design enables:

1. **Decoupling**: Each agent can operate independently, communicating through a centralized message broker
2. **Extensibility**: New agents can be added without modifying existing ones
3. **Resilience**: The system can continue operating if some agents fail
4. **Specialization**: Each agent can focus on a specific domain of expertise

![System Architecture](images/system_architecture.png)

## Core Components

### Agent Base Class

All agents inherit from the `Agent` base class defined in `system/agent.py`, which provides:

- Message sending and receiving infrastructure
- Lifecycle management (setup, start, stop, cleanup)
- Error handling and logging capabilities
- Asynchronous processing loop

```python
class Agent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_id: str, message_broker: MessageBroker):
        """Initialize the agent"""
        
    async def subscribe_to(self, message_types: List[MessageType]) -> None:
        """Subscribe to specific message types"""
        
    async def send_message(self, msg_type: MessageType, content: Dict[str, Any], 
                          recipients: Optional[List[str]] = None) -> None:
        """Send a message to other agents"""
        
    async def start(self) -> None:
        """Start the agent's processing loop"""
        
    async def stop(self) -> None:
        """Stop the agent's processing loop"""
        
    @abstractmethod
    async def setup(self) -> None:
        """Initialize the agent. Override in subclass."""
        
    @abstractmethod
    async def process_cycle(self) -> None:
        """Main processing cycle. Override in subclass."""
        
    @abstractmethod
    async def handle_message(self, message: Message) -> None:
        """Handle incoming messages. Override in subclass."""
```

### Message Broker

The `MessageBroker` class in `system/agent.py` manages message routing between agents:

- Message subscription and filtering
- Efficient message delivery
- Message batching for performance
- Subscriber caching for optimized routing

```python
class MessageBroker:
    """Central message broker for agent communication with optimized performance"""
    
    def register_agent(self, agent_id: str) -> asyncio.Queue:
        """Register an agent and return its message queue"""
        
    def subscribe(self, agent_id: str, message_types: List[MessageType]) -> None:
        """Subscribe an agent to specific message types"""
        
    async def publish(self, message: Message) -> None:
        """Publish a message to all subscribers"""
        
    async def publish_batch(self, messages: List[Message]) -> None:
        """Publish a batch of messages efficiently"""
```

### Message Class

The `Message` class provides a standardized format for inter-agent communication:

```python
class Message:
    """Message object for communication between agents"""
    
    def __init__(self, msg_id: str, msg_type: MessageType, sender: str, 
                 recipients: List[str], content: Dict[str, Any]):
        """Initialize a new message"""
```

### API Client

The `APIClient` class in `system/api_client.py` provides a standardized interface for API communication:

```python
class APIClient:
    """Client for making API requests with retry logic and error handling"""
    
    async def request(self, method: str, endpoint: str, data: Any = None, 
                     params: Dict[str, Any] = None, headers: Dict[str, str] = None, 
                     retry_count: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
        """Send a request to the API with retry logic"""
```

### Deriv API Client

The `DerivApiClient` class in `system/deriv_api_client.py` provides specific functionality for interacting with the Deriv trading platform:

```python
class DerivApiClient:
    """Client for interacting with the Deriv API with improved connection handling"""
    
    async def connect(self, retry_count: int = 0) -> bool:
        """Connect to the Deriv API with retry logic"""
        
    async def get_price_proposal(self, symbol: str, contract_type: str, 
                                amount: float, duration: int, duration_unit: str,
                                basis: str = "stake") -> Dict:
        """Get price proposal for a contract"""
        
    async def buy_contract(self, proposal_id: str, price: float) -> Dict:
        """Buy a contract based on proposal ID"""
```

## Specialized Agents

### Technical Analysis Agent

Located in `agents/technical_analysis_agent.py`, this agent:

- Analyzes price data using technical indicators
- Identifies patterns and signals
- Generates trade signals with confidence scores
- Maintains a history of signals for performance analysis

### Fundamental Analysis Agent

Located in `agents/fundamental_analysis_agent.py`, this agent:

- Monitors economic calendars and news feeds
- Assesses the impact of fundamental events on currencies
- Generates directional bias signals based on fundamental data
- Provides context for technical signals

### Risk Management Agent

Located in `agents/risk_management_agent.py`, this agent:

- Evaluates trade proposals against risk parameters
- Calculates optimal position sizes
- Monitors portfolio exposure and correlation
- Enforces risk limits and circuit breakers

### Strategy Optimization Agent

Located in `agents/strategy_optimization_agent.py`, this agent:

- Analyzes historical performance of trading strategies
- Tunes strategy parameters based on market conditions
- Implements machine learning for strategy improvement
- Identifies market regimes and adapts strategies accordingly

### Trade Execution Agent

Located in `agents/trade_execution_agent.py`, this agent:

- Receives approved trade proposals
- Executes trades via the Deriv API
- Monitors open positions
- Handles trade lifecycle events (fills, partial fills, etc.)
- Reports trade results back to the system

## Data Structures

The system defines several core data structures in `system/core.py`:

### Enumerations

```python
class Direction(Enum):
    """Trade direction enumeration"""
    LONG = "LONG"     # Buy / bullish position
    SHORT = "SHORT"   # Sell / bearish position
    NEUTRAL = "NEUTRAL"  # No directional bias

class TradeStatus(Enum):
    """Trade status enumeration for tracking lifecycle"""
    PROPOSED = "PROPOSED"    # Initial proposal
    APPROVED = "APPROVED"    # Approved by risk manager
    REJECTED = "REJECTED"    # Rejected by risk manager
    PENDING = "PENDING"      # Pending execution
    EXECUTED = "EXECUTED"    # Successfully executed
    CANCELED = "CANCELED"    # Canceled before execution
    CLOSED = "CLOSED"        # Position closed
    EXPIRED = "EXPIRED"      # Expired without execution

class Confidence(Enum):
    """Confidence level enumeration"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
```

### Trading Objects

```python
class TechnicalSignal:
    """Technical analysis signal data structure"""
    symbol: str
    timeframe: Union[str, Timeframe]
    indicator: Union[str, Indicator]
    direction: Direction
    confidence: Union[float, Confidence]
    value: float
    threshold: float = 0.0
    timestamp: Optional[str] = None
    description: Optional[str] = None

class TradeProposal:
    """Trade proposal data structure"""
    id: str
    symbol: str
    direction: Direction
    size: float
    strategy_name: str
    technical_confidence: Confidence
    fundamental_alignment: Confidence
    risk_score: float
    status: TradeStatus
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_limit_seconds: int = 3600
    expiry_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class TradeExecution:
    """Trade execution data structure"""
    proposal_id: str
    execution_id: str
    symbol: str
    direction: Direction
    executed_size: float
    executed_price: float
    execution_time: datetime
    status: TradeStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## Message Flow

The system's operation can be understood through the flow of messages between agents:

1. **Market Data Flow**:
   - External source → Technical Analysis Agent → Message Broker
   - External source → Fundamental Analysis Agent → Message Broker

2. **Signal Generation Flow**:
   - Technical Analysis Agent → Message Broker → Strategy Optimization Agent
   - Fundamental Analysis Agent → Message Broker → Strategy Optimization Agent

3. **Trade Proposal Flow**:
   - Strategy Optimization Agent → Message Broker → Risk Management Agent
   - Risk Management Agent → Message Broker → Trade Execution Agent

4. **Trade Execution Flow**:
   - Trade Execution Agent → Deriv API → Trade Execution Agent
   - Trade Execution Agent → Message Broker → All Agents

5. **Feedback Loop**:
   - Trade Execution Agent → Message Broker → Strategy Optimization Agent
   - Strategy Optimization Agent → Message Broker → All Agents

## Asynchronous Processing

The system uses Python's asyncio to enable non-blocking operations:

- Each agent runs in its own processing loop
- API calls are non-blocking
- Message processing is handled asynchronously
- The system can process multiple operations concurrently

```python
async def run_system(config, run_tradetest=False):
    """Main function to run the entire system"""
    # Initialize the message broker
    message_broker = MessageBroker()
    
    # Initialize all agents
    agents = await initialize_agents(config, message_broker)
    
    # Start all agents
    start_tasks = [agent.start() for agent in agents.values()]
    await asyncio.gather(*start_tasks)
    
    # Set up graceful shutdown
    loop = asyncio.get_event_loop()
    signals = (signal.SIGINT, signal.SIGTERM)
    for s in signals:
        loop.add_signal_handler(s, lambda s=s: handle_shutdown())
```

## Configuration System

The system uses a JSON configuration file to control its behavior:

- System-wide settings
- Agent-specific parameters
- Risk management thresholds
- Market data sources
- API connection details

Configuration validation ensures that all parameters are valid before the system starts.

## Error Handling

The system implements a comprehensive error handling framework:

- Specific error types for different failure scenarios
- Error callbacks for specialized handling
- Automatic retry logic for recoverable errors
- Graceful degradation when components fail
- Detailed error logging with context

## Enhanced Console Output

The system uses color-coded and icon-enhanced console output:

- Different colors for different message types
- Icons for visual identification
- Consistent formatting for readability
- Progress indicators for long-running operations
- Status updates for system components

## Status Monitoring

The system includes comprehensive status monitoring:

- Real-time tracking of system processes
- Progress indicators for long-running operations
- Hierarchical status tracking for dependencies
- Timing information for performance analysis
- Formatted status reports

## Deployment Considerations

The system can be deployed in various configurations:

### Development Mode

- Local development with simulated trading
- Detailed logging and debug information
- Fast iteration on strategies and components

### Testing Mode

- Connected to Deriv demo account
- Limited risk settings
- Full functionality but with safeguards

### Production Mode

- Connected to Deriv live account
- Optimized performance settings
- Reduced logging except for critical information
- Enhanced security measures

## Security Architecture

The system implements several security best practices:

- API tokens stored as environment variables, not in code
- Separation between demo and live trading environments
- Input validation for all external data
- Rate limiting for API requests
- Circuit breakers for exceptional market conditions
- Detailed audit logging of all trading activities

## Extensibility Points

The system is designed to be extended in several ways:

### New Agents

New specialized agents can be added by:

1. Creating a new class that inherits from `Agent`
2. Implementing the required abstract methods
3. Registering the agent in the configuration
4. Defining message subscriptions

### Additional Data Sources

New data sources can be integrated by:

1. Creating a new data client that wraps the API
2. Implementing data transformation to system formats
3. Updating configuration to use the new source
4. Creating or modifying an agent to consume the data

### Alternative Trading Platforms

Support for additional trading platforms can be added by:

1. Creating a new API client for the platform
2. Implementing the required trading methods
3. Mapping between system concepts and platform specifics
4. Updating the Trade Execution Agent to support the new platform

## Testing Infrastructure

The system includes a comprehensive testing framework:

- Unit tests for individual components
- Integration tests for agent interactions
- End-to-end tests for complete workflows
- Performance tests for optimization
- Specific trade tests for API verification

## Future Architecture Evolution

The architecture is designed to evolve in several directions:

1. **Scalability**: Adding support for multiple trading accounts or higher frequency trading
2. **Advanced Analytics**: Integrating more sophisticated machine learning models
3. **Extended Asset Classes**: Supporting additional markets beyond forex
4. **Distributed Deployment**: Running components across multiple machines
5. **Real-time Monitoring**: Adding a web dashboard for system monitoring