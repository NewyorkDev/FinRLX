#!/opt/homebrew/bin/python3.12
"""
INVESTIGATE DTS ISSUES - Deep dive into current DTS problems
"""

import os
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

def investigate_dts_problems():
    """Investigate exactly what DTS problems the health monitor is finding"""
    print("🔍 INVESTIGATING DTS PROBLEMS")
    print("=" * 60)
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Get 4-hour cutoff (same as health monitor)
    cutoff_4h = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"📅 Checking data since: {cutoff_4h}")
    
    print("\n1️⃣ ANALYZED_STOCKS TABLE (4-hour window):")
    print("-" * 40)
    
    # Check analyzed_stocks for NULL DTS issues (same query as health monitor)
    try:
        analyzed_result = supabase.table('analyzed_stocks').select(
            'ticker, dts_score, squeeze_score, trend_score, created_at'
        ).gte('created_at', cutoff_4h).execute()
        
        if analyzed_result.data:
            null_dts = [r for r in analyzed_result.data if r.get('dts_score') is None]
            valid_dts = [r for r in analyzed_result.data if r.get('dts_score') is not None]
            
            print(f"📊 Total records (4h): {len(analyzed_result.data)}")
            print(f"❌ NULL DTS scores: {len(null_dts)}")
            print(f"✅ Valid DTS scores: {len(valid_dts)}")
            
            if null_dts:
                print("\n🚨 NULL DTS EXAMPLES:")
                for record in null_dts[:5]:
                    ticker = record.get('ticker', 'N/A')
                    created = record.get('created_at', 'N/A')[:16]
                    squeeze = record.get('squeeze_score', 'N/A')
                    trend = record.get('trend_score', 'N/A')
                    print(f"   {ticker}: DTS=NULL, Squeeze={squeeze}, Trend={trend}, Time={created}")
            
            if valid_dts:
                print("\n✅ VALID DTS EXAMPLES:")
                for record in valid_dts[:5]:
                    ticker = record.get('ticker', 'N/A')
                    dts = record.get('dts_score', 'N/A')
                    created = record.get('created_at', 'N/A')[:16]
                    print(f"   {ticker}: DTS={dts}, Time={created}")
        else:
            print("📭 No records found in analyzed_stocks (4h)")
            
    except Exception as e:
        print(f"❌ Error querying analyzed_stocks: {e}")
    
    print("\n2️⃣ V9_MULTI_SOURCE_ANALYSIS TABLE (4-hour window):")
    print("-" * 50)
    
    # Check v9_multi_source_analysis for available DTS data
    try:
        v9_result = supabase.table('v9_multi_source_analysis').select(
            'ticker, v9_combined_score, dts_score, created_at'
        ).gte('created_at', cutoff_4h).execute()
        
        if v9_result.data:
            null_dts = [r for r in v9_result.data if r.get('dts_score') is None]
            valid_dts = [r for r in v9_result.data if r.get('dts_score') is not None]
            
            print(f"📊 Total records (4h): {len(v9_result.data)}")
            print(f"❌ NULL DTS scores: {len(null_dts)}")
            print(f"✅ Valid DTS scores: {len(valid_dts)}")
            
            if valid_dts:
                print("\n✅ AVAILABLE DTS DATA:")
                for record in valid_dts[:10]:
                    ticker = record.get('ticker', 'N/A')
                    dts = record.get('dts_score', 'N/A')
                    v9b = record.get('v9_combined_score', 'N/A')
                    created = record.get('created_at', 'N/A')[:16]
                    print(f"   {ticker}: DTS={dts}, V9B={v9b}, Time={created}")
        else:
            print("📭 No records found in v9_multi_source_analysis (4h)")
            
    except Exception as e:
        print(f"❌ Error querying v9_multi_source_analysis: {e}")
    
    print("\n3️⃣ SYNC GAP ANALYSIS:")
    print("-" * 25)
    
    # Find tickers that exist in v9_multi_source_analysis but not analyzed_stocks
    try:
        if analyzed_result.data and v9_result.data:
            analyzed_tickers = {r['ticker'] for r in analyzed_result.data if r.get('dts_score') is not None}
            v9_tickers = {r['ticker'] for r in v9_result.data if r.get('dts_score') is not None}
            
            missing_in_analyzed = v9_tickers - analyzed_tickers
            print(f"🔄 Tickers with DTS in v9 but missing/NULL in analyzed: {len(missing_in_analyzed)}")
            
            if missing_in_analyzed:
                print("📋 MISSING TICKERS:")
                for ticker in list(missing_in_analyzed)[:10]:
                    print(f"   {ticker}")
                    
    except Exception as e:
        print(f"❌ Error in sync gap analysis: {e}")
    
    print("\n4️⃣ QUALIFICATION STATUS:")
    print("-" * 28)
    
    # Check qualification status (DTS >= 70)
    try:
        qualified_result = supabase.table('analyzed_stocks').select(
            'ticker, dts_score, squeeze_score'
        ).gte('dts_score', 70.0).order('dts_score', desc=True).limit(10).execute()
        
        if qualified_result.data:
            print(f"🎯 Qualified stocks (DTS ≥ 70): {len(qualified_result.data)}")
            for stock in qualified_result.data:
                ticker = stock['ticker']
                dts = stock['dts_score']
                squeeze = stock.get('squeeze_score', 'N/A')
                print(f"   {ticker}: DTS={dts}, Squeeze={squeeze}")
        else:
            print("❌ No qualified stocks found")
            
    except Exception as e:
        print(f"❌ Error checking qualification: {e}")

def main():
    investigate_dts_problems()

if __name__ == "__main__":
    main()