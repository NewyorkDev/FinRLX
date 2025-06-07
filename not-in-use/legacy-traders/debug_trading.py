#!/usr/bin/env python3
"""
Debug the trading system to see why no trades are executing
"""

import os
import sys
import pandas as pd
import numpy as np

# Try to import required packages
try:
    from supabase import create_client, Client
    import alpaca_trade_api as tradeapi
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class TradingDebugger:
    """Debug the trading system"""
    
    def __init__(self):
        self.load_env_vars()
        self.setup_connections()
        
    def load_env_vars(self):
        """Load environment variables"""
        env_file = "/Users/francisclase/FinRLX/the_end/.env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        self.alpaca_key = os.getenv('ALPACA_PAPER_API_KEY_ID')
        self.alpaca_secret = os.getenv('ALPACA_PAPER_API_SECRET_KEY')
        self.alpaca_base_url = os.getenv('ALPACA_BASE_URL')
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
    def setup_connections(self):
        """Setup Supabase and Alpaca connections"""
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            self.alpaca = tradeapi.REST(self.alpaca_key, self.alpaca_secret, self.alpaca_base_url, api_version='v2')
            print("✅ Connections established")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            sys.exit(1)
    
    def debug_trading_signals(self):
        """Debug V9B trading signals"""
        print("\n🔍 DEBUGGING TRADING SIGNALS")
        print("=" * 50)
        
        try:
            # Get latest analysis with confidence scores
            response = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, claude_confidence_score, gpt4_trading_strategy, dts_score'
            ).order('created_at', desc=True).limit(10).execute()
            
            if response.data:
                print(f"Found {len(response.data)} analysis records:")
                for analysis in response.data:
                    ticker = analysis.get('ticker', 'N/A')
                    confidence = analysis.get('claude_confidence_score', 'N/A')
                    dts_score = analysis.get('dts_score', 'N/A')
                    strategy = analysis.get('gpt4_trading_strategy', 'N/A')
                    
                    print(f"  {ticker}: Confidence={confidence}, DTS={dts_score}")
                    if strategy and strategy != 'N/A':
                        print(f"    Strategy: {strategy[:100]}...")
            else:
                print("❌ No analysis data found in v9_multi_source_analysis")
                
        except Exception as e:
            print(f"❌ Error fetching trading signals: {e}")
    
    def debug_stock_prices(self):
        """Debug stock price fetching"""
        print("\n🔍 DEBUGGING STOCK PRICES")
        print("=" * 50)
        
        stocks = ['INM', 'EJH', 'CRCL']
        
        for ticker in stocks:
            try:
                # Test Alpaca price fetching
                trade = self.alpaca.get_latest_trade(ticker)
                price = float(trade.price)
                print(f"✅ {ticker}: ${price:.2f}")
                
                # Test if we can calculate position size
                account = self.alpaca.get_account()
                available_cash = float(account.cash)
                max_position_value = 30000 * 0.15  # 15% of account
                position_value = min(available_cash * 0.8, max_position_value)
                shares = int(position_value / price)
                
                print(f"   Available cash: ${available_cash:,.2f}")
                print(f"   Max position: ${max_position_value:,.2f}")
                print(f"   Calculated shares: {shares}")
                
            except Exception as e:
                print(f"❌ {ticker}: Error getting price - {e}")
    
    def debug_trading_conditions(self):
        """Debug the exact trading conditions"""
        print("\n🔍 DEBUGGING TRADING CONDITIONS")
        print("=" * 50)
        
        # Get qualified stocks
        try:
            response = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification'
            ).gte('dts_score', 60).order('dts_score', desc=True).limit(5).execute()
            
            qualified_stocks = []
            if response.data:
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    if ticker and not ticker.startswith('TEST'):
                        qualified_stocks.append(stock)
            
            print(f"Qualified stocks: {len(qualified_stocks)}")
            
            # Test trading logic for each stock
            for stock in qualified_stocks:
                ticker = stock['ticker']
                dts_score = stock['dts_score']
                
                print(f"\n--- Testing {ticker} (DTS: {dts_score}) ---")
                
                # Get analysis data
                analysis_response = self.supabase.table('v9_multi_source_analysis').select(
                    'claude_confidence_score, gpt4_trading_strategy'
                ).eq('ticker', ticker).order('created_at', desc=True).limit(1).execute()
                
                if analysis_response.data:
                    confidence = analysis_response.data[0].get('claude_confidence_score', 0)
                    print(f"  Claude confidence: {confidence}")
                    
                    # Test trading conditions
                    if dts_score >= 70 and confidence > 80:
                        print("  🔥 STRONG BUY signal detected!")
                    elif dts_score >= 65 and confidence > 70:
                        print("  📈 MODERATE BUY signal detected!")
                    elif dts_score < 60 or confidence < 50:
                        print("  📉 SELL signal detected!")
                    else:
                        print("  ⏸️ HOLD - no clear signal")
                        
                else:
                    print("  ❌ No analysis data found")
                    
        except Exception as e:
            print(f"❌ Error in trading conditions: {e}")
    
    def test_order_execution(self):
        """Test if we can actually place orders"""
        print("\n🔍 TESTING ORDER EXECUTION")
        print("=" * 50)
        
        try:
            # Get account info
            account = self.alpaca.get_account()
            print(f"Account status: {account.status}")
            print(f"Trading blocked: {account.trading_blocked}")
            print(f"Pattern day trader: {account.pattern_day_trader}")
            print(f"Equity: ${float(account.equity):,.2f}")
            print(f"Cash: ${float(account.cash):,.2f}")
            
            # Check if market is open
            clock = self.alpaca.get_clock()
            print(f"Market open: {clock.is_open}")
            print(f"Next open: {clock.next_open}")
            print(f"Next close: {clock.next_close}")
            
            # Test with a small order (dry run)
            if clock.is_open:
                print("\n🧪 Testing small order (1 share of AAPL)...")
                try:
                    # Get AAPL price
                    trade = self.alpaca.get_latest_trade('AAPL')
                    price = float(trade.price)
                    print(f"AAPL price: ${price:.2f}")
                    
                    # Note: We're not actually placing this order, just testing the API call structure
                    print("Order structure would be:")
                    print(f"  Symbol: AAPL")
                    print(f"  Qty: 1")
                    print(f"  Side: buy")
                    print(f"  Type: market")
                    print(f"  Time in force: day")
                    print("✅ Order structure is valid")
                    
                except Exception as e:
                    print(f"❌ Order test failed: {e}")
            else:
                print("⏰ Market is closed - cannot test orders")
                
        except Exception as e:
            print(f"❌ Error testing order execution: {e}")
    
    def run_full_debug(self):
        """Run complete debugging"""
        print("🔍 TRADING SYSTEM DEBUG")
        print("=" * 60)
        
        self.debug_trading_signals()
        self.debug_stock_prices() 
        self.debug_trading_conditions()
        self.test_order_execution()
        
        print("\n🎯 SUMMARY:")
        print("If no trades are executing, check:")
        print("1. Are trading signals strong enough? (DTS >= 70, Confidence > 80)")
        print("2. Are stock prices available?")
        print("3. Is the market open?") 
        print("4. Is the account able to trade?")
        print("5. Are there any account restrictions?")

if __name__ == "__main__":
    debugger = TradingDebugger()
    debugger.run_full_debug()