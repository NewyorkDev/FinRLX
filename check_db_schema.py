#!/opt/homebrew/bin/python3.12

import os
from supabase import create_client

def load_environment():
    """Load environment variables from the_end/.env file"""
    env_file = os.path.join(os.path.dirname(__file__), 'the_end', '.env')
    env_vars = {}
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
                os.environ[key] = value
    return env_vars

def main():
    print('🔍 CHECKING DATABASE SCHEMA')
    print('=' * 60)
    
    # Load environment
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Check analyzed_stocks table structure
    try:
        result = supabase.table('analyzed_stocks').select('*').limit(1).execute()
        if result.data:
            print('📊 ANALYZED_STOCKS TABLE COLUMNS:')
            for col in sorted(result.data[0].keys()):
                print(f'   ✅ {col}')
                
            # Show sample data
            print('\n📋 SAMPLE DATA:')
            sample = result.data[0]
            for key, value in sample.items():
                print(f'   {key}: {value}')
        else:
            print('❌ No data in analyzed_stocks table')
    except Exception as e:
        print(f'❌ Error checking analyzed_stocks: {e}')
    
    print('\n' + '=' * 60)
    
    # Check v9_multi_source_analysis table structure  
    try:
        result = supabase.table('v9_multi_source_analysis').select('*').limit(1).execute()
        if result.data:
            print('📈 V9_MULTI_SOURCE_ANALYSIS TABLE COLUMNS:')
            for col in sorted(result.data[0].keys()):
                print(f'   ✅ {col}')
                
            # Show sample data
            print('\n📋 SAMPLE DATA:')
            sample = result.data[0]
            for key, value in sample.items():
                print(f'   {key}: {value}')
        else:
            print('❌ No data in v9_multi_source_analysis table')
    except Exception as e:
        print(f'❌ Error checking v9_multi_source_analysis: {e}')
    
    print('\n' + '=' * 60)
    print('🎯 CHECKING FOR HIGH-PERFORMING STOCKS WITH ACTUAL SCORES')
    
    # Try different column names that might exist
    possible_score_columns = ['score', 'dts_score', 'v9_score', 'analysis_score', 'momentum_score']
    
    for col in possible_score_columns:
        try:
            result = supabase.table('analyzed_stocks').select(f'ticker, {col}').not_.is_(col, 'null').gte(col, 70).limit(5).execute()
            if result.data:
                print(f'\n📈 STOCKS WITH HIGH {col.upper()}:')
                for stock in result.data:
                    print(f'   {stock["ticker"]}: {stock[col]}')
        except Exception as e:
            print(f'❌ Column {col} not found or error: {e}')

if __name__ == "__main__":
    main()