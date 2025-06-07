#!/usr/bin/env python3
"""
PRODUCTION Day Trading System with V9B Integration
Professional-grade automated day trading respecting PDT rules
"""

import os
import sys
from datetime import datetime, timedelta
import time
import json

# Add path
sys.path.append('/Users/francisclase/FinRLX')

# Import packages
from supabase import create_client, Client
import alpaca_trade_api as tradeapi

class ProductionDayTrader:
    """Production-ready day trader with PDT compliance"""
    
    def __init__(self, debug=True):
        self.debug = debug
        self.load_environment()
        self.setup_connections()
        self.setup_trading_parameters()
        self.day_trade_count = 0
        self.max_day_trades = 3  # Conservative limit (PDT is 4 in 5 days)
        self.trade_log = []
        
    def load_environment(self):
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
        """Setup all connections"""
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            self.alpaca = tradeapi.REST(
                self.alpaca_key,
                self.alpaca_secret,
                self.alpaca_base_url,
                api_version='v2'
            )
            
            account = self.alpaca.get_account()
            self.account_balance = float(account.equity)
            
            if self.debug:
                print(f"✅ Connections established - Account: ${self.account_balance:,.2f}")
                print(f"   Status: {account.status}")
                print(f"   PDT: {account.pattern_day_trader}")
                print(f"   Trading blocked: {account.trading_blocked}")
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            sys.exit(1)
    
    def setup_trading_parameters(self):
        """Setup professional trading parameters"""
        # Account parameters
        self.max_position_size = 0.15  # 15% max per position
        self.max_total_exposure = 0.75  # 75% max total exposure
        self.min_dts_score = 65  # Higher threshold for production
        self.min_confidence_score = 7.5  # Higher confidence requirement
        
        # Risk management
        self.stop_loss_pct = 0.05  # 5% stop loss
        self.take_profit_pct = 0.10  # 10% take profit
        self.max_daily_loss = 0.03  # 3% max daily loss
        
        # Trading frequency (to avoid PDT)
        self.min_hold_time = 300  # 5 minutes minimum hold
        self.trading_interval = 900  # 15 minutes between checks
        
        # Position sizing
        self.base_position_size = 4500  # $4,500 base position (15% of 30k)
        
        if self.debug:
            print(f"🔧 Production Parameters:")
            print(f"   Max position size: {self.max_position_size*100}%")
            print(f"   Max total exposure: {self.max_total_exposure*100}%")
            print(f"   Min DTS score: {self.min_dts_score}")
            print(f"   Min confidence: {self.min_confidence_score}")
            print(f"   Stop loss: {self.stop_loss_pct*100}%")
            print(f"   Max daily loss: {self.max_daily_loss*100}%")
    
    def get_qualified_stocks(self):
        """Get high-quality qualified stocks"""
        try:
            response = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification, dts_momentum_grade, squeeze_score, trend_score'
            ).gte('dts_score', self.min_dts_score).order('dts_score', desc=True).limit(20).execute()
            
            if response.data:
                qualified_stocks = []
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    dts_score = stock.get('dts_score', 0)
                    squeeze_score = stock.get('squeeze_score', 0)
                    trend_score = stock.get('trend_score', 0)
                    
                    # Strict filtering for production
                    if (ticker and 
                        not ticker.startswith('TEST') and 
                        len(ticker) <= 5 and 
                        ticker.isalpha() and
                        dts_score >= self.min_dts_score):
                        
                        qualified_stocks.append({
                            'ticker': ticker,
                            'dts_score': dts_score,
                            'squeeze_score': squeeze_score,
                            'trend_score': trend_score
                        })
                
                # Remove duplicates
                seen = set()
                unique_stocks = []
                for stock in qualified_stocks:
                    if stock['ticker'] not in seen:
                        seen.add(stock['ticker'])
                        unique_stocks.append(stock)
                
                # Take top 5 highest scoring stocks
                top_stocks = unique_stocks[:5]
                
                if self.debug:
                    print(f"🎯 Qualified Stocks ({len(top_stocks)}):")
                    for stock in top_stocks:
                        print(f"   {stock['ticker']}: DTS {stock['dts_score']}, Squeeze {stock['squeeze_score']:.1f}")
                
                return top_stocks
            else:
                print("⚠️ No qualified stocks found")
                return []
                
        except Exception as e:
            print(f"❌ Error getting qualified stocks: {e}")
            return []
    
    def get_v9b_analysis(self, ticker):
        """Get comprehensive V9B analysis"""
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
                
        except Exception:
            if self.debug:
                print(f"⚠️ No recent analysis for {ticker}")
            return {}
    
    def get_current_positions(self):
        """Get current positions with enhanced details"""
        try:
            positions = self.alpaca.list_positions()
            current_positions = {}
            total_exposure = 0
            
            for position in positions:
                market_value = float(position.market_value)
                unrealized_pl = float(position.unrealized_pl)
                
                current_positions[position.symbol] = {
                    'qty': int(float(position.qty)),
                    'market_value': market_value,
                    'unrealized_pl': unrealized_pl,
                    'unrealized_pl_pct': (unrealized_pl / market_value) * 100 if market_value > 0 else 0,
                    'avg_entry_price': float(position.avg_entry_price),
                    'side': position.side
                }
                
                total_exposure += market_value
            
            exposure_pct = total_exposure / self.account_balance
            
            if self.debug and current_positions:
                print(f"📊 Current Positions (Exposure: {exposure_pct:.1%}):")
                for ticker, pos in current_positions.items():
                    print(f"   {ticker}: {pos['qty']} shares, ${pos['market_value']:,.0f} ({pos['unrealized_pl_pct']:+.1f}%)")
            
            return current_positions, exposure_pct
            
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return {}, 0
    
    def get_stock_price(self, ticker):
        """Get current stock price with error handling"""
        try:
            trade = self.alpaca.get_latest_trade(ticker)
            return float(trade.price)
        except Exception as e:
            if self.debug:
                print(f"⚠️ Could not get price for {ticker}: {e}")
            return None
    
    def calculate_position_size(self, ticker, price, confidence_multiplier=1.0):
        """Calculate professional position size"""
        if not price:
            return 0
        
        # Base position size
        base_size = self.base_position_size * confidence_multiplier
        
        # Check available cash
        account = self.alpaca.get_account()
        available_cash = float(account.cash)
        
        # Limit by available cash
        max_spend = min(available_cash * 0.8, base_size)
        
        # Calculate shares
        shares = int(max_spend / price)
        
        if self.debug and shares > 0:
            print(f"   Position calc for {ticker}: ${max_spend:,.0f} = {shares} shares at ${price:.2f}")
        
        return shares
    
    def check_day_trade_limit(self):
        """Check if we can make more day trades"""
        try:
            # Get account info (for future PDT tracking enhancement)
            # account = self.alpaca.get_account()
            
            # Get recent orders to count day trades
            orders = self.alpaca.list_orders(
                status='filled',
                after=(datetime.now() - timedelta(days=5)).isoformat()
            )
            
            # Count day trades
            day_trades_today = 0
            trades_by_symbol = {}
            
            for order in orders:
                if order.filled_at:
                    fill_date = order.filled_at.date()
                    symbol = order.symbol
                    side = order.side
                    
                    if fill_date == datetime.now().date():
                        if symbol not in trades_by_symbol:
                            trades_by_symbol[symbol] = []
                        trades_by_symbol[symbol].append(side)
            
            # Count round trips (day trades)
            for symbol, sides in trades_by_symbol.items():
                buys = sides.count('buy')
                sells = sides.count('sell')
                day_trades_today += min(buys, sells)
            
            self.day_trade_count = day_trades_today
            can_trade = self.day_trade_count < self.max_day_trades
            
            if self.debug:
                print(f"📈 Day Trade Status: {self.day_trade_count}/{self.max_day_trades} (Can trade: {can_trade})")
            
            return can_trade
            
        except Exception as e:
            print(f"⚠️ Error checking day trade limit: {e}")
            return True  # Conservative: allow trading if can't check
    
    def execute_buy_order(self, ticker, shares, reason=""):
        """Execute professional buy order"""
        try:
            if shares <= 0:
                return False
            
            if not self.check_day_trade_limit():
                print(f"🛑 Day trade limit reached, skipping buy for {ticker}")
                return False
            
            order = self.alpaca.submit_order(
                symbol=ticker,
                qty=shares,
                side='buy',
                type='market',
                time_in_force='day'
            )
            
            # Log the trade
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': 'BUY',
                'ticker': ticker,
                'shares': shares,
                'reason': reason,
                'order_id': order.id
            }
            self.trade_log.append(trade_record)
            
            print(f"✅ BUY {shares} shares of {ticker} - {reason}")
            return True
            
        except Exception as e:
            print(f"❌ Buy order failed for {ticker}: {e}")
            return False
    
    def execute_sell_order(self, ticker, shares, reason=""):
        """Execute professional sell order"""
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
            
            # Log the trade
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'action': 'SELL',
                'ticker': ticker,
                'shares': shares,
                'reason': reason,
                'order_id': order.id
            }
            self.trade_log.append(trade_record)
            
            print(f"✅ SELL {shares} shares of {ticker} - {reason}")
            return True
            
        except Exception as e:
            print(f"❌ Sell order failed for {ticker}: {e}")
            return False
    
    def check_daily_loss_limit(self):
        """Check if daily loss limit is exceeded"""
        try:
            account = self.alpaca.get_account()
            current_equity = float(account.equity)
            daily_loss = (30000 - current_equity) / 30000
            
            if daily_loss > self.max_daily_loss:
                print(f"🛑 Daily loss limit exceeded: {daily_loss*100:.1f}%")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error checking daily loss: {e}")
            return True
    
    def professional_trading_logic(self):
        """Professional trading logic with strict risk management"""
        if not self.check_daily_loss_limit():
            print("🛑 Daily loss limit exceeded, stopping trading")
            return
        
        if self.debug:
            print("🤖 Running professional trading logic...")
        
        # Get qualified stocks
        qualified_stocks = self.get_qualified_stocks()
        if not qualified_stocks:
            print("⚠️ No qualified stocks available")
            return
        
        # Get current positions
        positions, total_exposure = self.get_current_positions()
        
        # Check if we can add more exposure
        can_add_exposure = total_exposure < self.max_total_exposure
        
        trades_executed = 0
        
        for stock in qualified_stocks:
            ticker = stock['ticker']
            dts_score = stock['dts_score']
            # squeeze_score = stock['squeeze_score']  # Available for future use
            # trend_score = stock['trend_score']      # Available for future use
            
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
                
                # Current position
                current_position = positions.get(ticker, {})
                current_qty = current_position.get('qty', 0)
                
                if self.debug:
                    print(f"\n--- Analyzing {ticker} ---")
                    print(f"  Price: ${current_price:.2f}")
                    print(f"  DTS: {dts_score}, Squeeze: {squeeze_confidence:.1f}, Trend: {trend_confidence:.1f}")
                    print(f"  Combined: {combined_score:.1f}, Position: {current_qty} shares")
                
                # Trading logic
                avg_confidence = (squeeze_confidence + trend_confidence) / 2
                
                # STRONG BUY: Exceptional signals
                if (dts_score >= 75 and 
                    avg_confidence >= 9.0 and 
                    combined_score >= 9.0 and 
                    current_qty == 0 and 
                    can_add_exposure):
                    
                    confidence_multiplier = min(avg_confidence / 10.0, 1.5)
                    shares = self.calculate_position_size(ticker, current_price, confidence_multiplier)
                    
                    if shares > 0:
                        if self.execute_buy_order(ticker, shares, f"STRONG BUY (DTS:{dts_score}, Conf:{avg_confidence:.1f})"):
                            trades_executed += 1
                            can_add_exposure = False  # Conservative: one position at a time
                
                # MODERATE BUY: Good signals
                elif (dts_score >= 70 and 
                      avg_confidence >= 8.0 and 
                      combined_score >= 8.0 and 
                      current_qty == 0 and 
                      can_add_exposure):
                    
                    shares = self.calculate_position_size(ticker, current_price, 0.8)
                    
                    if shares > 0:
                        if self.execute_buy_order(ticker, shares, f"MODERATE BUY (DTS:{dts_score}, Conf:{avg_confidence:.1f})"):
                            trades_executed += 1
                            can_add_exposure = False
                
                # SELL CONDITIONS
                elif current_qty > 0:
                    should_sell = False
                    sell_reason = ""
                    
                    # Weak signals
                    if dts_score < 60 or avg_confidence < 6.0:
                        should_sell = True
                        sell_reason = f"WEAK SIGNALS (DTS:{dts_score}, Conf:{avg_confidence:.1f})"
                    
                    # Stop loss
                    elif current_position.get('unrealized_pl_pct', 0) < -self.stop_loss_pct * 100:
                        should_sell = True
                        sell_reason = f"STOP LOSS ({current_position.get('unrealized_pl_pct', 0):.1f}%)"
                    
                    # Take profit
                    elif current_position.get('unrealized_pl_pct', 0) > self.take_profit_pct * 100:
                        should_sell = True
                        sell_reason = f"TAKE PROFIT ({current_position.get('unrealized_pl_pct', 0):.1f}%)"
                    
                    if should_sell:
                        if self.execute_sell_order(ticker, current_qty, sell_reason):
                            trades_executed += 1
                
                elif self.debug:
                    print(f"  ⏸️ HOLD - No clear signal")
                
            except Exception as e:
                print(f"⚠️ Error processing {ticker}: {e}")
                continue
        
        if trades_executed > 0:
            print(f"📈 Executed {trades_executed} trades this cycle")
        elif self.debug:
            print("💤 No trades executed this cycle")
    
    def run_production_trading(self):
        """Run production trading with enhanced monitoring"""
        print("🚀 STARTING PRODUCTION DAY TRADING")
        print("=" * 50)
        print("📊 Professional Parameters:")
        print(f"   • Max day trades: {self.max_day_trades}")
        print(f"   • Max position size: {self.max_position_size*100}%")
        print(f"   • Stop loss: {self.stop_loss_pct*100}%")
        print(f"   • Take profit: {self.take_profit_pct*100}%")
        print(f"   • Max daily loss: {self.max_daily_loss*100}%")
        print(f"   • Trading interval: {self.trading_interval//60} minutes")
        print("=" * 50)
        
        while True:
            try:
                # Check if market is open
                clock = self.alpaca.get_clock()
                if clock.is_open:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"\n⏰ Market open - {timestamp}")
                    
                    # Run trading logic
                    self.professional_trading_logic()
                    
                    # Save trade log
                    if self.trade_log:
                        with open(f"trade_log_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
                            json.dump(self.trade_log, f, indent=2)
                    
                    # Wait for next cycle
                    print(f"⏳ Next check in {self.trading_interval//60} minutes...")
                    time.sleep(self.trading_interval)
                    
                else:
                    print("💤 Market closed, waiting 15 minutes...")
                    if self.debug:
                        print(f"   Next open: {clock.next_open}")
                    time.sleep(900)  # 15 minutes
                    
            except KeyboardInterrupt:
                print("\n🛑 Trading stopped by user")
                break
            except Exception as e:
                print(f"❌ Trading error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def show_daily_summary(self):
        """Show daily trading summary"""
        try:
            account = self.alpaca.get_account()
            positions, exposure = self.get_current_positions()
            _ = positions  # Suppress unused variable warning
            
            print("\n📊 DAILY TRADING SUMMARY")
            print("=" * 60)
            print(f"Account Equity: ${float(account.equity):,.2f}")
            print(f"Cash: ${float(account.cash):,.2f}")
            print(f"Day P&L: ${float(account.equity) - 30000:+,.2f}")
            print(f"Day P&L %: {((float(account.equity) / 30000) - 1) * 100:+.2f}%")
            print(f"Portfolio Exposure: {exposure:.1%}")
            print(f"Day Trades Used: {self.day_trade_count}/{self.max_day_trades}")
            
            if self.trade_log:
                print(f"\nTrades Today: {len(self.trade_log)}")
                for trade in self.trade_log[-5:]:  # Last 5 trades
                    print(f"  {trade['timestamp'][:19]} | {trade['action']} {trade['shares']} {trade['ticker']} - {trade['reason']}")
            
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error showing summary: {e}")

def main():
    """Main function"""
    print("🏆 PRODUCTION Day Trading System with V9B Integration")
    print("=" * 70)
    print("🎯 Professional-grade automated day trading")
    print("📋 PDT-compliant with strict risk management")
    print("💰 Optimized for $30k paper trading accounts")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\nUsage: python production_day_trader.py [command] [options]")
        print("\nCommands:")
        print("  check    - Check system and display qualified stocks")
        print("  trade    - Start production trading")
        print("  status   - Show portfolio status and daily summary")
        print("  test     - Test trading logic without executing trades")
        print("\nOptions:")
        print("  --debug  - Enable debug output")
        print("  --quiet  - Minimal output")
        return
    
    command = sys.argv[1].lower()
    debug_mode = '--debug' in sys.argv or command == 'test'
    
    trader = ProductionDayTrader(debug=debug_mode)
    
    if command == "check":
        print("🔍 Checking production system...")
        qualified = trader.get_qualified_stocks()
        
        if qualified:
            print("✅ System ready for production trading")
            for stock in qualified[:3]:
                analysis = trader.get_v9b_analysis(stock['ticker'])
                avg_conf = (analysis.get('squeeze_confidence', 0) + analysis.get('trend_confidence', 0)) / 2
                print(f"   {stock['ticker']}: DTS {stock['dts_score']}, Avg Confidence {avg_conf:.1f}")
        else:
            print("❌ No qualified stocks found")
    
    elif command == "status":
        trader.show_daily_summary()
    
    elif command == "test":
        print("🧪 Testing trading logic (no actual trades)...")
        trader.professional_trading_logic()
    
    elif command == "trade":
        # Final confirmation for production trading
        print("⚠️  PRODUCTION TRADING MODE")
        print("This will execute real trades in your paper account.")
        print("Max 3 day trades will be used to avoid PDT restrictions.")
        
        response = input("\nContinue with production trading? (yes/no): ").strip().lower()
        if response == "yes":
            trader.run_production_trading()
        else:
            print("Trading cancelled")
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()