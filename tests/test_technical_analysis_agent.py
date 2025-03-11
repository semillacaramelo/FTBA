
import unittest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from agents.technical_analysis_agent import TechnicalAnalysisAgent
from system.agent import MessageBroker, MessageType, Message
from system.core import Direction, Confidence, Indicator

class TestTechnicalAnalysisAgent(unittest.TestCase):
    """Test cases for TechnicalAnalysisAgent"""
    
    def setUp(self):
        """Set up test environment"""
        self.message_broker = MessageBroker()
        self.config = {
            "analysis_interval_seconds": 1,
            "signal_threshold": 0.6
        }
        self.agent = TechnicalAnalysisAgent(
            agent_id="test_technical",
            message_broker=self.message_broker,
            config=self.config
        )
        
        # Mock logger
        self.agent.logger = MagicMock()
        
        # Mock methods
        self.agent.send_message = MagicMock()
        
    def test_initialization(self):
        """Test agent initialization"""
        self.assertEqual(self.agent.agent_id, "test_technical")
        self.assertEqual(self.agent.analysis_interval, 1)
        self.assertEqual(self.agent.signal_threshold, 0.6)
        self.assertEqual(self.agent.market_data, {})
        self.assertEqual(self.agent.indicators, {})
    
    @patch.object(TechnicalAnalysisAgent, 'subscribe_to')
    def test_setup(self, mock_subscribe):
        """Test agent setup"""
        # Run the setup method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.agent.setup())
        
        # Check if the right subscriptions were made
        mock_subscribe.assert_called_once()
        mock_subscribe.assert_called_with([
            MessageType.SYSTEM_STATUS,
            MessageType.MARKET_DATA,
            MessageType.TRADE_RESULT
        ])
        
        loop.close()
    
    def test_update_market_data(self):
        """Test updating market data"""
        # Create sample market data message
        message_content = {
            "symbol": "EUR/USD",
            "timeframe": "M5",
            "ohlc": {
                "open": 1.1000,
                "high": 1.1050,
                "low": 1.0950,
                "close": 1.1020,
                "volume": 1000
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        message = Message(
            msg_id="test1",
            sender="market_data",
            recipients=["test_technical"],
            type=MessageType.MARKET_DATA,
            content=message_content
        )
        
        # Run the update method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.agent.update_market_data(message))
        
        # Check if data was stored correctly
        self.assertIn("EUR/USD", self.agent.market_data)
        self.assertIn("M5", self.agent.market_data["EUR/USD"])
        self.assertEqual(len(self.agent.market_data["EUR/USD"]["M5"]["close"]), 1)
        self.assertEqual(self.agent.market_data["EUR/USD"]["M5"]["close"][0], 1.1020)
        
        loop.close()
    
    def test_sma_calculation(self):
        """Test SMA calculation"""
        import numpy as np
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        sma5 = self.agent._calculate_sma(data, 5)
        
        # Should have 6 values (10 - 5 + 1)
        self.assertEqual(len(sma5), 6)
        
        # Check values
        np.testing.assert_almost_equal(sma5[0], 3.0)
        np.testing.assert_almost_equal(sma5[-1], 8.0)
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        import numpy as np
        # Create a price series with clear up and down movements
        data = np.array([10, 11, 12, 11, 10, 9, 8, 9, 10, 11, 12, 13, 14, 13, 12])
        
        rsi = self.agent._calculate_rsi(data, period=5)
        
        # Should have correct length (data length - period)
        self.assertEqual(len(rsi), len(data) - 5)
        
        # RSI should be between 0 and 100
        self.assertTrue(all(0 <= val <= 100 for val in rsi))
    
    def test_signal_generation(self):
        """Test signal generation from indicators"""
        # Setup sample data
        self.agent.market_data["EUR/USD"] = {
            "M5": {
                "open": [1.1000, 1.1010, 1.1020],
                "high": [1.1050, 1.1060, 1.1070],
                "low": [1.0950, 1.0960, 1.0970],
                "close": [1.1020, 1.1030, 1.1040],
                "volume": [1000, 1100, 1200],
                "timestamp": ["2023-01-01T00:00:00", "2023-01-01T00:05:00", "2023-01-01T00:10:00"]
            }
        }
        
        # Mock indicators to simulate a crossover
        self.agent.indicators["EUR/USD"] = {
            "SMA20": [1.1010, 1.1025, 1.1035],
            "SMA50": [1.1030, 1.1020, 1.1010],
            "RSI": [45, 55, 60]
        }
        
        signals = self.agent._generate_signals("EUR/USD", "M5")
        
        # Should generate at least one signal (SMA crossover)
        self.assertGreaterEqual(len(signals), 1)
        
        # Check signal properties
        signal = signals[0]
        self.assertEqual(signal.symbol, "EUR/USD")
        self.assertEqual(signal.timeframe, "M5")
        self.assertTrue(isinstance(signal.confidence, float))

if __name__ == '__main__':
    unittest.main()
