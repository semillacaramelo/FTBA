
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Callable, Set


class MessageType(Enum):
    """Enumeration of message types for inter-agent communication"""
    SYSTEM_STATUS = auto()
    TECHNICAL_SIGNAL = auto()
    FUNDAMENTAL_UPDATE = auto()
    TRADE_PROPOSAL = auto()
    TRADE_APPROVAL = auto()
    TRADE_REJECTION = auto()
    TRADE_EXECUTION = auto()
    TRADE_RESULT = auto()
    STRATEGY_UPDATE = auto()
    RISK_UPDATE = auto()
    ERROR = auto()


class Message:
    """Message object for communication between agents"""
    
    def __init__(self, msg_id: str, msg_type: MessageType, sender: str, 
                 recipients: List[str], content: Dict):
        self.id = msg_id
        self.type = msg_type
        self.sender = sender
        self.recipients = recipients
        self.content = content
        self.timestamp = datetime.utcnow()
    
    def __str__(self) -> str:
        return (f"Message(id={self.id}, type={self.type.name}, "
                f"sender={self.sender}, recipients={self.recipients})")


class MessageBroker:
    """Central message broker for agent communication"""
    
    def __init__(self):
        self.subscribers = {}  # message_type -> [agent_ids]
        self.queues = {}       # agent_id -> asyncio.Queue
        self.logger = logging.getLogger("message_broker")
        self.message_counter = 0
    
    def register_agent(self, agent_id: str) -> asyncio.Queue:
        """Register an agent and return its message queue"""
        if agent_id in self.queues:
            self.logger.warning(f"Agent {agent_id} already registered, returning existing queue")
            return self.queues[agent_id]
        
        self.queues[agent_id] = asyncio.Queue()
        self.logger.debug(f"Registered agent: {agent_id}")
        return self.queues[agent_id]
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        if agent_id in self.queues:
            del self.queues[agent_id]
            
        # Remove agent from all subscription lists
        for msg_type in self.subscribers:
            if agent_id in self.subscribers[msg_type]:
                self.subscribers[msg_type].remove(agent_id)
        
        self.logger.debug(f"Unregistered agent: {agent_id}")
    
    def subscribe(self, agent_id: str, message_types: List[MessageType]) -> None:
        """Subscribe an agent to specific message types"""
        for msg_type in message_types:
            if msg_type not in self.subscribers:
                self.subscribers[msg_type] = set()
            
            self.subscribers[msg_type].add(agent_id)
        
        self.logger.debug(f"Agent {agent_id} subscribed to {[mt.name for mt in message_types]}")
    
    def unsubscribe(self, agent_id: str, message_types: List[MessageType]) -> None:
        """Unsubscribe an agent from specific message types"""
        for msg_type in message_types:
            if msg_type in self.subscribers and agent_id in self.subscribers[msg_type]:
                self.subscribers[msg_type].remove(agent_id)
        
        self.logger.debug(f"Agent {agent_id} unsubscribed from {[mt.name for mt in message_types]}")
    
    async def publish(self, message: Message) -> None:
        """Publish a message to all subscribers"""
        self.message_counter += 1
        
        # If specific recipients are defined, send only to them
        if message.recipients:
            for recipient in message.recipients:
                if recipient in self.queues:
                    await self.queues[recipient].put(message)
            return
        
        # Otherwise, send to all subscribers of this message type
        if message.type in self.subscribers:
            for agent_id in self.subscribers[message.type]:
                if agent_id != message.sender and agent_id in self.queues:  # Don't send to self
                    await self.queues[agent_id].put(message)
        
        self.logger.debug(f"Published message: {message}")
    
    def get_next_message_id(self) -> str:
        """Generate a unique message ID"""
        return f"msg_{self.message_counter}"


class Agent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_id: str, message_broker: MessageBroker):
        self.id = agent_id
        self.message_broker = message_broker
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.message_queue = message_broker.register_agent(agent_id)
        self.running = False
        self.processing_task = None
    
    async def subscribe_to(self, message_types: List[MessageType]) -> None:
        """Subscribe to specific message types"""
        self.message_broker.subscribe(self.id, message_types)
    
    async def unsubscribe_from(self, message_types: List[MessageType]) -> None:
        """Unsubscribe from specific message types"""
        self.message_broker.unsubscribe(self.id, message_types)
    
    async def send_message(self, msg_type: MessageType, content: Dict, 
                           recipients: List[str] = None) -> None:
        """Send a message to other agents"""
        message = Message(
            msg_id=self.message_broker.get_next_message_id(),
            msg_type=msg_type,
            sender=self.id,
            recipients=recipients or [],
            content=content
        )
        await self.message_broker.publish(message)
    
    async def start(self) -> None:
        """Start the agent's processing loop"""
        if self.running:
            self.logger.warning(f"Agent {self.id} is already running")
            return
        
        self.running = True
        self.logger.info(f"Starting agent: {self.id}")
        
        # Initialize the agent
        await self.setup()
        
        # Start the message processing loop
        self.processing_task = asyncio.create_task(self._process_loop())
    
    async def stop(self) -> None:
        """Stop the agent's processing loop"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info(f"Stopping agent: {self.id}")
        
        # Cancel the processing task
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Clean up agent resources
        await self.cleanup()
        
        # Unregister from message broker
        self.message_broker.unregister_agent(self.id)
    
    async def _process_loop(self) -> None:
        """Main processing loop for the agent"""
        try:
            while self.running:
                # Process messages
                while not self.message_queue.empty():
                    message = await self.message_queue.get()
                    try:
                        await self.handle_message(message)
                    except Exception as e:
                        self.logger.error(f"Error handling message {message}: {e}")
                    finally:
                        self.message_queue.task_done()
                
                # Run agent-specific processing
                try:
                    await self.process_cycle()
                except Exception as e:
                    self.logger.error(f"Error in process_cycle: {e}")
                    # Short pause to prevent busy-looping in case of persistent errors
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info(f"Processing loop cancelled for agent: {self.id}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in agent processing loop: {e}")
    
    @abstractmethod
    async def setup(self) -> None:
        """Initialize the agent. Override in subclass."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources. Override in subclass."""
        pass
    
    @abstractmethod
    async def process_cycle(self) -> None:
        """Main processing cycle. Override in subclass."""
        pass
    
    @abstractmethod
    async def handle_message(self, message: Message) -> None:
        """Handle incoming messages. Override in subclass."""
        pass
