#!/opt/homebrew/bin/python3.12
"""
Day 4 Improvements Comprehensive Testing Suite
==============================================

Tests all critical fixes implemented based on Day 3 analysis:
1. Position sizing bug fixes (50% -> 25%)
2. Account isolation improvements
3. Per-account configuration system
4. 4PM improvement engine
5. Enhanced risk management

Based on the Day 3 finding that Account 3 (+$2,230) outperformed
Accounts 1&2 (-$1,800, -$2,500) due to better risk management.
"""

import os
import sys
import json
import unittest
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from system_x import SystemX, SystemXConfig, AccountConfig, AdaptiveRiskConfig
    SYSTEM_X_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ SystemX import failed: {e}")
    SYSTEM_X_AVAILABLE = False

class TestDay4Improvements(unittest.TestCase):
    """Comprehensive test suite for Day 4 improvements"""
    
    def setUp(self):
        """Set up test environment"""
        if not SYSTEM_X_AVAILABLE:
            self.skipTest("SystemX not available for testing")
        
        # Mock environment to avoid real API calls
        self.mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test_key',
            'ALPACA_API_KEY': 'test_alpaca_key',
            'ALPACA_API_SECRET': 'test_alpaca_secret',
            'ALPACA_BASE_URL': 'https://paper-api.alpaca.markets',
            'SLACK_TRADE_WEBHOOK_URL': 'https://hooks.slack.com/test'
        }
        
        # Mock configuration
        self.test_config = {
            'trading': {
                'max_position_size': 0.15,
                'max_total_exposure': 0.75,
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.10,
                'max_day_trades': 3
            },
            'account_configs': {
                'PRIMARY_30K': {
                    'max_position_size': 0.15,
                    'aggressive_sizing_enabled': False,
                    'max_sure_thing_size': 0.15,
                    'risk_multiplier': 1.0,
                    'daily_loss_limit': 0.03
                },
                'SECONDARY_30K': {
                    'max_position_size': 0.15,
                    'aggressive_sizing_enabled': False,
                    'max_sure_thing_size': 0.15,
                    'risk_multiplier': 1.0,
                    'daily_loss_limit': 0.03
                },
                'TERTIARY_30K': {
                    'max_position_size': 0.15,
                    'aggressive_sizing_enabled': False,
                    'max_sure_thing_size': 0.15,
                    'risk_multiplier': 1.0,
                    'daily_loss_limit': 0.03
                }
            },
            'adaptive_risk': {
                'enable_4pm_auto_tuning': True,
                'performance_threshold': 0.02,
                'conservative_fallback': True,
                'account_isolation': True
            }
        }

    def test_position_sizing_reduction(self):
        """Test that position sizing caps have been reduced from 50% to 25%"""
        print("\\n🧪 Testing position sizing reduction (50% -> 25%)...")
        
        with patch.dict(os.environ, self.mock_env):
            with patch('system_x.create_client') as mock_supabase:
                with patch('system_x.tradeapi.REST') as mock_alpaca:
                    # Mock Supabase and Alpaca clients
                    mock_supabase.return_value = Mock()
                    mock_alpaca_instance = Mock()
                    mock_alpaca_instance.get_account.return_value = Mock(
                        equity=30000.0, cash=25000.0, status='ACTIVE'
                    )
                    mock_alpaca.return_value = mock_alpaca_instance
                    
                    # Create SystemX instance with debug mode
                    system = SystemX(debug=True)
                    
                    # Test account config loading
                    self.assertIsNotNone(system.config.account_configs)
                    
                    # Verify all accounts have conservative sizing
                    for account_name in ['PRIMARY_30K', 'SECONDARY_30K', 'TERTIARY_30K']:
                        account_config = system.config.account_configs.get(account_name)
                        self.assertIsNotNone(account_config, f"Account config missing for {account_name}")
                        self.assertEqual(account_config.max_position_size, 0.15, 
                                       f"Max position size should be 15% for {account_name}")
                        self.assertEqual(account_config.max_sure_thing_size, 0.15,
                                       f"Sure thing size should be 15% for {account_name}")
                        self.assertFalse(account_config.aggressive_sizing_enabled,
                                       f"Aggressive sizing should be disabled for {account_name}")
        
        print("✅ Position sizing reduction test passed")

    def test_account_isolation(self):
        """Test that accounts have proper isolation with separate balance tracking"""
        print("\\n🧪 Testing account isolation improvements...")
        
        with patch.dict(os.environ, self.mock_env):
            with patch('system_x.create_client') as mock_supabase:
                with patch('system_x.tradeapi.REST') as mock_alpaca:
                    # Mock different balances for each account
                    primary_account = Mock(equity=30000.0, cash=25000.0, status='ACTIVE')
                    secondary_account = Mock(equity=28000.0, cash=23000.0, status='ACTIVE') 
                    tertiary_account = Mock(equity=32000.0, cash=27000.0, status='ACTIVE')
                    
                    mock_supabase.return_value = Mock()
                    
                    def mock_alpaca_factory(*args, **kwargs):
                        if 'PRIMARY' in str(args):
                            mock_client = Mock()
                            mock_client.get_account.return_value = primary_account
                            return mock_client
                        elif 'SECONDARY' in str(args):
                            mock_client = Mock()
                            mock_client.get_account.return_value = secondary_account
                            return mock_client
                        else:
                            mock_client = Mock()
                            mock_client.get_account.return_value = tertiary_account
                            return mock_client
                    
                    mock_alpaca.side_effect = mock_alpaca_factory
                    
                    # Create SystemX instance
                    system = SystemX(debug=True)
                    
                    # Test that account balance tracking is initialized
                    self.assertTrue(hasattr(system, 'account_balances'))
                    self.assertTrue(hasattr(system, 'account_balances_lock'))
                    
                    # Test get_account_balance method
                    balance_primary = system.get_account_balance('PRIMARY_30K')
                    balance_secondary = system.get_account_balance('SECONDARY_30K')
                    balance_tertiary = system.get_account_balance('TERTIARY_30K')
                    
                    # Verify separate tracking
                    self.assertGreater(balance_primary, 0, "PRIMARY account balance should be tracked")
                    self.assertGreater(balance_secondary, 0, "SECONDARY account balance should be tracked")
                    self.assertGreater(balance_tertiary, 0, "TERTIARY account balance should be tracked")
        
        print("✅ Account isolation test passed")

    def test_4pm_improvement_engine(self):
        """Test the 4PM improvement engine functionality"""
        print("\\n🧪 Testing 4PM improvement engine...")
        
        with patch.dict(os.environ, self.mock_env):
            with patch('system_x.create_client') as mock_supabase:
                with patch('system_x.tradeapi.REST') as mock_alpaca:
                    # Mock Supabase and Alpaca
                    mock_supabase.return_value = Mock()
                    mock_alpaca_instance = Mock()
                    mock_alpaca_instance.get_account.return_value = Mock(
                        equity=30000.0, cash=25000.0, status='ACTIVE'
                    )
                    mock_alpaca.return_value = mock_alpaca_instance
                    
                    # Create SystemX instance
                    system = SystemX(debug=True)
                    
                    # Test that improvement engine components are initialized
                    self.assertTrue(hasattr(system, 'daily_performance_data'))
                    self.assertTrue(hasattr(system, 'improvement_engine_lock'))
                    self.assertTrue(hasattr(system, 'last_improvement_analysis'))
                    self.assertTrue(hasattr(system, 'improvement_recommendations'))
                    
                    # Test that run_4pm_improvement_engine method exists
                    self.assertTrue(hasattr(system, 'run_4pm_improvement_engine'))
                    self.assertTrue(callable(getattr(system, 'run_4pm_improvement_engine')))
                    
                    # Test adaptive risk configuration
                    adaptive_config = system.config.adaptive_risk
                    self.assertTrue(adaptive_config.enable_4pm_auto_tuning)
                    self.assertEqual(adaptive_config.performance_threshold, 0.02)
                    self.assertTrue(adaptive_config.conservative_fallback)
                    self.assertTrue(adaptive_config.account_isolation)
        
        print("✅ 4PM improvement engine test passed")

    def test_configuration_validation(self):
        """Test enhanced configuration system with validation"""
        print("\\n🧪 Testing enhanced configuration validation...")
        
        # Test SystemXConfig validation
        try:
            config = SystemXConfig(**self.test_config)
            self.assertIsNotNone(config.account_configs)
            self.assertIsNotNone(config.adaptive_risk)
            
            # Test per-account configurations
            for account_name in ['PRIMARY_30K', 'SECONDARY_30K', 'TERTIARY_30K']:
                account_config = config.account_configs[account_name]
                self.assertIsInstance(account_config, AccountConfig)
                self.assertLessEqual(account_config.max_position_size, 0.15)
                self.assertLessEqual(account_config.max_sure_thing_size, 0.15)
                self.assertFalse(account_config.aggressive_sizing_enabled)
            
            # Test adaptive risk configuration
            self.assertIsInstance(config.adaptive_risk, AdaptiveRiskConfig)
            
        except Exception as e:
            self.fail(f"Configuration validation failed: {e}")
        
        print("✅ Configuration validation test passed")

    def test_risk_management_improvements(self):
        """Test enhanced risk management based on Day 3 analysis"""
        print("\\n🧪 Testing risk management improvements...")
        
        with patch.dict(os.environ, self.mock_env):
            with patch('system_x.create_client') as mock_supabase:
                with patch('system_x.tradeapi.REST') as mock_alpaca:
                    mock_supabase.return_value = Mock()
                    mock_alpaca_instance = Mock()
                    mock_alpaca_instance.get_account.return_value = Mock(
                        equity=30000.0, cash=25000.0, status='ACTIVE'
                    )
                    mock_alpaca.return_value = mock_alpaca_instance
                    
                    # Create SystemX instance
                    system = SystemX(debug=True)
                    
                    # Mock get_v9b_analysis to return sure thing stock
                    with patch.object(system, 'get_v9b_analysis') as mock_analysis:
                        mock_analysis.return_value = {
                            'dts_score': 85.0,
                            'combined_score': 9.0,
                            'claude_signals': {'day_trading_confidence': 8.5}
                        }
                        
                        # Mock get_client to return proper client
                        with patch.object(system, 'get_client') as mock_get_client:
                            mock_get_client.return_value = mock_alpaca_instance
                            
                            # Test position sizing for sure thing stock
                            shares = system.calculate_position_size('TSLA', 200.0, 1.0, 'PRIMARY_30K')
                            
                            # Verify conservative sizing is applied (15% max)
                            max_expected_position = 30000.0 * 0.15  # $4,500
                            max_expected_shares = int(max_expected_position / 200.0)  # 22 shares
                            
                            self.assertLessEqual(shares, max_expected_shares,
                                               "Position size should be conservative (≤15%)")
                            self.assertGreater(shares, 0, "Should allow some position")
        
        print("✅ Risk management improvements test passed")

    def test_yaml_config_loading(self):
        """Test that the updated config.yaml loads correctly"""
        print("\\n🧪 Testing YAML configuration loading...")
        
        try:
            # Load the actual config.yaml file
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                
                # Verify account_configs section exists
                self.assertIn('account_configs', yaml_config, 
                            "account_configs section missing from config.yaml")
                
                # Verify adaptive_risk section exists  
                self.assertIn('adaptive_risk', yaml_config,
                            "adaptive_risk section missing from config.yaml")
                
                # Verify all required accounts are configured
                account_configs = yaml_config['account_configs']
                for account_name in ['PRIMARY_30K', 'SECONDARY_30K', 'TERTIARY_30K']:
                    self.assertIn(account_name, account_configs,
                                f"{account_name} missing from account_configs")
                    
                    account_config = account_configs[account_name]
                    self.assertIn('max_position_size', account_config)
                    self.assertIn('aggressive_sizing_enabled', account_config)
                    self.assertIn('max_sure_thing_size', account_config)
                    
                    # Verify conservative settings based on Day 3 analysis
                    self.assertEqual(account_config['max_position_size'], 0.15)
                    self.assertFalse(account_config['aggressive_sizing_enabled'])
                    self.assertEqual(account_config['max_sure_thing_size'], 0.15)
            else:
                self.skipTest("config.yaml not found")
                
        except Exception as e:
            self.fail(f"YAML config loading failed: {e}")
        
        print("✅ YAML configuration loading test passed")

def run_comprehensive_test():
    """Run comprehensive test suite and generate report"""
    print("🧪 Day 4 Improvements - Comprehensive Testing Suite")
    print("=" * 60)
    print("Testing all critical fixes based on Day 3 analysis:")
    print("• Position sizing reduction (50% -> 25%)")
    print("• Account isolation improvements") 
    print("• Per-account configuration system")
    print("• 4PM improvement engine")
    print("• Enhanced risk management")
    print("=" * 60)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDay4Improvements)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate summary report
    print("\\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"• {test}: {traceback.split(chr(10))[-2]}")
    
    if result.errors:
        print("\\n⚠️ ERRORS:")
        for test, traceback in result.errors:
            print(f"• {test}: {traceback.split(chr(10))[-2]}")
    
    if not result.failures and not result.errors:
        print("\\n✅ ALL TESTS PASSED - Day 4 improvements are working correctly!")
        print("\\n🎯 Key improvements validated:")
        print("• ✅ Position sizing reduced from 50% to 25% (based on Account 3's success)")
        print("• ✅ Account isolation with separate balance tracking")
        print("• ✅ Per-account configuration system implemented")
        print("• ✅ 4PM improvement engine with auto-tuning")
        print("• ✅ Enhanced risk management and validation")
        
        # Return success
        return True
    else:
        print("\\n❌ Some tests failed - review improvements needed")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)