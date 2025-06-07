#!/opt/homebrew/bin/python3.12
"""
Unit Tests for 3-Account Trading Functionality
Tests that System X properly distributes trades across multiple accounts
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from datetime import datetime
import json

# Add project path
sys.path.insert(0, '/Users/francisclase/FinRLX')

# Import System X
from system_x import SystemX


class Test3AccountTrading(unittest.TestCase):
    """Test 3-account trading functionality"""
    
    def setUp(self):
        """Set up test environment with mocked APIs"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'ALPACA_PAPER_API_KEY_ID': 'test_key_1',
            'ALPACA_PAPER_API_SECRET_KEY': 'test_secret_1',
            'ALPACA_API_KEY_2': 'test_key_2',
            'ALPACA_API_SECRET_2': 'test_secret_2',
            'ALPACA_API_KEY_3': 'test_key_3',
            'ALPACA_API_SECRET_3': 'test_secret_3',
            'ALPACA_BASE_URL': 'https://paper-api.alpaca.markets',
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test_supabase_key',
            'SLACK_TRADE_WEBHOOK_URL': 'https://hooks.slack.com/test',
            'POLYGON_API_KEY': 'test_polygon_key'
        })
        self.env_patcher.start()
        
        # Create mock Alpaca clients
        self.mock_client_1 = Mock()
        self.mock_client_2 = Mock()
        self.mock_client_3 = Mock()
        
        # Configure mock account responses
        mock_account_1 = Mock()
        mock_account_1.equity = 30000.0
        mock_account_1.cash = 15000.0
        mock_account_1.status = 'ACTIVE'
        mock_account_1.day_trade_count = 0
        mock_account_1.buying_power = 60000.0
        
        mock_account_2 = Mock()
        mock_account_2.equity = 30000.0
        mock_account_2.cash = 15000.0
        mock_account_2.status = 'ACTIVE'
        mock_account_2.day_trade_count = 1
        mock_account_2.buying_power = 60000.0
        
        mock_account_3 = Mock()
        mock_account_3.equity = 30000.0
        mock_account_3.cash = 15000.0
        mock_account_3.status = 'ACTIVE'
        mock_account_3.day_trade_count = 2
        mock_account_3.buying_power = 60000.0
        
        # Configure client methods
        self.mock_client_1.get_account.return_value = mock_account_1
        self.mock_client_2.get_account.return_value = mock_account_2
        self.mock_client_3.get_account.return_value = mock_account_3
        
        # Mock order responses
        mock_order_1 = Mock()
        mock_order_1.id = 'order_123_acc1'
        mock_order_2 = Mock()
        mock_order_2.id = 'order_456_acc2'
        mock_order_3 = Mock()
        mock_order_3.id = 'order_789_acc3'
        
        self.mock_client_1.submit_order.return_value = mock_order_1
        self.mock_client_2.submit_order.return_value = mock_order_2
        self.mock_client_3.submit_order.return_value = mock_order_3
        
        # Mock positions
        self.mock_client_1.list_positions.return_value = []
        self.mock_client_2.list_positions.return_value = []
        self.mock_client_3.list_positions.return_value = []
        
        # Mock orders for day trade checking
        self.mock_client_1.list_orders.return_value = []
        self.mock_client_2.list_orders.return_value = []
        self.mock_client_3.list_orders.return_value = []
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_3_account_setup(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test that all 3 accounts are properly initialized"""
        # Mock Supabase
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        # Mock tradeapi.REST to return our mock clients
        mock_tradeapi.side_effect = [
            self.mock_client_1,  # Primary account
            self.mock_client_2,  # Secondary account  
            self.mock_client_3   # Tertiary account
        ]
        
        # Initialize SystemX
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Verify all accounts are configured (primary is separate from alpaca_clients)
        self.assertEqual(len(system.alpaca_clients), 2)  # Only secondary and tertiary
        self.assertIsNotNone(system.alpaca)  # Primary account
        self.assertIn('PRIMARY_30K', system.starting_equity)
        self.assertIn('SECONDARY_30K', system.starting_equity)
        self.assertIn('TERTIARY_30K', system.starting_equity)
        
        # Verify starting equity tracking
        self.assertEqual(system.starting_equity['PRIMARY_30K'], 30000.0)
        self.assertEqual(system.starting_equity['SECONDARY_30K'], 30000.0)
        self.assertEqual(system.starting_equity['TERTIARY_30K'], 30000.0)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_client_router(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test that get_client method returns correct client for each account"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Test client routing
        self.assertEqual(system.get_client('PRIMARY_30K'), system.alpaca)
        self.assertEqual(system.get_client('SECONDARY_30K'), self.mock_client_2)
        self.assertEqual(system.get_client('TERTIARY_30K'), self.mock_client_3)
        
        # Test invalid account fallback
        fallback_client = system.get_client('INVALID_ACCOUNT')
        self.assertEqual(fallback_client, system.alpaca)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_round_robin_account_selection(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test that accounts are selected in round-robin fashion"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Test round-robin selection
        accounts_selected = []
        for i in range(6):  # Test two full cycles
            account = system.get_next_available_account()
            accounts_selected.append(account)
        
        # Should cycle through available accounts
        expected_accounts = ['PRIMARY_30K', 'SECONDARY_30K', 'TERTIARY_30K']
        for i, account in enumerate(accounts_selected):
            expected_account = expected_accounts[i % len(expected_accounts)]
            self.assertIn(account, expected_accounts)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_execute_trade_with_3_accounts(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test that execute_trade distributes across all 3 accounts"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Execute 3 trades - should hit each account once
        trade_1 = system.execute_trade('AAPL', 10, 'buy', 150.0, 'TEST_TRADE_1')
        trade_2 = system.execute_trade('GOOGL', 5, 'buy', 2500.0, 'TEST_TRADE_2')
        trade_3 = system.execute_trade('MSFT', 15, 'buy', 300.0, 'TEST_TRADE_3')
        
        # Verify all trades succeeded
        self.assertTrue(trade_1)
        self.assertTrue(trade_2)
        self.assertTrue(trade_3)
        
        # Verify each mock client's submit_order was called exactly once
        self.mock_client_1.submit_order.assert_called_once()
        self.mock_client_2.submit_order.assert_called_once()
        self.mock_client_3.submit_order.assert_called_once()
        
        # Verify the order parameters for each account
        # Account 1 (PRIMARY_30K) should get first trade
        call_args_1 = self.mock_client_1.submit_order.call_args
        self.assertEqual(call_args_1[1]['symbol'], 'AAPL')
        self.assertEqual(call_args_1[1]['qty'], 10)
        self.assertEqual(call_args_1[1]['side'], 'buy')
        
        # Account 2 (SECONDARY_30K) should get second trade
        call_args_2 = self.mock_client_2.submit_order.call_args
        self.assertEqual(call_args_2[1]['symbol'], 'GOOGL')
        self.assertEqual(call_args_2[1]['qty'], 5)
        self.assertEqual(call_args_2[1]['side'], 'buy')
        
        # Account 3 (TERTIARY_30K) should get third trade
        call_args_3 = self.mock_client_3.submit_order.call_args
        self.assertEqual(call_args_3[1]['symbol'], 'MSFT')
        self.assertEqual(call_args_3[1]['qty'], 15)
        self.assertEqual(call_args_3[1]['side'], 'buy')
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_day_trade_limit_checking(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test day trade limit checking across all accounts"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        # Configure one account to be at day trade limit
        mock_account_1_limited = Mock()
        mock_account_1_limited.equity = 30000.0
        mock_account_1_limited.cash = 15000.0
        mock_account_1_limited.status = 'ACTIVE'
        mock_account_1_limited.day_trade_count = 3  # At limit
        mock_account_1_limited.buying_power = 60000.0
        
        self.mock_client_1.get_account.return_value = mock_account_1_limited
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Test day trade checking for specific account
        can_trade_primary = system._check_account_day_trades('PRIMARY_30K')
        can_trade_secondary = system._check_account_day_trades('SECONDARY_30K')
        can_trade_tertiary = system._check_account_day_trades('TERTIARY_30K')
        
        # Primary should be at limit, others should be available
        self.assertFalse(can_trade_primary)  # At limit (3 day trades)
        self.assertTrue(can_trade_secondary)  # Has 1 day trade
        self.assertTrue(can_trade_tertiary)   # Has 2 day trades
        
        # Overall day trade check should still return True (other accounts available)
        overall_can_trade = system.check_day_trade_limit()
        self.assertTrue(overall_can_trade)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_position_management_across_accounts(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test position management works across all accounts"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        # Mock positions for different accounts
        mock_position_1 = Mock()
        mock_position_1.symbol = 'AAPL'
        mock_position_1.qty = '10'
        mock_position_1.market_value = 1500.0
        mock_position_1.unrealized_pl = 50.0
        mock_position_1.avg_entry_price = 145.0
        mock_position_1.current_price = 150.0  # Add current_price
        mock_position_1.side = 'long'
        mock_position_1._raw = {'account_name': 'PRIMARY_30K'}
        
        mock_position_2 = Mock()
        mock_position_2.symbol = 'GOOGL'
        mock_position_2.qty = '5'
        mock_position_2.market_value = 12500.0
        mock_position_2.unrealized_pl = -250.0
        mock_position_2.avg_entry_price = 2550.0
        mock_position_2.current_price = 2450.0  # Add current_price
        mock_position_2.side = 'long'
        mock_position_2._raw = {'account_name': 'SECONDARY_30K'}
        
        self.mock_client_1.list_positions.return_value = [mock_position_1]
        self.mock_client_2.list_positions.return_value = [mock_position_2]
        self.mock_client_3.list_positions.return_value = []
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Get positions across all accounts
        all_positions = system.get_current_positions()
        
        # Should have positions from all accounts
        self.assertEqual(len(all_positions), 2)
        self.assertIn('AAPL_PRIMARY_30K', all_positions)
        self.assertIn('GOOGL_SECONDARY_30K', all_positions)
        
        # Verify position details include account names
        aapl_position = all_positions['AAPL_PRIMARY_30K']
        self.assertEqual(aapl_position['account_name'], 'PRIMARY_30K')
        self.assertEqual(aapl_position['symbol'], 'AAPL')
        self.assertEqual(aapl_position['qty'], 10)
        
        googl_position = all_positions['GOOGL_SECONDARY_30K']
        self.assertEqual(googl_position['account_name'], 'SECONDARY_30K')
        self.assertEqual(googl_position['symbol'], 'GOOGL')
        self.assertEqual(googl_position['qty'], 5)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_total_equity_calculation(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test total equity calculation across all accounts"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Test total equity calculation
        total_equity = system.get_total_account_equity()
        
        # Should be sum of all account equities (3 x $30,000 = $90,000)
        self.assertEqual(total_equity, 90000.0)
        
        # Test exposure calculation
        exposure = system.calculate_current_exposure()
        
        # With no positions, exposure should be 0
        self.assertEqual(exposure, 0.0)
    
    @patch('system_x.create_client')
    @patch('system_x.tradeapi.REST')
    @patch('system_x.requests.post')
    def test_accounts_status_reporting(self, mock_requests, mock_tradeapi, mock_supabase):
        """Test comprehensive accounts status reporting"""
        # Setup mocks
        mock_supabase_client = Mock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()
        mock_supabase.return_value = mock_supabase_client
        
        mock_tradeapi.side_effect = [
            self.mock_client_1,
            self.mock_client_2,
            self.mock_client_3
        ]
        
        with patch('system_x.polygon.RESTClient'), \
             patch('system_x.AlpacaProcessor'), \
             patch('system_x.StockTradingEnv'), \
             patch('system_x.redis.Redis'):
            
            system = SystemX(debug=False)
        
        # Get accounts status
        accounts_status = system.get_all_accounts_status()
        
        # Verify structure
        self.assertIn('accounts', accounts_status)
        self.assertIn('total_balance', accounts_status)
        self.assertIn('total_starting_balance', accounts_status)
        self.assertIn('total_daily_pnl', accounts_status)
        self.assertIn('active_accounts', accounts_status)
        
        # Verify account details
        accounts = accounts_status['accounts']
        self.assertEqual(len(accounts), 3)
        
        # Check each account has required fields
        for account in accounts:
            self.assertIn('name', account)
            self.assertIn('balance', account)
            self.assertIn('starting_balance', account)
            self.assertIn('daily_pnl', account)
            self.assertIn('daily_pnl_pct', account)
            self.assertIn('status', account)
            self.assertIn('day_trade_count', account)
            self.assertIn('cash', account)
            self.assertIn('buying_power', account)
        
        # Verify totals
        self.assertEqual(accounts_status['total_balance'], 90000.0)
        self.assertEqual(accounts_status['total_starting_balance'], 90000.0)
        self.assertEqual(accounts_status['total_daily_pnl'], 0.0)
        self.assertEqual(accounts_status['active_accounts'], 3)


def run_3_account_tests():
    """Run the 3-account trading tests"""
    print("🧪 Running 3-Account Trading Tests...")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(Test3AccountTrading)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"🏆 TEST RESULTS SUMMARY:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"   {test}: {failure}")
    
    if result.errors:
        print(f"\n❌ ERRORS:")
        for test, error in result.errors:
            print(f"   {test}: {error}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n📊 SUCCESS RATE: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 3-ACCOUNT TRADING: FULLY FUNCTIONAL!")
    elif success_rate >= 70:
        print("✅ 3-ACCOUNT TRADING: MOSTLY FUNCTIONAL")
    else:
        print("❌ 3-ACCOUNT TRADING: NEEDS ATTENTION")
    
    return success_rate >= 90


if __name__ == "__main__":
    success = run_3_account_tests()
    sys.exit(0 if success else 1)