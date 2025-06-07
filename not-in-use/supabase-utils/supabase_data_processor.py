"""
Supabase Data Processor for FinRL
Integrates V9B trading system data with FinRL environment
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

class SupabaseDataProcessor:
    """
    Data processor that fetches qualified trading candidates from V9B Supabase system
    """
    
    def __init__(self):
        load_dotenv()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.min_dts_score = float(os.getenv('MIN_DTS_SCORE', 60))
        
    def get_qualified_stocks(self, limit: int = 10) -> List[str]:
        """
        Get qualified stocks for day trading based on DTS scores
        
        Args:
            limit: Maximum number of stocks to return
            
        Returns:
            List of ticker symbols
        """
        try:
            # Get stocks with DTS scores above threshold, ordered by score
            response = self.client.table('analyzed_stocks').select(
                'ticker, dts_score, dts_qualification, dts_momentum_grade, dts_risk_level'
            ).gte('dts_score', self.min_dts_score).order('dts_score', desc=True).limit(limit).execute()
            
            if response.data:
                # Filter out test stocks and return real tickers
                qualified_stocks = []
                for stock in response.data:
                    ticker = stock.get('ticker', '')
                    if ticker and not ticker.startswith('TEST'):
                        qualified_stocks.append(ticker)
                
                print(f"Found {len(qualified_stocks)} qualified stocks for trading")
                return qualified_stocks[:limit]
            else:
                print("No qualified stocks found")
                return []
                
        except Exception as e:
            print(f"Error fetching qualified stocks: {e}")
            return []
    
    def get_stock_analysis(self, ticker: str) -> Dict:
        """
        Get detailed analysis for a specific stock
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dict with stock analysis data
        """
        try:
            response = self.client.table('v9_multi_source_analysis').select(
                '*'
            ).eq('ticker', ticker).order('created_at', desc=True).limit(1).execute()
            
            if response.data:
                return response.data[0]
            else:
                return {}
                
        except Exception as e:
            print(f"Error fetching analysis for {ticker}: {e}")
            return {}
    
    def get_market_data_for_training(self, ticker_list: List[str], 
                                   start_date: str, end_date: str) -> pd.DataFrame:
        """
        Generate synthetic market data for training based on V9B analysis
        This is a placeholder - in production you would use real historical data
        
        Args:
            ticker_list: List of stock symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            DataFrame with OHLCV data
        """
        # For now, generate synthetic data based on current prices from V9B
        data_list = []
        
        for ticker in ticker_list:
            try:
                # Get latest price from v9_scraped_stocks
                response = self.client.table('v9_scraped_stocks').select(
                    'ticker, price, volume'
                ).eq('ticker', ticker).order('created_at', desc=True).limit(1).execute()
                
                if response.data:
                    current_price = float(response.data[0].get('price', 100))
                    current_volume = int(response.data[0].get('volume', 1000000))
                else:
                    current_price = 100.0  # Default price
                    current_volume = 1000000  # Default volume
                
                # Generate date range
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                
                # Generate synthetic OHLCV data with some volatility
                np.random.seed(42)  # For reproducible results
                
                prices = []
                base_price = current_price
                
                for i, date in enumerate(dates):
                    # Add some random walk to price
                    daily_return = np.random.normal(0, 0.02)  # 2% daily volatility
                    base_price *= (1 + daily_return)
                    
                    # Generate OHLC from base price
                    high_mult = 1 + abs(np.random.normal(0, 0.01))
                    low_mult = 1 - abs(np.random.normal(0, 0.01))
                    
                    open_price = base_price * np.random.uniform(0.99, 1.01)
                    high_price = base_price * high_mult
                    low_price = base_price * low_mult
                    close_price = base_price
                    volume = current_volume * np.random.uniform(0.5, 2.0)
                    
                    data_list.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'tic': ticker,
                        'open': round(open_price, 2),
                        'high': round(high_price, 2),
                        'low': round(low_price, 2),
                        'close': round(close_price, 2),
                        'volume': int(volume)
                    })
                    
            except Exception as e:
                print(f"Error generating data for {ticker}: {e}")
                continue
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['tic', 'date']).reset_index(drop=True)
        
        return df
    
    def get_real_time_data(self, ticker_list: List[str]) -> pd.DataFrame:
        """
        Get real-time data from V9B system
        
        Args:
            ticker_list: List of stock symbols
            
        Returns:
            DataFrame with current market data
        """
        data_list = []
        
        for ticker in ticker_list:
            try:
                # Get latest data from v9_scraped_stocks
                response = self.client.table('v9_scraped_stocks').select(
                    '*'
                ).eq('ticker', ticker).order('created_at', desc=True).limit(1).execute()
                
                if response.data:
                    stock_data = response.data[0]
                    current_time = datetime.now()
                    
                    # Extract price and volume
                    price = float(stock_data.get('price', 0))
                    volume = int(stock_data.get('volume', 0))
                    
                    data_list.append({
                        'timestamp': current_time,
                        'tic': ticker,
                        'open': price,
                        'high': price * 1.01,  # Simulate high
                        'low': price * 0.99,   # Simulate low
                        'close': price,
                        'volume': volume
                    })
                    
            except Exception as e:
                print(f"Error fetching real-time data for {ticker}: {e}")
                continue
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df = df.sort_values(['tic', 'timestamp']).reset_index(drop=True)
        
        return df
    
    def get_trading_signals(self) -> Dict[str, float]:
        """
        Get trading signals based on V9B analysis
        
        Returns:
            Dict mapping ticker to confidence score (0-1)
        """
        signals = {}
        
        try:
            # Get latest analysis with high confidence scores
            response = self.client.table('v9_multi_source_analysis').select(
                'ticker, claude_confidence_score, dts_score'
            ).gte('dts_score', self.min_dts_score).execute()
            
            if response.data:
                for analysis in response.data:
                    ticker = analysis.get('ticker')
                    confidence = analysis.get('claude_confidence_score', 0)
                    dts_score = analysis.get('dts_score', 0)
                    
                    if ticker and not ticker.startswith('TEST'):
                        # Combine confidence and DTS score for signal strength
                        signal_strength = (float(confidence) * 0.6 + float(dts_score) * 0.4) / 100
                        signals[ticker] = min(signal_strength, 1.0)
            
        except Exception as e:
            print(f"Error fetching trading signals: {e}")
        
        return signals
    
    def update_trading_performance(self, ticker: str, action: str, 
                                 quantity: int, price: float, 
                                 portfolio_value: float) -> bool:
        """
        Update trading performance back to Supabase
        
        Args:
            ticker: Stock symbol
            action: 'buy' or 'sell'
            quantity: Number of shares
            price: Execution price
            portfolio_value: Current portfolio value
            
        Returns:
            True if successful
        """
        try:
            # Insert trading record
            trade_data = {
                'ticker': ticker,
                'action': action,
                'quantity': quantity,
                'price': price,
                'portfolio_value': portfolio_value,
                'timestamp': datetime.now().isoformat(),
                'source': 'finrl_day_trading'
            }
            
            # Note: You may need to create a trading_records table in Supabase
            response = self.client.table('trading_records').insert(trade_data).execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating trading performance: {e}")
            return False

# Global instance
supabase_processor = SupabaseDataProcessor()