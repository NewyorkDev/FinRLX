"""
Day Trading Environment for FinRL with Supabase Integration
Optimized for 30k account with V9B stock selection
"""

import numpy as np
import pandas as pd
import gym
from gym import spaces
from typing import List, Dict
import os
from dotenv import load_dotenv

from finrl.supabase_data_processor import supabase_processor
from finrl.meta.data_processors.processor_alpaca import AlpacaProcessor

class DayTradingEnv(gym.Env):
    """
    Day Trading Environment with Supabase V9B Integration
    """
    
    def __init__(self, 
                 initial_amount: float = 30000,
                 max_stock: int = 5,
                 transaction_cost_pct: float = 0.001,
                 reward_scaling: float = 1e-4,
                 tech_indicator_list: List[str] = None):
        
        load_dotenv()
        
        # Environment parameters
        self.initial_amount = initial_amount
        self.max_stock = max_stock
        self.transaction_cost_pct = transaction_cost_pct
        self.reward_scaling = reward_scaling
        
        # Get qualified stocks from V9B system
        self.stock_list = supabase_processor.get_qualified_stocks(limit=max_stock)
        if not self.stock_list:
            # Fallback to default stocks if none found
            self.stock_list = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'][:max_stock]
        
        print(f"Trading universe: {self.stock_list}")
        
        self.stock_dim = len(self.stock_list)
        
        # Technical indicators
        if tech_indicator_list is None:
            self.tech_indicator_list = [
                "macd", "boll_ub", "boll_lb", "rsi_30", "cci_30", "dx_30",
                "close_30_sma", "close_60_sma"
            ]
        else:
            self.tech_indicator_list = tech_indicator_list
        
        self.tech_dim = len(self.tech_indicator_list)
        
        # State: [cash, stock_owned_1, ..., stock_owned_n, stock_price_1, ..., stock_price_n, tech_indicators]
        self.state_dim = 1 + self.stock_dim + self.stock_dim + self.stock_dim * self.tech_dim
        
        # Action: [action_stock_1, ..., action_stock_n]
        # Action values: -1 (sell all), 0 (hold), 1 (buy with available cash)
        self.action_dim = self.stock_dim
        
        # Gym spaces
        self.action_space = spaces.Box(low=-1, high=1, shape=(self.action_dim,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32)
        
        # Initialize state variables
        self.data = None
        self.current_step = 0
        self.cash = self.initial_amount
        self.stock_owned = np.zeros(self.stock_dim)
        self.stock_price = np.zeros(self.stock_dim)
        self.total_asset = self.initial_amount
        
        # For tracking
        self.asset_memory = [self.initial_amount]
        self.rewards_memory = []
        self.actions_memory = []
        self.trades = 0
        
        # Risk management
        self.position_size_pct = float(os.getenv('POSITION_SIZE_PERCENT', 0.15))  # 15% max per position
        self.stop_loss_pct = float(os.getenv('STOP_LOSS_PERCENT', 0.05))  # 5% stop loss
        self.take_profit_pct = float(os.getenv('TAKE_PROFIT_PERCENT', 0.10))  # 10% take profit
        
    def load_data(self, data: pd.DataFrame):
        """Load market data for the environment"""
        self.data = data.copy()
        self.data = self.data.sort_values(['date', 'tic']).reset_index(drop=True)
        
        # Get unique dates
        self.dates = self.data['date'].unique()
        self.total_steps = len(self.dates) - 1
        
        print(f"Loaded data: {len(self.data)} records, {len(self.dates)} trading days")
        
    def reset(self):
        """Reset the environment to initial state"""
        self.current_step = 0
        self.cash = self.initial_amount
        self.stock_owned = np.zeros(self.stock_dim)
        self.total_asset = self.initial_amount
        self.asset_memory = [self.initial_amount]
        self.rewards_memory = []
        self.actions_memory = []
        self.trades = 0
        
        return self._get_obs()
    
    def step(self, actions):
        """Execute one time step within the environment"""
        if self.current_step >= self.total_steps:
            return self._get_obs(), 0, True, {}
        
        # Get current market data
        current_date = self.dates[self.current_step]
        current_data = self.data[self.data['date'] == current_date]
        
        # Update stock prices
        for i, tic in enumerate(self.stock_list):
            stock_data = current_data[current_data['tic'] == tic]
            if not stock_data.empty:
                self.stock_price[i] = stock_data['close'].iloc[0]
        
        # Execute actions
        self._execute_actions(actions)
        
        # Calculate total asset value
        self.total_asset = self.cash + np.sum(self.stock_owned * self.stock_price)
        self.asset_memory.append(self.total_asset)
        
        # Calculate reward
        reward = self._calculate_reward()
        self.rewards_memory.append(reward)
        self.actions_memory.append(actions)
        
        # Move to next step
        self.current_step += 1
        
        # Check if done
        done = self.current_step >= self.total_steps
        
        # Info dict
        info = {
            'total_asset': self.total_asset,
            'cash': self.cash,
            'stock_owned': self.stock_owned.copy(),
            'stock_price': self.stock_price.copy(),
            'trades': self.trades
        }
        
        return self._get_obs(), reward, done, info
    
    def _execute_actions(self, actions):
        """Execute trading actions"""
        actions = np.array(actions)
        
        # Apply V9B trading signals for additional confirmation
        trading_signals = supabase_processor.get_trading_signals()
        
        for i, action in enumerate(actions):
            tic = self.stock_list[i]
            current_price = self.stock_price[i]
            
            if current_price == 0:  # Skip if no price data
                continue
            
            # Get V9B signal strength (0-1)
            signal_strength = trading_signals.get(tic, 0.5)
            
            # Modify action based on V9B signals
            if signal_strength < 0.3:  # Weak signal, reduce action strength
                action *= 0.5
            elif signal_strength > 0.8:  # Strong signal, boost action strength
                action *= 1.2
            
            # Execute trade based on action
            if action > 0.1:  # Buy signal
                self._execute_buy(i, action, current_price)
            elif action < -0.1:  # Sell signal
                self._execute_sell(i, abs(action), current_price)
    
    def _execute_buy(self, stock_idx: int, action_strength: float, price: float):
        """Execute buy order with risk management"""
        if price == 0 or self.cash < price:
            return
        
        # Calculate position size based on risk management
        max_position_value = self.total_asset * self.position_size_pct
        available_cash_for_position = min(self.cash, max_position_value)
        
        # Calculate shares to buy
        shares_to_buy = int((available_cash_for_position * action_strength) // price)
        
        if shares_to_buy > 0:
            # Calculate transaction cost
            transaction_value = shares_to_buy * price
            transaction_cost = transaction_value * self.transaction_cost_pct
            total_cost = transaction_value + transaction_cost
            
            if self.cash >= total_cost:
                self.cash -= total_cost
                self.stock_owned[stock_idx] += shares_to_buy
                self.trades += 1
                
                # Update performance in Supabase
                supabase_processor.update_trading_performance(
                    self.stock_list[stock_idx], 'buy', shares_to_buy, price, self.total_asset
                )
    
    def _execute_sell(self, stock_idx: int, action_strength: float, price: float):
        """Execute sell order"""
        if self.stock_owned[stock_idx] == 0 or price == 0:
            return
        
        # Calculate shares to sell
        shares_to_sell = int(self.stock_owned[stock_idx] * action_strength)
        
        if shares_to_sell > 0:
            # Calculate transaction proceeds
            transaction_value = shares_to_sell * price
            transaction_cost = transaction_value * self.transaction_cost_pct
            proceeds = transaction_value - transaction_cost
            
            self.cash += proceeds
            self.stock_owned[stock_idx] -= shares_to_sell
            self.trades += 1
            
            # Update performance in Supabase
            supabase_processor.update_trading_performance(
                self.stock_list[stock_idx], 'sell', shares_to_sell, price, self.total_asset
            )
    
    def _calculate_reward(self):
        """Calculate reward based on portfolio performance"""
        if len(self.asset_memory) < 2:
            return 0
        
        # Portfolio return
        portfolio_return = (self.total_asset - self.asset_memory[-2]) / self.asset_memory[-2]
        
        # Risk-adjusted reward
        reward = portfolio_return * self.reward_scaling
        
        # Penalty for excessive trading
        if self.trades > 0:
            trade_penalty = min(self.trades * 0.001, 0.01)  # Max 1% penalty
            reward -= trade_penalty
        
        return reward
    
    def _get_obs(self):
        """Get current observation"""
        if self.data is None or self.current_step >= len(self.dates):
            # Return zero state if no data
            return np.zeros(self.state_dim, dtype=np.float32)
        
        # Get current market data
        current_date = self.dates[self.current_step]
        current_data = self.data[self.data['date'] == current_date]
        
        # Cash (normalized)
        cash_normalized = self.cash / self.initial_amount
        
        # Stock owned (normalized)
        stock_owned_normalized = self.stock_owned / 100  # Normalize by typical position size
        
        # Stock prices (normalized)
        stock_prices_normalized = self.stock_price / 1000  # Normalize by typical price range
        
        # Technical indicators
        tech_indicators = []
        for tic in self.stock_list:
            stock_data = current_data[current_data['tic'] == tic]
            if not stock_data.empty:
                for indicator in self.tech_indicator_list:
                    if indicator in stock_data.columns:
                        tech_indicators.append(stock_data[indicator].iloc[0])
                    else:
                        tech_indicators.append(0.0)
            else:
                tech_indicators.extend([0.0] * self.tech_dim)
        
        # Combine all state components
        state = np.concatenate([
            [cash_normalized],
            stock_owned_normalized,
            stock_prices_normalized,
            tech_indicators
        ])
        
        # Ensure state has correct dimensions
        if len(state) != self.state_dim:
            state = np.pad(state, (0, max(0, self.state_dim - len(state))))[:self.state_dim]
        
        return state.astype(np.float32)
    
    def render(self, mode='human'):
        """Render the environment"""
        if len(self.asset_memory) > 1:
            print(f"Step: {self.current_step}")
            print(f"Total Asset: ${self.total_asset:.2f}")
            print(f"Cash: ${self.cash:.2f}")
            print(f"Portfolio Return: {(self.total_asset / self.initial_amount - 1) * 100:.2f}%")
            print(f"Trades: {self.trades}")
            print("-" * 50)