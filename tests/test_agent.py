
import asyncio
import pytest
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from system.agent import Agent, MessageBroker, MessageType, Message


class TestAgent(Agent):
    """Test agent implementation for unit tests"""
    
    def __init__(self, agent_id, message_broker):
        super().__init__(agent_id, message_broker)
        self.messages_received = []
        self.setup_called = False
        self.cleanup_called = False
        self.cycle_counter = 0
        self.handle_message_mock = AsyncMock()
        
    async def setup(self):
        self.setup_called = True
    
    async def cleanup(self):
        self.cleanup_called = True
    
    async def process_cycle(self):
        self.cycle_counter += 1
        await asyncio.sleep(0.01)
    
    async def handle_message(self, message):
        self.messages_received.append(message)
        await self.handle_message_mock(message)


@pytest.fixture
def message_broker():
    """Create a message broker for testing"""
    return MessageBroker()


@pytest.fixture
async def test_agent(message_broker):
    """Create a test agent"""
    agent = TestAgent("test_agent", message_broker)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.mark.asyncio
async def test_agent_initialization(message_broker):
    """Test agent initialization"""
    agent = TestAgent("test_id", message_broker)
    
    assert agent.id == "test_id"
    assert agent.message_broker == message_broker
    assert agent.running == False
    assert agent.processing_task is None


@pytest.mark.asyncio
async def test_agent_start_stop(message_broker):
    """Test agent start and stop methods"""
    agent = TestAgent("test_agent", message_broker)
    
    # Test start
    await agent.start()
    assert agent.running == True
    assert agent.processing_task is not None
    assert agent.setup_called == True
    
    # Wait for a few cycles
    await asyncio.sleep(0.05)
    assert agent.cycle_counter > 0
    
    # Test stop
    await agent.stop()
    assert agent.running == False
    assert agent.cleanup_called == True
    
    # Wait to ensure processing has stopped
    previous_counter = agent.cycle_counter
    await asyncio.sleep(0.05)
    assert agent.cycle_counter == previous_counter  # Should not increase after stop


@pytest.mark.asyncio
async def test_agent_send_message(test_agent, message_broker):
    """Test agent can send messages"""
    # Create another agent to receive the message
    receiver = TestAgent("receiver", message_broker)
    await receiver.start()
    await receiver.subscribe_to([MessageType.SYSTEM_STATUS])
    
    # Send a message
    await test_agent.send_message(
        MessageType.SYSTEM_STATUS,
        {"status": "test message"}
    )
    
    # Wait for message to be processed
    await asyncio.sleep(0.05)
    
    # Check receiver got the message
    assert len(receiver.messages_received) == 1
    message = receiver.messages_received[0]
    assert message.type == MessageType.SYSTEM_STATUS
    assert message.sender == "test_agent"
    assert message.content == {"status": "test message"}
    
    # Cleanup
    await receiver.stop()


@pytest.mark.asyncio
async def test_agent_message_batching(message_broker):
    """Test agent message batching functionality"""
    # Create an agent with small batch size
    batch_agent = TestAgent("batch_agent", message_broker)
    batch_agent._batch_size = 3
    batch_agent._batch_interval = 0.1
    await batch_agent.start()
    
    # Create a receiver
    receiver = TestAgent("receiver", message_broker)
    await receiver.start()
    await receiver.subscribe_to([MessageType.TECHNICAL_SIGNAL])
    
    # Send multiple messages
    for i in range(5):
        await batch_agent.send_message(
            MessageType.TECHNICAL_SIGNAL,
            {"value": i}
        )
    
    # Wait for batch interval to expire
    await asyncio.sleep(0.15)
    
    # Verify all messages were received
    assert len(receiver.messages_received) == 5
    values = [msg.content["value"] for msg in receiver.messages_received]
    assert sorted(values) == [0, 1, 2, 3, 4]
    
    # Cleanup
    await batch_agent.stop()
    await receiver.stop()


@pytest.mark.asyncio
async def test_agent_handle_message_error(message_broker):
    """Test agent handles errors in message processing"""
    # Create agent that will raise an exception when handling a message
    error_agent = TestAgent("error_agent", message_broker)
    error_agent.handle_message_mock.side_effect = Exception("Test error")
    await error_agent.start()
    await error_agent.subscribe_to([MessageType.TECHNICAL_SIGNAL])
    
    # Send a message that will trigger the error
    message = Message(
        msg_id="error_test",
        msg_type=MessageType.TECHNICAL_SIGNAL,
        sender="test",
        recipients=[],
        content={"test": "error"}
    )
    
    # Publish directly to avoid batching
    await message_broker.publish(message)
    
    # Wait for processing
    await asyncio.sleep(0.05)
    
    # Verify message was received despite the error
    assert len(error_agent.messages_received) == 1
    assert error_agent.messages_received[0].id == "error_test"
    
    # Verify the mock was called, confirming the error was handled
    error_agent.handle_message_mock.assert_called_once()
    
    # Verify agent is still running
    assert error_agent.running == True
    
    # Cleanup
    await error_agent.stop()


@pytest.mark.asyncio
async def test_agent_process_cycle_error(message_broker):
    """Test agent handles errors in process_cycle"""
    # Create a custom agent with error in process_cycle
    class ErrorCycleAgent(TestAgent):
        async def process_cycle(self):
            self.cycle_counter += 1
            raise Exception("Test cycle error")
    
    error_agent = ErrorCycleAgent("cycle_error_agent", message_broker)
    await error_agent.start()
    
    # Wait for a few cycle attempts
    await asyncio.sleep(0.1)
    
    # Verify agent attempted some cycles
    assert error_agent.cycle_counter > 0
    
    # Verify agent is still running despite errors
    assert error_agent.running == True
    
    # Cleanup
    await error_agent.stop()
