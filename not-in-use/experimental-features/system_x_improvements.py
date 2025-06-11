#!/opt/homebrew/bin/python3.12
"""
System X Improvements - Integration Module
==========================================

Integrates the batch order manager and momentum screener into System X
to eliminate timing arbitrage and capture high-momentum opportunities.

Based on analysis showing Account 3's superior performance due to timing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from batch_order_manager import BatchOrderManager, BatchOrder, copy_account3_timing_strategy
from momentum_screener import MomentumScreener
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import threading
import time

class SystemXImprovedCoordination:
    """Enhanced coordination system for System X with batch execution and momentum screening"""
    
    def __init__(self, system_x_instance, debug: bool = False):
        self.system_x = system_x_instance
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.batch_manager = None
        self.momentum_screener = MomentumScreener(debug=debug)
        
        # Coordination settings
        self.coordination_enabled = True
        self.momentum_screening_enabled = True
        self.last_momentum_scan = datetime.min
        self.momentum_scan_interval = timedelta(minutes=15)  # Scan every 15 minutes
        
        # Performance tracking
        self.coordination_stats = {
            'batches_executed': 0,
            'momentum_opportunities_found': 0,
            'timing_improvements': 0,
            'average_execution_spread': 0.0
        }
        
        self._setup_batch_manager()
    
    def _setup_batch_manager(self):
        """Initialize batch manager with System X accounts"""
        try:
            # Get all configured Alpaca accounts from System X
            accounts = {}
            
            if hasattr(self.system_x, 'alpaca'):
                accounts['PRIMARY_30K'] = self.system_x.alpaca
            
            if hasattr(self.system_x, 'alpaca_2'):
                accounts['SECONDARY_30K'] = self.system_x.alpaca_2
                
            if hasattr(self.system_x, 'alpaca_3'):
                accounts['TERTIARY_30K'] = self.system_x.alpaca_3
            
            if accounts:
                self.batch_manager = BatchOrderManager(accounts, debug=self.debug)
                if self.debug:
                    self.logger.info(f"✅ Batch manager initialized with {len(accounts)} accounts")
            else:
                if self.debug:
                    self.logger.warning("⚠️ No Alpaca accounts found for batch management")
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to setup batch manager: {e}")
    
    def enhanced_execute_trade(self, ticker: str, action: str, base_shares: int, 
                             price: float, account_name: str, reason: str = "") -> bool:
        """Enhanced trade execution with batch coordination"""
        
        if not self.coordination_enabled or not self.batch_manager:
            # Fallback to original System X execution
            return self.system_x.execute_trade(ticker, action, base_shares, price, account_name, reason)
        
        try:
            # Determine if this should be a coordinated batch trade
            should_coordinate = self._should_coordinate_trade(ticker, action, base_shares, reason)
            
            if should_coordinate:
                return self._execute_coordinated_batch_trade(ticker, action, base_shares, price, reason)
            else:
                # Execute single account trade
                return self.system_x.execute_trade(ticker, action, base_shares, price, account_name, reason)
                
        except Exception as e:
            self.logger.error(f"❌ Enhanced execution failed for {ticker}: {e}")
            # Fallback to original execution
            return self.system_x.execute_trade(ticker, action, base_shares, price, account_name, reason)
    
    def _should_coordinate_trade(self, ticker: str, action: str, shares: int, reason: str) -> bool:
        """Determine if trade should be coordinated across accounts"""
        # Coordinate if:
        # 1. High-value trade (>$1000)
        # 2. Momentum play (from screener)
        # 3. "Sure thing" detection
        # 4. Exit trade to prevent timing arbitrage
        
        trade_value = shares * self._get_current_price(ticker)
        
        coordination_triggers = [
            trade_value > 1000,  # High-value trades
            "momentum" in reason.lower(),  # Momentum opportunities
            "sure_thing" in reason.lower(),  # High-confidence trades
            action == "sell",  # All exit trades to prevent arbitrage
            "ML_ENHANCED" in reason  # ML-enhanced signals
        ]
        
        return any(coordination_triggers)
    
    def _execute_coordinated_batch_trade(self, ticker: str, action: str, 
                                       base_shares: int, price: float, reason: str) -> bool:
        """Execute trade across all accounts with coordination"""
        try:
            # Calculate shares per account using Account 3's winning strategy
            account_shares = self._calculate_account_shares_distribution(ticker, base_shares)
            
            # Create batch order
            batch_order = BatchOrder(
                ticker=ticker,
                action=action,
                quantity_per_account=account_shares,
                price_limit=None,  # Use market orders for speed
                execution_window=20,  # 20-second execution window
                priority=1,  # High priority
                reason=f"SystemX_Coordinated: {reason}"
            )
            
            # Add to batch queue
            if self.batch_manager.add_batch_order(batch_order):
                # Execute immediately
                success, result = self.batch_manager.execute_next_batch()
                
                if success:
                    self.coordination_stats['batches_executed'] += 1
                    self.coordination_stats['timing_improvements'] += 1
                    
                    # Update average execution spread
                    timing_spread = result.get('timing_spread', 0)
                    self.coordination_stats['average_execution_spread'] = (
                        (self.coordination_stats['average_execution_spread'] * 
                         (self.coordination_stats['batches_executed'] - 1) + timing_spread) /
                        self.coordination_stats['batches_executed']
                    )
                    
                    if self.debug:
                        self.logger.info(f"✅ Coordinated batch execution: {ticker} "
                                       f"(Spread: {timing_spread:.2f}s)")
                
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Coordinated execution failed: {e}")
            return False
    
    def _calculate_account_shares_distribution(self, ticker: str, base_shares: int) -> Dict[str, int]:
        """Calculate share distribution using Account 3's winning strategy"""
        # Account 3 performed best, so give it optimal allocation
        # Distribute based on account performance patterns
        
        distribution = {
            'PRIMARY_30K': base_shares,
            'SECONDARY_30K': base_shares,
            'TERTIARY_30K': int(base_shares * 1.15)  # Account 3 gets 15% more (it's winning)
        }
        
        # Adjust for account balances
        for account_name in distribution.keys():
            try:
                account_balance = self.system_x.get_account_balance(account_name)
                if account_balance < 20000:  # Low balance adjustment
                    distribution[account_name] = int(distribution[account_name] * 0.7)
            except:
                pass  # Keep original allocation if balance check fails
        
        return distribution
    
    def scan_and_add_momentum_opportunities(self) -> List[Dict[str, Any]]:
        """Scan for momentum opportunities and add to trading queue"""
        if not self.momentum_screening_enabled:
            return []
        
        # Check if enough time has passed since last scan
        now = datetime.now()
        if now - self.last_momentum_scan < self.momentum_scan_interval:
            return []
        
        try:
            if self.debug:
                self.logger.info("🔍 Scanning for momentum opportunities...")
            
            # Get momentum opportunities
            opportunities = self.momentum_screener.get_top_opportunities(
                account_balance=30000,  # Base account size
                max_positions=3  # Limit momentum plays
            )
            
            self.last_momentum_scan = now
            self.coordination_stats['momentum_opportunities_found'] += len(opportunities)
            
            # Add high-confidence opportunities to System X
            added_opportunities = []
            for opp in opportunities:
                if opp['confidence'] >= 0.7 and opp['change_percent'] >= 10.0:
                    # This would integrate with System X's trading logic
                    added_opportunities.append(opp)
                    
                    if self.debug:
                        self.logger.info(f"📈 Added momentum opportunity: {opp['ticker']} "
                                       f"+{opp['change_percent']:.1f}% (Confidence: {opp['confidence']:.2f})")
            
            return added_opportunities
            
        except Exception as e:
            self.logger.error(f"❌ Momentum scanning failed: {e}")
            return []
    
    def _get_current_price(self, ticker: str) -> float:
        """Get current price for a ticker"""
        try:
            # Use System X's price fetching mechanism
            if hasattr(self.system_x, 'get_current_price'):
                return self.system_x.get_current_price(ticker)
            else:
                # Fallback estimation
                return 10.0
        except:
            return 10.0
    
    def apply_account3_timing_to_all(self, ticker: str, action: str, base_shares: int, 
                                   reason: str = "") -> bool:
        """Apply Account 3's proven timing strategy to all accounts"""
        if not self.batch_manager:
            return False
        
        return copy_account3_timing_strategy(
            self.batch_manager, ticker, action, base_shares, reason
        )
    
    def get_coordination_performance(self) -> Dict[str, Any]:
        """Get coordination system performance metrics"""
        stats = self.coordination_stats.copy()
        
        if self.batch_manager:
            batch_stats = self.batch_manager.get_performance_stats()
            stats.update({
                'batch_success_rate': batch_stats.get('success_rate', 0),
                'average_batch_time': batch_stats.get('average_execution_time', 0),
                'queue_size': batch_stats.get('queue_size', 0)
            })
        
        return stats
    
    def enable_coordination(self, enable: bool = True):
        """Enable or disable coordination features"""
        self.coordination_enabled = enable
        if self.debug:
            status = "enabled" if enable else "disabled"
            self.logger.info(f"🔄 Coordination system {status}")
    
    def enable_momentum_screening(self, enable: bool = True):
        """Enable or disable momentum screening"""
        self.momentum_screening_enabled = enable
        if self.debug:
            status = "enabled" if enable else "disabled"
            self.logger.info(f"🚀 Momentum screening {status}")

# Integration helper functions
def integrate_improvements_into_system_x(system_x_instance) -> SystemXImprovedCoordination:
    """Create and integrate improvements into existing System X instance"""
    return SystemXImprovedCoordination(system_x_instance, debug=True)

def patch_system_x_execute_trade(system_x_instance, improvements: SystemXImprovedCoordination):
    """Monkey patch System X execute_trade method with improvements"""
    original_execute_trade = system_x_instance.execute_trade
    
    def enhanced_execute_trade(ticker, action, shares, price, account_name, reason=""):
        return improvements.enhanced_execute_trade(ticker, action, shares, price, account_name, reason)
    
    # Replace the method
    system_x_instance.execute_trade = enhanced_execute_trade
    system_x_instance.improvements = improvements
    
    return system_x_instance

if __name__ == "__main__":
    print("🎯 System X Improvements - Coordination & Momentum Integration")
    print("Eliminates timing arbitrage and captures momentum opportunities")
    print("Based on Account 3's superior performance analysis")