# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinRL (Financial Reinforcement Learning) is a deep reinforcement learning framework for automated trading in quantitative finance. The project follows a three-layer architecture:

1. **Market Environments** (meta layer): Gym-style environments for financial markets
2. **Agents**: DRL algorithms (ElegantRL, Stable-Baselines3, RLLib)  
3. **Applications**: Domain-specific trading applications

## Core Architecture

### Three-Layer Framework
- **Meta Layer** (`finrl/meta/`): Core infrastructure for data processing and environments
- **Agent Layer** (`finrl/agents/`): DRL algorithm implementations
- **Application Layer** (`finrl/applications/`): Ready-to-use trading strategies

### Main Pipeline
The framework follows a **train-test-trade** pipeline:
- `finrl/train.py`: Train DRL models on historical data
- `finrl/test.py`: Backtest trained models  
- `finrl/trade.py`: Deploy models for live/paper trading
- `finrl/main.py`: Command-line interface orchestrating the pipeline

### Key Components
- **DataProcessor** (`finrl/meta/data_processor.py`): Unified interface for multiple data sources
- **Environment Classes** (`finrl/meta/env_*/`): Gym environments for different trading scenarios
- **DRL Agents** (`finrl/agents/`): Wrappers for different RL libraries

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test module  
pytest unit_tests/test_core.py

# Run tests with coverage
pytest --cov=finrl unit_tests/
```

### Code Quality
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Format code with black
black finrl/

# Check with flake8
flake8 finrl/

# Sort imports
isort finrl/
```

### Installation
```bash
# Install in development mode
pip install -e .

# Install with poetry
poetry install

# Install with specific DRL library
pip install -e .[elegantrl]
```

### Running Examples
```bash
# Train model
python finrl/main.py --mode=train

# Test/backtest model  
python finrl/main.py --mode=test

# Paper trading (requires API keys)
python finrl/main.py --mode=trade
```

## Configuration

### Key Config Files
- `finrl/config.py`: Core configuration (dates, parameters, data directories)
- `finrl/config_tickers.py`: Stock ticker lists (DOW_30_TICKER, etc.)
- `finrl/meta/meta_config.py`: Meta-layer specific configuration

### Environment Variables
For live trading, create `finrl/config_private.py`:
```python
ALPACA_API_KEY = "your_key"
ALPACA_API_SECRET = "your_secret"
```

## Data Sources

The framework supports multiple data providers via processor classes:
- **YahooFinance**: Default free provider (`processor_yahoofinance.py`)
- **Alpaca**: US stocks with real-time data (`processor_alpaca.py`)
- **WRDS**: Academic/institutional data (`processor_wrds.py`)
- **CCXT**: Cryptocurrency exchanges (`processor_ccxt.py`)

Each processor implements: `download_data()`, `clean_data()`, `add_technical_indicator()`, `add_vix()`

## DRL Libraries

The framework supports three DRL libraries:
1. **ElegantRL**: High-performance library optimized for finance (default)
2. **Stable-Baselines3**: Popular, well-documented library  
3. **RLLib**: Ray's distributed RL library

Agent selection via `drl_lib` parameter in train/test functions.

## Common Workflows

### Adding New Indicators
1. Extend technical indicator list in `config.py`
2. Implement in data processors using stockstats library
3. Update environment state space dimensions

### Creating New Environments
1. Inherit from `gym.Env` in `finrl/meta/env_*/`
2. Implement required methods: `reset()`, `step()`, `render()`
3. Define observation/action spaces and reward function

### Adding Data Sources
1. Create processor class in `finrl/meta/data_processors/`
2. Implement standard interface methods
3. Register in `DataProcessor.__init__()`

## File Organization

```
finrl/
├── main.py              # CLI entry point
├── train.py, test.py    # Core pipeline functions  
├── config.py            # Global configuration
├── meta/                # Core infrastructure
│   ├── data_processor.py         # Data source abstraction
│   ├── data_processors/          # Specific data source implementations
│   ├── env_stock_trading/        # Stock trading environments
│   ├── env_portfolio_*/          # Portfolio optimization environments
│   └── preprocessor/             # Legacy preprocessing utilities
├── agents/              # DRL algorithm wrappers
│   ├── elegantrl/       # ElegantRL integration
│   ├── stablebaselines3/# SB3 integration  
│   └── rllib/           # RLLib integration
└── applications/        # Ready-to-use strategies
    ├── stock_trading/   # Stock trading demos
    ├── portfolio_*/     # Portfolio optimization
    └── cryptocurrency_*/# Crypto trading
```

## Testing Strategy

- Unit tests in `unit_tests/` using pytest framework
- Integration tests cover data downloading and environment functionality
- Pre-commit hooks enforce code quality (black, flake8, import sorting)
- Test data uses small date ranges and ticker lists for speed