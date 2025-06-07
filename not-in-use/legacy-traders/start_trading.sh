#!/bin/bash

# Start FinRL Day Trading System with V9B Integration
# For 30k Alpaca accounts

echo "🏆 FinRL Day Trading System with V9B Integration"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "simple_day_trader.py" ]; then
    echo "❌ simple_day_trader.py not found. Please run from FinRLX directory."
    exit 1
fi

# Function to check dependencies
check_dependencies() {
    echo "🔍 Checking dependencies..."
    
    # Check Python packages
    python3 -c "import supabase, alpaca_trade_api" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "📦 Installing required packages..."
        pip3 install supabase alpaca-trade-api
    fi
    
    echo "✅ Dependencies checked"
}

# Function to run system check
system_check() {
    echo "🔍 Running system check..."
    python3 simple_day_trader.py check
    
    if [ $? -eq 0 ]; then
        echo "✅ System check passed"
        return 0
    else
        echo "❌ System check failed"
        return 1
    fi
}

# Function to show portfolio status
show_status() {
    echo "📊 Portfolio Status:"
    python3 simple_day_trader.py status
}

# Function to start trading
start_trading() {
    echo "🚀 Starting live trading..."
    echo "⚠️  CTRL+C to stop trading"
    echo "=================================================="
    
    python3 simple_day_trader.py trade
}

# Main menu
if [ $# -eq 0 ]; then
    echo "Usage: $0 [check|status|trade|install]"
    echo ""
    echo "Commands:"
    echo "  check   - Run system check (V9B data + Alpaca connection)"
    echo "  status  - Show current portfolio status"
    echo "  trade   - Start live trading (paper trading)"
    echo "  install - Install dependencies only"
    echo ""
    exit 0
fi

case "$1" in
    "install")
        check_dependencies
        ;;
    "check")
        check_dependencies
        system_check
        ;;
    "status")
        check_dependencies
        show_status
        ;;
    "trade")
        check_dependencies
        if system_check; then
            echo ""
            echo "🎯 Qualified stocks found. Starting trading..."
            echo "💰 Account balance: $30,000"
            echo "📈 Max position size: 15% per stock"
            echo "🛑 Stop loss: 5%"
            echo ""
            read -p "Continue with live trading? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                start_trading
            else
                echo "Trading cancelled"
            fi
        else
            echo "❌ System check failed. Please fix issues before trading."
        fi
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Use: $0 [check|status|trade|install]"
        exit 1
        ;;
esac

echo "✅ Done"