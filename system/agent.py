
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Callable, Set, Optional


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
    RISK_ASSESSMENT = auto()
    ERROR = auto()


class Message:
    """Message object for communication between agents"""
    
    def __init__(self, msg_id: str, msg_type: MessageType, sender: str, 
                 recipients: List[str], content: Dict[str, Any]):
        """
        Initialize a new message
        
        Args:
            msg_id: Unique identifier for the message
            msg_type: Type of message (from MessageType enum)
            sender: ID of the sending agent
            recipients: List of recipient agent IDs (empty for broadcast)
            content: Dictionary containing the message payload
        """
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
    """Central message broker for agent communication with optimized performance"""
    
    def __init__(self, batch_size: int = 10, cache_timeout: float = 5.0):
        """
        Initialize the message broker
        
        Args:
            batch_size: Maximum number of messages to batch in a single delivery
            cache_timeout: Time in seconds after which subscriber cache is invalidated
        """
        self.subscribers = {}  # message_type -> [agent_ids]
        self.queues = {}       # agent_id -> asyncio.Queue
        self.logger = logging.getLogger("message_broker")
        self.message_counter = 0
        self._subscribers_cache = {}  # Cached set of subscribers for each message type
        self._cache_timestamps = {}   # When each cache entry was last updated
        self.batch_size = batch_size
        self.cache_timeout = cache_timeout
    
    def register_agent(self, agent_id: str) -> asyncio.Queue:
        """
        Register an agent and return its message queue
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            asyncio.Queue: Message queue for the agent
        """
        if agent_id in self.queues:
            self.logger.warning(f"Agent {agent_id} already registered, returning existing queue")
            return self.queues[agent_id]
        
        self.queues[agent_id] = asyncio.Queue()
        self.logger.debug(f"Registered agent: {agent_id}")
        return self.queues[agent_id]
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent
        
        Args:
            agent_id: ID of the agent to unregister
        """
        if agent_id in self.queues:
            del self.queues[agent_id]
            
        # Remove agent from all subscription lists
        for msg_type in self.subscribers:
            if agent_id in self.subscribers[msg_type]:
                self.subscribers[msg_type].remove(agent_id)
                # Invalidate cache for this message type
                if msg_type in self._subscribers_cache:
                    del self._subscribers_cache[msg_type]
                    if msg_type in self._cache_timestamps:
                        del self._cache_timestamps[msg_type]
        
        self.logger.debug(f"Unregistered agent: {agent_id}")
    
    def subscribe(self, agent_id: str, message_types: List[MessageType]) -> None:
        """
        Subscribe an agent to specific message types
        
        Args:
            agent_id: ID of the agent
            message_types: List of message types to subscribe to
        """
        for msg_type in message_types:
            if msg_type not in self.subscribers:
                self.subscribers[msg_type] = set()
            
            self.subscribers[msg_type].add(agent_id)
            # Invalidate cache for this message type
            if msg_type in self._subscribers_cache:
                del self._subscribers_cache[msg_type]
                if msg_type in self._cache_timestamps:
                    del self._cache_timestamps[msg_type]
        
        self.logger.debug(f"Agent {agent_id} subscribed to {[mt.name for mt in message_types]}")
    
    def unsubscribe(self, agent_id: str, message_types: List[MessageType]) -> None:
        """
        Unsubscribe an agent from specific message types
        
        Args:
            agent_id: ID of the agent
            message_types: List of message types to unsubscribe from
        """
        for msg_type in message_types:
            if msg_type in self.subscribers and agent_id in self.subscribers[msg_type]:
                self.subscribers[msg_type].remove(agent_id)
                # Invalidate cache for this message type
                if msg_type in self._subscribers_cache:
                    del self._subscribers_cache[msg_type]
                    if msg_type in self._cache_timestamps:
                        del self._cache_timestamps[msg_type]
        
        self.logger.debug(f"Agent {agent_id} unsubscribed from {[mt.name for mt in message_types]}")
    
    def _get_subscribers_for_message_type(self, msg_type: MessageType) -> Set[str]:
        """
        Get cached or fresh set of subscribers for a message type
        
        Args:
            msg_type: The message type to get subscribers for
            
        Returns:
            Set[str]: Set of agent IDs subscribed to the message type
        """
        now = datetime.utcnow().timestamp()
        
        # If we have a cached value that is still valid, use it
        if (msg_type in self._subscribers_cache and 
            now - self._cache_timestamps.get(msg_type, 0) < self.cache_timeout):
            return self._subscribers_cache[msg_type]
        
        # Otherwise build and cache a new set
        if msg_type not in self.subscribers:
            subscriber_set = set()
        else:
            subscriber_set = set(self.subscribers[msg_type])
        
        self._subscribers_cache[msg_type] = subscriber_set
        self._cache_timestamps[msg_type] = now
        
        return subscriber_set
    
    async def publish(self, message: Message) -> None:
        """
        Publish a message to all subscribers
        
        Args:
            message: The message to publish
        """
        self.message_counter += 1
        
        # If specific recipients are defined, send only to them
        if message.recipients:
            for recipient in message.recipients:
                if recipient in self.queues:
                    await self.queues[recipient].put(message)
            return
        
        # Otherwise, send to all subscribers of this message type
        subscribers = self._get_subscribers_for_message_type(message.type)
        
        for agent_id in subscribers:
            if agent_id != message.sender and agent_id in self.queues:  # Don't send to self
                await self.queues[agent_id].put(message)
        
        self.logger.debug(f"Published message: {message}")
    
    async def publish_batch(self, messages: List[Message]) -> None:
        """
        Publish a batch of messages efficiently
        
        Args:
            messages: List of messages to publish
        """
        # Group messages by recipient for efficient delivery
        recipient_messages = {}  # agent_id -> list of messages
        
        for message in messages:
            self.message_counter += 1
            
            # Handle direct messages
            if message.recipients:
                for recipient in message.recipients:
                    if recipient in self.queues:
                        if recipient not in recipient_messages:
                            recipient_messages[recipient] = []
                        recipient_messages[recipient].append(message)
                continue
            
            # Handle broadcast messages
            subscribers = self._get_subscribers_for_message_type(message.type)
            
            for agent_id in subscribers:
                if agent_id != message.sender and agent_id in self.queues:
                    if agent_id not in recipient_messages:
                        recipient_messages[agent_id] = []
                    recipient_messages[agent_id].append(message)
            
            self.logger.debug(f"Batched message: {message}")
        
        # Deliver messages to each recipient
        for agent_id, msgs in recipient_messages.items():
            for msg in msgs:
                await self.queues[agent_id].put(msg)
    
    def get_next_message_id(self) -> str:
        """
        Generate a unique message ID
        
        Returns:
            str: Unique message ID
        """
        return f"msg_{self.message_counter}"


class Agent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_id: str, message_broker: MessageBroker):
        """
        Initialize the agent
        
        Args:
            agent_id: Unique identifier for the agent
            message_broker: Message broker instance for communication
        """
        self.id = agent_id
        self.message_broker = message_broker
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.message_queue = message_broker.register_agent(agent_id)
        self.running = False
        self.processing_task = None
        self._message_batch = []
        self._last_batch_time = datetime.utcnow()
        self._batch_size = message_broker.batch_size
        self._batch_interval = 0.1  # seconds
    
    async def subscribe_to(self, message_types: List[MessageType]) -> None:
        """
        Subscribe to specific message types
        
        Args:
            message_types: List of message types to subscribe to
        """
        self.message_broker.subscribe(self.id, message_types)
    
    async def unsubscribe_from(self, message_types: List[MessageType]) -> None:
        """
        Unsubscribe from specific message types
        
        Args:
            message_types: List of message types to unsubscribe from
        """
        self.message_broker.unsubscribe(self.id, message_types)
    
    async def send_message(self, msg_type: MessageType, content: Dict[str, Any], 
                          recipients: Optional[List[str]] = None) -> None:
        """
        Send a message to other agents
        
        Args:
            msg_type: Type of message to send
            content: Dictionary containing the message content
            recipients: List of specific recipients (None for broadcast)
        """
        message = Message(
            msg_id=self.message_broker.get_next_message_id(),
            msg_type=msg_type,
            sender=self.id,
            recipients=recipients or [],
            content=content
        )
        
        # Add to batch if batching enabled
        if self._batch_size > 1:
            now = datetime.utcnow()
            self._message_batch.append(message)
            
            # Send batch if full or interval elapsed
            if (len(self._message_batch) >= self._batch_size or 
                (now - self._last_batch_time).total_seconds() >= self._batch_interval):
                await self._send_message_batch()
            
            # Schedule a task to send partial batch after interval
            if len(self._message_batch) == 1:
                asyncio.create_task(self._schedule_batch_send())
        else:
            # Send immediately if batching disabled
            await self.message_broker.publish(message)
    
    async def _schedule_batch_send(self) -> None:
        """Schedule sending of a partial message batch after the interval"""
        await asyncio.sleep(self._batch_interval)
        if self._message_batch:  # Check if there are still messages to send
            await self._send_message_batch()
    
    async def _send_message_batch(self) -> None:
        """Send the current batch of messages"""
        if not self._message_batch:
            return
            
        batch = self._message_batch.copy()
        self._message_batch = []
        self._last_batch_time = datetime.utcnow()
        
        await self.message_broker.publish_batch(batch)
    
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
        
        # Send any pending messages
        await self._send_message_batch()
        
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
                # Process messages (up to batch_size at a time for efficiency)
                messages_processed = 0
                
                while not self.message_queue.empty() and messages_processed < self._batch_size:
                    message = await self.message_queue.get()
                    try:
                        await self.handle_message(message)
                        messages_processed += 1
                    except Exception as e:
                        self.logger.error(f"Error handling message {message}: {e}", exc_info=True)
                    finally:
                        self.message_queue.task_done()
                
                # If no messages were processed, avoid CPU spinning
                if messages_processed == 0:
                    # Send any pending outgoing messages
                    if self._message_batch and (datetime.utcnow() - self._last_batch_time).total_seconds() >= self._batch_interval:
                        await self._send_message_batch()
                    
                    await asyncio.sleep(0.01)
                
                # Run agent-specific processing
                try:
                    await self.process_cycle()
                except Exception as e:
                    self.logger.error(f"Error in process_cycle: {e}", exc_info=True)
                    # Short pause to prevent busy-looping in case of persistent errors
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info(f"Processing loop cancelled for agent: {self.id}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in agent processing loop: {e}", exc_info=True)
    
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
