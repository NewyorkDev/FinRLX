#!/usr/bin/env python3.12
"""
Test script to demonstrate the new aggressive position sizing for "sure thing" stocks
on accounts 1&2 (PRIMARY_30K and SECONDARY_30K).
"""

import sys
import os
sys.path.append('.')

from system_x import SystemX

def test_aggressive_sizing():
    """Test the aggressive position sizing functionality"""
    print("🎯 Testing Aggressive Position Sizing for Sure Thing Stocks")
    print("=" * 70)
    
    try:
        # Initialize System X in debug mode to see detailed output
        trader = SystemX(debug=True, dry_run=True)
        
        print("\n📋 Testing Sure Thing Detection:")
        print("-" * 40)
        
        # Test stocks with mock data (in real scenario, this would pull from Supabase)
        test_stocks = [
            {'ticker': 'MOCK_SURE', 'dts': 85, 'v9b': 9.2},  # Should be a sure thing
            {'ticker': 'MOCK_GOOD', 'dts': 75, 'v9b': 8.5},  # Good but not sure thing
            {'ticker': 'MOCK_WEAK', 'dts': 65, 'v9b': 7.0}   # Qualified but weak
        ]
        
        for stock in test_stocks:
            # Mock the V9B analysis method for testing
            original_method = trader.get_v9b_analysis
            def mock_analysis(ticker):
                if ticker == stock['ticker']:
                    return {'dts_score': stock['dts'], 'combined_score': stock['v9b']}
                return {}
            
            trader.get_v9b_analysis = mock_analysis
            
            is_sure = trader.is_sure_thing_stock(stock['ticker'])
            print(f"   {stock['ticker']}: DTS {stock['dts']}, V9B {stock['v9b']:.1f} → Sure Thing: {'YES' if is_sure else 'NO'}")
            
            trader.get_v9b_analysis = original_method
        
        print("\n💰 Testing Position Sizing Logic:")
        print("-" * 40)
        
        # Test position sizing for different accounts and stock types
        test_price = 100.0
        test_accounts = ["PRIMARY_30K", "SECONDARY_30K", "TERTIARY_30K"]
        
        # Mock a sure thing stock
        def mock_sure_thing(ticker):
            return ticker == "SURE_THING_STOCK"
        
        trader.is_sure_thing_stock = mock_sure_thing
        
        for account in test_accounts:
            print(f"\n   🏦 Account: {account}")
            
            # Test with sure thing stock
            shares_sure = trader.calculate_position_size("SURE_THING_STOCK", test_price, 1.0, account)
            position_value_sure = shares_sure * test_price
            position_pct_sure = (position_value_sure / 30000) * 100  # Assuming $30K account
            
            print(f"      Sure Thing: {shares_sure} shares (${position_value_sure:,.0f} = {position_pct_sure:.1f}%)")
            
            # Test with regular stock
            shares_regular = trader.calculate_position_size("REGULAR_STOCK", test_price, 1.0, account)
            position_value_regular = shares_regular * test_price
            position_pct_regular = (position_value_regular / 30000) * 100
            
            print(f"      Regular:    {shares_regular} shares (${position_value_regular:,.0f} = {position_pct_regular:.1f}%)")
        
        print("\n✅ Aggressive Position Sizing Test Complete!")
        print("\nKey Features Implemented:")
        print("• Sure Thing Detection: DTS ≥ 78 AND V9B ≥ 8.8")
        print("• Aggressive Accounts: PRIMARY_30K and SECONDARY_30K")
        print("• Conservative Account: TERTIARY_30K") 
        print("• Position Size Limit: Up to 50% for sure things on aggressive accounts")
        print("• Standard Limit: 15% for all other cases")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_aggressive_sizing()
    sys.exit(0 if success else 1)