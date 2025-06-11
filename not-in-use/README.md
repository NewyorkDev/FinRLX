# Not-In-Use Directory

This directory contains files that are no longer actively used in the FinRLX project but are kept for historical reference and potential future use.

## Directory Structure

### 📁 `legacy-traders/`
Previous trading system implementations that have been superseded by System X:
- `complete_finrl_trader.py` - Early comprehensive FinRL trading implementation
- `day_trading_main.py` - Original day trading main script
- `debug_trading.py` - Trading debugging utilities  
- `finrl_v9b_trader.py` - V9B integration trading system
- `fixed_day_trader.py` - Fixed version of day trader
- `production_day_trader.py` - Production day trading implementation
- `simple_day_trader.py` - Simple day trading system
- `launch_trading.py` - Trading launch script
- `day_trading_env.py` - Custom day trading environment
- `start_trading.sh` - Legacy trading startup script

### 📁 `supabase-utils/`
Supabase-related utility scripts:
- `supabase_data_processor.py` - Data processing utilities for Supabase

### 📁 `exploration-scripts/`
Scripts used for exploration and research:
- `explore_supabase.py` - Supabase database exploration
- `supabase_deep_dive.py` - Deep analysis of Supabase structure

### 📁 `analysis-tools/`
Analysis and reporting tools:
- `portfolio_analysis.py` - Portfolio analysis utilities

### 📁 `one-time-scripts/`
Scripts designed for one-time use (indicated by suffix):
- `check_and_create_tables_(one-time).py` - Table creation verification
- `create_supabase_tables_(one-time).py` - Initial table setup
- `test_supabase_connection_(one-time).py` - Connection testing

### 📁 `experimental-features/`
Experimental implementations that were tested but not adopted:
- `system_x_improvements.py` - Batch order coordination and momentum screening experiments
- `start_system_x_improved.sh` - Enhanced launcher script with PM2, Redis, and advanced features

## Active Systems

**Currently Active:**
- `system_x.py` - Main autonomous trading and backtesting system with Account Mode System
- `start_system_x.sh` - System X management script
- V9B system (separate repository)

## Notes

- Files in this directory are not actively maintained
- Before using any legacy code, check if equivalent functionality exists in System X
- Some scripts may require dependency updates to run with current environment
- One-time scripts were used during initial setup and typically don't need to be run again