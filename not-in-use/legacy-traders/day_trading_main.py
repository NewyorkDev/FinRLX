#!/usr/bin/env python3
"""
FinRL Day Trading System with V9B Supabase Integration
Optimized for 30k Alpaca accounts
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add finrl to path
sys.path.append('/Users/francisclase/FinRLX')

from finrl.supabase_data_processor import supabase_processor
from finrl.day_trading_env import DayTradingEnv
from finrl.meta.data_processors.processor_alpaca import AlpacaProcessor
from finrl.meta.paper_trading.alpaca import PaperTradingAlpaca

# Stable Baselines3 for RL training
try:
    from stable_baselines3 import PPO, A2C
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.callbacks import BaseCallback
except ImportError:
    print("Installing stable-baselines3...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "stable-baselines3[extra]"], check=True)
    from stable_baselines3 import PPO, A2C
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.callbacks import BaseCallback

class TradingCallback(BaseCallback):
    """Callback for monitoring training progress"""
    
    def __init__(self, verbose=0):
        super(TradingCallback, self).__init__(verbose)
        self.episode_rewards = []
        
    def _on_step(self) -> bool:
        # Log progress every 1000 steps
        if self.n_calls % 1000 == 0:
            print(f"Training step: {self.n_calls}")
        return True

def prepare_training_data():
    """Prepare data for training the RL agent"""
    print("📊 Preparing training data...")
    
    # Get qualified stocks from V9B
    stock_list = supabase_processor.get_qualified_stocks(limit=5)
    if not stock_list:
        print("⚠️ No qualified stocks found, using defaults")
        stock_list = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    print(f"🎯 Trading universe: {stock_list}")
    
    # Generate training data (6 months)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    # Use Supabase processor to get synthetic training data
    data = supabase_processor.get_market_data_for_training(stock_list, start_date, end_date)
    
    if data.empty:
        print("⚠️ No training data available, generating synthetic data...")
        # Generate basic synthetic data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data_list = []
        
        for date in dates:
            for i, ticker in enumerate(stock_list):
                # Simple synthetic data
                price = 100 + i * 10 + np.random.normal(0, 5)
                data_list.append({
                    'date': date,
                    'tic': ticker,
                    'open': price,
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'close': price,
                    'volume': np.random.randint(100000, 1000000)
                })
        
        data = pd.DataFrame(data_list)
    
    # Add basic technical indicators
    data = add_technical_indicators(data)
    
    print(f"✅ Training data prepared: {len(data)} records")
    return data

def add_technical_indicators(data):
    """Add basic technical indicators to the data"""
    from stockstats import StockDataFrame as Sdf
    
    try:
        stock = Sdf.retype(data)
        
        # Add basic indicators
        indicators = ['macd', 'rsi_30', 'close_30_sma', 'close_60_sma']
        
        for indicator in indicators:
            try:
                _ = stock[indicator]  # This adds the indicator to the dataframe
            except:
                # If indicator calculation fails, add zeros
                data[indicator] = 0
        
        # Fill NaN values
        data = data.fillna(0)
        
    except Exception as e:
        print(f"Warning: Could not add technical indicators: {e}")
        # Add dummy indicators
        indicators = ['macd', 'rsi_30', 'close_30_sma', 'close_60_sma', 'boll_ub', 'boll_lb', 'cci_30', 'dx_30']
        for indicator in indicators:
            data[indicator] = 0
    
    return data

def train_agent():
    """Train the RL agent for day trading"""
    print("🤖 Training RL agent...")
    
    # Prepare data
    data = prepare_training_data()
    
    # Create environment
    env = DayTradingEnv(
        initial_amount=30000,
        max_stock=5,
        transaction_cost_pct=0.001,
        reward_scaling=1e-4
    )
    
    # Load data into environment
    env.load_data(data)
    
    # Wrap environment
    env = DummyVecEnv([lambda: env])
    
    # Create RL agent
    model = PPO(
        'MlpPolicy',
        env,
        verbose=1,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01
    )
    
    # Train the model
    print("🚀 Starting training...")
    callback = TradingCallback()
    model.learn(total_timesteps=50000, callback=callback)
    
    # Save the model
    model_path = "/Users/francisclase/FinRLX/trained_models/day_trading_model"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    
    print(f"✅ Model saved to {model_path}")
    return model

def test_agent():
    """Test the trained agent"""
    print("🧪 Testing trained agent...")
    
    model_path = "/Users/francisclase/FinRLX/trained_models/day_trading_model"
    
    if not os.path.exists(model_path + ".zip"):
        print("❌ No trained model found. Please train first.")
        return None
    
    # Load model
    model = PPO.load(model_path)
    
    # Prepare test data (last 30 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    stock_list = supabase_processor.get_qualified_stocks(limit=5)
    if not stock_list:
        stock_list = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    data = supabase_processor.get_market_data_for_training(stock_list, start_date, end_date)
    data = add_technical_indicators(data)
    
    # Create test environment
    env = DayTradingEnv(initial_amount=30000, max_stock=5)
    env.load_data(data)
    
    # Run test
    obs = env.reset()
    total_reward = 0
    done = False
    step = 0
    
    print("📈 Running backtest...")
    
    while not done and step < 100:  # Limit steps for testing
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        total_reward += reward
        step += 1
        
        if step % 10 == 0:
            print(f"Step {step}: Portfolio value: ${info['total_asset']:.2f}")
    
    final_return = (info['total_asset'] / 30000 - 1) * 100
    print(f"✅ Backtest completed:")
    print(f"   Final portfolio value: ${info['total_asset']:.2f}")
    print(f"   Total return: {final_return:.2f}%")
    print(f"   Total trades: {info['trades']}")
    
    return model

def start_live_trading():
    """Start live trading with Alpaca"""
    print("🚀 Starting live trading...")
    
    load_dotenv()
    
    # Check if model exists
    model_path = "/Users/francisclase/FinRLX/trained_models/day_trading_model"
    if not os.path.exists(model_path + ".zip"):
        print("❌ No trained model found. Training first...")
        train_agent()
    
    # Load model
    model = PPO.load(model_path)
    
    # Get trading parameters
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')
    api_base_url = os.getenv('ALPACA_API_BASE_URL')
    
    if not all([api_key, api_secret, api_base_url]):
        print("❌ Alpaca API credentials not found!")
        return
    
    # Get qualified stocks
    stock_list = supabase_processor.get_qualified_stocks(limit=5)
    if not stock_list:
        print("⚠️ No qualified stocks found, using defaults")
        stock_list = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    print(f"🎯 Live trading with: {stock_list}")
    
    # Technical indicators for live trading
    tech_indicators = ['macd', 'rsi_30', 'close_30_sma', 'close_60_sma']
    
    try:
        # Initialize paper trading
        paper_trading = PaperTradingAlpaca(
            ticker_list=stock_list,
            time_interval="1Min",
            drl_lib="stable_baselines3",
            agent="ppo",
            cwd=model_path,
            net_dim=512,
            state_dim=1 + len(stock_list) * 3 + len(stock_list) * len(tech_indicators),
            action_dim=len(stock_list),
            API_KEY=api_key,
            API_SECRET=api_secret,
            API_BASE_URL=api_base_url,
            tech_indicator_list=tech_indicators,
            turbulence_thresh=30,
            max_stock=100
        )
        
        print("✅ Paper trading initialized")
        print("🔄 Starting live trading loop...")
        
        # Run live trading
        paper_trading.run()
        
    except Exception as e:
        print(f"❌ Live trading error: {e}")
        print("💡 Try running in test mode first")

def main():
    """Main function"""
    print("🏆 FinRL Day Trading System with V9B Integration")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage: python day_trading_main.py [train|test|trade|check]")
        print("  train - Train the RL agent")
        print("  test  - Test the trained agent")
        print("  trade - Start live trading")
        print("  check - Check V9B data connection")
        return
    
    command = sys.argv[1].lower()
    
    if command == "check":
        print("🔍 Checking V9B data connection...")
        stocks = supabase_processor.get_qualified_stocks(limit=10)
        signals = supabase_processor.get_trading_signals()
        print(f"✅ Found {len(stocks)} qualified stocks")
        print(f"✅ Found {len(signals)} trading signals")
        print("🎯 Top candidates:", stocks[:5])
        
    elif command == "train":
        train_agent()
        
    elif command == "test":
        test_agent()
        
    elif command == "trade":
        start_live_trading()
        
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()