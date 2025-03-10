
import asyncio
import pytest
from system.agent import Agent, MessageBroker, MessageType, Message

class TestAgent(Agent):
    """Test implementation of the Agent abstract base class"""
    
    def __init__(self, agent_id, message_broker):
        super().__init__(agent_id, message_broker)
        self.setup_called = False
        self.cleanup_called = False
        self.messages_received = []
        self.cycle_count = 0
        self.sleep_time = 0.01  # Short sleep for testing
        
    async def setup(self):
        self.setup_called = True
        
    async def cleanup(self):
        self.cleanup_called = True
        
    async def process_cycle(self):
        self.cycle_count += 1
        await asyncio.sleep(self.sleep_time)
        
    async def handle_message(self, message):
        self.messages_received.append(message)

@pytest.fixture
def message_broker():
    return MessageBroker()

@pytest.mark.asyncio
async def test_agent_lifecycle(message_broker):
    """Test basic agent lifecycle - start and stop"""
    agent = TestAgent("test_agent", message_broker)
    
    # Start the agent
    await agent.start()
    assert agent.running is True
    assert agent.setup_called is True
    
    # Let it run for a bit
    await asyncio.sleep(0.05)
    assert agent.cycle_count > 0
    
    # Stop the agent
    await agent.stop()
    assert agent.running is False
    assert agent.cleanup_called is True

@pytest.mark.asyncio
async def test_agent_messaging(message_broker):
    """Test messaging between agents"""
    agent1 = TestAgent("agent1", message_broker)
    agent2 = TestAgent("agent2", message_broker)
    
    # Start both agents
    await agent1.start()
    await agent2.start()
    
    # Subscribe agent2 to a message type
    await agent2.subscribe_to([MessageType.TECHNICAL_SIGNAL])
    
    # Send a message from agent1 to agent2
    await agent1.send_message(
        MessageType.TECHNICAL_SIGNAL,
        {"data": "test_signal"}
    )
    
    # Give time for message processing
    await asyncio.sleep(0.05)
    
    # Check if agent2 received the message
    assert len(agent2.messages_received) == 1
    assert agent2.messages_received[0].type == MessageType.TECHNICAL_SIGNAL
    assert agent2.messages_received[0].content == {"data": "test_signal"}
    
    # Agent1 should not have received any messages
    assert len(agent1.messages_received) == 0
    
    # Clean up
    await agent1.stop()
    await agent2.stop()

@pytest.mark.asyncio
async def test_direct_messaging(message_broker):
    """Test direct messaging between agents"""
    agent1 = TestAgent("agent1", message_broker)
    agent2 = TestAgent("agent2", message_broker)
    agent3 = TestAgent("agent3", message_broker)
    
    # Start all agents
    await agent1.start()
    await agent2.start()
    await agent3.start()
    
    # Subscribe all agents to the same message type
    await agent1.subscribe_to([MessageType.SYSTEM_STATUS])
    await agent2.subscribe_to([MessageType.SYSTEM_STATUS])
    await agent3.subscribe_to([MessageType.SYSTEM_STATUS])
    
    # Send a direct message from agent1 to agent2
    await agent1.send_message(
        MessageType.SYSTEM_STATUS,
        {"status": "direct_test"},
        recipients=["agent2"]
    )
    
    # Give time for message processing
    await asyncio.sleep(0.05)
    
    # Check that only agent2 received the message
    assert len(agent2.messages_received) == 1
    assert agent2.messages_received[0].content == {"status": "direct_test"}
    
    # Agent3 should not have received the message
    assert len(agent3.messages_received) == 0
    
    # Clean up
    await agent1.stop()
    await agent2.stop()
    await agent3.stop()
