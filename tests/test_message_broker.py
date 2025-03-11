
"""
Unit tests for the message broker component.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from system.agent import MessageBroker, MessageType, Message

@pytest.fixture
def message_broker():
    """Create a message broker for testing"""
    return MessageBroker()

@pytest.mark.asyncio
async def test_register_agent(message_broker):
    """Test registering an agent with the message broker"""
    queue = message_broker.register_agent("test_agent")
    assert isinstance(queue, asyncio.Queue)
    assert "test_agent" in message_broker.queues

@pytest.mark.asyncio
async def test_unregister_agent(message_broker):
    """Test unregistering an agent from the message broker"""
    message_broker.register_agent("test_agent")
    message_broker.unregister_agent("test_agent")
    assert "test_agent" not in message_broker.queues

@pytest.mark.asyncio
async def test_subscribe_unsubscribe(message_broker):
    """Test subscribing and unsubscribing from message types"""
    message_broker.subscribe("test_agent", [MessageType.TECHNICAL_SIGNAL])
    assert "test_agent" in message_broker.subscribers[MessageType.TECHNICAL_SIGNAL]
    
    message_broker.unsubscribe("test_agent", [MessageType.TECHNICAL_SIGNAL])
    assert "test_agent" not in message_broker.subscribers[MessageType.TECHNICAL_SIGNAL]

@pytest.mark.asyncio
async def test_publish_with_recipients(message_broker):
    """Test publishing a message with specific recipients"""
    queue = message_broker.register_agent("test_agent")
    
    message = Message(
        msg_id="test_id",
        msg_type=MessageType.TECHNICAL_SIGNAL,
        sender="sender_agent",
        recipients=["test_agent"],
        content={"key": "value"}
    )
    
    await message_broker.publish(message)
    
    # Check that the message was added to the queue
    received_message = await queue.get()
    assert received_message.id == "test_id"
    assert received_message.content["key"] == "value"

@pytest.mark.asyncio
async def test_publish_to_subscribers(message_broker):
    """Test publishing a message to subscribers"""
    queue = message_broker.register_agent("test_agent")
    message_broker.subscribe("test_agent", [MessageType.TECHNICAL_SIGNAL])
    
    message = Message(
        msg_id="test_id",
        msg_type=MessageType.TECHNICAL_SIGNAL,
        sender="sender_agent",
        recipients=[],  # No specific recipients
        content={"key": "value"}
    )
    
    await message_broker.publish(message)
    
    # Check that the message was added to the queue
    received_message = await queue.get()
    assert received_message.id == "test_id"
    assert received_message.content["key"] == "value"

@pytest.mark.asyncio
async def test_dont_send_to_self(message_broker):
    """Test that messages are not sent to the sender"""
    queue = message_broker.register_agent("test_agent")
    message_broker.subscribe("test_agent", [MessageType.TECHNICAL_SIGNAL])
    
    message = Message(
        msg_id="test_id",
        msg_type=MessageType.TECHNICAL_SIGNAL,
        sender="test_agent",  # Same as the subscriber
        recipients=[],
        content={"key": "value"}
    )
    
    await message_broker.publish(message)
    
    # Check that the queue is empty (message was not sent to self)
    assert queue.empty()
