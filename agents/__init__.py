
"""
Agents module for the Multi-Agent Forex Trading System.
"""

from agents.technical_analysis_agent import TechnicalAnalysisAgent
from agents.fundamental_analysis_agent import FundamentalAnalysisAgent
from agents.risk_management_agent import RiskManagementAgent
from agents.strategy_optimization_agent import StrategyOptimizationAgent
from agents.trade_execution_agent import TradeExecutionAgent
from agents.asset_selection_agent import AssetSelectionAgent

__all__ = [
    'TechnicalAnalysisAgent',
    'FundamentalAnalysisAgent',
    'RiskManagementAgent',
    'StrategyOptimizationAgent',
    'TradeExecutionAgent',
    'AssetSelectionAgent'
]
