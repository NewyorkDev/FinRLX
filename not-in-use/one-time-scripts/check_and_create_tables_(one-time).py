#!/usr/bin/env python3
"""
Script to check existing Supabase tables and create missing System X tables.
"""

import os
import sys
import requests
import json
from typing import List, Dict, Any

class SupabaseTableManager:
    def __init__(self, url: str, service_key: str):
        self.url = url
        self.service_key = service_key
        self.headers = {
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'apikey': service_key
        }
        
        # Extract connection info from Supabase URL
        # Format: https://ttwbilpwrzoizbthembb.supabase.co
        self.project_ref = url.split('//')[1].split('.')[0]
        self.postgres_url = f"postgresql://postgres:{self._get_db_password()}@db.{self.project_ref}.supabase.co:5432/postgres"
    
    def _get_db_password(self):
        """Extract database password from service key JWT token."""
        # For now, we'll use a direct connection approach
        # In production, you'd decode the JWT to get the password
        return "your_db_password"  # This needs to be the actual DB password
    
    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables in the database using direct query."""
        try:
            # Try to query existing tables through REST API first
            # Check if any of our target tables exist by trying to select from them
            tables_to_check = ['system_x_logs', 'trade_execution_logs', 'backtest_execution_logs', 'system_health_metrics']
            existing_tables = []
            
            for table in tables_to_check:
                try:
                    response = requests.get(
                        f"{self.url}/rest/v1/{table}",
                        headers=self.headers,
                        params={'limit': '1'}
                    )
                    if response.status_code == 200:
                        existing_tables.append(table)
                        print(f"✅ Table '{table}' exists")
                    elif response.status_code == 404:
                        print(f"❌ Table '{table}' does not exist")
                    else:
                        print(f"? Table '{table}' status unclear: {response.status_code}")
                except Exception as e:
                    print(f"Error checking table {table}: {e}")
            
            return existing_tables
                
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            return []
    
    def create_table_via_sql_endpoint(self, sql: str) -> bool:
        """Create table using Supabase SQL endpoint."""
        try:
            # Try using the SQL endpoint if available
            sql_endpoint = f"{self.url}/rest/v1/rpc/exec_sql"
            response = requests.post(
                sql_endpoint,
                headers=self.headers,
                json={"query": sql}
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ SQL executed successfully via SQL endpoint")
                return True
            else:
                print(f"SQL endpoint not available: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error using SQL endpoint: {e}")
            return False
    
    def create_table_if_not_exists(self, table_name: str, create_sql: str) -> bool:
        """Create table if it doesn't exist."""
        existing_tables = self.get_existing_tables()
        
        if table_name in existing_tables:
            print(f"✅ Table '{table_name}' already exists")
            return True
        else:
            print(f"🔄 Creating table '{table_name}'...")
            
            # Since we can't execute DDL via REST API, we'll provide the SQL
            print(f"📝 SQL to execute manually in Supabase SQL Editor:")
            print(f"{'='*50}")
            print(create_sql.strip())
            print(f"{'='*50}")
            
            # Try to create via API (will likely fail, but we'll try)
            return self.create_table_via_sql_endpoint(create_sql)

def main():
    # Load environment variables
    supabase_url = "https://ttwbilpwrzoizbthembb.supabase.co"
    supabase_service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR0d2JpbHB3cnpvaXpidGhlbWJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDIxNjc3NCwiZXhwIjoyMDU5NzkyNzc0fQ.thB5A0wjzIO0GXQ9XXLU9tgQDu0MXk3cI4KoOShYlcs"
    
    print("🔍 Checking Supabase database tables...")
    print(f"Supabase URL: {supabase_url}")
    
    # Initialize Supabase manager
    manager = SupabaseTableManager(supabase_url, supabase_service_key)
    
    # Get existing tables
    print("\n📋 Listing existing tables...")
    existing_tables = manager.get_existing_tables()
    
    if existing_tables:
        print("Existing tables:")
        for table in existing_tables:
            print(f"  - {table}")
    else:
        print("No tables found or unable to fetch tables.")
    
    # Define System X tables and their schemas
    system_x_tables = {
        'system_x_logs': '''
            CREATE TABLE system_x_logs (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                event_type TEXT NOT NULL,
                event_data JSONB,
                status TEXT DEFAULT 'INFO',
                error_details TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''',
        
        'trade_execution_logs': '''
            CREATE TABLE trade_execution_logs (
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
        ''',
        
        'backtest_execution_logs': '''
            CREATE TABLE backtest_execution_logs (
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
        ''',
        
        'system_health_metrics': '''
            CREATE TABLE system_health_metrics (
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
        '''
    }
    
    print(f"\n🔧 Checking and creating System X tables...")
    
    # Check and create each table
    success_count = 0
    for table_name, create_sql in system_x_tables.items():
        print(f"\n📊 Processing table: {table_name}")
        if manager.create_table_if_not_exists(table_name, create_sql):
            success_count += 1
    
    print(f"\n✅ Summary: {success_count}/{len(system_x_tables)} tables processed successfully")
    
    # Refresh and show final table list
    print("\n📋 Final table list:")
    final_tables = manager.get_existing_tables()
    for table in final_tables:
        print(f"  - {table}")

if __name__ == "__main__":
    main()