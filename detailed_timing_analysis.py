#!/usr/bin/env python3
"""
Detailed Timing Analysis: Why Account 3 Outperformed Accounts 1&2

This script provides a deeper analysis of the timing differences and their impact on performance.
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import alpaca_trade_api as tradeapi
import pytz
from typing import Dict, List, Any
import json
from dotenv import load_dotenv

load_dotenv()

class DetailedTimingAnalyzer:
    def __init__(self):
        # Alpaca account configurations
        self.accounts = {
            'PRIMARY_30K': {
                'api_key': os.getenv('ALPACA_API_KEY'),
                'api_secret': os.getenv('ALPACA_API_SECRET'),
                'base_url': os.getenv('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            },
            'SECONDARY_30K': {
                'api_key': os.getenv('ALPACA_API_KEY_2'),
                'api_secret': os.getenv('ALPACA_API_SECRET_2'),
                'base_url': os.getenv('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            },
            'TERTIARY_30K': {
                'api_key': os.getenv('ALPACA_API_KEY_3'),
                'api_secret': os.getenv('ALPACA_API_SECRET_3'),
                'base_url': os.getenv('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            }
        }
        
        # Initialize Alpaca clients
        self.alpaca_clients = {}
        for account_name, config in self.accounts.items():
            try:
                self.alpaca_clients[account_name] = tradeapi.REST(
                    config['api_key'],
                    config['api_secret'],
                    config['base_url'],
                    api_version='v2'
                )
            except Exception as e:
                print(f"❌ Failed to connect to {account_name}: {e}")
        
        self.eastern = pytz.timezone('US/Eastern')
    
    def analyze_performance_by_timing_strategy(self):
        """Analyze how different timing strategies affected performance"""
        
        print("\n" + "="*80)
        print("📊 DETAILED TIMING STRATEGY ANALYSIS")
        print("="*80)
        
        # Get all trades for today
        all_trades = []
        performance_summary = {}
        
        for account_name in self.accounts.keys():
            client = self.alpaca_clients[account_name]
            
            # Get portfolio performance
            try:
                portfolio = client.get_portfolio_history(period='1D', timeframe='5Min')
                if portfolio.equity:
                    equity_values = [float(x) for x in portfolio.equity]
                    start_equity = equity_values[0]
                    end_equity = equity_values[-1]
                    performance_summary[account_name] = {
                        'start': start_equity,
                        'end': end_equity,
                        'pnl': end_equity - start_equity,
                        'pnl_pct': ((end_equity - start_equity) / start_equity) * 100
                    }
            except Exception as e:
                print(f"Error getting portfolio for {account_name}: {e}")
            
            # Get today's orders
            today_start = datetime.now(self.eastern).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now(self.eastern).replace(hour=23, minute=59, second=59, microsecond=999999)
            
            try:
                orders = client.list_orders(
                    status='filled',
                    after=today_start.isoformat(),
                    until=today_end.isoformat(),
                    limit=500
                )
                
                for order in orders:
                    trade_data = {
                        'account': account_name,
                        'symbol': order.symbol,
                        'side': order.side,
                        'qty': float(order.qty),
                        'price': float(order.filled_avg_price),
                        'filled_at': pd.to_datetime(order.filled_at).tz_convert(self.eastern),
                        'value': float(order.qty) * float(order.filled_avg_price)
                    }
                    all_trades.append(trade_data)
                    
            except Exception as e:
                print(f"Error getting orders for {account_name}: {e}")
        
        # Analyze timing patterns
        if all_trades:
            df = pd.DataFrame(all_trades)
            
            print(f"\n📈 PERFORMANCE SUMMARY:")
            print("-" * 50)
            for account, perf in performance_summary.items():
                pnl_emoji = "🟢" if perf['pnl'] >= 0 else "🔴"
                print(f"{pnl_emoji} {account}: ${perf['pnl']:+,.0f} ({perf['pnl_pct']:+.2f}%)")
            
            # Find the winning strategy
            best_account = max(performance_summary.keys(), key=lambda x: performance_summary[x]['pnl'])
            worst_account = min(performance_summary.keys(), key=lambda x: performance_summary[x]['pnl'])
            
            print(f"\n🏆 BEST PERFORMING ACCOUNT: {best_account}")
            print(f"💸 WORST PERFORMING ACCOUNT: {worst_account}")
            
            # Analyze trading patterns of best vs worst
            self.analyze_trading_patterns(df, best_account, worst_account)
            
            # Analyze timing differences for each stock
            self.analyze_stock_timing_impact(df)
            
            # Analyze market timing
            self.analyze_market_timing_patterns(df)
    
    def analyze_trading_patterns(self, df, best_account, worst_account):
        """Compare trading patterns between best and worst performing accounts"""
        
        print(f"\n📊 TRADING PATTERN COMPARISON")
        print("-" * 50)
        
        for account in [best_account, worst_account]:
            account_trades = df[df['account'] == account]
            
            if not account_trades.empty:
                # Group by hour to see timing patterns
                account_trades['hour'] = account_trades['filled_at'].dt.hour
                
                buy_trades = account_trades[account_trades['side'] == 'buy']
                sell_trades = account_trades[account_trades['side'] == 'sell']
                
                print(f"\n{account}:")
                print(f"  Total trades: {len(account_trades)}")
                print(f"  Buy trades: {len(buy_trades)} (${buy_trades['value'].sum():,.0f})")
                print(f"  Sell trades: {len(sell_trades)} (${sell_trades['value'].sum():,.0f})")
                
                # Timing analysis
                if not buy_trades.empty:
                    avg_buy_hour = buy_trades['hour'].mean()
                    print(f"  Average buy time: {avg_buy_hour:.1f}:00")
                
                if not sell_trades.empty:
                    avg_sell_hour = sell_trades['hour'].mean()
                    print(f"  Average sell time: {avg_sell_hour:.1f}:00")
                
                # Most active hours
                hourly_activity = account_trades.groupby('hour').size()
                if not hourly_activity.empty:
                    most_active_hour = hourly_activity.idxmax()
                    print(f"  Most active hour: {most_active_hour}:00 ({hourly_activity.max()} trades)")
    
    def analyze_stock_timing_impact(self, df):
        """Analyze how timing differences affected each stock's performance"""
        
        print(f"\n📈 STOCK-BY-STOCK TIMING IMPACT")
        print("-" * 50)
        
        stocks_traded = df['symbol'].unique()
        
        for stock in stocks_traded:
            stock_trades = df[df['symbol'] == stock].copy()
            
            if len(stock_trades) > 1:  # Multiple accounts traded this stock
                print(f"\n📊 {stock}:")
                
                # Group by account and get first buy/last sell for each
                account_summary = {}
                
                for account in stock_trades['account'].unique():
                    account_stock_trades = stock_trades[stock_trades['account'] == account]
                    
                    buys = account_stock_trades[account_stock_trades['side'] == 'buy']
                    sells = account_stock_trades[account_stock_trades['side'] == 'sell']
                    
                    summary = {'account': account}
                    
                    if not buys.empty:
                        first_buy = buys.loc[buys['filled_at'].idxmin()]
                        summary['first_buy_time'] = first_buy['filled_at']
                        summary['first_buy_price'] = first_buy['price']
                        summary['total_bought'] = buys['qty'].sum()
                        summary['avg_buy_price'] = (buys['qty'] * buys['price']).sum() / buys['qty'].sum()
                    
                    if not sells.empty:
                        last_sell = sells.loc[sells['filled_at'].idxmax()]
                        summary['last_sell_time'] = last_sell['filled_at']
                        summary['last_sell_price'] = last_sell['price']
                        summary['total_sold'] = sells['qty'].sum()
                        summary['avg_sell_price'] = (sells['qty'] * sells['price']).sum() / sells['qty'].sum()
                    
                    account_summary[account] = summary
                
                # Compare timing and prices
                for account, data in account_summary.items():
                    if 'first_buy_time' in data:
                        buy_time_str = data['first_buy_time'].strftime('%H:%M:%S')
                        print(f"  {account}: First buy @ {buy_time_str} for ${data['first_buy_price']:.2f}")
                        
                        if 'avg_sell_price' in data and 'avg_buy_price' in data:
                            profit_per_share = data['avg_sell_price'] - data['avg_buy_price']
                            print(f"    Avg P&L per share: ${profit_per_share:+.2f}")
                
                # Find timing advantage
                buy_times = [(acc, data['first_buy_time'], data['first_buy_price']) 
                           for acc, data in account_summary.items() 
                           if 'first_buy_time' in data]
                
                if len(buy_times) > 1:
                    buy_times.sort(key=lambda x: x[1])  # Sort by time
                    earliest = buy_times[0]
                    latest = buy_times[-1]
                    
                    time_diff = (latest[1] - earliest[1]).total_seconds() / 60
                    price_diff = latest[2] - earliest[2]
                    
                    if time_diff > 5:  # More than 5 minutes difference
                        advantage = "EARLY ADVANTAGE" if price_diff > 0 else "LATE ADVANTAGE"
                        print(f"  ⚡ {advantage}: {earliest[0]} was {time_diff:.1f} min earlier")
                        print(f"     Price difference: ${price_diff:+.4f}")
    
    def analyze_market_timing_patterns(self, df):
        """Analyze market timing patterns"""
        
        print(f"\n⏰ MARKET TIMING ANALYSIS")
        print("-" * 50)
        
        # Add hour column
        df['hour'] = df['filled_at'].dt.hour
        df['minute'] = df['filled_at'].dt.minute
        
        print("\n📊 Trading Activity by Hour:")
        hourly_summary = df.groupby(['hour', 'account']).agg({
            'value': 'sum',
            'symbol': 'count'
        }).round(0)
        
        for hour in sorted(df['hour'].unique()):
            print(f"\n{hour:02d}:00 Hour:")
            hour_data = df[df['hour'] == hour]
            
            for account in sorted(hour_data['account'].unique()):
                account_hour = hour_data[hour_data['account'] == account]
                trade_count = len(account_hour)
                trade_value = account_hour['value'].sum()
                
                buy_count = len(account_hour[account_hour['side'] == 'buy'])
                sell_count = len(account_hour[account_hour['side'] == 'sell'])
                
                print(f"  {account}: {trade_count} trades (${trade_value:,.0f}) - {buy_count}B/{sell_count}S")
        
        # Market open analysis (9:30-10:00)
        print(f"\n🌅 MARKET OPEN ANALYSIS (9:30-10:00):")
        market_open = df[(df['hour'] == 9) & (df['minute'] >= 30) | (df['hour'] == 10) & (df['minute'] == 0)]
        
        if not market_open.empty:
            for account in sorted(market_open['account'].unique()):
                account_open = market_open[market_open['account'] == account]
                
                buys = account_open[account_open['side'] == 'buy']
                aggressive_entry = len(buys) > 0
                
                print(f"  {account}: {len(account_open)} trades, {'🟢 Aggressive Entry' if aggressive_entry else '🔴 Cautious Entry'}")
        
        # Market close analysis (15:30-16:00)
        print(f"\n🌆 MARKET CLOSE ANALYSIS (15:30-16:00):")
        market_close = df[(df['hour'] == 15) & (df['minute'] >= 30) | (df['hour'] == 16)]
        
        if not market_close.empty:
            for account in sorted(market_close['account'].unique()):
                account_close = market_close[market_close['account'] == account]
                
                sells = account_close[account_close['side'] == 'sell']
                position_cleanup = len(sells) > 0
                
                print(f"  {account}: {len(account_close)} trades, {'🧹 Position Cleanup' if position_cleanup else '📊 Normal Activity'}")

def main():
    print("🚀 Starting Detailed Timing Analysis...")
    
    analyzer = DetailedTimingAnalyzer()
    analyzer.analyze_performance_by_timing_strategy()
    
    print("\n✅ Detailed analysis complete!")

if __name__ == "__main__":
    main()