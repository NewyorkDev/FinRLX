#!/usr/bin/env python3
"""
Analyze Today's Trading Performance Across Three Alpaca Accounts

This script connects to all three Alpaca accounts and analyzes:
1. Trade execution timing differences
2. Performance impact of timing differences
3. Cross-reference with today's top gainers
4. Identify which account had better entry timing
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import alpaca_trade_api as tradeapi
from supabase import create_client, Client
import pytz
from typing import Dict, List, Any
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class TradingAnalyzer:
    def __init__(self):
        """Initialize connections to all three Alpaca accounts and Supabase"""
        
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
                print(f"✅ Connected to {account_name}")
            except Exception as e:
                print(f"❌ Failed to connect to {account_name}: {e}")
        
        # Initialize Supabase client
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            self.supabase: Client = create_client(supabase_url, supabase_key)
            print("✅ Connected to Supabase")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            self.supabase = None
        
        # Today's top gainers for reference
        self.top_gainers_today = {
            'BULLZ': 53.19,
            'NKTR': 29.12,
            'INSM': 28.65,
            'BGM': 23.75,
            'MTSR': 15.50
        }
        
        # Set timezone
        self.eastern = pytz.timezone('US/Eastern')
        
    def get_today_date_range(self):
        """Get today's date range in EST"""
        now = datetime.now(self.eastern)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return today_start, today_end
    
    def get_account_orders_today(self, account_name: str) -> List[Dict]:
        """Get all orders for an account today"""
        if account_name not in self.alpaca_clients:
            return []
        
        client = self.alpaca_clients[account_name]
        today_start, today_end = self.get_today_date_range()
        
        try:
            # Get orders from today
            orders = client.list_orders(
                status='all',
                after=today_start.isoformat(),
                until=today_end.isoformat(),
                limit=500
            )
            
            order_data = []
            for order in orders:
                order_dict = {
                    'account': account_name,
                    'symbol': order.symbol,
                    'side': order.side,
                    'qty': float(order.qty),
                    'order_type': order.order_type,
                    'status': order.status,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'filled_qty': float(order.filled_qty or 0),
                    'filled_avg_price': float(order.filled_avg_price or 0),
                    'order_id': order.id
                }
                
                if order.filled_at:
                    # Convert to Eastern time
                    filled_time = pd.to_datetime(order.filled_at).tz_convert(self.eastern)
                    order_dict['filled_time_est'] = filled_time
                
                order_data.append(order_dict)
            
            print(f"📊 {account_name}: Found {len(order_data)} orders today")
            return order_data
            
        except Exception as e:
            print(f"❌ Error getting orders for {account_name}: {e}")
            return []
    
    def get_account_positions_today(self, account_name: str) -> List[Dict]:
        """Get current positions for an account"""
        if account_name not in self.alpaca_clients:
            return []
        
        client = self.alpaca_clients[account_name]
        
        try:
            positions = client.list_positions()
            position_data = []
            
            for position in positions:
                position_data.append({
                    'account': account_name,
                    'symbol': position.symbol,
                    'qty': float(position.qty),
                    'market_value': float(position.market_value),
                    'avg_entry_price': float(position.avg_entry_price),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'current_price': float(position.current_price)
                })
            
            print(f"📊 {account_name}: {len(position_data)} current positions")
            return position_data
            
        except Exception as e:
            print(f"❌ Error getting positions for {account_name}: {e}")
            return []
    
    def get_account_portfolio_history(self, account_name: str) -> Dict:
        """Get portfolio performance for today"""
        if account_name not in self.alpaca_clients:
            return {}
        
        client = self.alpaca_clients[account_name]
        
        try:
            # Get portfolio history for today
            portfolio = client.get_portfolio_history(
                period='1D',
                timeframe='5Min'
            )
            
            if not portfolio.equity:
                return {}
            
            # Calculate performance
            equity_values = [float(x) for x in portfolio.equity]
            start_equity = equity_values[0]
            end_equity = equity_values[-1]
            
            return {
                'account': account_name,
                'start_equity': start_equity,
                'end_equity': end_equity,
                'pnl_dollar': end_equity - start_equity,
                'pnl_percent': ((end_equity - start_equity) / start_equity) * 100,
                'equity_timeline': equity_values,
                'timestamps': portfolio.timestamp
            }
            
        except Exception as e:
            print(f"❌ Error getting portfolio history for {account_name}: {e}")
            return {}
    
    def get_supabase_trade_logs(self) -> List[Dict]:
        """Get trade execution logs from Supabase for today"""
        if not self.supabase:
            return []
        
        today_start, today_end = self.get_today_date_range()
        
        try:
            response = self.supabase.table('trade_execution_logs').select('*').gte(
                'timestamp', today_start.isoformat()
            ).lte(
                'timestamp', today_end.isoformat()
            ).execute()
            
            print(f"📊 Supabase: Found {len(response.data)} trade logs today")
            return response.data
            
        except Exception as e:
            print(f"❌ Error getting Supabase trade logs: {e}")
            return []
    
    def analyze_timing_differences(self, all_orders: List[Dict]) -> Dict:
        """Analyze timing differences for the same stocks across accounts"""
        
        # Group orders by symbol
        orders_by_symbol = {}
        for order in all_orders:
            if order['status'] == 'filled' and order['filled_at']:
                symbol = order['symbol']
                if symbol not in orders_by_symbol:
                    orders_by_symbol[symbol] = []
                orders_by_symbol[symbol].append(order)
        
        timing_analysis = {}
        
        for symbol, orders in orders_by_symbol.items():
            if len(orders) > 1:  # Multiple accounts traded this symbol
                # Sort by fill time
                orders.sort(key=lambda x: x['filled_time_est'])
                
                timing_analysis[symbol] = {
                    'orders': orders,
                    'first_fill': orders[0],
                    'last_fill': orders[-1],
                    'time_spread_minutes': (orders[-1]['filled_time_est'] - orders[0]['filled_time_est']).total_seconds() / 60,
                    'price_spread': orders[-1]['filled_avg_price'] - orders[0]['filled_avg_price'],
                    'accounts_involved': [order['account'] for order in orders]
                }
        
        return timing_analysis
    
    def check_top_gainers_exposure(self, all_orders: List[Dict], all_positions: List[Dict]) -> Dict:
        """Check if any accounts captured today's top gainers"""
        
        exposure_analysis = {}
        
        for symbol, gain_percent in self.top_gainers_today.items():
            exposure_analysis[symbol] = {
                'gain_percent': gain_percent,
                'orders': [order for order in all_orders if order['symbol'] == symbol],
                'positions': [pos for pos in all_positions if pos['symbol'] == symbol],
                'captured': False
            }
            
            if exposure_analysis[symbol]['orders'] or exposure_analysis[symbol]['positions']:
                exposure_analysis[symbol]['captured'] = True
        
        return exposure_analysis
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive analysis report"""
        
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TRADING ANALYSIS - TODAY")
        print("="*80)
        
        # Collect all data
        all_orders = []
        all_positions = []
        portfolio_performance = {}
        
        for account_name in self.accounts.keys():
            print(f"\n📈 Analyzing {account_name}...")
            
            # Get orders
            orders = self.get_account_orders_today(account_name)
            all_orders.extend(orders)
            
            # Get positions
            positions = self.get_account_positions_today(account_name)
            all_positions.extend(positions)
            
            # Get portfolio performance
            portfolio_performance[account_name] = self.get_account_portfolio_history(account_name)
        
        # Get Supabase logs
        supabase_logs = self.get_supabase_trade_logs()
        
        # Analyze timing differences
        timing_analysis = self.analyze_timing_differences(all_orders)
        
        # Check top gainers exposure
        top_gainers_analysis = self.check_top_gainers_exposure(all_orders, all_positions)
        
        # Generate report
        report = []
        report.append("\n🎯 EXECUTIVE SUMMARY")
        report.append("-" * 50)
        
        # Portfolio performance summary
        for account_name, perf in portfolio_performance.items():
            if perf:
                pnl_emoji = "🟢" if perf['pnl_dollar'] >= 0 else "🔴"
                report.append(f"{pnl_emoji} {account_name}: ${perf['pnl_dollar']:+,.0f} ({perf['pnl_percent']:+.2f}%)")
        
        # Trading activity summary
        total_orders = len([o for o in all_orders if o['status'] == 'filled'])
        report.append(f"\n📊 Total filled orders today: {total_orders}")
        
        # Timing analysis
        if timing_analysis:
            report.append(f"\n⏱️ TIMING DIFFERENCES ANALYSIS")
            report.append("-" * 50)
            
            for symbol, analysis in timing_analysis.items():
                report.append(f"\n📈 {symbol}:")
                report.append(f"   Time spread: {analysis['time_spread_minutes']:.1f} minutes")
                report.append(f"   Price spread: ${analysis['price_spread']:+.4f}")
                report.append(f"   First fill: {analysis['first_fill']['account']} @ {analysis['first_fill']['filled_time_est'].strftime('%H:%M:%S')}")
                report.append(f"   Last fill: {analysis['last_fill']['account']} @ {analysis['last_fill']['filled_time_est'].strftime('%H:%M:%S')}")
                
                # Calculate impact
                if analysis['price_spread'] != 0:
                    shares = analysis['last_fill']['filled_qty']
                    timing_impact = analysis['price_spread'] * shares
                    report.append(f"   Timing impact: ${timing_impact:+.2f}")
        
        # Top gainers analysis
        captured_gainers = [symbol for symbol, data in top_gainers_analysis.items() if data['captured']]
        if captured_gainers:
            report.append(f"\n🎯 TOP GAINERS CAPTURED: {len(captured_gainers)}")
            report.append("-" * 50)
            
            for symbol in captured_gainers:
                data = top_gainers_analysis[symbol]
                report.append(f"\n✅ {symbol} (+{data['gain_percent']:.1f}%):")
                
                for order in data['orders']:
                    side_emoji = "🟢" if order['side'] == 'buy' else "🔴"
                    report.append(f"   {side_emoji} {order['account']}: {order['side']} {order['filled_qty']} @ ${order['filled_avg_price']:.2f}")
                
                for pos in data['positions']:
                    pl_emoji = "🟢" if pos['unrealized_pl'] >= 0 else "🔴"
                    report.append(f"   {pl_emoji} {pos['account']}: {pos['qty']} shares, ${pos['unrealized_pl']:+,.0f} unrealized P&L")
        else:
            report.append(f"\n❌ TOP GAINERS MISSED")
            report.append("-" * 50)
            report.append("None of today's top gainers were captured by any account:")
            for symbol, gain in self.top_gainers_today.items():
                report.append(f"   ❌ {symbol} +{gain:.1f}%")
        
        # Detailed order analysis
        if all_orders:
            report.append(f"\n📋 DETAILED ORDER ANALYSIS")
            report.append("-" * 50)
            
            orders_df = pd.DataFrame(all_orders)
            filled_orders = orders_df[orders_df['status'] == 'filled']
            
            if not filled_orders.empty:
                # Group by account
                for account in filled_orders['account'].unique():
                    account_orders = filled_orders[filled_orders['account'] == account]
                    report.append(f"\n{account} ({len(account_orders)} orders):")
                    
                    for _, order in account_orders.iterrows():
                        side_emoji = "🟢" if order['side'] == 'buy' else "🔴"
                        fill_time = order['filled_time_est'].strftime('%H:%M:%S') if pd.notna(order.get('filled_time_est')) else 'N/A'
                        report.append(f"   {side_emoji} {order['symbol']}: {order['side']} {order['filled_qty']} @ ${order['filled_avg_price']:.2f} at {fill_time}")
        
        # System logs from Supabase
        if supabase_logs:
            report.append(f"\n🗃️ SYSTEM TRADE LOGS ({len(supabase_logs)} entries)")
            report.append("-" * 50)
            
            for log in supabase_logs[-10:]:  # Last 10 logs
                timestamp = pd.to_datetime(log['timestamp']).strftime('%H:%M:%S')
                report.append(f"   {timestamp}: {log.get('ticker', 'N/A')} - {log.get('action', 'N/A')} - {log.get('account_name', 'N/A')}")
        
        return "\n".join(report)

def main():
    """Main execution function"""
    print("🚀 Starting Trading Analysis...")
    
    analyzer = TradingAnalyzer()
    report = analyzer.generate_comprehensive_report()
    
    print(report)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trading_analysis_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"\n💾 Report saved to: {filename}")
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()