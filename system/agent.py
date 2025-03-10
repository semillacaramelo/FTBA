from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime

from system.core import Message, MessageType

class Agent(ABC):
    """Base class for all trading agents"""
    
    def __init__(self, agent_id: str, message_broker=None):
        self.agent_id = agent_id
        self.message_broker = message_broker
        self.running = False
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.subscribed_topics = []
        
    async def start(self):
        """Start the agent's processing loop"""
        self.running = True
        await self.setup()
        self.logger.info(f"Agent {self.agent_id} started")
        
        while self.running:
            try:
                await self.process_cycle()
                await asyncio.sleep(0.01)  # Don't hog the event loop
            except Exception as e:
                self.logger.exception(f"Error in agent loop: {e}")
    
    async def stop(self):
        """Stop the agent"""
        self.running = False
        await self.cleanup()
        self.logger.info(f"Agent {self.agent_id} stopped")
    
    async def send_message(self, msg_type: MessageType, content: Dict, recipients=None, correlation_id=None):
        """Send a message to other agents via the message broker"""
        message = Message.create(msg_type, self.agent_id, content, recipients)
        if correlation_id:
            message.correlation_id = correlation_id
        if self.message_broker:
            await self.message_broker.publish_message(message)
        else:
            self.logger.warning("No message broker available, message not sent")
    
    async def subscribe_to(self, message_types: List[MessageType]):
        """Subscribe to specific message types"""
        self.subscribed_topics.extend(message_types)
        if self.message_broker:
            await self.message_broker.subscribe(self.agent_id, message_types, self.handle_message)
    
    @abstractmethod
    async def setup(self):
        """Set up the agent when starting"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up when agent is stopping"""
        pass
    
    @abstractmethod
    async def process_cycle(self):
        """Process a single cycle of the agent's main loop"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: Message):
        """Handle incoming messages"""
        pass


class MessageBroker:
    """Message broker for inter-agent communication"""
    
    def __init__(self):
        self.subscriptions = {}  # Map message types to subscribers
        self.message_history = []
        self.logger = logging.getLogger("message_broker")
    
    async def publish_message(self, message: Message):
        """Publish a message to all subscribers"""
        self.message_history.append(message)
        
        # If message has specific recipients, only send to them
        if message.recipients:
            for recipient_id in message.recipients:
                await self._deliver_to_agent(recipient_id, message)
            return
        
        # Otherwise broadcast to all subscribers of this message type
        subscribers = self.subscriptions.get(message.type, [])
        for subscriber_id, callback in subscribers:
            try:
                await callback(message)
            except Exception as e:
                self.logger.error(f"Error delivering message to {subscriber_id}: {e}")
    
    async def _deliver_to_agent(self, agent_id, message):
        """Deliver a message to a specific agent"""
        for msg_type in self.subscriptions:
            for subscriber_id, callback in self.subscriptions[msg_type]:
                if subscriber_id == agent_id:
                    try:
                        await callback(message)
                        return
                    except Exception as e:
                        self.logger.error(f"Error delivering message to {agent_id}: {e}")
        
        self.logger.warning(f"Recipient {agent_id} not found for message {message.id}")
    
    async def subscribe(self, agent_id, message_types, callback):
        """Subscribe an agent to specific message types"""
        for msg_type in message_types:
            if msg_type not in self.subscriptions:
                self.subscriptions[msg_type] = []
            self.subscriptions[msg_type].append((agent_id, callback))
            self.logger.info(f"Agent {agent_id} subscribed to {msg_type.value}")
