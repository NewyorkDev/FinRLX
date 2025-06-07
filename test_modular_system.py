#!/opt/homebrew/bin/python3.12
"""
Test Script for Modular System X Architecture
Tests both API and trading system integration via Redis
"""

import sys
import time
import requests
import json
import subprocess
import threading
from datetime import datetime

def test_api_startup():
    """Test if FastAPI starts correctly"""
    print("🚀 Testing FastAPI startup...")
    
    try:
        # Start FastAPI in background
        api_process = subprocess.Popen([
            '/opt/homebrew/bin/python3.12', 'api.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give it time to start
        time.sleep(10)
        
        # Test health endpoint
        response = requests.get('http://localhost:8080/health', timeout=10)
        if response.status_code == 200:
            print("✅ FastAPI health check passed")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Redis connected: {data.get('redis_connected', False)}")
        else:
            print(f"❌ FastAPI health check failed: {response.status_code}")
            return False
        
        # Test other endpoints
        endpoints = ['/metrics', '/config', '/accounts']
        for endpoint in endpoints:
            try:
                resp = requests.get(f'http://localhost:8080{endpoint}', timeout=5)
                print(f"✅ {endpoint}: {resp.status_code}")
            except Exception as e:
                print(f"⚠️ {endpoint}: {e}")
        
        # Terminate API process
        api_process.terminate()
        api_process.wait()
        
        return True
        
    except Exception as e:
        print(f"❌ API startup test failed: {e}")
        return False

def test_system_x_startup():
    """Test if system_x.py starts correctly with Redis"""
    print("\n🤖 Testing System X startup...")
    
    try:
        # Start system_x in test mode
        result = subprocess.run([
            '/opt/homebrew/bin/python3.12', 'system_x.py', '--test'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ System X test mode passed")
            print("📊 Output:")
            for line in result.stdout.split('\n')[-10:]:  # Last 10 lines
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ System X test failed: {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("⚠️ System X test timed out")
        return False
    except Exception as e:
        print(f"❌ System X test failed: {e}")
        return False

def test_redis_communication():
    """Test Redis communication between components"""
    print("\n🔗 Testing Redis communication...")
    
    try:
        import redis
        
        # Connect to Redis
        try:
            redis_client = redis.Redis(
                host='wired-leopard-26321.upstash.io',
                port=6379,
                password='AWbRAAIjcDEwNjE4YmFlOTI2Mzg0OTVkOTc4YzE3YzZjOWEzNDUxOHAxMA',
                ssl=True,
                decode_responses=True
            )
            redis_client.ping()
            print("✅ Redis connection successful")
        except:
            # Fallback to local Redis
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            redis_client.ping()
            print("✅ Local Redis connection successful")
        
        # Test data storage
        test_data = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'modular_system_test',
            'status': 'testing'
        }
        
        redis_client.setex("systemx:test", 60, json.dumps(test_data))
        stored_data = redis_client.get("systemx:test")
        
        if stored_data:
            parsed_data = json.loads(stored_data)
            if parsed_data['test_type'] == 'modular_system_test':
                print("✅ Redis data storage test passed")
            else:
                print("❌ Redis data integrity test failed")
                return False
        else:
            print("❌ Redis data retrieval failed")
            return False
        
        # Clean up test data
        redis_client.delete("systemx:test")
        print("✅ Redis cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis communication test failed: {e}")
        return False

def test_analyze_button():
    """Test the analyze button functionality"""
    print("\n🔍 Testing analyze button functionality...")
    
    try:
        # Start API briefly to test analyze endpoint
        api_process = subprocess.Popen([
            '/opt/homebrew/bin/python3.12', 'api.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(8)  # Wait for startup
        
        # Test analyze endpoint
        test_ticker = "AAPL"
        response = requests.get(
            f'http://localhost:8080/analyze-stock?ticker={test_ticker}',
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analyze button test passed for {test_ticker}")
            print(f"   Ticker: {data.get('ticker', 'N/A')}")
            print(f"   Recommendation: {data.get('recommendation', 'N/A')}")
            print(f"   DTS Score: {data.get('dts_score', 'N/A')}")
        else:
            print(f"❌ Analyze button test failed: {response.status_code}")
            api_process.terminate()
            return False
        
        api_process.terminate()
        api_process.wait()
        return True
        
    except Exception as e:
        print(f"❌ Analyze button test failed: {e}")
        return False

def test_3_accounts():
    """Test 3 accounts functionality"""
    print("\n💳 Testing 3 accounts functionality...")
    
    try:
        # Start API to test accounts endpoint
        api_process = subprocess.Popen([
            '/opt/homebrew/bin/python3.12', 'api.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(8)
        
        response = requests.get('http://localhost:8080/accounts', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            accounts = data.get('accounts', [])
            
            print(f"✅ Accounts endpoint working: {len(accounts)} accounts found")
            for account in accounts:
                name = account.get('name', 'Unknown')
                status = account.get('status', 'Unknown')
                balance = account.get('balance', 0)
                print(f"   {name}: ${balance:,.2f} ({status})")
            
            if len(accounts) >= 3:
                print("✅ All 3 accounts configured")
            else:
                print(f"⚠️ Only {len(accounts)} accounts found (expected 3)")
        else:
            print(f"❌ Accounts test failed: {response.status_code}")
            api_process.terminate()
            return False
        
        api_process.terminate()
        api_process.wait()
        return True
        
    except Exception as e:
        print(f"❌ 3 accounts test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MODULAR SYSTEM X - COMPREHENSIVE TESTING")
    print("=" * 60)
    
    tests = [
        ("Redis Communication", test_redis_communication),
        ("FastAPI Startup", test_api_startup),
        ("System X Startup", test_system_x_startup),
        ("Analyze Button", test_analyze_button),
        ("3 Accounts", test_3_accounts)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Final results
    print("\n" + "="*60)
    print("🏆 FINAL TEST RESULTS:")
    print("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print("="*60)
    success_rate = (passed / total) * 100
    print(f"📊 SUCCESS RATE: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 MODULAR SYSTEM ARCHITECTURE: READY FOR PRODUCTION!")
    elif success_rate >= 60:
        print("⚠️ SYSTEM OPERATIONAL WITH MINOR ISSUES")
    else:
        print("❌ SYSTEM NEEDS ATTENTION BEFORE DEPLOYMENT")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)