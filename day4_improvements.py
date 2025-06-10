#!/opt/homebrew/bin/python3.12
"""
Day 4 Trading Improvements Based on Day 3 Analysis
==================================================

CRITICAL FINDINGS FROM DAY 3:
- Account 3 (+$2,230) WON with 15% position sizing
- Accounts 1&2 (-$1,800, -$2,500) LOST with 50% position sizing
- Same stocks, different risk management = opposite outcomes

ROOT CAUSE: Position sizing risk overwhelmed stock selection skill
"""

# Improved Position Sizing Recommendations for Day 4

class Day4Improvements:
    """Implementation guide for Day 4 trading improvements"""
    
    def __init__(self):
        self.improvements = {
            "position_sizing": {
                "recommendation": "REDUCE AGGRESSIVE CAPS",
                "current_problem": "50% positions too risky",
                "solution": {
                    "max_sure_thing_position": 0.25,  # Reduce from 50% to 25%
                    "max_regular_position": 0.15,     # Keep at 15%
                    "max_portfolio_exposure": 0.60,   # Reduce from 75% to 60%
                    "rationale": "Account 3 proved 15% works better than 50%"
                }
            },
            
            "sure_thing_criteria": {
                "recommendation": "STRICTER QUALIFICATION",
                "current_problem": "DTS ≥ 78 + V9B ≥ 8.8 not reliable enough",
                "solution": {
                    "new_dts_threshold": 85.0,       # Raise from 78 to 85
                    "new_v9b_threshold": 9.2,        # Raise from 8.8 to 9.2
                    "required_claude_confidence": 8.5, # Must have Claude 8.5+/10
                    "volume_confirmation": True,      # Require volume validation
                    "rationale": "Higher bars for aggressive sizing"
                }
            },
            
            "risk_management": {
                "recommendation": "PORTFOLIO-LEVEL CONTROLS",
                "current_problem": "No overall risk limits",
                "solution": {
                    "max_sector_exposure": 0.30,     # Max 30% in any sector
                    "correlation_check": True,       # Avoid correlated positions
                    "position_diversification": 8,   # Min 8 different stocks
                    "daily_loss_circuit_breaker": 0.02, # Stop at 2% daily loss
                    "rationale": "Prevent concentration disasters"
                }
            },
            
            "account_coordination": {
                "recommendation": "SYNCHRONIZED EXECUTION",
                "current_problem": "Round-robin creates timing differences",
                "solution": {
                    "batch_execution": True,         # Execute all accounts together
                    "price_synchronization": True,   # Use same prices for all
                    "unified_signals": True,         # Same entry/exit signals
                    "rationale": "Eliminate timing arbitrage between accounts"
                }
            },
            
            "learning_system": {
                "recommendation": "REAL-TIME ADAPTATION",
                "current_problem": "No feedback loop from failures",
                "solution": {
                    "performance_monitoring": True,   # Track per-account P&L
                    "position_size_adjustment": True, # Reduce on losses
                    "strategy_switching": True,       # Copy successful account
                    "daily_analysis": True,          # 4PM improvement analysis
                    "rationale": "Learn from Account 3's success"
                }
            }
        }
    
    def generate_code_changes(self):
        """Generate specific code modifications for system_x.py"""
        return """
        # MODIFICATION 1: Reduce aggressive position sizing caps
        # Lines 2276-2280, 2472-2476, 2577-2579
        if is_sure_thing and account_name in ["PRIMARY_30K", "SECONDARY_30K"]:
            max_position = 0.25  # REDUCED from 0.50 to 0.25
            kelly_cap = 0.25     # REDUCED from 0.50 to 0.25
        
        # MODIFICATION 2: Stricter "sure thing" criteria  
        # Lines 2336-2407 in is_sure_thing_stock()
        def is_sure_thing_stock(self, ticker, dts_score, v9b_score, claude_confidence):
            return (dts_score >= 85.0 and           # RAISED from 78.0
                   v9b_score >= 9.2 and            # RAISED from 8.8  
                   claude_confidence >= 8.5)        # NEW requirement
        
        # MODIFICATION 3: Portfolio-level risk controls
        def check_portfolio_risk(self, new_position_size, ticker, account_name):
            # Check sector concentration
            sector_exposure = self.calculate_sector_exposure(ticker)
            if sector_exposure + new_position_size > 0.30:
                return False
            
            # Check total positions
            if len(self.get_current_positions()) >= 8:
                return False
                
            return True
        """
    
    def day4_strategy(self):
        """Specific strategy for Day 4"""
        return {
            "primary_goal": "APPLY ACCOUNT 3'S WINNING FORMULA TO ALL ACCOUNTS",
            "position_sizing": "25% max for highest confidence, 15% standard",
            "risk_management": "Portfolio diversification + daily loss limits",
            "execution": "Synchronized across accounts to eliminate timing arbitrage",
            "learning": "Real-time adaptation based on performance feedback",
            "target": "Consistent gains across all 3 accounts"
        }

# Implementation Priority for Day 4
def get_implementation_priority():
    return [
        "1. IMMEDIATE: Reduce position sizing caps (50% → 25%)",
        "2. URGENT: Implement portfolio risk controls", 
        "3. HIGH: Stricter 'sure thing' qualification criteria",
        "4. MEDIUM: Synchronized account execution",
        "5. LOW: Real-time learning system (future enhancement)"
    ]

if __name__ == "__main__":
    improvements = Day4Improvements()
    print("Day 4 Improvement Analysis Complete")
    print("Key Changes:", improvements.day4_strategy())
    print("Priority:", get_implementation_priority())