
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

async def initialize_agents(config: Dict, message_broker) -> Dict:
    """Initialize all agents based on configuration"""
    agents = {}
    
    # Technical Analysis Agent
    if "technical_analysis" in config.get("agents", {}):
        technical_agent = TechnicalAnalysisAgent(
            agent_id="technical_analysis",
            message_broker=message_broker,
            config=config["agents"]["technical_analysis"]
        )
        agents["technical_analysis"] = technical_agent
    
    # Fundamental Analysis Agent
    if "fundamental_analysis" in config.get("agents", {}):
        fundamental_agent = FundamentalAnalysisAgent(
            agent_id="fundamental_analysis",
            message_broker=message_broker,
            config=config["agents"]["fundamental_analysis"]
        )
        agents["fundamental_analysis"] = fundamental_agent
    
    # Risk Management Agent
    if "risk_management" in config.get("agents", {}):
        risk_agent = RiskManagementAgent(
            agent_id="risk_management",
            message_broker=message_broker,
            config=config["agents"]["risk_management"]
        )
        agents["risk_management"] = risk_agent
    
    # Strategy Optimization Agent
    if "strategy_optimization" in config.get("agents", {}):
        strategy_agent = StrategyOptimizationAgent(
            agent_id="strategy_optimization",
            message_broker=message_broker,
            config=config["agents"]["strategy_optimization"]
        )
        agents["strategy_optimization"] = strategy_agent
    
    # Trade Execution Agent
    if "trade_execution" in config.get("agents", {}):
        execution_agent = TradeExecutionAgent(
            agent_id="trade_execution",
            message_broker=message_broker,
            config=config["agents"]["trade_execution"]
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
    except Exception as e:
        logger.error(f"Error during system operation: {e}")
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
    
    try:
        with open(args.config) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)
    
    # Force simulation mode if specified
    if args.simulation:
        if "trade_execution" in config.get("agents", {}):
            config["agents"]["trade_execution"]["gateway_type"] = "simulation"
        print("Running in SIMULATION mode - no real trades will be executed")
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("Multi-Agent Forex Trading System starting up")
    
    # Run the async event loop
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_system(config))
    except KeyboardInterrupt:
        logger.info("Manual interrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
