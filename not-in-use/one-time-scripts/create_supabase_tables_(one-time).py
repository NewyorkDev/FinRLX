#!/usr/bin/env python3
"""
Create missing Supabase tables for System X
Fixes the 404 JSON generation errors
"""

import os
import sys
from supabase import create_client, Client

def load_environment():
    """Load environment variables"""
    env_file = "/Users/francisclase/FinRLX/the_end/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def check_and_create_tables():
    """Check existing tables and create missing System X tables"""
    
    load_environment()
    
    # Connect to Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found")
        return False
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("🔍 Checking existing Supabase tables...")
    
    # Test what tables exist
    existing_tables = []
    test_tables = [
        'analyzed_stocks',
        'v9_multi_source_analysis', 
        'v9_session_metadata',
        'backtest_results',
        'portfolio_snapshots',
        'system_x_logs',
        'trade_execution_logs',
        'backtest_execution_logs',
        'system_health_metrics'
    ]
    
    for table in test_tables:
        try:
            response = supabase.table(table).select('count').limit(1).execute()
            existing_tables.append(table)
            print(f"✅ {table} - EXISTS")
        except Exception as e:
            print(f"❌ {table} - MISSING")
    
    print(f"\n📊 Found {len(existing_tables)} existing tables")
    
    # System X required tables
    system_x_tables = [
        'system_x_logs',
        'trade_execution_logs', 
        'backtest_execution_logs',
        'system_health_metrics'
    ]
    
    missing_tables = [table for table in system_x_tables if table not in existing_tables]
    
    if not missing_tables:
        print("✅ All System X tables exist!")
        return True
    
    print(f"\n🛠️ Creating {len(missing_tables)} missing System X tables...")
    
    # Create missing tables using Supabase SQL
    sql_commands = {
        'system_x_logs': """
            CREATE TABLE IF NOT EXISTS system_x_logs (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                event_type TEXT NOT NULL,
                event_data JSONB,
                status TEXT DEFAULT 'INFO',
                error_details TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """,
        
        'trade_execution_logs': """
            CREATE TABLE IF NOT EXISTS trade_execution_logs (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                trade_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity NUMERIC NOT NULL,
                price NUMERIC NOT NULL,
                total_value NUMERIC NOT NULL,
                reason TEXT,
                account_name TEXT,
                pnl NUMERIC DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """,
        
        'backtest_execution_logs': """
            CREATE TABLE IF NOT EXISTS backtest_execution_logs (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                backtest_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                strategy TEXT NOT NULL,
                symbols TEXT[],
                total_return NUMERIC,
                sharpe_ratio NUMERIC,
                max_drawdown NUMERIC,
                win_rate NUMERIC,
                total_trades INTEGER,
                results_data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """,
        
        'system_health_metrics': """
            CREATE TABLE IF NOT EXISTS system_health_metrics (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                cpu_usage NUMERIC,
                memory_usage NUMERIC,
                error_count INTEGER DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                backtest_count INTEGER DEFAULT 0,
                account_balance NUMERIC,
                total_exposure NUMERIC,
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """
    }
    
    # Execute SQL commands
    for table_name in missing_tables:
        if table_name in sql_commands:
            try:
                print(f"   Creating {table_name}...")
                result = supabase.rpc('exec_sql', {'sql': sql_commands[table_name]}).execute()
                print(f"   ✅ {table_name} created successfully")
            except Exception as e:
                print(f"   ❌ Failed to create {table_name}: {e}")
                # Try alternative method - direct table creation
                try:
                    # Create a dummy record to trigger table creation
                    dummy_data = {}
                    if table_name == 'system_x_logs':
                        dummy_data = {
                            'session_id': 'INIT',
                            'timestamp': '2025-06-06T00:00:00Z',
                            'event_type': 'TABLE_CREATION',
                            'status': 'INFO'
                        }
                    elif table_name == 'trade_execution_logs':
                        dummy_data = {
                            'session_id': 'INIT',
                            'trade_id': 'INIT',
                            'timestamp': '2025-06-06T00:00:00Z',
                            'symbol': 'INIT',
                            'action': 'INIT',
                            'quantity': 0,
                            'price': 0,
                            'total_value': 0
                        }
                    elif table_name == 'backtest_execution_logs':
                        dummy_data = {
                            'session_id': 'INIT',
                            'backtest_id': 'INIT',
                            'timestamp': '2025-06-06T00:00:00Z',
                            'strategy': 'INIT',
                            'symbols': ['INIT']
                        }
                    elif table_name == 'system_health_metrics':
                        dummy_data = {
                            'session_id': 'INIT',
                            'timestamp': '2025-06-06T00:00:00Z',
                            'status': 'INIT'
                        }
                    
                    # This will fail but might give us better error info
                    supabase.table(table_name).insert(dummy_data).execute()
                    
                except Exception as e2:
                    print(f"   ⚠️ Table {table_name} creation method failed: {e2}")
    
    print("\n🎯 Table creation process completed")
    
    # Verify tables exist now
    print("\n🔍 Verifying System X tables...")
    all_exist = True
    for table in system_x_tables:
        try:
            response = supabase.table(table).select('count').limit(1).execute()
            print(f"✅ {table} - VERIFIED")
        except Exception as e:
            print(f"❌ {table} - STILL MISSING")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    success = check_and_create_tables()
    if success:
        print("\n🎉 All System X tables are ready!")
        sys.exit(0)
    else:
        print("\n❌ Some tables are still missing")
        sys.exit(1)