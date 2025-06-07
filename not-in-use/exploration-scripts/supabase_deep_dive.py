#!/usr/bin/env python3
"""
Deep dive into Supabase database structure for V9B trading system
This script performs more comprehensive discovery and analysis
"""

import requests
import json
import os
from typing import Dict, List, Any
from datetime import datetime, timedelta

class SupabaseDeepDive:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip('/')
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def discover_all_tables(self) -> List[str]:
        """Attempt comprehensive table discovery using multiple methods"""
        tables = set()
        
        # Method 1: Try common trading system table patterns
        potential_tables = [
            # Core trading tables
            'analyzed_stocks', 'v9_multi_source_analysis', 'v9_session_metadata',
            'backtest_results', 'trading_signals', 'portfolio_positions', 
            'trade_logs', 'trade_history', 'transactions',
            
            # Market data tables
            'market_data', 'price_data', 'stock_prices', 'historical_data',
            'real_time_quotes', 'options_data', 'crypto_data',
            
            # Analysis and research tables
            'technical_indicators', 'fundamental_data', 'sentiment_analysis',
            'news_data', 'earnings_data', 'analyst_ratings',
            
            # System and monitoring tables
            'system_status', 'system_logs', 'error_logs', 'audit_logs',
            'job_queue', 'scheduled_tasks', 'cron_jobs', 'monitoring',
            
            # User and session tables
            'users', 'user_sessions', 'api_keys', 'permissions',
            'user_preferences', 'watchlists', 'alerts',
            
            # Risk management tables
            'risk_metrics', 'position_limits', 'drawdown_history',
            'risk_alerts', 'compliance_logs',
            
            # Performance tracking
            'performance_metrics', 'returns_history', 'benchmark_data',
            'portfolio_snapshots', 'daily_pnl',
            
            # Configuration tables
            'strategies', 'strategy_parameters', 'market_settings',
            'trading_hours', 'holidays', 'exchanges',
            
            # V9-specific tables
            'v9_configs', 'v9_results', 'v9_analysis_history',
            'v9_bridge_logs', 'v9_scoring_history'
        ]
        
        print("Discovering tables...")
        for table in potential_tables:
            try:
                response = requests.get(
                    f"{self.url}/rest/v1/{table}?limit=1",
                    headers=self.headers,
                    timeout=5
                )
                if response.status_code in [200, 406]:  # 406 = exists but access limited
                    tables.add(table)
                    status = "✓" if response.status_code == 200 else "?"
                    print(f"{status} Found: {table}")
                    
            except Exception as e:
                continue
        
        return sorted(list(tables))
    
    def analyze_table_relationships(self, tables: List[str]) -> Dict[str, List[str]]:
        """Analyze potential relationships between tables"""
        relationships = {}
        
        for table in tables:
            try:
                # Get sample data to identify foreign keys
                response = requests.get(
                    f"{self.url}/rest/v1/{table}?limit=5",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        sample = data[0]
                        related_tables = []
                        
                        # Look for common foreign key patterns
                        for field, value in sample.items():
                            if field.endswith('_id') and field != 'id':
                                potential_table = field.replace('_id', 's')
                                if potential_table in tables:
                                    related_tables.append(potential_table)
                            
                            # Look for session_id references
                            if 'session' in field.lower():
                                related_tables.append('sessions')
                        
                        relationships[table] = related_tables
                        
            except Exception as e:
                continue
        
        return relationships
    
    def get_recent_activity(self, table: str, days: int = 7) -> Dict[str, Any]:
        """Get recent activity statistics for a table"""
        try:
            # Try to get records from last N days
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            response = requests.get(
                f"{self.url}/rest/v1/{table}?created_at=gte.{cutoff_date}&order=created_at.desc",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'recent_count': len(data),
                    'latest_entry': data[0]['created_at'] if data else None,
                    'active': len(data) > 0
                }
        except:
            pass
        
        return {'recent_count': 0, 'latest_entry': None, 'active': False}
    
    def analyze_data_patterns(self, table: str) -> Dict[str, Any]:
        """Analyze data patterns in a table"""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{table}?limit=10&order=created_at.desc",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    return {'pattern': 'empty_table'}
                
                # Analyze patterns
                analysis = {
                    'sample_size': len(data),
                    'has_timestamps': any('created_at' in record for record in data),
                    'has_session_id': any('session_id' in record for record in data),
                    'unique_sessions': len(set(r.get('session_id', '') for r in data)) if any('session_id' in record for record in data) else 0,
                    'date_range': None
                }
                
                # Get date range if timestamps exist
                if analysis['has_timestamps']:
                    timestamps = [r['created_at'] for r in data if 'created_at' in r]
                    if timestamps:
                        analysis['date_range'] = {
                            'earliest': min(timestamps),
                            'latest': max(timestamps)
                        }
                
                return analysis
                
        except Exception as e:
            return {'error': str(e)}
    
    def check_system_automation(self, tables: List[str]) -> Dict[str, Any]:
        """Check for signs of automated processes"""
        automation_indicators = {}
        
        # Look for regular patterns in data creation
        for table in tables:
            try:
                # Get recent records with timestamps
                response = requests.get(
                    f"{self.url}/rest/v1/{table}?order=created_at.desc&limit=20",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and 'created_at' in data[0]:
                        timestamps = [r['created_at'] for r in data]
                        
                        # Check for regular intervals
                        intervals = []
                        for i in range(1, len(timestamps)):
                            try:
                                t1 = datetime.fromisoformat(timestamps[i-1].replace('Z', '+00:00'))
                                t2 = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
                                intervals.append(abs((t1 - t2).total_seconds()))
                            except:
                                continue
                        
                        if intervals:
                            avg_interval = sum(intervals) / len(intervals)
                            
                            # Detect patterns
                            pattern = 'irregular'
                            if 3500 <= avg_interval <= 3700:  # ~1 hour
                                pattern = 'hourly'
                            elif 85000 <= avg_interval <= 90000:  # ~24 hours
                                pattern = 'daily'
                            elif 580000 <= avg_interval <= 620000:  # ~weekly
                                pattern = 'weekly'
                            
                            automation_indicators[table] = {
                                'avg_interval_seconds': avg_interval,
                                'pattern': pattern,
                                'sample_count': len(intervals),
                                'likely_automated': pattern != 'irregular'
                            }
                            
            except Exception as e:
                continue
        
        return automation_indicators

def main():
    # Load environment variables
    supabase_url = "https://ttwbilpwrzoizbthembb.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR0d2JpbHB3cnpvaXpidGhlbWJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDIxNjc3NCwiZXhwIjoyMDU5NzkyNzc0fQ.thB5A0wjzIO0GXQ9XXLU9tgQDu0MXk3cI4KoOShYlcs"
    
    explorer = SupabaseDeepDive(supabase_url, service_key)
    
    print("=== COMPREHENSIVE SUPABASE V9B SYSTEM ANALYSIS ===\n")
    
    # 1. Comprehensive table discovery
    print("1. COMPREHENSIVE TABLE DISCOVERY")
    print("=" * 50)
    tables = explorer.discover_all_tables()
    print(f"\nTotal tables found: {len(tables)}")
    print(f"Tables: {', '.join(tables)}\n")
    
    # 2. Analyze table relationships
    print("2. TABLE RELATIONSHIP ANALYSIS")
    print("=" * 50)
    relationships = explorer.analyze_table_relationships(tables)
    for table, related in relationships.items():
        if related:
            print(f"{table} -> {', '.join(related)}")
    print()
    
    # 3. Recent activity analysis
    print("3. RECENT ACTIVITY ANALYSIS (Last 7 days)")
    print("=" * 50)
    for table in tables:
        activity = explorer.get_recent_activity(table, 7)
        status = "🟢" if activity['active'] else "🔴"
        print(f"{status} {table}: {activity['recent_count']} records")
        if activity['latest_entry']:
            print(f"   Latest: {activity['latest_entry']}")
    print()
    
    # 4. Data pattern analysis
    print("4. DATA PATTERN ANALYSIS")
    print("=" * 50)
    for table in tables:
        patterns = explorer.analyze_data_patterns(table)
        print(f"\n--- {table} ---")
        if 'error' in patterns:
            print(f"Error: {patterns['error']}")
        else:
            print(f"Sample size: {patterns.get('sample_size', 0)}")
            print(f"Has timestamps: {patterns.get('has_timestamps', False)}")
            print(f"Has session tracking: {patterns.get('has_session_id', False)}")
            if patterns.get('unique_sessions'):
                print(f"Unique sessions: {patterns['unique_sessions']}")
            if patterns.get('date_range'):
                print(f"Date range: {patterns['date_range']['earliest']} to {patterns['date_range']['latest']}")
    
    # 5. Automation detection
    print("\n\n5. AUTOMATION DETECTION")
    print("=" * 50)
    automation = explorer.check_system_automation(tables)
    if automation:
        for table, info in automation.items():
            automated = "🤖" if info['likely_automated'] else "👤"
            print(f"{automated} {table}: {info['pattern']} pattern")
            print(f"   Avg interval: {info['avg_interval_seconds']:.1f} seconds")
    else:
        print("No clear automation patterns detected")
    
    # 6. System X Integration Assessment
    print("\n\n6. SYSTEM X INTEGRATION ASSESSMENT")
    print("=" * 50)
    
    capabilities = {
        'stock_analysis': 'analyzed_stocks' in tables,
        'multi_source_analysis': 'v9_multi_source_analysis' in tables,
        'session_tracking': 'v9_session_metadata' in tables,
        'backtesting': 'backtest_results' in tables,
        'real_time_data': any('real_time' in t for t in tables),
        'trading_logs': any('trade' in t and 'log' in t for t in tables),
        'portfolio_tracking': any('portfolio' in t for t in tables),
        'risk_management': any('risk' in t for t in tables),
        'system_monitoring': any(t in ['system_status', 'system_logs', 'monitoring'] for t in tables)
    }
    
    print("Current capabilities:")
    for capability, available in capabilities.items():
        status = "✅" if available else "❌"
        print(f"{status} {capability.replace('_', ' ').title()}")
    
    print("\nRecommended System X enhancements:")
    if not capabilities['trading_logs']:
        print("- Create comprehensive trading logs table")
    if not capabilities['portfolio_tracking']:
        print("- Add portfolio positions tracking")
    if not capabilities['risk_management']:
        print("- Implement risk metrics and monitoring")
    if not capabilities['system_monitoring']:
        print("- Add system status and health monitoring")
    if not capabilities['real_time_data']:
        print("- Consider real-time market data integration")
    
    # 7. Data volume and growth analysis
    print("\n\n7. DATA VOLUME ANALYSIS")
    print("=" * 50)
    total_recent_activity = sum(explorer.get_recent_activity(table, 7)['recent_count'] for table in tables)
    daily_avg = total_recent_activity / 7
    
    print(f"Total records created in last 7 days: {total_recent_activity}")
    print(f"Average daily record creation: {daily_avg:.1f}")
    
    # Estimate storage needs
    if daily_avg > 0:
        monthly_estimate = daily_avg * 30
        yearly_estimate = daily_avg * 365
        print(f"Estimated monthly records: {monthly_estimate:.0f}")
        print(f"Estimated yearly records: {yearly_estimate:.0f}")

if __name__ == "__main__":
    main()