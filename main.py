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
from system.colored_logger import setup_colored_logging, get_colored_logger
from system.status_monitor import (
    register_status, start_status, complete_status, 
    fail_status, wait_status, update_progress, 
    start_status_monitor, stop_status_monitor,
    display_status, ProcessStatus
)
from system.console_utils import print_header, print_message, print_status, Icons, MessageType, Colors

def setup_logging(config: Dict) -> logging.Logger:
    """Set up logging based on configuration"""
    log_level = config.get("system", {}).get("log_level", "INFO")
    log_dir = "logs"

    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler for logging to file
    file_handler = logging.FileHandler(f"{log_dir}/system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    
    # Setup colored logging for console output
    setup_colored_logging(getattr(logging, log_level))
    
    # Add file handler to root logger
    logging.getLogger().addHandler(file_handler)
    
    # Get logger for main module with colored output
    logger = get_colored_logger("main")
    
    # Register main system components in status monitor
    register_status("system", "Multi-Agent Forex Trading System")
    register_status("message_broker", "System Message Broker", "system")
    register_status("agents", "Trading Agents", "system")

    return logger

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
    parser = argparse.ArgumentParser(
        description="Multi-Agent Forex Trading Bot Autonomous (FTBA)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║ {Colors.GREEN}FTBA - Multi-Agent Forex Trading Bot Autonomous{Colors.CYAN}             ║
║                                                           ║
║ {Colors.YELLOW}A system of cooperating agents for automated forex trading{Colors.CYAN} ║ 
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}

Example commands:
  python main.py                           # Run with default settings
  python main.py --simulation              # Run in simulation mode
  python main.py --tradetest               # Test trade execution with demo account
  python main.py --config custom_config.json  # Use custom configuration
"""
    )
    parser.add_argument(
        "--config", 
        default="config/settings.json",
        help=f"{Colors.BLUE}Path to configuration file{Colors.RESET}"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help=f"{Colors.GREEN}Run in simulation mode (no real trades){Colors.RESET}"
    )
    parser.add_argument(
        "--tradetest",
        action="store_true",
        help=f"{Colors.YELLOW}Execute one PUT and one CALL trade in the demo account to verify functionality{Colors.RESET}"
    )
    return parser.parse_args()

async def run_system(config, run_tradetest=False):
    """Main function to run the entire system"""
    # Get logger with colored output
    logger = get_colored_logger("main")
    
    # Initialize system status
    start_status("system")
    logger.info("Initializing the Multi-Agent Forex Trading System")

    # Create message broker
    message_broker = MessageBroker()
    start_status("message_broker")
    complete_status("message_broker", "Initialized")
    logger.info("Message broker initialized")

    # Initialize all agents status
    start_status("agents")
    update_progress("agents", 0.1, "Initializing agents")
    
    # Initialize all agents
    agents = await initialize_agents(config, message_broker)

    if not agents:
        logger.error("No agents configured. Please check your configuration.")
        fail_status("agents", "No agents configured")
        fail_status("system", "Initialization failed")
        return

    # Register individual agent statuses
    for name in agents.keys():
        register_status(f"agent.{name}", f"{name.replace('_', ' ').title()} Agent", "agents")
    
    update_progress("agents", 0.5, "Agents initialized")
    logger.info(f"Initialized {len(agents)} agents: {', '.join(agents.keys())}")

    # Start all agents
    tasks = []
    for name, agent in agents.items():
        logger.info(f"Starting agent: {name}")
        start_status(f"agent.{name}")
        task = asyncio.create_task(agent.start())
        tasks.append(task)
    
    update_progress("agents", 1.0, "All agents started")
    complete_status("agents", f"{len(agents)} agents initialized and started")
    
    # Set up graceful shutdown
    stop_event = asyncio.Event()

    def handle_shutdown():
        logger.info("Shutdown signal received. Stopping agents...")
        for name in agents.keys():
            wait_status(f"agent.{name}", "Shutting down")
        stop_event.set()
        
    # If tradetest flag is set, run the test trades after agents are started
    if run_tradetest and "trade_execution" in agents:
        trade_execution_agent = agents["trade_execution"]
        logger.info("Trade test requested - waiting for agents to initialize...")
        
        # Register trade test status
        register_status("trade_test", "Test Trade Execution", "system")
        start_status("trade_test")
        wait_status("trade_test", "Waiting for agents to initialize")
        
        # Wait a moment for agents to initialize and connect
        await asyncio.sleep(3)
        
        update_progress("trade_test", 0.3, "Executing test trades")
        logger.info("Executing test trades...")
        try:
            # Call the execute_test_trades method using getattr to bypass type checking
            test_trade_method = getattr(trade_execution_agent, "execute_test_trades")
            success, message = await test_trade_method()
            
            if success:
                logger.info(f"Trade test successful: {message}")
                complete_status("trade_test", message)
            else:
                logger.error(f"Trade test failed: {message}")
                fail_status("trade_test", message)
        except Exception as e:
            logger.error(f"Error executing test trades: {e}")
            fail_status("trade_test", f"Error: {str(e)}")
        
        # Force manual shutdown since we've completed the test
        logger.info("Trade test completed, shutting down system...")
        # Wait a moment for test trades to register
        await asyncio.sleep(2)
        # Trigger shutdown
        handle_shutdown()

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
                complete_status(f"agent.{name}", "Stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")
                fail_status(f"agent.{name}", f"Error stopping: {str(e)}")

        # Cancel any remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or be cancelled
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    complete_status("system", "System shutdown complete")
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
        
        # Run system with tradetest flag if specified
        if args.tradetest:
            logger.info("Trade test mode enabled - will execute one PUT and one CALL test trade")
            # Ensure we're using the demo account
            if "trade_execution" in config.get("agents", {}):
                config["agents"]["trade_execution"]["use_demo_account"] = True
            asyncio.run(run_system(config, run_tradetest=True))
        else:
            asyncio.run(run_system(config))
    except KeyboardInterrupt:
        logger.info("System shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()