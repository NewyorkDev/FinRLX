#!/usr/bin/env python3
"""Test Supabase connection and examine stock data tables"""

import os
import sys
from datetime import datetime
import pandas as pd

# Try to import supabase with fallback installation
try:
    from supabase import create_client, Client
except ImportError:
    print("Installing supabase...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
    from supabase import create_client, Client

def test_supabase_connection():
    """Test connection to Supabase and examine V9B stock data"""
    
    # Load environment variables from .env file
    env_file = "/Users/francisclase/FinRLX/the_end/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found!")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connection established")
        
        # Test connection by listing tables
        print("\n📊 Examining V9B data tables...")
        
        # Check v9_scraped_stocks table
        try:
            stocks_response = supabase.table('v9_scraped_stocks').select('*').limit(5).execute()
            if stocks_response.data:
                print(f"✅ v9_scraped_stocks: {len(stocks_response.data)} sample records")
                for stock in stocks_response.data[:3]:
                    print(f"   - {stock.get('ticker', 'N/A')}: ${stock.get('price', 'N/A')} (Volume: {stock.get('volume', 'N/A')})")
            else:
                print("⚠️ v9_scraped_stocks: No data found")
        except Exception as e:
            print(f"❌ v9_scraped_stocks error: {e}")
        
        # Check v9_multi_source_analysis table
        try:
            analysis_response = supabase.table('v9_multi_source_analysis').select('*').limit(5).execute()
            if analysis_response.data:
                print(f"✅ v9_multi_source_analysis: {len(analysis_response.data)} sample records")
                for analysis in analysis_response.data[:3]:
                    print(f"   - {analysis.get('ticker', 'N/A')}: DTS Score: {analysis.get('dts_score', 'N/A')}")
            else:
                print("⚠️ v9_multi_source_analysis: No data found")
        except Exception as e:
            print(f"❌ v9_multi_source_analysis error: {e}")
        
        # Check analyzed_stocks table for qualified trading candidates
        try:
            qualified_response = supabase.table('analyzed_stocks').select('*').eq('dts_qualification', 'qualified').execute()
            if qualified_response.data:
                print(f"✅ qualified stocks for trading: {len(qualified_response.data)} candidates")
                for stock in qualified_response.data[:5]:
                    print(f"   - {stock.get('ticker', 'N/A')}: DTS {stock.get('dts_score', 'N/A')} ({stock.get('dts_momentum_grade', 'N/A')})")
            else:
                print("⚠️ No qualified stocks found in analyzed_stocks table")
        except Exception as e:
            print(f"❌ analyzed_stocks error: {e}")
        
        # Get latest session data
        try:
            session_response = supabase.table('v9_session_metadata').select('*').order('created_at', desc=True).limit(1).execute()
            if session_response.data:
                latest_session = session_response.data[0]
                print(f"✅ Latest V9B session: {latest_session.get('session_id', 'N/A')}")
                print(f"   - Analysis Type: {latest_session.get('analysis_type', 'N/A')}")
                print(f"   - Total Cost: ${latest_session.get('total_cost', 'N/A')}")
            else:
                print("⚠️ No session metadata found")
        except Exception as e:
            print(f"❌ v9_session_metadata error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def get_trading_candidates():
    """Get qualified stocks for day trading from Supabase"""
    
    # Load environment variables
    env_file = "/Users/francisclase/FinRLX/the_end/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get all qualified stocks with high DTS scores
        response = supabase.table('analyzed_stocks').select(
            'ticker, dts_score, dts_qualification, dts_momentum_grade, dts_risk_level'
        ).gte('dts_score', 50).order('dts_score', desc=True).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            print(f"\n🎯 Top trading candidates ({len(df)} stocks):")
            print(df.head(10).to_string(index=False))
            return df['ticker'].tolist()[:10]  # Return top 10 candidates
        else:
            print("No trading candidates found")
            return []
            
    except Exception as e:
        print(f"Error getting trading candidates: {e}")
        return []

if __name__ == "__main__":
    print("🔍 Testing Supabase connection and V9B data...")
    
    if test_supabase_connection():
        print("\n" + "="*50)
        candidates = get_trading_candidates()
        if candidates:
            print(f"\n✅ Ready for trading with {len(candidates)} qualified stocks")
            print(f"Top candidates: {', '.join(candidates[:5])}")
        else:
            print("\n⚠️ No qualified trading candidates found")
    else:
        print("\n❌ Failed to connect to Supabase")