#!/usr/bin/env python3
"""
Simplified Day Trading System with V9B Integration
Direct approach without heavy FinRL dependencies
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading

# Try to import supabase with fallback installation
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing supabase...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
    from supabase import create_client, Client

# Try to import alpaca with fallback installation
try:
    import alpaca_trade_api as tradeapi
except ImportError:
    print("Installing alpaca-trade-api...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "alpaca-trade-api"], check=True)
    import alpaca_trade_api as tradeapi

class SimpleDayTrader:
    """Simplified day trader using V9B qualified stocks"""
    
    def __init__(self):
        self.load_env_vars()
        self.setup_supabase()
        self.setup_alpaca()
        
        # Trading parameters
        self.account_balance = 30000
        self.max_position_size = 0.15  # 15% per position
        self.min_dts_score = 60
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
    
    def setup_supabase(self):
        """Initialize Supabase client"""
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
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
            print(f"✅ Alpaca connected - Account: ${float(account.equity):.2f}")
            self.account_balance = float(account.equity)
            
        except Exception as e:
            print(f"❌ Alpaca connection failed: {e}")
            sys.exit(1)
    
    def get_qualified_stocks(self):
        """Get qualified stocks from V9B system"""
        try:
            response = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification, dts_momentum_grade'
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
                            'grade': stock.get('dts_momentum_grade', '')
                        })
                
                self.qualified_stocks = stocks[:5]  # Top 5 stocks
                print(f"🎯 Qualified stocks: {[s['ticker'] for s in self.qualified_stocks]}")
                return True
            else:
                print("⚠️ No qualified stocks found")
                return False
                
        except Exception as e:
            print(f"❌ Error fetching qualified stocks: {e}")
            return False
    
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
            # Get latest trade
            trade = self.alpaca.get_latest_trade(ticker)
            return float(trade.price)
        except Exception as e:
            print(f"⚠️ Could not get price for {ticker}: {e}")
            return None
    
    def calculate_position_size(self, ticker, current_price):
        """Calculate appropriate position size"""
        if not current_price:
            return 0
        
        # Maximum position value (15% of account)
        max_position_value = self.account_balance * self.max_position_size
        
        # Get available cash
        account = self.alpaca.get_account()
        available_cash = float(account.cash)
        
        # Position value limited by available cash and max position size
        position_value = min(available_cash * 0.8, max_position_value)  # Use 80% of available cash
        
        # Calculate shares
        shares = int(position_value / current_price)
        
        return shares
    
    def execute_buy_order(self, ticker, shares):
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
            
            print(f"✅ BUY order submitted: {shares} shares of {ticker}")
            return True
            
        except Exception as e:
            print(f"❌ Buy order failed for {ticker}: {e}")
            return False
    
    def execute_sell_order(self, ticker, shares):
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
            
            print(f"✅ SELL order submitted: {shares} shares of {ticker}")
            return True
            
        except Exception as e:
            print(f"❌ Sell order failed for {ticker}: {e}")
            return False
    
    def trading_logic(self):
        """Main trading logic"""
        print("🤖 Running trading logic...")
        
        # Get current positions
        positions = self.get_current_positions()
        
        # Get latest V9B analysis
        try:
            response = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, claude_confidence_score, gpt4_trading_strategy'
            ).order('created_at', desc=True).limit(10).execute()
            
            analysis_data = {}
            if response.data:
                for item in response.data:
                    ticker = item.get('ticker')
                    if ticker:
                        analysis_data[ticker] = {
                            'confidence': item.get('claude_confidence_score', 0),
                            'strategy': item.get('gpt4_trading_strategy', '')
                        }
        except:
            analysis_data = {}
        
        # Trading decisions for each qualified stock
        for stock in self.qualified_stocks:
            ticker = stock['ticker']
            dts_score = stock['dts_score']
            
            try:
                # Get current price
                current_price = self.get_stock_price(ticker)
                if not current_price:
                    continue
                
                # Check if we have a position
                current_position = positions.get(ticker, {})
                current_qty = current_position.get('qty', 0)
                
                # Get V9B analysis confidence
                confidence = analysis_data.get(ticker, {}).get('confidence', 0)
                
                # Trading decision based on DTS score and confidence
                if dts_score >= 70 and confidence > 80:
                    # Strong buy signal
                    if current_qty == 0:
                        shares = self.calculate_position_size(ticker, current_price)
                        if shares > 0:
                            self.execute_buy_order(ticker, shares)
                            print(f"🔥 STRONG BUY: {ticker} (DTS: {dts_score}, Confidence: {confidence})")
                
                elif dts_score >= 65 and confidence > 70:
                    # Moderate buy signal
                    if current_qty == 0:
                        shares = self.calculate_position_size(ticker, current_price) // 2  # Half position
                        if shares > 0:
                            self.execute_buy_order(ticker, shares)
                            print(f"📈 MODERATE BUY: {ticker} (DTS: {dts_score}, Confidence: {confidence})")
                
                elif dts_score < 60 or confidence < 50:
                    # Sell signal
                    if current_qty > 0:
                        self.execute_sell_order(ticker, current_qty)
                        print(f"📉 SELL: {ticker} (DTS: {dts_score}, Confidence: {confidence})")
                
                # Risk management: Stop loss at -5%
                if current_qty > 0:
                    unrealized_pl_pct = current_position.get('unrealized_pl', 0) / current_position.get('market_value', 1)
                    if unrealized_pl_pct < -0.05:  # -5% stop loss
                        self.execute_sell_order(ticker, current_qty)
                        print(f"🛑 STOP LOSS: {ticker} ({unrealized_pl_pct*100:.1f}%)")
                
            except Exception as e:
                print(f"⚠️ Error processing {ticker}: {e}")
                continue
    
    def run_continuous_trading(self):
        """Run continuous trading during market hours"""
        print("🚀 Starting continuous day trading...")
        
        while True:
            try:
                # Check if market is open
                clock = self.alpaca.get_clock()
                if clock.is_open:
                    print(f"⏰ Market is open - {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Update qualified stocks
                    self.get_qualified_stocks()
                    
                    # Run trading logic
                    self.trading_logic()
                    
                    # Wait 5 minutes before next check
                    time.sleep(300)  # 5 minutes
                    
                else:
                    print("💤 Market is closed, waiting...")
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
            
            print("\n📊 PORTFOLIO STATUS")
            print("=" * 50)
            print(f"Total Equity: ${float(account.equity):,.2f}")
            print(f"Cash: ${float(account.cash):,.2f}")
            # Get day P&L if available
            try:
                day_pl = float(getattr(account, 'unrealized_pl', 0))
                print(f"Day P&L: ${day_pl:,.2f}")
                print(f"Day P&L %: {(day_pl / float(account.equity)) * 100:.2f}%")
            except:
                print(f"Day P&L: $0.00")
                print(f"Day P&L %: 0.00%")
            
            if positions:
                print("\n🎯 CURRENT POSITIONS:")
                for ticker, pos in positions.items():
                    pl_pct = (pos['unrealized_pl'] / pos['market_value']) * 100 if pos['market_value'] > 0 else 0
                    print(f"  {ticker}: {pos['qty']} shares, ${pos['market_value']:,.2f} ({pl_pct:+.1f}%)")
            else:
                print("\n💰 No current positions")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error showing portfolio: {e}")

def main():
    """Main function"""
    print("🏆 Simple Day Trading System with V9B Integration")
    print("=" * 60)
    
    trader = SimpleDayTrader()
    
    if len(sys.argv) < 2:
        print("Usage: python simple_day_trader.py [check|trade|status]")
        print("  check  - Check V9B data and connections")
        print("  trade  - Start live trading")
        print("  status - Show portfolio status")
        return
    
    command = sys.argv[1].lower()
    
    if command == "check":
        print("🔍 Checking connections and data...")
        if trader.get_qualified_stocks():
            print("✅ V9B data check passed")
            for stock in trader.qualified_stocks:
                print(f"  {stock['ticker']}: DTS {stock['dts_score']} ({stock['grade']})")
        else:
            print("❌ V9B data check failed")
    
    elif command == "status":
        trader.show_portfolio_status()
    
    elif command == "trade":
        trader.get_qualified_stocks()
        trader.run_continuous_trading()
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()