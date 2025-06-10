#!/opt/homebrew/bin/python3.12
"""
SUPABASE TABLE AUDIT - Identify unused tables for cleanup
Analyzes which tables are actively used vs obsolete
"""

import os
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

def get_all_tables(supabase):
    """Get list of all tables in the database"""
    try:
        # Query information_schema to get all user tables
        result = supabase.rpc('get_table_list', {}).execute()
        return result.data if result.data else []
    except:
        # Fallback: try a few known table patterns
        print("⚠️ Using fallback table discovery...")
        potential_tables = [
            'analyzed_stocks', 'v9_multi_source_analysis', 'v9_session_metadata',
            'backtest_results', 'portfolio_snapshots', 'trading_logs', 'trade_logs',
            'real_time_quotes', 'risk_metrics', 'system_status', 'system_logs',
            'holdings', 'orders', 'positions', 'accounts', 'strategies',
            'market_data', 'indicators', 'signals', 'news', 'sentiment',
            'v9_analysis', 'stock_data', 'price_data', 'volume_data'
        ]
        
        existing_tables = []
        for table in potential_tables:
            try:
                result = supabase.table(table).select('*').limit(1).execute()
                existing_tables.append({'table_name': table, 'accessible': True})
                print(f"✅ Found table: {table}")
            except Exception as e:
                if 'does not exist' in str(e):
                    continue
                else:
                    print(f"❌ Error accessing {table}: {e}")
        
        return existing_tables

def analyze_table_usage(supabase, table_name):
    """Analyze recent activity and record count for a table"""
    try:
        # Get total count
        count_result = supabase.table(table_name).select('*', count='exact').limit(1).execute()
        total_count = count_result.count if hasattr(count_result, 'count') else 0
        
        # Get recent activity (last 7 days)
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Try different timestamp columns
        recent_count = 0
        last_activity = None
        
        for date_col in ['created_at', 'updated_at', 'timestamp', 'analysis_timestamp']:
            try:
                recent_result = supabase.table(table_name).select('*', count='exact').gte(date_col, cutoff_date).limit(1).execute()
                if hasattr(recent_result, 'count') and recent_result.count > 0:
                    recent_count = recent_result.count
                    
                    # Get most recent record
                    latest_result = supabase.table(table_name).select(date_col).order(date_col, desc=True).limit(1).execute()
                    if latest_result.data:
                        last_activity = latest_result.data[0][date_col]
                    break
            except:
                continue
        
        return {
            'total_records': total_count,
            'recent_records_7d': recent_count,
            'last_activity': last_activity,
            'activity_level': 'HIGH' if recent_count > 10 else 'MEDIUM' if recent_count > 0 else 'NONE'
        }
        
    except Exception as e:
        return {
            'total_records': 0,
            'recent_records_7d': 0,
            'last_activity': None,
            'activity_level': 'ERROR',
            'error': str(e)
        }

def check_systemx_usage():
    """Check which tables SystemX actually uses"""
    systemx_tables = set()
    
    # Check system_x.py for table references
    try:
        with open('system_x.py', 'r') as f:
            content = f.read()
            
            # Look for .table() calls
            import re
            table_patterns = [
                r"\.table\(['\"]([^'\"]+)['\"]",
                r"FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                r"INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                r"UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                r"DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)"
            ]
            
            for pattern in table_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                systemx_tables.update(matches)
                
    except Exception as e:
        print(f"⚠️ Could not analyze system_x.py: {e}")
    
    return systemx_tables

def main():
    """Main table audit"""
    print("🔍 SUPABASE TABLE AUDIT - CLEANUP ANALYSIS")
    print("=" * 60)
    
    env_vars = load_environment()
    if not env_vars:
        print("❌ Failed to load environment")
        return
    
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    print("📊 Discovering all tables...")
    tables = get_all_tables(supabase)
    
    if not tables:
        print("❌ No tables found")
        return
    
    print(f"✅ Found {len(tables)} tables")
    
    print("\n🔍 Checking SystemX usage patterns...")
    systemx_tables = check_systemx_usage()
    print(f"📝 SystemX references {len(systemx_tables)} tables: {', '.join(sorted(systemx_tables))}")
    
    print("\n📈 Analyzing table activity...")
    
    active_tables = []
    inactive_tables = []
    
    for table_info in tables:
        table_name = table_info.get('table_name') if isinstance(table_info, dict) else table_info
        
        print(f"\n📋 Analyzing: {table_name}")
        usage = analyze_table_usage(supabase, table_name)
        
        used_by_systemx = table_name in systemx_tables
        is_active = usage['activity_level'] in ['HIGH', 'MEDIUM']
        
        status_indicators = []
        if used_by_systemx:
            status_indicators.append("🔧 SystemX")
        if is_active:
            status_indicators.append(f"📊 {usage['activity_level']}")
        
        print(f"   Records: {usage['total_records']:,} total, {usage['recent_records_7d']} recent")
        print(f"   Last activity: {usage.get('last_activity', 'Unknown')}")
        print(f"   Status: {' | '.join(status_indicators) if status_indicators else '💀 UNUSED'}")
        
        table_analysis = {
            'name': table_name,
            'used_by_systemx': used_by_systemx,
            'total_records': usage['total_records'],
            'recent_activity': usage['recent_records_7d'],
            'last_activity': usage.get('last_activity'),
            'activity_level': usage['activity_level'],
            'recommendation': 'KEEP' if (used_by_systemx or is_active) else 'DELETE'
        }
        
        if table_analysis['recommendation'] == 'KEEP':
            active_tables.append(table_analysis)
        else:
            inactive_tables.append(table_analysis)
    
    # Summary and recommendations
    print("\n" + "=" * 60)
    print("📊 CLEANUP RECOMMENDATIONS")
    print("-" * 30)
    
    print(f"\n✅ KEEP ({len(active_tables)} tables):")
    for table in active_tables:
        reason = []
        if table['used_by_systemx']:
            reason.append("SystemX dependency")
        if table['activity_level'] in ['HIGH', 'MEDIUM']:
            reason.append(f"{table['activity_level'].lower()} activity")
        
        print(f"   {table['name']} - {', '.join(reason)}")
    
    print(f"\n🗑️ DELETE ({len(inactive_tables)} tables):")
    for table in inactive_tables:
        print(f"   {table['name']} - {table['total_records']:,} records, no recent activity")
    
    if inactive_tables:
        print(f"\n💾 Total storage to reclaim: ~{sum(t['total_records'] for t in inactive_tables):,} records")
        
        print("\n🚨 DELETION COMMANDS:")
        for table in inactive_tables:
            print(f"   DROP TABLE IF EXISTS {table['name']};")
    else:
        print("\n✨ No unused tables found - database is already clean!")

if __name__ == "__main__":
    main()