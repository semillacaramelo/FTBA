
import unittest
import importlib

class TestImports(unittest.TestCase):
    """Test that all imports work correctly"""
    
    def test_agent_imports(self):
        """Test that agent imports work correctly"""
        # Import main agents module
        import agents
        
        # Check that all agents are properly imported
        self.assertTrue(hasattr(agents, 'TechnicalAnalysisAgent'))
        self.assertTrue(hasattr(agents, 'FundamentalAnalysisAgent'))
        self.assertTrue(hasattr(agents, 'RiskManagementAgent'))
        self.assertTrue(hasattr(agents, 'StrategyOptimizationAgent'))
        self.assertTrue(hasattr(agents, 'TradeExecutionAgent'))
        
        # Check that the imports are actually the right classes
        self.assertEqual(agents.TechnicalAnalysisAgent.__name__, 'TechnicalAnalysisAgent')
        self.assertEqual(agents.FundamentalAnalysisAgent.__name__, 'FundamentalAnalysisAgent')
        self.assertEqual(agents.RiskManagementAgent.__name__, 'RiskManagementAgent')
        self.assertEqual(agents.StrategyOptimizationAgent.__name__, 'StrategyOptimizationAgent')
        self.assertEqual(agents.TradeExecutionAgent.__name__, 'TradeExecutionAgent')
        
        # Try to instantiate agents (requiring just the class, not actual instances)
        agent_classes = [
            agents.TechnicalAnalysisAgent,
            agents.FundamentalAnalysisAgent,
            agents.RiskManagementAgent,
            agents.StrategyOptimizationAgent,
            agents.TradeExecutionAgent
        ]
        
        for cls in agent_classes:
            self.assertTrue(callable(cls.__init__))
    
    def test_system_imports(self):
        """Test that system imports work correctly"""
        # Test core system modules
        modules_to_test = [
            'system.agent',
            'system.core',
            'system.error_handling',
            'system.config_validator'
        ]
        
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")
    
    def test_main_imports(self):
        """Test that main.py imports work correctly"""
        try:
            import main
            self.assertIsNotNone(main)
        except ImportError as e:
            self.fail(f"Failed to import main: {e}")

if __name__ == '__main__':
    unittest.main()
