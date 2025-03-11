"""
Status monitoring utilities for tracking and displaying process status.
This module helps maintain visibility into the application's activity.
"""
import logging
import time
import threading
import sys
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

from system.console_utils import (
    Colors, Icons, MessageType, 
    print_message, print_status, print_progress
)

class ProcessStatus(Enum):
    """Status of a process or task"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class StatusItem:
    """Represents a process or component whose status is being tracked"""
    
    def __init__(self, name: str, description: str, status: ProcessStatus = ProcessStatus.NOT_STARTED):
        """
        Initialize a status item
        
        Args:
            name: Name identifier for the process
            description: Human-readable description
            status: Current status
        """
        self.name = name
        self.description = description
        self.status = status
        self.start_time = None
        self.end_time = None
        self.progress = 0.0
        self.message = ""
        self.parent = None
        self.children = []
        self.logger = logging.getLogger(f"status.{name}")
    
    def start(self) -> None:
        """Mark the process as started"""
        self.status = ProcessStatus.RUNNING
        self.start_time = time.time()
        self.logger.info(f"Starting: {self.description}")
    
    def complete(self, message: str = "") -> None:
        """Mark the process as completed"""
        self.status = ProcessStatus.COMPLETED
        self.end_time = time.time()
        self.progress = 1.0
        if message:
            self.message = message
        self.logger.info(f"Completed: {self.description} {message}")
    
    def fail(self, message: str) -> None:
        """Mark the process as failed"""
        self.status = ProcessStatus.FAILED
        self.end_time = time.time()
        self.message = message
        self.logger.error(f"Failed: {self.description} - {message}")
    
    def wait(self, message: str) -> None:
        """Mark the process as waiting"""
        self.status = ProcessStatus.WAITING
        self.message = message
        self.logger.info(f"Waiting: {self.description} - {message}")
    
    def update_progress(self, progress: float, message: str = "") -> None:
        """
        Update the progress of the process
        
        Args:
            progress: Progress value between 0 and 1
            message: Optional status message
        """
        self.progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
        if message:
            self.message = message
            self.logger.info(f"Progress ({progress:.1%}): {message}")
    
    def add_child(self, child: 'StatusItem') -> None:
        """
        Add a child status item
        
        Args:
            child: Child status item
        """
        self.children.append(child)
        child.parent = self
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if not self.start_time:
            return 0.0
        
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def format_status(self, include_children: bool = True) -> str:
        """
        Format the status as a string
        
        Args:
            include_children: Whether to include children in the output
            
        Returns:
            str: Formatted status string
        """
        status_str = f"{self.name}: [{self.status.value.upper()}] {self.description}"
        
        # Add elapsed time for running processes
        if self.start_time and self.status in [ProcessStatus.RUNNING, ProcessStatus.WAITING]:
            elapsed = self.get_elapsed_time()
            status_str += f" ({elapsed:.1f}s)"
        
        # Add message if present
        if self.message:
            status_str += f" - {self.message}"
        
        # Add children if requested
        if include_children and self.children:
            child_status = "\n  " + "\n  ".join([child.format_status(False) for child in self.children])
            status_str += child_status
        
        return status_str

class StatusMonitor:
    """
    Monitors and displays the status of multiple processes.
    This class helps maintain visibility into what the application is doing.
    """
    
    def __init__(self):
        """Initialize the status monitor"""
        self.items: Dict[str, StatusItem] = {}
        self.display_thread = None
        self.stop_event = threading.Event()
        self.logger = logging.getLogger("status_monitor")
    
    def register_item(self, name: str, description: str, parent_name: Optional[str] = None) -> StatusItem:
        """
        Register a new process to monitor
        
        Args:
            name: Unique identifier for the process
            description: Human-readable description
            parent_name: Optional parent process name
            
        Returns:
            StatusItem: The created status item
        """
        item = StatusItem(name, description)
        self.items[name] = item
        
        # If a parent is specified, add this as a child
        if parent_name and parent_name in self.items:
            self.items[parent_name].add_child(item)
        
        return item
    
    def get_item(self, name: str) -> Optional[StatusItem]:
        """
        Get a status item by name
        
        Args:
            name: Name of the item to retrieve
            
        Returns:
            Optional[StatusItem]: The status item if found, None otherwise
        """
        return self.items.get(name)
    
    def start_item(self, name: str) -> None:
        """
        Mark a process as started
        
        Args:
            name: Name of the process
        """
        if name in self.items:
            self.items[name].start()
    
    def complete_item(self, name: str, message: str = "") -> None:
        """
        Mark a process as completed
        
        Args:
            name: Name of the process
            message: Optional completion message
        """
        if name in self.items:
            self.items[name].complete(message)
    
    def fail_item(self, name: str, message: str) -> None:
        """
        Mark a process as failed
        
        Args:
            name: Name of the process
            message: Failure message
        """
        if name in self.items:
            self.items[name].fail(message)
    
    def wait_item(self, name: str, message: str) -> None:
        """
        Mark a process as waiting
        
        Args:
            name: Name of the process
            message: Wait reason
        """
        if name in self.items:
            self.items[name].wait(message)
    
    def update_progress(self, name: str, progress: float, message: str = "") -> None:
        """
        Update the progress of a process
        
        Args:
            name: Name of the process
            progress: Progress value between 0 and 1
            message: Optional status message
        """
        if name in self.items:
            self.items[name].update_progress(progress, message)
    
    def display_status(self) -> None:
        """Display the current status of all root processes"""
        # Only display root items (those without parents)
        root_items = [item for item in self.items.values() if not item.parent]
        
        # Clear the screen
        print("\033c", end="")
        
        # Print header
        print(f"{Colors.BOLD}{Colors.CYAN}=== System Status ==={Colors.RESET}")
        print()
        
        # Print each root item
        for item in root_items:
            status_str = item.format_status()
            if item.status == ProcessStatus.RUNNING:
                print_status("RUNNING", status_str)
            elif item.status == ProcessStatus.COMPLETED:
                print_status("COMPLETED", status_str)
            elif item.status == ProcessStatus.FAILED:
                print_status("FAILED", status_str)
            elif item.status == ProcessStatus.WAITING:
                print_status("WAITING", status_str)
            else:
                print_status(item.status.value.upper(), status_str)
            
            # For running items with progress, show a progress bar
            if item.status == ProcessStatus.RUNNING and item.progress > 0:
                print_progress(item.progress)
            
            print()
    
    def start_monitor_thread(self, interval: float = 1.0) -> None:
        """
        Start a background thread to periodically display status
        
        Args:
            interval: Update interval in seconds
        """
        if self.display_thread and self.display_thread.is_alive():
            return
        
        self.stop_event.clear()
        
        def _monitor_thread():
            while not self.stop_event.is_set():
                self.display_status()
                time.sleep(interval)
        
        self.display_thread = threading.Thread(target=_monitor_thread, daemon=True)
        self.display_thread.start()
    
    def stop_monitor_thread(self) -> None:
        """Stop the status display thread"""
        if self.display_thread and self.display_thread.is_alive():
            self.stop_event.set()
            self.display_thread.join(timeout=2.0)
            self.display_thread = None

# Create a global instance
global_monitor = StatusMonitor()

def register_status(name: str, description: str, parent_name: Optional[str] = None) -> StatusItem:
    """
    Register a new process to monitor
    
    Args:
        name: Unique identifier for the process
        description: Human-readable description
        parent_name: Optional parent process name
        
    Returns:
        StatusItem: The created status item
    """
    return global_monitor.register_item(name, description, parent_name)

def start_status(name: str) -> None:
    """
    Mark a process as started
    
    Args:
        name: Name of the process
    """
    global_monitor.start_item(name)

def complete_status(name: str, message: str = "") -> None:
    """
    Mark a process as completed
    
    Args:
        name: Name of the process
        message: Optional completion message
    """
    global_monitor.complete_item(name, message)

def fail_status(name: str, message: str) -> None:
    """
    Mark a process as failed
    
    Args:
        name: Name of the process
        message: Failure message
    """
    global_monitor.fail_item(name, message)

def wait_status(name: str, message: str) -> None:
    """
    Mark a process as waiting
    
    Args:
        name: Name of the process
        message: Wait reason
    """
    global_monitor.wait_item(name, message)

def update_progress(name: str, progress: float, message: str = "") -> None:
    """
    Update the progress of a process
    
    Args:
        name: Name of the process
        progress: Progress value between 0 and 1
        message: Optional status message
    """
    global_monitor.update_progress(name, progress, message)

def get_status(name: str) -> Optional[StatusItem]:
    """
    Get a status item by name
    
    Args:
        name: Name of the item to retrieve
        
    Returns:
        Optional[StatusItem]: The status item if found, None otherwise
    """
    return global_monitor.get_item(name)

def display_status() -> None:
    """Display the current status of all root processes"""
    global_monitor.display_status()

def start_status_monitor(interval: float = 1.0) -> None:
    """
    Start a background thread to periodically display status
    
    Args:
        interval: Update interval in seconds
    """
    global_monitor.start_monitor_thread(interval)

def stop_status_monitor() -> None:
    """Stop the status display thread"""
    global_monitor.stop_monitor_thread()