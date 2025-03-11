import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from logging.handlers import RotatingFileHandler

from system.config_validator import ConfigValidator, ConfigValidationResult
from system.agent import Agent, MessageBroker
from agents import (
    TechnicalAnalysisAgent,
    FundamentalAnalysisAgent,
    RiskManagementAgent,
    StrategyOptimizationAgent,
    TradeExecutionAgent,
    AssetSelectionAgent
)
from system.error_handling import setup_error_handling
from system.config_validator import validate_configuration

def setup_logging(config: Dict) -> logging.Logger:
    """Set up logging based on configuration"""
    log_level = config.get("system", {}).get("log_level", "INFO")
    log_dir = "logs"

    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Set up logging to file and console
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"{log_dir}/system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger("main")

async def initialize_agents(config: Dict, message_broker: MessageBroker) -> Dict[str, Agent]:
    """Initialize all agents based on configuration"""
    agents = {}

    # Technical Analysis Agent
    if "technical_analysis" in config.get("agents", {}):
        agent_config = config["agents"]["technical_analysis"]
        agent_config["parent_config"] = config  # Pass the full config
        technical_agent = TechnicalAnalysisAgent(
            agent_id="technical_analysis",
            message_broker=message_broker,
            config=agent_config
        )
        agents["technical_analysis"] = technical_agent

    # Fundamental Analysis Agent
    if "fundamental_analysis" in config.get("agents", {}):
        agent_config = config["agents"]["fundamental_analysis"]
        agent_config["parent_config"] = config  # Pass the full config
        fundamental_agent = FundamentalAnalysisAgent(
            agent_id="fundamental_analysis",
            message_broker=message_broker,
            config=agent_config
        )
        agents["fundamental_analysis"] = fundamental_agent

    # Risk Management Agent
    if "risk_management" in config.get("agents", {}):
        agent_config = config["agents"]["risk_management"]
        agent_config["parent_config"] = config  # Pass the full config
        risk_agent = RiskManagementAgent(
            agent_id="risk_management",
            message_broker=message_broker,
            config=agent_config
        )
        agents["risk_management"] = risk_agent

    # Strategy Optimization Agent
    if "strategy_optimization" in config.get("agents", {}):
        agent_config = config["agents"]["strategy_optimization"]
        agent_config["parent_config"] = config  # Pass the full config
        strategy_agent = StrategyOptimizationAgent(
            agent_id="strategy_optimization",
            message_broker=message_broker,
            config=agent_config
        )
        agents["strategy_optimization"] = strategy_agent
    
    # Asset Selection Agent
    if "asset_selection" in config.get("agents", {}):
        agent_config = config["agents"]["asset_selection"].copy()  # Make a copy to avoid modifying original
        agent_config["parent_config"] = config  # Pass the full config
        asset_selection_agent = AssetSelectionAgent(
            agent_id="asset_selection",
            message_broker=message_broker,
            config=agent_config
        )
        agents["asset_selection"] = asset_selection_agent

    # Trade Execution Agent
    if "trade_execution" in config.get("agents", {}):
        agent_config = config["agents"]["trade_execution"].copy()  # Make a copy to avoid modifying original
        agent_config["parent_config"] = config  # Pass the full config
        execution_agent = TradeExecutionAgent(
            agent_id="trade_execution",
            message_broker=message_broker,
            config=agent_config
        )
        agents["trade_execution"] = execution_agent

    return agents

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

async def run_system(config):
    """Main function to run the entire system"""
    logger = logging.getLogger("main")
    logger.info("Initializing the Multi-Agent Forex Trading System")

    # Create message broker
    message_broker = MessageBroker()
    logger.info("Message broker initialized")

    # Initialize all agents
    agents = await initialize_agents(config, message_broker)

    if not agents:
        logger.error("No agents configured. Please check your configuration.")
        return

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

    # Register signal handlers only when loop is running
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown)

    try:
        # Wait for shutdown signal
        await stop_event.wait()
    finally:
        # Stop all agents gracefully
        for name, agent in agents.items():
            logger.info(f"Stopping agent: {name}")
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")

        # Cancel any remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("System shutdown complete")

def main():
    """Entry point for the application"""
    args = parse_arguments()

    # Create default config directory and example config if they don't exist
    os.makedirs("config", exist_ok=True)

    # Load configuration
    if not os.path.exists(args.config):
        print(f"Configuration file {args.config} not found.")

        # Check if example config exists
        example_config = "config/settings.example.json"
        if os.path.exists(example_config):
            print(f"You can copy {example_config} to {args.config} to get started.")

        sys.exit(1)

    # Validate configuration
    valid, config = validate_configuration(args.config)
    if not valid:
        print("Configuration validation failed. Please check the logs for details.")
        sys.exit(1)

    # Force simulation mode if specified
    if args.simulation:
        if "trade_execution" in config.get("agents", {}):
            config["agents"]["trade_execution"]["gateway_type"] = "simulation"
        print("Running in SIMULATION mode - no real trades will be executed")

    # Setup logging
    logger = setup_logging(config)
    logger.info("Multi-Agent Forex Trading System starting up")

    # Setup error handling
    setup_error_handling()

    # Run the async event loop
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_system(config))
    except KeyboardInterrupt:
        logger.info("System shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()