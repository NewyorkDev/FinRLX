#!/usr/bin/env python3
"""
Fixed Day Trading System with V9B Integration
Uses correct V9B database schema and improved trading logic
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading

# Import required packages
try:
    from supabase import create_client, Client
    import alpaca_trade_api as tradeapi
except ImportError as e:
    print(f"Installing missing packages...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase", "alpaca-trade-api"], check=True)
    from supabase import create_client, Client
    import alpaca_trade_api as tradeapi

class FixedDayTrader:
    """Fixed day trader with correct V9B schema"""
    
    def __init__(self, debug_mode=True):
        self.debug_mode = debug_mode
        self.load_env_vars()
        self.setup_supabase()
        self.setup_alpaca()
        
        # Trading parameters
        self.account_balance = 30000
        self.max_position_size = 0.15  # 15% per position
        self.min_dts_score = 60
        self.min_confidence_threshold = 7.0  # Adjusted for squeeze_confidence_score
        self.qualified_stocks = []
        
    def load_env_vars(self):
        """Load environment variables from .env file"""
        env_file = "/Users/francisclase/FinRLX/the_end/.env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        # Get API credentials
        self.alpaca_key = os.getenv('ALPACA_PAPER_API_KEY_ID')
        self.alpaca_secret = os.getenv('ALPACA_PAPER_API_SECRET_KEY')
        self.alpaca_base_url = os.getenv('ALPACA_BASE_URL')
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if self.debug_mode:
            print(f"🔧 API Key: {self.alpaca_key[:10]}...")
            print(f"🔧 Base URL: {self.alpaca_base_url}")
    
    def setup_supabase(self):
        """Initialize Supabase client"""
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            if self.debug_mode:
                print("✅ Supabase connected")
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            sys.exit(1)
    
    def setup_alpaca(self):
        """Initialize Alpaca client"""
        try:
            self.alpaca = tradeapi.REST(
                self.alpaca_key,
                self.alpaca_secret,
                self.alpaca_base_url,
                api_version='v2'
            )
            
            # Test connection
            account = self.alpaca.get_account()
            self.account_balance = float(account.equity)
            
            if self.debug_mode:
                print(f"✅ Alpaca connected - Account: ${self.account_balance:,.2f}")
                print(f"   Status: {account.status}")
                print(f"   PDT: {account.pattern_day_trader}")
                print(f"   Trading blocked: {account.trading_blocked}")
            
        except Exception as e:
            print(f"❌ Alpaca connection failed: {e}")
            sys.exit(1)
    
    def get_qualified_stocks(self):
        """Get qualified stocks from V9B system using correct schema"""
        try:
            response = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification, dts_momentum_grade, squeeze_score, trend_score'
            ).gte('dts_score', self.min_dts_score).order('dts_score', desc=True).limit(10).execute()
            
            if response.data:
                stocks = []
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    if ticker and not ticker.startswith('TEST'):
                        stocks.append({
                            'ticker': ticker,
                            'dts_score': stock.get('dts_score', 0),
                            'qualification': stock.get('dts_qualification', ''),
                            'grade': stock.get('dts_momentum_grade', ''),
                            'squeeze_score': stock.get('squeeze_score', 0),
                            'trend_score': stock.get('trend_score', 0)
                        })
                
                self.qualified_stocks = stocks[:5]  # Top 5 stocks
                if self.debug_mode:
                    print(f"🎯 Qualified stocks: {[s['ticker'] for s in self.qualified_stocks]}")
                return True
            else:
                if self.debug_mode:
                    print("⚠️ No qualified stocks found")
                return False
                
        except Exception as e:
            print(f"❌ Error fetching qualified stocks: {e}")
            return False
    
    def get_v9b_analysis(self, ticker):
        """Get V9B analysis using correct schema"""
        try:
            response = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, squeeze_confidence_score, trend_confidence_score, v9_combined_score, claude_analysis'
            ).eq('ticker', ticker).order('created_at', desc=True).limit(1).execute()
            
            if response.data:
                analysis = response.data[0]
                return {
                    'squeeze_confidence': float(analysis.get('squeeze_confidence_score', 0)),
                    'trend_confidence': float(analysis.get('trend_confidence_score', 0)),
                    'combined_score': float(analysis.get('v9_combined_score', 0)),
                    'claude_analysis': analysis.get('claude_analysis', '')
                }
            else:
                return {}
                
        except Exception as e:
            if self.debug_mode:
                print(f"⚠️ Error fetching analysis for {ticker}: {e}")
            return {}
    
    def get_current_positions(self):
        """Get current positions from Alpaca"""
        try:
            positions = self.alpaca.list_positions()
            current_positions = {}
            
            for position in positions:
                current_positions[position.symbol] = {
                    'qty': int(float(position.qty)),
                    'market_value': float(position.market_value),
                    'unrealized_pl': float(position.unrealized_pl),
                    'side': position.side
                }
            
            return current_positions
            
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return {}
    
    def get_stock_price(self, ticker):
        """Get current stock price"""
        try:
            trade = self.alpaca.get_latest_trade(ticker)
            return float(trade.price)
        except Exception as e:
            if self.debug_mode:
                print(f"⚠️ Could not get price for {ticker}: {e}")
            return None
    
    def calculate_position_size(self, ticker, current_price, confidence_multiplier=1.0):
        """Calculate appropriate position size based on confidence"""
        if not current_price:
            return 0
        
        # Maximum position value (15% of account)
        max_position_value = self.account_balance * self.max_position_size
        
        # Adjust based on confidence (0.5 to 1.5 multiplier)
        adjusted_position_value = max_position_value * confidence_multiplier
        
        # Get available cash
        account = self.alpaca.get_account()
        available_cash = float(account.cash)
        
        # Position value limited by available cash and max position size
        position_value = min(available_cash * 0.8, adjusted_position_value)
        
        # Calculate shares
        shares = int(position_value / current_price)
        
        if self.debug_mode and shares > 0:
            print(f"  Position calc for {ticker}: ${position_value:,.0f} = {shares} shares at ${current_price:.2f}")
        
        return shares
    
    def execute_buy_order(self, ticker, shares, reason=""):
        """Execute buy order"""
        try:
            if shares <= 0:
                return False
            
            order = self.alpaca.submit_order(
                symbol=ticker,
                qty=shares,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            print(f"✅ BUY {shares} shares of {ticker} - {reason}")
            return True
            
        except Exception as e:
            print(f"❌ Buy order failed for {ticker}: {e}")
            return False
    
    def execute_sell_order(self, ticker, shares, reason=""):
        """Execute sell order"""
        try:
            if shares <= 0:
                return False
            
            order = self.alpaca.submit_order(
                symbol=ticker,
                qty=shares,
                side='sell',
                type='market',
                time_in_force='day'
            )
            
            print(f"✅ SELL {shares} shares of {ticker} - {reason}")
            return True
            
        except Exception as e:
            print(f"❌ Sell order failed for {ticker}: {e}")
            return False
    
    def trading_logic(self):
        """Enhanced trading logic with V9B signals"""
        if self.debug_mode:
            print("🤖 Running enhanced trading logic...")
        
        # Get current positions
        positions = self.get_current_positions()
        
        if self.debug_mode and positions:
            print(f"📊 Current positions: {list(positions.keys())}")
        
        trades_executed = 0
        
        # Trading decisions for each qualified stock
        for stock in self.qualified_stocks:
            ticker = stock['ticker']
            dts_score = stock['dts_score']
            squeeze_score = stock.get('squeeze_score', 0)
            trend_score = stock.get('trend_score', 0)
            
            try:
                # Get current price
                current_price = self.get_stock_price(ticker)
                if not current_price:
                    continue
                
                # Get V9B analysis
                analysis = self.get_v9b_analysis(ticker)
                squeeze_confidence = analysis.get('squeeze_confidence', 0)
                trend_confidence = analysis.get('trend_confidence', 0)
                combined_score = analysis.get('combined_score', 0)
                
                # Check if we have a position
                current_position = positions.get(ticker, {})
                current_qty = current_position.get('qty', 0)
                
                if self.debug_mode:
                    print(f"\n--- Analyzing {ticker} ---")
                    print(f"  Price: ${current_price:.2f}")
                    print(f"  DTS Score: {dts_score}")
                    print(f"  Squeeze Confidence: {squeeze_confidence}")
                    print(f"  Trend Confidence: {trend_confidence}")
                    print(f"  Combined Score: {combined_score}")
                    print(f"  Current Position: {current_qty} shares")
                
                # Enhanced trading conditions using V9B scoring
                confidence_avg = (squeeze_confidence + trend_confidence) / 2
                
                # Strong buy signals
                if (dts_score >= 70 and 
                    confidence_avg >= 8.0 and 
                    combined_score >= 8.0 and 
                    current_qty == 0):
                    
                    confidence_multiplier = min(confidence_avg / 10.0, 1.5)  # Cap at 1.5x
                    shares = self.calculate_position_size(ticker, current_price, confidence_multiplier)
                    
                    if shares > 0:
                        if self.execute_buy_order(ticker, shares, f"STRONG BUY (DTS:{dts_score}, Conf:{confidence_avg:.1f})"):
                            trades_executed += 1
                
                # Moderate buy signals  
                elif (dts_score >= 65 and 
                      confidence_avg >= 7.0 and 
                      combined_score >= 7.0 and 
                      current_qty == 0):
                    
                    shares = self.calculate_position_size(ticker, current_price, 0.7)  # Smaller position
                    
                    if shares > 0:
                        if self.execute_buy_order(ticker, shares, f"MODERATE BUY (DTS:{dts_score}, Conf:{confidence_avg:.1f})"):
                            trades_executed += 1
                
                # Sell signals
                elif (current_qty > 0 and 
                      (dts_score < 60 or confidence_avg < 6.0 or combined_score < 6.0)):
                    
                    if self.execute_sell_order(ticker, current_qty, f"SELL SIGNAL (DTS:{dts_score}, Conf:{confidence_avg:.1f})"):
                        trades_executed += 1
                
                # Risk management: Stop loss at -5%
                elif current_qty > 0:
                    unrealized_pl_pct = current_position.get('unrealized_pl', 0) / max(current_position.get('market_value', 1), 1)
                    if unrealized_pl_pct < -0.05:  # -5% stop loss
                        if self.execute_sell_order(ticker, current_qty, f"STOP LOSS ({unrealized_pl_pct*100:.1f}%)"):
                            trades_executed += 1
                
                elif self.debug_mode:
                    print(f"  ⏸️ HOLD - No clear signal")
                
            except Exception as e:
                print(f"⚠️ Error processing {ticker}: {e}")
                continue
        
        if trades_executed > 0:
            print(f"📈 Executed {trades_executed} trades this cycle")
        elif self.debug_mode:
            print("💤 No trades executed this cycle")
    
    def run_continuous_trading(self):
        """Run continuous trading during market hours"""
        print("🚀 Starting enhanced day trading with V9B signals...")
        print("📊 Enhanced Trading Conditions:")
        print("   🔥 STRONG BUY: DTS ≥ 70, Confidence ≥ 8.0, Combined ≥ 8.0")
        print("   📈 MODERATE BUY: DTS ≥ 65, Confidence ≥ 7.0, Combined ≥ 7.0") 
        print("   📉 SELL: DTS < 60 OR Confidence < 6.0 OR Combined < 6.0")
        print("   🛑 STOP LOSS: -5% unrealized P&L")
        print()
        
        while True:
            try:
                # Check if market is open
                clock = self.alpaca.get_clock()
                if clock.is_open:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"⏰ Market open - {timestamp}")
                    
                    # Update qualified stocks
                    self.get_qualified_stocks()
                    
                    # Run trading logic
                    self.trading_logic()
                    
                    # Wait 5 minutes before next check
                    time.sleep(300)  # 5 minutes
                    
                else:
                    print("💤 Market closed, waiting 15 minutes...")
                    if self.debug_mode:
                        print(f"   Next open: {clock.next_open}")
                    time.sleep(900)  # 15 minutes
                    
            except KeyboardInterrupt:
                print("\n🛑 Trading stopped by user")
                break
            except Exception as e:
                print(f"❌ Trading error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def show_portfolio_status(self):
        """Show current portfolio status"""
        try:
            account = self.alpaca.get_account()
            positions = self.get_current_positions()
            
            print("\n📊 ENHANCED PORTFOLIO STATUS")
            print("=" * 60)
            print(f"Total Equity: ${float(account.equity):,.2f}")
            print(f"Cash: ${float(account.cash):,.2f}")
            print(f"Buying Power: ${float(account.buying_power):,.2f}")
            
            # Calculate P&L if possible
            try:
                pnl = float(account.equity) - 30000  # Assuming started with 30k
                pnl_pct = (pnl / 30000) * 100
                print(f"Total P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
            except:
                print(f"Total P&L: Calculating...")
            
            if positions:
                print(f"\n🎯 CURRENT POSITIONS ({len(positions)}):")
                total_position_value = 0
                for ticker, pos in positions.items():
                    pl_pct = (pos['unrealized_pl'] / pos['market_value']) * 100 if pos['market_value'] > 0 else 0
                    print(f"  {ticker}: {pos['qty']} shares, ${pos['market_value']:,.2f} ({pl_pct:+.1f}%)")
                    total_position_value += pos['market_value']
                
                print(f"Total Position Value: ${total_position_value:,.2f}")
                exposure_pct = (total_position_value / float(account.equity)) * 100
                print(f"Portfolio Exposure: {exposure_pct:.1f}%")
            else:
                print("\n💰 No current positions")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error showing portfolio: {e}")

def main():
    """Main function"""
    print("🏆 FIXED Day Trading System with V9B Integration")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("Usage: python fixed_day_trader.py [check|trade|status|debug]")
        print("  check  - Check V9B data and connections")
        print("  trade  - Start live trading")
        print("  status - Show portfolio status")
        print("  debug  - Run in debug mode with detailed output")
        return
    
    command = sys.argv[1].lower()
    debug_mode = command == "debug" or "--debug" in sys.argv
    
    trader = FixedDayTrader(debug_mode=debug_mode)
    
    if command in ["check", "debug"]:
        print("🔍 Checking enhanced system...")
        if trader.get_qualified_stocks():
            print("✅ V9B data check passed")
            for stock in trader.qualified_stocks:
                analysis = trader.get_v9b_analysis(stock['ticker'])
                squeeze_conf = analysis.get('squeeze_confidence', 0)
                trend_conf = analysis.get('trend_confidence', 0)
                print(f"  {stock['ticker']}: DTS {stock['dts_score']}, Squeeze {squeeze_conf:.1f}, Trend {trend_conf:.1f}")
        else:
            print("❌ V9B data check failed")
    
    elif command == "status":
        trader.show_portfolio_status()
    
    elif command == "trade":
        trader.get_qualified_stocks()
        
        # Show current market status
        clock = trader.alpaca.get_clock()
        print(f"Market Status: {'🟢 OPEN' if clock.is_open else '🔴 CLOSED'}")
        if not clock.is_open:
            print(f"Next Open: {clock.next_open}")
            print("⚠️ Trading will begin when market opens")
        
        print(f"Account Balance: ${trader.account_balance:,.2f}")
        print(f"Qualified Stocks: {len(trader.qualified_stocks)}")
        
        if trader.qualified_stocks:
            trader.run_continuous_trading()
        else:
            print("❌ No qualified stocks found for trading")
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()