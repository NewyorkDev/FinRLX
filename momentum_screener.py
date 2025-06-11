#!/opt/homebrew/bin/python3.12
"""
Momentum Screener - Catch Daily High-Gain Opportunities
======================================================

Addresses the critical gap: All accounts missed today's major gainers
BULLZ +53.19%, NKTR +29.12%, INSM +28.65%, BGM +23.75%, MTSR +15.50%

Even small positions in these would have dramatically improved performance.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import alpaca_trade_api as tradeapi
import logging
from dataclasses import dataclass

@dataclass
class MomentumOpportunity:
    """Represents a high-momentum trading opportunity"""
    ticker: str
    current_price: float
    change_percent: float
    volume: int
    volume_ratio: float  # Current volume vs average
    market_cap: Optional[float]
    momentum_score: float
    entry_confidence: float
    risk_level: str
    recommended_position_size: float

class MomentumScreener:
    """Identifies high-momentum stocks for immediate trading opportunities"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # Momentum thresholds based on today's missed opportunities
        self.momentum_thresholds = {
            'extreme_momentum': 25.0,   # BULLZ +53% level
            'high_momentum': 15.0,      # MTSR +15% level  
            'moderate_momentum': 8.0,   # Strong but manageable
            'min_momentum': 5.0         # Minimum consideration
        }
        
        # Volume requirements
        self.volume_thresholds = {
            'min_volume': 100000,       # Minimum daily volume
            'volume_spike_ratio': 2.0,  # 2x average volume
            'high_volume_ratio': 5.0    # 5x average for extreme confidence
        }
        
        # Risk management
        self.position_size_caps = {
            'extreme_momentum': 0.08,   # 8% max for 25%+ gainers
            'high_momentum': 0.12,      # 12% max for 15%+ gainers
            'moderate_momentum': 0.15,  # 15% max for 8%+ gainers
        }
    
    def scan_for_momentum_opportunities(self, 
                                     min_change_percent: float = 8.0,
                                     max_results: int = 20) -> List[MomentumOpportunity]:
        """Scan for high-momentum trading opportunities"""
        try:
            if self.debug:
                self.logger.info(f"🔍 Scanning for momentum opportunities (min +{min_change_percent}%)")
            
            # Get top gainers from multiple sources
            opportunities = []
            
            # Source 1: Yahoo Finance trending tickers
            trending_tickers = self._get_yahoo_trending_tickers()
            
            # Source 2: Predefined high-momentum watchlist
            momentum_watchlist = self._get_momentum_watchlist()
            
            # Combine all tickers for analysis
            all_tickers = list(set(trending_tickers + momentum_watchlist))
            
            if self.debug:
                self.logger.info(f"   Analyzing {len(all_tickers)} tickers for momentum")
            
            # Analyze each ticker
            for ticker in all_tickers[:50]:  # Limit to avoid rate limits
                try:
                    opportunity = self._analyze_ticker_momentum(ticker)
                    
                    if opportunity and opportunity.change_percent >= min_change_percent:
                        opportunities.append(opportunity)
                        
                        if self.debug:
                            self.logger.info(f"   📈 {ticker}: +{opportunity.change_percent:.1f}% "
                                           f"(Score: {opportunity.momentum_score:.1f})")
                
                except Exception as ticker_error:
                    if self.debug:
                        self.logger.warning(f"   ⚠️ Error analyzing {ticker}: {ticker_error}")
                    continue
            
            # Sort by momentum score and return top results
            opportunities.sort(key=lambda x: x.momentum_score, reverse=True)
            
            if self.debug:
                self.logger.info(f"✅ Found {len(opportunities)} momentum opportunities")
            
            return opportunities[:max_results]
            
        except Exception as e:
            self.logger.error(f"❌ Error scanning for momentum: {e}")
            return []
    
    def _get_yahoo_trending_tickers(self) -> List[str]:
        """Get trending tickers from Yahoo Finance"""
        try:
            # Use yfinance to get some popular trending stocks
            # This is a simplified version - in production you'd use Yahoo Finance API
            trending_base = [
                'TSLA', 'AAPL', 'NVDA', 'AMD', 'MSFT', 'GOOGL', 'AMZN', 'META',
                'NFLX', 'BABA', 'PLTR', 'RIVN', 'LCID', 'NIO', 'XPEV', 'LI'
            ]
            
            # Add some penny stocks and biotech (common momentum plays)
            momentum_stocks = [
                'SNDL', 'NAKD', 'GEVO', 'PLUG', 'FCEL', 'NKLA', 'SPCE', 'WKHS',
                'OCGN', 'PROG', 'BBIG', 'ATER', 'RDBX', 'MULN', 'IMPP', 'NILE'
            ]
            
            return trending_base + momentum_stocks
            
        except Exception as e:
            if self.debug:
                self.logger.warning(f"Failed to get trending tickers: {e}")
            return []
    
    def _get_momentum_watchlist(self) -> List[str]:
        """Get curated momentum watchlist including today's winners"""
        return [
            # Today's missed opportunities
            'BULLZ', 'NKTR', 'INSM', 'BGM', 'MTSR',
            
            # High-momentum ETFs
            'TQQQ', 'SOXL', 'TECL', 'NAIL', 'CURE', 'LABU',
            
            # Biotech momentum plays
            'BIIB', 'GILD', 'MRNA', 'BNTX', 'REGN', 'VRTX',
            
            # Meme stock potential
            'GME', 'AMC', 'BB', 'WISH', 'CLOV', 'SDC',
            
            # Penny stock momentum
            'SNDL', 'GNUS', 'EXPR', 'KOSS', 'NAKD', 'NOK'
        ]
    
    def _analyze_ticker_momentum(self, ticker: str) -> Optional[MomentumOpportunity]:
        """Analyze individual ticker for momentum opportunity"""
        try:
            # Get stock data
            stock = yf.Ticker(ticker)
            
            # Get current price and daily data
            info = stock.info
            current_price = info.get('currentPrice', 0)
            
            if current_price == 0:
                # Try to get from regular market price
                current_price = info.get('regularMarketPrice', 0)
            
            if current_price == 0:
                return None
            
            # Get daily change
            previous_close = info.get('previousClose', current_price)
            change_percent = ((current_price - previous_close) / previous_close) * 100
            
            # Get volume data
            volume = info.get('volume', 0)
            avg_volume = info.get('averageVolume', volume)
            volume_ratio = volume / max(avg_volume, 1)
            
            # Get market cap for risk assessment
            market_cap = info.get('marketCap', 0)
            
            # Calculate momentum score
            momentum_score = self._calculate_momentum_score(
                change_percent, volume_ratio, market_cap, current_price
            )
            
            # Determine risk level and position sizing
            risk_level, position_size = self._assess_risk_and_sizing(
                change_percent, market_cap, volume_ratio
            )
            
            # Calculate entry confidence
            entry_confidence = self._calculate_entry_confidence(
                change_percent, volume_ratio, momentum_score
            )
            
            return MomentumOpportunity(
                ticker=ticker,
                current_price=current_price,
                change_percent=change_percent,
                volume=volume,
                volume_ratio=volume_ratio,
                market_cap=market_cap,
                momentum_score=momentum_score,
                entry_confidence=entry_confidence,
                risk_level=risk_level,
                recommended_position_size=position_size
            )
            
        except Exception as e:
            if self.debug:
                self.logger.warning(f"Error analyzing {ticker}: {e}")
            return None
    
    def _calculate_momentum_score(self, change_percent: float, volume_ratio: float,
                                market_cap: float, price: float) -> float:
        """Calculate composite momentum score"""
        # Base score from price change
        change_score = min(change_percent / 10.0, 10.0)  # Cap at 10 for 100% gains
        
        # Volume score (higher volume = higher confidence)
        volume_score = min(volume_ratio / 2.0, 5.0)  # Cap at 5 for 10x volume
        
        # Market cap score (smaller cap = higher momentum potential, higher risk)
        if market_cap > 10_000_000_000:  # Large cap
            cap_score = 1.0
        elif market_cap > 1_000_000_000:  # Mid cap
            cap_score = 2.0
        elif market_cap > 100_000_000:   # Small cap
            cap_score = 3.0
        else:  # Micro cap
            cap_score = 4.0
        
        # Price score (penny stocks get momentum boost but risk penalty)
        if price < 1.0:
            price_score = 2.0
        elif price < 5.0:
            price_score = 1.5
        else:
            price_score = 1.0
        
        # Composite score
        momentum_score = (change_score * 0.4 + volume_score * 0.3 + 
                         cap_score * 0.2 + price_score * 0.1)
        
        return round(momentum_score, 2)
    
    def _assess_risk_and_sizing(self, change_percent: float, market_cap: float, 
                              volume_ratio: float) -> Tuple[str, float]:
        """Assess risk level and recommend position sizing"""
        # Determine risk level
        if change_percent >= 25:
            risk_level = "EXTREME"
            base_size = self.position_size_caps['extreme_momentum']
        elif change_percent >= 15:
            risk_level = "HIGH"
            base_size = self.position_size_caps['high_momentum']
        elif change_percent >= 8:
            risk_level = "MODERATE"
            base_size = self.position_size_caps['moderate_momentum']
        else:
            risk_level = "LOW"
            base_size = 0.15
        
        # Adjust for market cap (smaller = more risk, smaller position)
        if market_cap < 100_000_000:  # Micro cap
            size_multiplier = 0.5
            risk_level = "EXTREME"
        elif market_cap < 1_000_000_000:  # Small cap
            size_multiplier = 0.7
        else:  # Mid/Large cap
            size_multiplier = 1.0
        
        # Adjust for volume (higher volume = more confidence)
        if volume_ratio >= 5.0:
            volume_multiplier = 1.2
        elif volume_ratio >= 2.0:
            volume_multiplier = 1.0
        else:
            volume_multiplier = 0.6
            risk_level = "HIGH"
        
        final_position_size = base_size * size_multiplier * volume_multiplier
        final_position_size = min(final_position_size, 0.15)  # Never exceed 15%
        
        return risk_level, round(final_position_size, 3)
    
    def _calculate_entry_confidence(self, change_percent: float, volume_ratio: float,
                                  momentum_score: float) -> float:
        """Calculate entry confidence (0-1 scale)"""
        # Higher gains with volume support = higher confidence
        change_confidence = min(change_percent / 30.0, 1.0)  # Cap at 30% gains
        volume_confidence = min(volume_ratio / 5.0, 1.0)     # Cap at 5x volume
        score_confidence = min(momentum_score / 10.0, 1.0)   # Cap at score 10
        
        overall_confidence = (change_confidence * 0.4 + 
                            volume_confidence * 0.4 + 
                            score_confidence * 0.2)
        
        return round(overall_confidence, 3)
    
    def get_top_opportunities(self, account_balance: float = 30000,
                            max_positions: int = 5) -> List[Dict[str, any]]:
        """Get top momentum opportunities with position sizing for account balance"""
        opportunities = self.scan_for_momentum_opportunities()
        
        recommendations = []
        for opp in opportunities[:max_positions]:
            position_value = account_balance * opp.recommended_position_size
            shares = int(position_value / opp.current_price)
            
            if shares > 0:
                recommendations.append({
                    'ticker': opp.ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': opp.current_price,
                    'position_size_pct': opp.recommended_position_size * 100,
                    'change_percent': opp.change_percent,
                    'momentum_score': opp.momentum_score,
                    'confidence': opp.entry_confidence,
                    'risk_level': opp.risk_level,
                    'reason': f"Momentum: +{opp.change_percent:.1f}%, Score: {opp.momentum_score}"
                })
        
        return recommendations

if __name__ == "__main__":
    screener = MomentumScreener(debug=True)
    opportunities = screener.get_top_opportunities()
    
    print("🚀 MOMENTUM OPPORTUNITIES:")
    print("=" * 60)
    for opp in opportunities:
        print(f"{opp['ticker']:6} | {opp['action']:4} {opp['shares']:4} shares @ ${opp['price']:6.2f} | "
              f"+{opp['change_percent']:5.1f}% | {opp['risk_level']:8} | Score: {opp['momentum_score']:4.1f}")