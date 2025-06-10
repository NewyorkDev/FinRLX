#!/opt/homebrew/bin/python3.12
"""
CHECK V9B SCORES - Find broken V9B scores causing urgent alerts
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

def check_v9b_scores():
    """Check for broken V9B scores (< 5.0) causing urgent alerts"""
    print("🔍 CHECKING V9B SCORES FOR URGENT ISSUES")
    print("=" * 60)
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Check last 4 hours (same as health monitor)
    cutoff_time = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"📅 Checking V9B scores since: {cutoff_time}")
    
    try:
        # Same query as health monitor
        v9b_result = supabase.table('v9_multi_source_analysis').select(
            'ticker, v9_combined_score, dts_score, created_at'
        ).gte('created_at', cutoff_time).execute()
        
        if v9b_result.data:
            print(f"📊 Total V9B records (4h): {len(v9b_result.data)}")
            
            broken_v9b_scores = []
            low_scores = []
            good_scores = []
            
            for item in v9b_result.data:
                ticker = item.get('ticker', 'UNKNOWN')
                v9b_score = item.get('v9_combined_score', 0)
                dts_score = item.get('dts_score')
                created = item.get('created_at', 'N/A')[:16]
                
                if v9b_score and v9b_score < 5.0:
                    broken_v9b_scores.append({
                        'ticker': ticker,
                        'v9b_score': v9b_score,
                        'dts_score': dts_score,
                        'created': created
                    })
                elif v9b_score and v9b_score < 7.5:
                    low_scores.append({
                        'ticker': ticker,
                        'v9b_score': v9b_score,
                        'dts_score': dts_score,
                        'created': created
                    })
                else:
                    good_scores.append({
                        'ticker': ticker,
                        'v9b_score': v9b_score,
                        'dts_score': dts_score,
                        'created': created
                    })
            
            print(f"🚨 URGENT ISSUES (V9B < 5.0): {len(broken_v9b_scores)}")
            print(f"⚠️ Low V9B scores (5.0-7.5): {len(low_scores)}")
            print(f"✅ Good V9B scores (≥7.5): {len(good_scores)}")
            
            if broken_v9b_scores:
                print("\n🚨 URGENT ISSUES DETECTED (causing health alerts):")
                for item in broken_v9b_scores:
                    print(f"   {item['ticker']}: V9B={item['v9b_score']}, DTS={item['dts_score']}, Time={item['created']}")
            
            if low_scores:
                print("\n⚠️ LOW V9B SCORES:")
                for item in low_scores[:5]:
                    print(f"   {item['ticker']}: V9B={item['v9b_score']}, DTS={item['dts_score']}, Time={item['created']}")
            
            if good_scores:
                print("\n✅ GOOD V9B SCORES:")
                for item in good_scores[:5]:
                    print(f"   {item['ticker']}: V9B={item['v9b_score']}, DTS={item['dts_score']}, Time={item['created']}")
                    
            return len(broken_v9b_scores)
        else:
            print("📭 No V9B records found")
            return 0
            
    except Exception as e:
        print(f"❌ Error checking V9B scores: {e}")
        return -1

def main():
    broken_count = check_v9b_scores()
    
    if broken_count > 0:
        print(f"\n🚨 FOUND ROOT CAUSE: {broken_count} broken V9B scores (< 5.0)")
        print("💡 These are triggering the 'URGENT DTS PROBLEMS DETECTED' alerts")
        print("🔧 Need to fix V9B score scaling or filter out low scores")
    elif broken_count == 0:
        print("\n✅ No broken V9B scores found")
        print("🤔 Health monitor alerts may be delayed or caching old data")
    else:
        print("\n❌ Error occurred during analysis")
    
    return broken_count

if __name__ == "__main__":
    main()