import asyncio
import pytest
import pytest_asyncio
from typing import List
from system.agent import Agent, MessageBroker, MessageType, Message

class TestAgent(Agent):
    """Test agent implementation for unit tests"""
    
    def __init__(self, agent_id, message_broker):
        super().__init__(agent_id, message_broker)
        self.messages_received = []
        self.setup_called = False
        self.cleanup_called = False
    
    async def setup(self):
        self.setup_called = True
    
    async def cleanup(self):
        self.cleanup_called = True
    
    async def process_cycle(self):
        await asyncio.sleep(0.01)
    
    async def handle_message(self, message):
        self.messages_received.append(message)

@pytest_asyncio.fixture
async def message_broker():
    """Create a message broker for testing"""
    broker = MessageBroker(batch_size=2)
    return broker  # Changed from yield to return

@pytest.mark.asyncio
async def test_message_broker_initialization():
    """Test message broker initialization"""
    broker = MessageBroker()
    assert broker is not None
    assert broker.subscribers == {}
    assert broker.queues == {}

@pytest.mark.asyncio
async def test_agent_registration():
    """Test agent registration with message broker"""
    broker = MessageBroker()
    queue = broker.register_agent("test_agent")
    
    assert "test_agent" in broker.queues
    assert broker.queues["test_agent"] == queue
    assert queue.empty()
    
    # Test unregistration
    broker.unregister_agent("test_agent")
    assert "test_agent" not in broker.queues

@pytest.mark.asyncio
async def test_subscribe_unsubscribe():
    """Test subscription and unsubscription"""
    broker = MessageBroker()
    broker.register_agent("agent1")
    
    # Subscribe
    broker.subscribe("agent1", [MessageType.SYSTEM_STATUS])
    assert MessageType.SYSTEM_STATUS in broker.subscribers
    assert "agent1" in broker.subscribers[MessageType.SYSTEM_STATUS]
    
    # Unsubscribe
    broker.unsubscribe("agent1", [MessageType.SYSTEM_STATUS])
    assert "agent1" not in broker.subscribers[MessageType.SYSTEM_STATUS]

@pytest.mark.asyncio
async def test_publish_message():
    """Test publishing a message"""
    broker = MessageBroker()
    queue1 = broker.register_agent("agent1")
    queue2 = broker.register_agent("agent2")
    
    broker.subscribe("agent1", [MessageType.SYSTEM_STATUS])
    broker.subscribe("agent2", [MessageType.SYSTEM_STATUS])
    
    # Create and publish a message
    message = Message(
        msg_id="test_msg",
        msg_type=MessageType.SYSTEM_STATUS,
        sender="agent1",
        recipients=[],
        content={"status": "test"}
    )
    
    await broker.publish(message)
    
    # Only agent2 should receive it (not the sender)
    assert queue1.empty()
    assert not queue2.empty()
    
    received = await queue2.get()
    assert received.id == "test_msg"
    assert received.type == MessageType.SYSTEM_STATUS

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

@pytest.mark.asyncio
async def test_message_batch_publishing(message_broker):
    """Test batched message publishing"""
    agent1 = TestAgent("agent1", message_broker)
    agent2 = TestAgent("agent2", message_broker)
    
    # Start agents
    await agent1.start()
    await agent2.start()
    
    # Subscribe to message types
    await agent1.subscribe_to([MessageType.TECHNICAL_SIGNAL])
    await agent2.subscribe_to([MessageType.TECHNICAL_SIGNAL])
    
    # Send multiple messages that should be batched
    batch_messages = [
        Message(
            msg_id=f"batch_{i}",
            msg_type=MessageType.TECHNICAL_SIGNAL,
            sender="test_sender",
            recipients=[],
            content={"value": i}
        )
        for i in range(5)
    ]
    
    # Send batch
    await message_broker.publish_batch(batch_messages)
    
    # Wait for processing
    await asyncio.sleep(0.05)
    
    # Both agents should have received all messages
    assert len(agent1.messages_received) == 5
    assert len(agent2.messages_received) == 5
    
    # Verify correct messages were received
    values_agent1 = [msg.content["value"] for msg in agent1.messages_received]
    values_agent2 = [msg.content["value"] for msg in agent2.messages_received]
    
    assert sorted(values_agent1) == [0, 1, 2, 3, 4]
    assert sorted(values_agent2) == [0, 1, 2, 3, 4]
    
    # Clean up
    await agent1.stop()
    await agent2.stop()

@pytest.mark.asyncio
async def test_subscriber_caching(message_broker):
    """Test subscriber caching for performance"""
    # Setup multiple agents
    agents = [TestAgent(f"agent{i}", message_broker) for i in range(5)]
    
    # Start all agents
    for agent in agents:
        await agent.start()
        await agent.subscribe_to([MessageType.SYSTEM_STATUS])
    
    # Send a broadcast message
    test_message = Message(
        msg_id="test_cache",
        msg_type=MessageType.SYSTEM_STATUS,
        sender="test_sender",
        recipients=[],
        content={"status": "cache_test"}
    )
    
    # First send fills the cache
    await message_broker.publish(test_message)
    
    # Verify cache was created
    assert MessageType.SYSTEM_STATUS in message_broker._subscribers_cache
    
    # Send another message using the cache
    test_message2 = Message(
        msg_id="test_cache2",
        msg_type=MessageType.SYSTEM_STATUS,
        sender="test_sender",
        recipients=[],
        content={"status": "cache_test2"}
    )
    
    await message_broker.publish(test_message2)
    
    # Wait for processing
    await asyncio.sleep(0.05)
    
    # Verify each agent received both messages
    for agent in agents:
        assert len(agent.messages_received) == 2
        assert agent.messages_received[0].content["status"] == "cache_test"
        assert agent.messages_received[1].content["status"] == "cache_test2"
    
    # Clean up
    for agent in agents:
        await agent.stop()
