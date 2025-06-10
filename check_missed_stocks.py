#!/opt/homebrew/bin/python3.12

import os
import sys
from datetime import datetime, timedelta
from supabase import create_client

def load_environment():
    """Load environment variables from the_end/.env file"""
    env_file = os.path.join(os.path.dirname(__file__), 'the_end', '.env')
    env_vars = {}
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
        return env_vars
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return {}

def main():
    print("🔍 Checking SystemX for High-Performing Stocks")
    print("=" * 60)
    
    # Load environment
    env_vars = load_environment()
    if not env_vars.get('SUPABASE_URL'):
        print("❌ Failed to load environment variables")
        return
    
    # Initialize Supabase
    try:
        supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
        print("✅ Supabase connection established")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return
    
    # Check for the high-performing stocks
    tickers = ['NA', 'KLTO', 'KNW']
    yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')  # Check last 2 days
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n🎯 Target stocks: {', '.join(tickers)}")
    print(f"📅 Date range: {yesterday} to {today}")
    print()
    
    # Check analyzed_stocks table
    print("📊 ANALYZED_STOCKS TABLE:")
    print("-" * 50)
    for ticker in tickers:
        try:
            result = supabase.table('analyzed_stocks').select('*').eq('ticker', ticker).gte('created_at', yesterday).execute()
            if result.data:
                for stock in result.data:
                    dts = stock.get('dts_score', 'N/A')
                    created = stock.get('created_at', 'N/A')[:19] if stock.get('created_at') else 'N/A'
                    squeeze = stock.get('squeeze_momentum', 'N/A')
                    trend = stock.get('trend_strength', 'N/A')
                    print(f"✅ {ticker}: DTS={dts}, Squeeze={squeeze}, Trend={trend}, Created={created}")
            else:
                print(f"❌ {ticker}: NOT FOUND in analyzed_stocks")
        except Exception as e:
            print(f"❌ {ticker}: Error querying - {e}")
    
    print("\n📈 V9_MULTI_SOURCE_ANALYSIS TABLE:")
    print("-" * 50)
    for ticker in tickers:
        try:
            result = supabase.table('v9_multi_source_analysis').select('*').eq('ticker', ticker).gte('created_at', yesterday).execute()
            if result.data:
                for analysis in result.data:
                    v9_score = analysis.get('v9_score', 'N/A')
                    created = analysis.get('created_at', 'N/A')[:19] if analysis.get('created_at') else 'N/A'
                    analysis_preview = analysis.get('analysis', 'N/A')[:100] if analysis.get('analysis') else 'N/A'
                    print(f"✅ {ticker}: V9={v9_score}, Created={created}")
                    print(f"   Analysis: {analysis_preview}...")
            else:
                print(f"❌ {ticker}: NOT FOUND in v9_multi_source_analysis")
        except Exception as e:
            print(f"❌ {ticker}: Error querying - {e}")
    
    print("\n🎯 ALL RECENT HIGH-SCORING STOCKS (DTS >= 80):")
    print("-" * 50)
    try:
        result = supabase.table('analyzed_stocks').select('ticker, dts_score, squeeze_momentum, trend_strength, created_at').gte('dts_score', 80).gte('created_at', yesterday).order('dts_score', desc=True).limit(10).execute()
        if result.data:
            for stock in result.data:
                ticker = stock['ticker']
                dts = stock['dts_score']
                squeeze = stock.get('squeeze_momentum', 'N/A')
                trend = stock.get('trend_strength', 'N/A')
                created = stock['created_at'][:19]
                print(f"📈 {ticker}: DTS={dts}, Squeeze={squeeze}, Trend={trend}, Created={created}")
        else:
            print("❌ NO HIGH-SCORING STOCKS FOUND (DTS >= 80)")
    except Exception as e:
        print(f"❌ Error querying high-scoring stocks: {e}")
    
    print("\n🔥 ALL RECENT V9B HIGH-SCORING STOCKS (V9 >= 85):")
    print("-" * 50)
    try:
        result = supabase.table('v9_multi_source_analysis').select('ticker, v9_score, created_at').gte('v9_score', 85).gte('created_at', yesterday).order('v9_score', desc=True).limit(10).execute()
        if result.data:
            for stock in result.data:
                ticker = stock['ticker']
                v9_score = stock['v9_score']
                created = stock['created_at'][:19]
                print(f"🔥 {ticker}: V9={v9_score}, Created={created}")
        else:
            print("❌ NO HIGH V9B SCORING STOCKS FOUND (V9 >= 85)")
    except Exception as e:
        print(f"❌ Error querying high V9B stocks: {e}")
    
    print("\n🔍 CHECKING TOTAL STOCK COVERAGE:")
    print("-" * 50)
    try:
        # Count total stocks analyzed today
        analyzed_today = supabase.table('analyzed_stocks').select('ticker', count='exact').gte('created_at', today).execute()
        v9_today = supabase.table('v9_multi_source_analysis').select('ticker', count='exact').gte('created_at', today).execute()
        
        print(f"📊 Stocks analyzed today: {analyzed_today.count if analyzed_today.count else 0}")
        print(f"📈 V9B analyses today: {v9_today.count if v9_today.count else 0}")
        
        # Check if any stocks were added in the last hour
        last_hour = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        recent_analyzed = supabase.table('analyzed_stocks').select('ticker').gte('created_at', last_hour).execute()
        recent_v9 = supabase.table('v9_multi_source_analysis').select('ticker').gte('created_at', last_hour).execute()
        
        print(f"⏰ Stocks analyzed last hour: {len(recent_analyzed.data) if recent_analyzed.data else 0}")
        print(f"⏰ V9B analyses last hour: {len(recent_v9.data) if recent_v9.data else 0}")
        
    except Exception as e:
        print(f"❌ Error checking coverage: {e}")

if __name__ == "__main__":
    main()