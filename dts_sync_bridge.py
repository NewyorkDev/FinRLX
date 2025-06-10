#!/opt/homebrew/bin/python3.12
"""
DTS SYNC BRIDGE - Critical Data Pipeline Repair
Synchronizes DTS scores from v9_multi_source_analysis to analyzed_stocks table
Restores trading capability by fixing the broken data flow
"""

import os
import sys
import time
import json
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

def sync_dts_scores():
    """Sync DTS scores from v9_multi_source_analysis to analyzed_stocks"""
    print(f"🔄 Starting DTS sync bridge at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    env_vars = load_environment()
    if not env_vars:
        print("❌ Failed to load environment variables")
        return False
    
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    try:
        # Get recent DTS data from v9_multi_source_analysis (last 4 hours)
        cutoff_time = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📊 Fetching DTS data from v9_multi_source_analysis since {cutoff_time}...")
        
        source_result = supabase.table('v9_multi_source_analysis').select(
            'ticker, session_id, dts_score, v9_combined_score, '
            'dts_rvol_component, dts_atr_component, dts_vwap_component, dts_rotation_component, dts_catalyst_component, '
            'created_at'
        ).gte('created_at', cutoff_time).not_.is_('dts_score', 'null').execute()
        
        if not source_result.data:
            print("❌ No DTS data found in v9_multi_source_analysis")
            return False
        
        print(f"✅ Found {len(source_result.data)} records with DTS scores")
        
        # Process each record
        synced_count = 0
        for record in source_result.data:
            ticker = record['ticker']
            session_id = record['session_id']
            dts_score = record.get('dts_score')
            v9_score = record.get('v9_combined_score', 0)
            created_at = record['created_at']
            
            if not dts_score:
                continue
                
            # Calculate DTS components
            rvol_score = record.get('dts_rvol_component', 0)
            atr_score = record.get('dts_atr_component', 0) 
            vwap_score = record.get('dts_vwap_component', 0)
            rotation_score = record.get('dts_rotation_component', 0)
            catalyst_score = record.get('dts_catalyst_component', 0)
            
            # Create or update analyzed_stocks entry
            analyzed_data = {
                'ticker': ticker,
                'session_id': session_id,
                'dts_score': dts_score,
                'squeeze_score': v9_score * 10 if v9_score < 10 else v9_score,  # Apply scaling to squeeze_score
                'dts_rvol_component': rvol_score,
                'dts_atr_component': atr_score,
                'dts_vwap_component': vwap_score,
                'dts_rotation_component': rotation_score,
                'dts_catalyst_component': catalyst_score,
                'created_at': created_at
            }
            
            try:
                # Check if ticker already exists
                existing_result = supabase.table('analyzed_stocks').select('id').eq('ticker', ticker).limit(1).execute()
                
                if existing_result.data:
                    # Update existing record
                    update_result = supabase.table('analyzed_stocks').update(analyzed_data).eq('ticker', ticker).execute()
                    upsert_result = update_result
                else:
                    # Insert new record
                    insert_result = supabase.table('analyzed_stocks').insert(analyzed_data).execute()
                    upsert_result = insert_result
                
                if upsert_result.data:
                    synced_count += 1
                    print(f"   ✅ {ticker}: DTS={dts_score:.1f}, Squeeze={analyzed_data['squeeze_score']:.1f}")
                    
            except Exception as e:
                print(f"   ❌ {ticker}: Sync failed - {e}")
                continue
        
        print(f"\n🎯 Sync complete: {synced_count}/{len(source_result.data)} records synced")
        
        # Verify SystemX can now see qualified stocks
        print("\n🔍 Verifying trading capability...")
        qualified_result = supabase.table('analyzed_stocks').select(
            'ticker, dts_score, squeeze_score'
        ).gte('dts_score', 60.0).gte('squeeze_score', 75.0).order('dts_score', desc=True).limit(10).execute()
        
        if qualified_result.data:
            print(f"✅ TRADING RESTORED: {len(qualified_result.data)} qualified stocks now available:")
            for stock in qualified_result.data:
                ticker = stock['ticker']
                dts = stock['dts_score']
                squeeze = stock['squeeze_score']
                sure_thing = "🔥 SURE THING!" if dts >= 78 and squeeze >= 88 else ""
                print(f"   {ticker}: DTS={dts:.1f}, Squeeze={squeeze:.1f} {sure_thing}")
        else:
            print("⚠️ No qualified stocks found - may need more data")
        
        return synced_count > 0
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False

def continuous_sync_mode():
    """Run continuous sync every 5 minutes"""
    print("🔄 Starting continuous DTS sync mode (5-minute intervals)")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            success = sync_dts_scores()
            if success:
                print("✅ Sync cycle completed successfully")
            else:
                print("❌ Sync cycle failed")
            
            print(f"😴 Sleeping 5 minutes... (next sync at {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M:%S')})")
            time.sleep(300)  # 5 minutes
            
    except KeyboardInterrupt:
        print("\n🛑 Continuous sync stopped by user")

def main():
    """Main execution"""
    print("🔧 DTS SYNC BRIDGE - CRITICAL DATA PIPELINE REPAIR")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        continuous_sync_mode()
    else:
        print("🔄 Running one-time DTS sync...")
        success = sync_dts_scores()
        
        if success:
            print("\n🚀 DTS SYNC SUCCESSFUL - TRADING CAPABILITY RESTORED!")
            print("💡 To run continuous sync: python dts_sync_bridge.py --continuous")
        else:
            print("\n❌ DTS sync failed - manual intervention required")
        
        return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)