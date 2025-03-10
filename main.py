#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Multi-Agent Forex Trading System

This is the main entry point for the collaborative multi-agent forex trading system.
It initializes all agents, establishes the messaging infrastructure, and coordinates
the overall system operation.
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List

from system.agent import MessageBroker
from agents.technical_analysis_agent import TechnicalAnalysisAgent
from agents.fundamental_analysis_agent import FundamentalAnalysisAgent
from agents.risk_management_agent import RiskManagementAgent
from agents.strategy_optimization_agent import StrategyOptimizationAgent
from agents.trade_execution_agent import TradeExecutionAgent


def setup_logging(config):
    """Configure the logging system"""
    log_level = getattr(logging, config["system"].get("log_level", "INFO"))
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)
    
    log_filename = f"{log_directory}/forex_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("main")
    logger.info(f"Logging initialized. Log file: {log_filename}")
    return logger


def load_config(config_path="config/settings.json"):
    """Load system configuration from file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        print("Please create a configuration file or copy from settings.example.json")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Invalid JSON in configuration file: {config_path}")
        sys.exit(1)


async def initialize_agents(config, message_broker):
    """Initialize all agents with their configurations"""
    agents = {}
    
    # Create agents with their specific configurations
    agents["technical_analysis"] = TechnicalAnalysisAgent(
        "technical_analysis", message_broker, config["agents"]["technical_analysis"]
    )
    
    agents["fundamental_analysis"] = FundamentalAnalysisAgent(
        "fundamental_analysis", message_broker, config["agents"]["fundamental_analysis"]
    )
    
    agents["risk_management"] = RiskManagementAgent(
        "risk_management", message_broker, config["agents"]["risk_management"]
    )
    
    agents["strategy_optimization"] = StrategyOptimizationAgent(
        "strategy_optimization", message_broker, config["agents"]["strategy_optimization"]
    )
    
    agents["trade_execution"] = TradeExecutionAgent(
        "trade_execution", message_broker, config["agents"]["trade_execution"]
    )
    
    return agents


async def run_system(config):
    """Main function to run the entire system"""
    logger = logging.getLogger("main")
    logger.info("Initializing the Multi-Agent Forex Trading System")
    
    # Create message broker
    message_broker = MessageBroker()
    logger.info("Message broker initialized")
    
    # Initialize all agents
    agents = await initialize_agents(config, message_broker)
    logger.info(f"Initialized {len(agents)} agents: {', '.join(agents.keys())}")
    
    # Start all agents
    tasks = []
    for name, agent in agents.items():
        logger.info(f"Starting agent: {name}")
        task = asyncio.create_task(agent.start())
        tasks.append(task)
    
    # Set up graceful shutdown
    stop_event = asyncio.Event()
    
    def handle_shutdown():
        logger.info("Shutdown signal received. Stopping agents...")
        stop_event.set()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(sig, handle_shutdown)
    
    # Wait for shutdown signal
    await stop_event.wait()
    
    # Stop all agents gracefully
    for name, agent in agents.items():
        logger.info(f"Stopping agent: {name}")
        await agent.stop()
    
    # Cancel any remaining tasks
    for task in tasks:
        if not task.done():
            task.cancel()
    
    logger.info("System shutdown complete")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Multi-Agent Forex Trading System")
    parser.add_argument(
        "--config", 
        default="config/settings.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode (no real trades)"
    )
    return parser.parse_args()


def main():
    """Entry point for the application"""
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args.config)
    
    # Force simulation mode if specified
    if args.simulation:
        if "trade_execution" in config["agents"]:
            config["agents"]["trade_execution"]["gateway_type"] = "simulation"
        print("Running in SIMULATION mode - no real trades will be executed")
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("Multi-Agent Forex Trading System starting up")
    
    # Run the async event loop
    try:
        asyncio.run(run_system(config))
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
    finally:
        logger.info("System terminated")


if __name__ == "__main__":
    main()