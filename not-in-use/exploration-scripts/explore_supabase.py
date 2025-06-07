#!/usr/bin/env python3
"""
Script to explore Supabase database structure for V9B trading system
"""

import requests
import json
import os
from typing import Dict, List, Any

class SupabaseExplorer:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip('/')
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        try:
            # Use PostgREST introspection
            response = requests.get(
                f"{self.url}/rest/v1/",
                headers=self.headers
            )
            
            if response.status_code == 200:
                # Try to get table info from schema endpoint
                schema_response = requests.get(
                    f"{self.url}/rest/v1/?select=*",
                    headers=self.headers
                )
                
                # Alternative: Query information_schema if available
                tables_query = {
                    "select": "table_name",
                    "table_schema": "eq.public"
                }
                
                info_response = requests.get(
                    f"{self.url}/rest/v1/information_schema.tables",
                    headers=self.headers,
                    params=tables_query
                )
                
                if info_response.status_code == 200:
                    tables_data = info_response.json()
                    return [table['table_name'] for table in tables_data]
                
        except Exception as e:
            print(f"Error getting tables: {e}")
            
        # Fallback: try known table names based on V9B system
        known_tables = [
            'analyzed_stocks',
            'v9_multi_source_analysis', 
            'v9_session_metadata',
            'trading_signals',
            'backtest_results',
            'portfolio_positions',
            'trade_logs',
            'system_status',
            'market_data',
            'risk_metrics'
        ]
        
        # Test which tables exist
        existing_tables = []
        for table in known_tables:
            try:
                response = requests.get(
                    f"{self.url}/rest/v1/{table}?limit=1",
                    headers=self.headers
                )
                if response.status_code == 200:
                    existing_tables.append(table)
                    print(f"✓ Found table: {table}")
                elif response.status_code == 406:
                    # Table exists but might have no data or access issues
                    existing_tables.append(table)
                    print(f"? Table exists but access limited: {table}")
                else:
                    print(f"✗ Table not found: {table} (status: {response.status_code})")
            except Exception as e:
                print(f"✗ Error checking table {table}: {e}")
                
        return existing_tables
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table"""
        try:
            # Try to get a sample record to understand structure
            response = requests.get(
                f"{self.url}/rest/v1/{table_name}?limit=1",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Get column names and sample data types
                    sample_record = data[0]
                    schema = {}
                    for key, value in sample_record.items():
                        value_type = type(value).__name__
                        if value is None:
                            value_type = "null/unknown"
                        schema[key] = {
                            'type': value_type,
                            'sample_value': str(value)[:100] if value is not None else None
                        }
                    return schema
                else:
                    print(f"Table {table_name} exists but is empty")
                    return {}
            else:
                print(f"Could not access table {table_name}: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error getting schema for {table_name}: {e}")
            return {}
    
    def get_table_count(self, table_name: str) -> int:
        """Get record count for a table"""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{table_name}?select=count",
                headers={**self.headers, 'Prefer': 'count=exact'}
            )
            
            if response.status_code == 200:
                # The count is in the Content-Range header
                content_range = response.headers.get('Content-Range', '')
                if content_range:
                    # Format: "0-24/25" or "*/0"
                    if '/' in content_range:
                        return int(content_range.split('/')[-1])
                return 0
            else:
                return -1  # Error
        except Exception as e:
            print(f"Error getting count for {table_name}: {e}")
            return -1
    
    def sample_table_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample records from a table"""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{table_name}?limit={limit}&order=created_at.desc",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Try without ordering in case created_at doesn't exist
                response = requests.get(
                    f"{self.url}/rest/v1/{table_name}?limit={limit}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
                return []
        except Exception as e:
            print(f"Error sampling data from {table_name}: {e}")
            return []

def main():
    # Load environment variables
    supabase_url = "https://ttwbilpwrzoizbthembb.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR0d2JpbHB3cnpvaXpidGhlbWJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDIxNjc3NCwiZXhwIjoyMDU5NzkyNzc0fQ.thB5A0wjzIO0GXQ9XXLU9tgQDu0MXk3cI4KoOShYlcs"
    
    explorer = SupabaseExplorer(supabase_url, service_key)
    
    print("=== SUPABASE V9B TRADING SYSTEM DATABASE EXPLORATION ===\n")
    
    # 1. Get all tables
    print("1. DISCOVERING TABLES...")
    tables = explorer.get_tables()
    print(f"\nFound {len(tables)} tables: {', '.join(tables)}\n")
    
    # 2. Analyze key tables
    key_tables = [
        'analyzed_stocks',
        'v9_multi_source_analysis', 
        'v9_session_metadata'
    ]
    
    # Add any trading/backtest related tables found
    trading_related = [t for t in tables if any(keyword in t.lower() 
                      for keyword in ['trade', 'backtest', 'portfolio', 'signal', 'position', 'log'])]
    
    key_tables.extend(trading_related)
    key_tables = list(set(key_tables))  # Remove duplicates
    
    print("2. ANALYZING KEY TABLES...")
    for table in key_tables:
        if table in tables:
            print(f"\n--- TABLE: {table} ---")
            
            # Get record count
            count = explorer.get_table_count(table)
            print(f"Record count: {count}")
            
            # Get schema
            schema = explorer.get_table_schema(table)
            if schema:
                print("Schema:")
                for column, info in schema.items():
                    print(f"  {column}: {info['type']}")
                    if info['sample_value']:
                        print(f"    Sample: {info['sample_value']}")
            
            # Get sample data
            sample_data = explorer.sample_table_data(table, 3)
            if sample_data:
                print(f"\nSample records ({len(sample_data)}):")
                for i, record in enumerate(sample_data, 1):
                    print(f"  Record {i}: {json.dumps(record, indent=4, default=str)}")
            
            print("-" * 50)
    
    # 3. Look for automated processes or system status
    print("\n3. CHECKING FOR AUTOMATED PROCESSES...")
    
    system_tables = [t for t in tables if any(keyword in t.lower() 
                    for keyword in ['status', 'job', 'schedule', 'process', 'task', 'cron'])]
    
    if system_tables:
        print(f"Found system-related tables: {', '.join(system_tables)}")
        for table in system_tables:
            sample = explorer.sample_table_data(table, 2)
            if sample:
                print(f"\n{table} sample:")
                print(json.dumps(sample, indent=2, default=str))
    else:
        print("No obvious system/automation tables found")
    
    # 4. Summary
    print("\n=== SUMMARY ===")
    print(f"Total tables discovered: {len(tables)}")
    print(f"Key tables analyzed: {len([t for t in key_tables if t in tables])}")
    print(f"Trading-related tables: {len(trading_related)}")
    print(f"System/automation tables: {len(system_tables)}")
    
    print("\nRecommendations for System X integration:")
    if 'analyzed_stocks' in tables:
        print("✓ Stock analysis data available")
    if any('backtest' in t.lower() for t in tables):
        print("✓ Backtesting infrastructure exists")
    if any('trade' in t.lower() for t in tables):
        print("✓ Trading logs/data available")
    if any('portfolio' in t.lower() for t in tables):
        print("✓ Portfolio tracking available")

if __name__ == "__main__":
    main()