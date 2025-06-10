#!/usr/bin/env python3
"""
Supabase Stock Checker for System X Trading System
==================================================

This script checks the Supabase database for available stocks in the System X trading system.
It examines both 'analyzed_stocks' and 'v9_multi_source_analysis' tables to show what stocks
are currently available for trading.

Usage:
    python check_supabase_stocks.py [--min-dts-score N] [--debug]

Requirements:
    - supabase-py library: pip install supabase
    - Environment variables in the_end/.env file

Author: System X Trading Bot
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Error: supabase-py library not installed")
    print("Install with: pip install supabase")
    sys.exit(1)


class SupabaseStockChecker:
    """Check Supabase database for available trading stocks"""
    
    def __init__(self, min_dts_score: float = 65.0, debug: bool = False):
        self.min_dts_score = min_dts_score
        self.debug = debug
        self.supabase: Optional[Client] = None
        
        # Load environment variables from the_end/.env
        self.load_environment()
        
        # Setup Supabase connection
        self.setup_supabase()
    
    def load_environment(self) -> None:
        """Load environment variables from the_end/.env file"""
        try:
            # Get script directory and construct path to .env file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            env_file = os.path.join(script_dir, 'the_end', '.env')
            
            if not os.path.exists(env_file):
                print(f"❌ Environment file not found: {env_file}")
                sys.exit(1)
            
            print(f"📂 Loading environment from: {env_file}")
            
            # Parse .env file manually (avoiding dependency on python-dotenv)
            with open(env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
                        except ValueError:
                            if self.debug:
                                print(f"⚠️ Skipping malformed line {line_num}: {line}")
            
            # Verify required environment variables
            required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
                sys.exit(1)
                
            print("✅ Environment variables loaded successfully")
            
        except Exception as e:
            print(f"❌ Error loading environment: {e}")
            sys.exit(1)
    
    def setup_supabase(self) -> None:
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not supabase_url or not supabase_key:
                print("❌ Supabase credentials not found in environment")
                sys.exit(1)
            
            self.supabase = create_client(supabase_url, supabase_key)
            
            # Test connection
            test_response = self.supabase.table('v9_session_metadata').select('count').limit(1).execute()
            print("✅ Supabase connection established")
            
        except Exception as e:
            print(f"❌ Error connecting to Supabase: {e}")
            if self.debug:
                traceback.print_exc()
            sys.exit(1)
    
    def check_table_availability(self) -> Dict[str, bool]:
        """Check which tables are available in the database"""
        tables_status = {}
        test_tables = ['analyzed_stocks', 'v9_multi_source_analysis', 'v9_session_metadata']
        
        print("\n🔍 Checking table availability...")
        
        for table in test_tables:
            try:
                self.supabase.table(table).select('count').limit(1).execute()
                tables_status[table] = True
                print(f"   ✅ {table}")
            except Exception as e:
                tables_status[table] = False
                print(f"   ❌ {table} - {e}")
                if self.debug:
                    print(f"      Debug: {traceback.format_exc()}")
        
        return tables_status
    
    def get_analyzed_stocks(self) -> List[Dict]:
        """Get qualified stocks from analyzed_stocks table"""
        try:
            print(f"\n📊 Querying analyzed_stocks table (DTS score >= {self.min_dts_score})...")
            
            response = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification, squeeze_score, trend_score, '
                'position_size_actual, created_at'
            ).gte('dts_score', self.min_dts_score).order('dts_score', desc=True).limit(50).execute()
            
            qualified_stocks = []
            
            if response.data:
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    
                    # Apply same filters as System X
                    if (ticker and 
                        not ticker.startswith('TEST') and 
                        len(ticker) <= 5 and 
                        ticker.isalpha() and
                        stock.get('dts_score', 0) >= self.min_dts_score):
                        
                        qualified_stocks.append({
                            'ticker': ticker,
                            'dts_score': stock.get('dts_score', 0),
                            'dts_qualification': stock.get('dts_qualification', ''),
                            'squeeze_score': stock.get('squeeze_score', 0),
                            'trend_score': stock.get('trend_score', 0),
                            'position_size': stock.get('position_size_actual', 0),
                            'created_at': stock.get('created_at', ''),
                            'updated_at': stock.get('created_at', ''),
                            'source': 'analyzed_stocks'
                        })
            
            print(f"   Found {len(qualified_stocks)} qualified stocks")
            return qualified_stocks
            
        except Exception as e:
            print(f"❌ Error querying analyzed_stocks: {e}")
            if self.debug:
                traceback.print_exc()
            return []
    
    def get_v9_analysis_stocks(self) -> List[Dict]:
        """Get recent stocks from v9_multi_source_analysis table"""
        try:
            # Get analysis from last 7 days
            cutoff_time = (datetime.now() - timedelta(days=7)).isoformat()
            
            print(f"\n📈 Querying v9_multi_source_analysis table (last 7 days, score >= 7.0)...")
            
            response = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, v9_combined_score, squeeze_confidence_score, trend_confidence_score, '
                'claude_analysis, created_at, technical_data'
            ).gte('created_at', cutoff_time).gte('v9_combined_score', 7.0).order(
                'v9_combined_score', desc=True
            ).limit(50).execute()
            
            analysis_stocks = []
            
            if response.data:
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    
                    # Apply same filters as System X
                    if (ticker and 
                        not ticker.startswith('TEST') and 
                        len(ticker) <= 5 and 
                        ticker.isalpha() and
                        stock.get('v9_combined_score', 0) >= 7.0):
                        
                        # Convert V9B score to estimated DTS score for consistency
                        estimated_dts = min(75, max(60, stock.get('v9_combined_score', 0) * 8))
                        
                        analysis_stocks.append({
                            'ticker': ticker,
                            'v9_combined_score': stock.get('v9_combined_score', 0),
                            'estimated_dts_score': estimated_dts,
                            'squeeze_confidence': stock.get('squeeze_confidence_score', 0),
                            'trend_confidence': stock.get('trend_confidence_score', 0),
                            'claude_analysis': stock.get('claude_analysis', '')[:100] + '...' if stock.get('claude_analysis') else '',
                            'analysis_timestamp': stock.get('created_at', ''),
                            'source': 'v9_multi_source_analysis'
                        })
            
            print(f"   Found {len(analysis_stocks)} recent analysis entries")
            return analysis_stocks
            
        except Exception as e:
            print(f"❌ Error querying v9_multi_source_analysis: {e}")
            if self.debug:
                traceback.print_exc()
            return []
    
    def display_stocks(self, analyzed_stocks: List[Dict], analysis_stocks: List[Dict]) -> None:
        """Display the available stocks in a formatted way"""
        print("\n" + "="*80)
        print("📋 AVAILABLE STOCKS FOR SYSTEM X TRADING")
        print("="*80)
        
        # Display analyzed_stocks
        if analyzed_stocks:
            print(f"\n🎯 QUALIFIED STOCKS FROM 'analyzed_stocks' table ({len(analyzed_stocks)} stocks):")
            print("-" * 75)
            print(f"{'Ticker':<8} {'DTS':<6} {'Squeeze':<8} {'Trend':<6} {'Position':<8} {'Qualification':<15}")
            print("-" * 75)
            
            for stock in analyzed_stocks[:15]:  # Show top 15
                ticker = stock['ticker'] or 'N/A'
                dts = stock['dts_score'] or 0
                squeeze = stock['squeeze_score'] or 0
                trend = stock['trend_score'] or 0
                position = stock['position_size'] or 0
                qual = stock['dts_qualification'][:12] if stock['dts_qualification'] else 'N/A'
                
                print(f"{ticker:<8} {dts:<6.1f} {squeeze:<8.1f} {trend:<6.1f} {position:<8.3f} {qual:<15}")
        else:
            print("\n❌ No qualified stocks found in 'analyzed_stocks' table")
        
        # Display v9_multi_source_analysis stocks
        if analysis_stocks:
            print(f"\n📊 RECENT ANALYSIS FROM 'v9_multi_source_analysis' table ({len(analysis_stocks)} stocks):")
            print("-" * 85)
            print(f"{'Ticker':<8} {'V9 Score':<9} {'Est DTS':<8} {'Squeeze':<8} {'Trend':<6} {'Analysis Preview':<30}")
            print("-" * 85)
            
            for stock in analysis_stocks[:15]:  # Show top 15
                ticker = stock['ticker'] or 'N/A'
                v9_score = stock['v9_combined_score'] or 0
                est_dts = stock['estimated_dts_score'] or 0
                squeeze = stock['squeeze_confidence'] or 0
                trend = stock['trend_confidence'] or 0
                analysis = stock['claude_analysis'][:25] if stock['claude_analysis'] else 'N/A'
                
                print(f"{ticker:<8} {v9_score:<9.1f} {est_dts:<8.1f} {squeeze:<8.1f} {trend:<6.1f} {analysis:<30}")
        else:
            print("\n❌ No recent analysis found in 'v9_multi_source_analysis' table")
        
        # Summary
        total_unique_tickers = len(set([s['ticker'] for s in analyzed_stocks] + [s['ticker'] for s in analysis_stocks]))
        print(f"\n📈 SUMMARY:")
        print(f"   • Total qualified stocks (analyzed_stocks): {len(analyzed_stocks)}")
        print(f"   • Total recent analysis entries: {len(analysis_stocks)}")
        print(f"   • Unique tickers across both tables: {total_unique_tickers}")
        print(f"   • Minimum DTS score filter: {self.min_dts_score}")
        
        if total_unique_tickers == 0:
            print("\n⚠️  No trading opportunities found!")
            print("   Possible reasons:")
            print("   • DTS score threshold too high")
            print("   • No recent market analysis")
            print("   • Database needs updating")
            print("   • All stocks filtered out (TEST tickers, invalid formats)")
    
    def run_check(self) -> None:
        """Run the complete stock availability check"""
        print("🚀 Starting Supabase Stock Availability Check for System X")
        print(f"⚙️  Minimum DTS Score: {self.min_dts_score}")
        print(f"🐛 Debug Mode: {'ON' if self.debug else 'OFF'}")
        
        # Check table availability
        tables_status = self.check_table_availability()
        
        if not any(tables_status.values()):
            print("\n❌ No accessible tables found. Cannot proceed.")
            return
        
        # Get stocks from both tables
        analyzed_stocks = []
        analysis_stocks = []
        
        if tables_status.get('analyzed_stocks', False):
            analyzed_stocks = self.get_analyzed_stocks()
        
        if tables_status.get('v9_multi_source_analysis', False):
            analysis_stocks = self.get_v9_analysis_stocks()
        
        # Display results
        self.display_stocks(analyzed_stocks, analysis_stocks)
        
        print(f"\n✅ Check completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Check Supabase database for available stocks in System X trading system"
    )
    parser.add_argument(
        '--min-dts-score', 
        type=float, 
        default=65.0,
        help='Minimum DTS score threshold (default: 65.0)'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    try:
        checker = SupabaseStockChecker(
            min_dts_score=args.min_dts_score,
            debug=args.debug
        )
        checker.run_check()
        
    except KeyboardInterrupt:
        print("\n🛑 Check interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()