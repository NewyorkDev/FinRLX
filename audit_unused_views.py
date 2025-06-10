#!/opt/homebrew/bin/python3.12
"""
SUPABASE VIEWS AUDIT - Identify unused views for cleanup
"""

import os
import subprocess
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

def get_all_views(supabase):
    """Get all views in the database"""
    try:
        result = supabase.rpc('sql', {
            'query': """
            SELECT table_name as view_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'VIEW'
            ORDER BY table_name;
            """
        }).execute()
        return [row['view_name'] for row in result.data] if result.data else []
    except:
        # Fallback - get from previous query
        return [
            'account_performance_summary', 'backtest_summary', 'closed_positions_performance',
            'component_availability', 'current_multi_losers', 'dts_component_breakdown',
            'error_summary', 'google_search_quota_status', 'health_performance_correlation',
            'high_confidence_predictions', 'latest_account_performance', 'latest_analysis',
            'latest_gpt_strategies', 'latest_hot_stocks', 'latest_model_predictions',
            'latest_system_health', 'latest_trading_performance', 'model_performance_analysis',
            'open_positions', 'position_summary_by_ticker', 'qualified_day_trading_stocks',
            'strategy_performance_summary', 'system_health_trends', 'ticker_prediction_accuracy',
            'top_hot_stocks', 'top_stocks_by_session', 'top_strategies', 'v9_data_source_coverage',
            'v9_latest_analysis_summary', 'v9_news_impact_analysis', 'v9_sentiment_summary',
            'weekly_performance_summary'
        ]

def check_view_references(view_name):
    """Check if a view is referenced in the codebase"""
    try:
        result = subprocess.run(
            ['grep', '-r', view_name, '.', '--include=*.py', '--include=*.js', '--include=*.sql', '--include=*.md'],
            capture_output=True, text=True, cwd='.'
        )
        return len(result.stdout.strip()) > 0
    except:
        return False

def main():
    """Audit views for cleanup"""
    print("🔍 SUPABASE VIEWS AUDIT - CLEANUP ANALYSIS")
    print("=" * 60)
    
    env_vars = load_environment()
    if not env_vars:
        print("❌ Failed to load environment")
        return
    
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    views = get_all_views(supabase)
    
    print(f"📊 Found {len(views)} views to analyze")
    
    used_views = []
    unused_views = []
    
    for view in views:
        print(f"🔍 Checking: {view}")
        is_referenced = check_view_references(view)
        
        if is_referenced:
            used_views.append(view)
            print(f"   ✅ USED - Found references in codebase")
        else:
            unused_views.append(view)
            print(f"   ❌ UNUSED - No references found")
    
    print("\n" + "=" * 60)
    print("📊 CLEANUP RECOMMENDATIONS")
    print("-" * 30)
    
    print(f"\n✅ KEEP ({len(used_views)} views):")
    for view in used_views:
        print(f"   {view}")
    
    print(f"\n🗑️ POTENTIAL DELETE ({len(unused_views)} views):")
    for view in unused_views:
        print(f"   {view}")
    
    if unused_views:
        print(f"\n🚨 DELETION COMMANDS (review carefully before running):")
        for view in unused_views:
            print(f"   DROP VIEW IF EXISTS {view};")
        
        print(f"\n⚠️ WARNING: Review these views manually before deletion!")
        print("   Some views might be used by external tools or dashboards.")
    else:
        print("\n✨ All views appear to be referenced in the codebase!")

if __name__ == "__main__":
    main()