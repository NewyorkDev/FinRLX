#!/opt/homebrew/bin/python3.12
"""
Batch Order Manager for Synchronized Multi-Account Execution
===========================================================

Solves the timing arbitrage problem by coordinating all three accounts
to execute trades within seconds of each other, not hours apart.

Based on the analysis showing TERTIARY's superior timing leading to
+$2,057 profit vs PRIMARY (-$1,908) and SECONDARY (-$2,541) losses.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import alpaca_trade_api as tradeapi
from dataclasses import dataclass
import logging

@dataclass
class BatchOrder:
    """Represents a synchronized order across multiple accounts"""
    ticker: str
    action: str  # 'buy' or 'sell'
    quantity_per_account: Dict[str, int]  # account_name -> shares
    price_limit: Optional[float] = None
    execution_window: int = 30  # seconds to complete all orders
    priority: int = 1  # 1=highest, 3=lowest
    reason: str = ""

class BatchOrderManager:
    """Coordinates simultaneous order execution across all accounts"""
    
    def __init__(self, accounts: Dict[str, tradeapi.REST], debug: bool = False):
        self.accounts = accounts
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # Coordination mechanisms
        self.order_queue: List[BatchOrder] = []
        self.queue_lock = threading.Lock()
        self.execution_lock = threading.Lock()
        
        # Performance tracking
        self.execution_stats = {
            'total_batches': 0,
            'successful_batches': 0,
            'average_execution_time': 0.0,
            'max_timing_spread': 0.0
        }
        
        # Account-specific execution delays (based on Account 3's superior timing)
        self.account_delays = {
            'PRIMARY_30K': 0.0,     # No delay
            'SECONDARY_30K': 0.5,   # 500ms delay 
            'TERTIARY_30K': 1.0     # 1 second delay (copy Account 3's timing)
        }
        
    def add_batch_order(self, batch_order: BatchOrder) -> bool:
        """Add order to batch execution queue"""
        try:
            with self.queue_lock:
                # Insert based on priority (1=highest priority first)
                insert_index = 0
                for i, existing_order in enumerate(self.order_queue):
                    if existing_order.priority > batch_order.priority:
                        insert_index = i
                        break
                    insert_index = i + 1
                
                self.order_queue.insert(insert_index, batch_order)
                
                if self.debug:
                    self.logger.info(f"📝 Added batch order: {batch_order.action.upper()} {batch_order.ticker} "
                                   f"(Priority: {batch_order.priority}, Queue size: {len(self.order_queue)})")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Failed to add batch order: {e}")
            return False
    
    def execute_next_batch(self) -> Tuple[bool, Dict[str, Any]]:
        """Execute the highest priority batch order"""
        with self.queue_lock:
            if not self.order_queue:
                return False, {"error": "No orders in queue"}
            
            batch_order = self.order_queue.pop(0)
        
        return self._execute_batch_synchronized(batch_order)
    
    def _execute_batch_synchronized(self, batch_order: BatchOrder) -> Tuple[bool, Dict[str, Any]]:
        """Execute orders across all accounts with tight timing coordination"""
        start_time = time.time()
        execution_results = {}
        timing_data = {}
        
        if self.debug:
            self.logger.info(f"🔄 Executing batch: {batch_order.action.upper()} {batch_order.ticker}")
            self.logger.info(f"   Accounts: {list(batch_order.quantity_per_account.keys())}")
            self.logger.info(f"   Window: {batch_order.execution_window}s")
        
        # Prepare all orders first
        order_tasks = []
        for account_name, quantity in batch_order.quantity_per_account.items():
            if account_name in self.accounts and quantity > 0:
                order_tasks.append({
                    'account_name': account_name,
                    'client': self.accounts[account_name],
                    'ticker': batch_order.ticker,
                    'action': batch_order.action,
                    'quantity': quantity,
                    'price_limit': batch_order.price_limit,
                    'delay': self.account_delays.get(account_name, 0.0)
                })
        
        if not order_tasks:
            return False, {"error": "No valid accounts for execution"}
        
        # Execute all orders concurrently with staggered timing
        with ThreadPoolExecutor(max_workers=len(order_tasks)) as executor:
            futures = []
            
            for task in order_tasks:
                future = executor.submit(self._execute_single_order_with_delay, task)
                futures.append((future, task['account_name']))
            
            # Collect results with timeout
            timeout = batch_order.execution_window
            completed_orders = 0
            
            for future, account_name in futures:
                try:
                    result = future.result(timeout=timeout)
                    execution_results[account_name] = result
                    timing_data[account_name] = result.get('execution_time', 0)
                    
                    if result.get('success', False):
                        completed_orders += 1
                        
                except Exception as e:
                    execution_results[account_name] = {
                        'success': False,
                        'error': str(e),
                        'execution_time': 0
                    }
        
        # Calculate timing statistics
        total_time = time.time() - start_time
        timing_spread = max(timing_data.values()) - min(timing_data.values()) if timing_data else 0
        
        # Update performance stats
        self.execution_stats['total_batches'] += 1
        if completed_orders == len(order_tasks):
            self.execution_stats['successful_batches'] += 1
        
        self.execution_stats['average_execution_time'] = (
            (self.execution_stats['average_execution_time'] * (self.execution_stats['total_batches'] - 1) + total_time)
            / self.execution_stats['total_batches']
        )
        
        self.execution_stats['max_timing_spread'] = max(
            self.execution_stats['max_timing_spread'], timing_spread
        )
        
        # Log results
        success_rate = completed_orders / len(order_tasks)
        if self.debug:
            self.logger.info(f"✅ Batch execution complete: {completed_orders}/{len(order_tasks)} successful")
            self.logger.info(f"   Total time: {total_time:.2f}s, Timing spread: {timing_spread:.2f}s")
            self.logger.info(f"   Success rate: {success_rate:.1%}")
        
        return success_rate >= 0.5, {
            'execution_results': execution_results,
            'total_time': total_time,
            'timing_spread': timing_spread,
            'success_rate': success_rate,
            'completed_orders': completed_orders,
            'batch_order': batch_order
        }
    
    def _execute_single_order_with_delay(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single order with account-specific delay for optimal timing"""
        start_time = time.time()
        
        # Apply account-specific delay (Account 3's timing advantage)
        if task['delay'] > 0:
            time.sleep(task['delay'])
        
        try:
            # Get current price for market order
            if task['price_limit'] is None:
                # Use market order
                order_type = 'market'
                limit_price = None
            else:
                order_type = 'limit'
                limit_price = task['price_limit']
            
            # Submit order
            order = task['client'].submit_order(
                symbol=task['ticker'],
                qty=task['quantity'],
                side=task['action'],
                type=order_type,
                time_in_force='day',
                limit_price=limit_price
            )
            
            execution_time = time.time() - start_time
            
            if self.debug:
                self.logger.info(f"   {task['account_name']}: {task['action'].upper()} {task['quantity']} {task['ticker']} "
                               f"@ {order.limit_price or 'market'} ({execution_time:.2f}s)")
            
            return {
                'success': True,
                'order_id': order.id,
                'execution_time': execution_time,
                'order': order,
                'account_name': task['account_name']
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            if self.debug:
                self.logger.error(f"   {task['account_name']}: FAILED {task['action'].upper()} {task['quantity']} "
                                f"{task['ticker']} - {error_msg} ({execution_time:.2f}s)")
            
            return {
                'success': False,
                'error': error_msg,
                'execution_time': execution_time,
                'account_name': task['account_name']
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get batch execution performance statistics"""
        return {
            **self.execution_stats,
            'queue_size': len(self.order_queue),
            'success_rate': (self.execution_stats['successful_batches'] / 
                           max(self.execution_stats['total_batches'], 1))
        }
    
    def clear_queue(self) -> int:
        """Clear all pending orders and return count"""
        with self.queue_lock:
            count = len(self.order_queue)
            self.order_queue.clear()
            return count

# Example usage for System X integration
def create_system_x_batch_manager(accounts_dict: Dict[str, tradeapi.REST]) -> BatchOrderManager:
    """Create batch manager configured for System X"""
    return BatchOrderManager(accounts_dict, debug=True)

def copy_account3_timing_strategy(batch_manager: BatchOrderManager, 
                                 ticker: str, action: str, base_quantity: int,
                                 reason: str = "") -> bool:
    """Apply Account 3's winning timing strategy to all accounts"""
    
    # Account 3's superior sizing strategy (more conservative, better timing)
    quantity_distribution = {
        'PRIMARY_30K': base_quantity,
        'SECONDARY_30K': base_quantity, 
        'TERTIARY_30K': int(base_quantity * 1.2)  # Account 3 gets slightly more (it's winning)
    }
    
    batch_order = BatchOrder(
        ticker=ticker,
        action=action,
        quantity_per_account=quantity_distribution,
        execution_window=15,  # Tight 15-second window
        priority=1,  # High priority
        reason=f"Account3_Strategy: {reason}"
    )
    
    return batch_manager.add_batch_order(batch_order)

if __name__ == "__main__":
    print("🎯 Batch Order Manager - Multi-Account Synchronization")
    print("Eliminates timing arbitrage between accounts")
    print("Based on Account 3's superior timing analysis")