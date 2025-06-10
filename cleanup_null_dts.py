#!/opt/homebrew/bin/python3.12
"""
CLEANUP NULL DTS RECORDS - Eliminate remaining DTS issues
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

def cleanup_null_dts():
    """Clean up NULL DTS records from analyzed_stocks"""
    print("🧹 CLEANING UP NULL DTS RECORDS")
    print("=" * 60)
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Find all NULL DTS records
    try:
        null_result = supabase.table('analyzed_stocks').select(
            'id, ticker, dts_score, created_at'
        ).is_('dts_score', 'null').execute()
        
        if null_result.data:
            print(f"🔍 Found {len(null_result.data)} NULL DTS records to clean up:")
            
            deleted_count = 0
            for record in null_result.data:
                record_id = record['id']
                ticker = record['ticker']
                created = record.get('created_at', 'N/A')[:16]
                
                try:
                    # Delete the record with NULL DTS
                    delete_result = supabase.table('analyzed_stocks').delete().eq('id', record_id).execute()
                    if delete_result.data:
                        deleted_count += 1
                        print(f"   ✅ Deleted {ticker} (ID: {record_id}, Time: {created})")
                    else:
                        print(f"   ❌ Failed to delete {ticker} (ID: {record_id})")
                        
                except Exception as e:
                    print(f"   ❌ Error deleting {ticker}: {e}")
            
            print(f"\n🎯 Cleanup complete: {deleted_count}/{len(null_result.data)} records deleted")
            
        else:
            print("✅ No NULL DTS records found - database is clean!")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    
    # Verify cleanup worked
    print("\n🔍 Verifying cleanup...")
    try:
        verify_result = supabase.table('analyzed_stocks').select(
            'ticker, dts_score'
        ).is_('dts_score', 'null').execute()
        
        if verify_result.data:
            print(f"⚠️ Still {len(verify_result.data)} NULL DTS records remaining")
            return False
        else:
            print("✅ All NULL DTS records eliminated!")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying cleanup: {e}")
        return False

def main():
    success = cleanup_null_dts()
    if success:
        print("\n🚀 NULL DTS CLEANUP SUCCESSFUL!")
        print("💡 SystemX should now report ZERO DTS issues")
    else:
        print("\n❌ Cleanup failed - manual intervention required")
    
    return success

if __name__ == "__main__":
    main()