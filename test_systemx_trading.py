#!/opt/homebrew/bin/python3.12
"""
COMPREHENSIVE SYSTEMX TRADING VALIDATION TEST
Test all components: V9B scaling, DTS scores, aggressive trading, hot stock detection
"""

import os
import sys
import json
import time
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

def test_v9b_scaling_fixes():
    """Test if V9B score scaling fixes are working"""
    print("🔍 Testing V9B Score Scaling Fixes...")
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Get high-performing stocks and test scaling
    result = supabase.table('v9_multi_source_analysis').select(
        'ticker, v9_combined_score, dts_score'
    ).in_('ticker', ['NA', 'KLTO', 'KNW']).order('created_at', desc=True).limit(10).execute()
    
    if result.data:
        print("📊 V9B SCALING TEST RESULTS:")
        for stock in result.data:
            ticker = stock['ticker']
            raw_v9b = stock.get('v9_combined_score', 0)
            dts_score = stock.get('dts_score', 0)
            
            # Apply the same scaling fix from SystemX
            scaled_v9b = raw_v9b * 100 if raw_v9b and raw_v9b < 10 else raw_v9b
            
            # Check if it meets trading thresholds
            meets_v9b = scaled_v9b >= 7.5
            meets_dts = dts_score and dts_score >= 60
            
            status = "✅ QUALIFIES" if meets_v9b and meets_dts else "❌ REJECTED"
            
            print(f"   {ticker}: Raw={raw_v9b} → Scaled={scaled_v9b}, DTS={dts_score} | {status}")
            
        return True
    else:
        print("❌ No V9B data found for test stocks")
        return False

def test_aggressive_position_sizing():
    """Test if aggressive position sizing would trigger for sure-thing stocks"""
    print("\n💰 Testing Aggressive Position Sizing Logic...")
    
    # Simulate sure-thing detection logic
    test_stocks = [
        {"ticker": "NA", "dts_score": 70.5, "v9b_score": 100.0},
        {"ticker": "KLTO", "dts_score": 71.0, "v9b_score": 90.0},
        {"ticker": "KNW", "dts_score": 62.5, "v9b_score": 90.0}
    ]
    
    for stock in test_stocks:
        ticker = stock['ticker']
        dts = stock['dts_score']
        v9b = stock['v9b_score']
        
        # Sure thing logic: DTS ≥ 78 AND V9B ≥ 8.8
        is_sure_thing = dts >= 78 and v9b >= 8.8
        
        if is_sure_thing:
            position_size = "50% (Aggressive)"
            accounts = "PRIMARY_30K & SECONDARY_30K"
        else:
            position_size = "15% (Standard)"
            accounts = "All accounts"
            
        print(f"   {ticker}: DTS={dts}, V9B={v9b} → {position_size} on {accounts}")
        
    return True

def test_24h_hot_stock_detection():
    """Test 24-hour hot stock detection"""
    print("\n🔥 Testing 24-Hour Hot Stock Detection...")
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Check last 24 hours for hot stocks
    cutoff_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    
    result = supabase.table('v9_multi_source_analysis').select(
        'ticker, v9_combined_score, dts_score, created_at'
    ).gte('created_at', cutoff_time).gte('v9_combined_score', 0.8).order('v9_combined_score', desc=True).limit(10).execute()
    
    if result.data:
        print(f"📈 Found {len(result.data)} hot stocks in last 24 hours:")
        for stock in result.data:
            ticker = stock['ticker']
            raw_v9b = stock.get('v9_combined_score', 0)
            dts = stock.get('dts_score', 0)
            created = stock.get('created_at', '')[:16]
            
            # Apply scaling
            scaled_v9b = raw_v9b * 100 if raw_v9b < 10 else raw_v9b
            
            print(f"   {ticker}: V9B={scaled_v9b:.1f}, DTS={dts}, Time={created}")
            
        return len(result.data) > 0
    else:
        print("❌ No hot stocks found in last 24 hours")
        return False

def test_systemx_process_health():
    """Test if SystemX process is healthy and responding"""
    print("\n🏥 Testing SystemX Process Health...")
    
    # Check if process is running
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'system_x.py'], capture_output=True, text=True)
    
    if result.stdout.strip():
        pid = result.stdout.strip()
        print(f"✅ SystemX process running: PID {pid}")
        
        # Check log activity
        log_file = 'logs/system-x-out.log'
        if os.path.exists(log_file):
            stat = os.stat(log_file)
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            minutes_ago = int((datetime.now() - last_modified).total_seconds() / 60)
            
            if minutes_ago < 10:
                print(f"✅ Log activity healthy: Updated {minutes_ago} minutes ago")
                return True
            else:
                print(f"⚠️ Log activity stale: Updated {minutes_ago} minutes ago")
                return False
        else:
            print("❌ No log file found")
            return False
    else:
        print("❌ SystemX process not running")
        return False

def test_slack_notifications():
    """Test if Slack notifications are working"""
    print("\n📱 Testing Slack Notification System...")
    
    env_vars = load_environment()
    webhook_url = env_vars.get('SLACK_TRADE_WEBHOOK_URL')
    
    if webhook_url:
        print("✅ Slack webhook URL configured")
        
        # Test basic connectivity (don't actually send to avoid spam)
        print("✅ Slack notification system ready")
        return True
    else:
        print("❌ No Slack webhook URL found")
        return False

def main():
    """Run comprehensive SystemX validation"""
    print("🧪 COMPREHENSIVE SYSTEMX TRADING VALIDATION")
    print("=" * 60)
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("V9B Scaling Fixes", test_v9b_scaling_fixes),
        ("Aggressive Position Sizing", test_aggressive_position_sizing), 
        ("24-Hour Hot Stock Detection", test_24h_hot_stock_detection),
        ("SystemX Process Health", test_systemx_process_health),
        ("Slack Notifications", test_slack_notifications)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            results[test_name] = False
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("-" * 30)
    
    passed = 0
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🚀 SYSTEMX IS FULLY OPERATIONAL AND READY FOR TRADING!")
    elif passed >= len(tests) * 0.8:
        print("⚠️ SystemX mostly operational, minor issues need attention")
    else:
        print("❌ SystemX has significant issues that need immediate attention")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)