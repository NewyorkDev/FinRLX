#!/usr/bin/env python3
"""
Complete Trading System Launcher
Integrates V9B data with FinRL for automated day trading
"""

import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

def check_market_hours():
    """Check if market is currently open"""
    try:
        import alpaca_trade_api as tradeapi
        
        # Load env vars
        env_file = "/Users/francisclase/FinRLX/the_end/.env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        alpaca_key = os.getenv('ALPACA_PAPER_API_KEY_ID')
        alpaca_secret = os.getenv('ALPACA_PAPER_API_SECRET_KEY')
        alpaca_base_url = os.getenv('ALPACA_BASE_URL')
        
        alpaca = tradeapi.REST(alpaca_key, alpaca_secret, alpaca_base_url, api_version='v2')
        clock = alpaca.get_clock()
        
        return clock.is_open, clock.next_open, clock.next_close
        
    except Exception as e:
        print(f"Error checking market hours: {e}")
        return False, None, None

def install_dependencies():
    """Install required packages"""
    print("📦 Installing/checking dependencies...")
    
    packages = [
        "supabase", 
        "alpaca-trade-api", 
        "pandas", 
        "numpy",
        "python-dotenv"
    ]
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True, text=True)
    
    print("✅ Dependencies ready")

def check_system():
    """Check all system components"""
    print("🔍 System Check")
    print("=" * 50)
    
    # Check if trading scripts exist
    scripts = [
        "fixed_day_trader.py",
        "simple_day_trader.py", 
        "debug_trading.py"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            print(f"✅ {script}")
        else:
            print(f"❌ {script} missing")
    
    # Check environment files
    env_files = [".env", "the_end/.env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✅ {env_file}")
        else:
            print(f"❌ {env_file} missing")
    
    # Check market status
    is_open, next_open, next_close = check_market_hours()
    market_status = "🟢 OPEN" if is_open else "🔴 CLOSED"
    print(f"📈 Market Status: {market_status}")
    
    if not is_open and next_open:
        print(f"   Next Open: {next_open}")
    
    # Test connections
    print("\n🔗 Testing Connections:")
    try:
        result = subprocess.run([sys.executable, "fixed_day_trader.py", "check"], 
                              capture_output=True, text=True, timeout=30)
        if "✅ V9B data check passed" in result.stdout:
            print("✅ V9B + Alpaca connections working")
        else:
            print("❌ Connection issues detected")
            print(result.stdout[-200:])  # Show last 200 chars
    except Exception as e:
        print(f"❌ Connection test failed: {e}")

def launch_trading():
    """Launch the trading system"""
    print("🚀 LAUNCHING TRADING SYSTEM")
    print("=" * 50)
    
    # Check market status first
    is_open, next_open, next_close = check_market_hours()
    
    if not is_open:
        print("⏰ Market is currently CLOSED")
        print(f"Next open: {next_open}")
        
        response = input("Start anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Trading cancelled")
            return
    
    # Show trading parameters
    print("📊 TRADING PARAMETERS:")
    print("   • Account: $30,000 paper trading")
    print("   • Max position: 15% per stock")
    print("   • Stop loss: 5%")
    print("   • Trading frequency: Every 5 minutes")
    print("   • Stock universe: V9B qualified stocks (DTS ≥ 60)")
    print("   • Buy signals: DTS ≥ 65 + V9B confidence ≥ 7.0")
    print("   • Strong buy: DTS ≥ 70 + V9B confidence ≥ 8.0")
    print()
    
    # Choose trading mode
    print("📋 TRADING MODES:")
    print("1. Enhanced Trading (recommended) - Uses V9B confidence scoring")
    print("2. Simple Trading - Basic DTS-based trading")
    print("3. Debug Mode - Detailed logging and analysis")
    
    while True:
        choice = input("\nSelect mode (1-3): ").strip()
        
        if choice == "1":
            print("🎯 Starting Enhanced Trading...")
            subprocess.run([sys.executable, "fixed_day_trader.py", "trade"])
            break
        elif choice == "2":
            print("🎯 Starting Simple Trading...")
            subprocess.run([sys.executable, "simple_day_trader.py", "trade"])
            break
        elif choice == "3":
            print("🎯 Starting Debug Mode...")
            subprocess.run([sys.executable, "fixed_day_trader.py", "debug"])
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

def show_portfolio():
    """Show portfolio status"""
    print("📊 PORTFOLIO STATUS")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "fixed_day_trader.py", "status"])
    except Exception as e:
        print(f"Error showing portfolio: {e}")

def setup_finrl_trader():
    """Set up FinRL-based DRL trader"""
    print("🤖 SETTING UP FinRL DRL TRADER")
    print("=" * 50)
    
    # This would train a DRL model using FinRL
    print("Training DRL model with V9B data...")
    print("Note: This requires historical data and training time")
    
    # For now, show what would be done
    print("Would execute:")
    print("1. Download historical data for V9B qualified stocks")
    print("2. Train PPO agent using FinRL")
    print("3. Test agent on recent data")
    print("4. Deploy for live trading")
    
    response = input("Continue with DRL setup? (y/N): ").strip().lower()
    if response == 'y':
        try:
            subprocess.run([sys.executable, "day_trading_main.py", "train"])
        except Exception as e:
            print(f"Error in DRL setup: {e}")

def create_market_watchlist():
    """Create a watchlist of V9B qualified stocks"""
    print("👀 MARKET WATCHLIST")
    print("=" * 50)
    
    try:
        from supabase import create_client
        
        # Load env vars
        env_file = "/Users/francisclase/FinRLX/the_end/.env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        supabase = create_client(supabase_url, supabase_key)
        
        # Get qualified stocks
        response = supabase.table('analyzed_stocks').select(
            'ticker, dts_score, dts_qualification, dts_momentum_grade'
        ).gte('dts_score', 50).order('dts_score', desc=True).limit(20).execute()
        
        if response.data:
            print(f"📈 Top {len(response.data)} stocks by DTS score:")
            print()
            print("Ticker  DTS Score  Qualification  Grade")
            print("-" * 40)
            
            for stock in response.data:
                ticker = stock.get('ticker', 'N/A')
                dts = stock.get('dts_score', 0)
                qual = stock.get('dts_qualification', 'N/A')
                grade = stock.get('dts_momentum_grade', 'N/A')
                
                if not ticker.startswith('TEST'):
                    print(f"{ticker:6} {dts:8.1f}  {qual:12} {grade:5}")
        else:
            print("No qualified stocks found")
            
    except Exception as e:
        print(f"Error creating watchlist: {e}")

def main():
    """Main launcher interface"""
    print("🏆 FINRL + V9B DAY TRADING SYSTEM")
    print("=" * 60)
    print("🎯 Automated day trading using V9B qualified stocks")
    print("💰 Optimized for $30k Alpaca paper trading accounts")
    print("=" * 60)
    
    while True:
        print("\n📋 MAIN MENU:")
        print("1. 🔍 System Check - Verify all components")
        print("2. 🚀 Launch Trading - Start automated trading")
        print("3. 📊 Portfolio Status - View current positions")
        print("4. 👀 Market Watchlist - View V9B qualified stocks")
        print("5. 🤖 Setup DRL Trader - Configure FinRL agent")
        print("6. 📦 Install Dependencies - Install required packages")
        print("7. ❌ Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == "1":
            install_dependencies()
            check_system()
        elif choice == "2":
            install_dependencies()
            launch_trading()
        elif choice == "3":
            show_portfolio()
        elif choice == "4":
            create_market_watchlist()
        elif choice == "5":
            setup_finrl_trader()
        elif choice == "6":
            install_dependencies()
        elif choice == "7":
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-7.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your setup and try again.")