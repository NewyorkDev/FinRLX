#!/opt/homebrew/bin/python3.12
"""
SYSTEMX HEALTH MONITOR & URGENT ALERT SYSTEM
Comprehensive monitoring for DTS problems, hot stocks, and system health
"""

import os
import sys
import json
import time
import requests
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from supabase import create_client

def load_environment():
    """Load environment variables from the_end/.env file"""
    env_file = os.path.join(os.path.dirname(__file__), 'the_end', '.env')
    env_vars = {}
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
        return env_vars
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        return {}

class HealthMonitor:
    def __init__(self):
        self.env_vars = load_environment()
        self.supabase = None
        self.slack_webhook = self.env_vars.get('SLACK_TRADE_WEBHOOK_URL')
        self.setup_logging()
        self.setup_supabase()
        
    def setup_logging(self):
        """Setup logging for health monitor"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/health_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_supabase(self):
        """Initialize Supabase connection"""
        try:
            if self.env_vars.get('SUPABASE_URL') and self.env_vars.get('SUPABASE_KEY'):
                self.supabase = create_client(
                    self.env_vars['SUPABASE_URL'], 
                    self.env_vars['SUPABASE_KEY']
                )
                self.logger.info("✅ Supabase connection established")
            else:
                self.logger.error("❌ Missing Supabase credentials")
        except Exception as e:
            self.logger.error(f"❌ Supabase connection failed: {e}")
            
    def send_slack_alert(self, message: str, urgent: bool = False):
        """Send alert to Slack"""
        if not self.slack_webhook:
            self.logger.warning("⚠️ No Slack webhook configured")
            return False
            
        try:
            emoji = "🚨" if urgent else "📊"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            payload = {
                "text": f"{emoji} **SYSTEMX HEALTH MONITOR** {emoji}",
                "attachments": [
                    {
                        "color": "danger" if urgent else "good",
                        "fields": [
                            {
                                "title": "Alert Type",
                                "value": "URGENT" if urgent else "INFO",
                                "short": True
                            },
                            {
                                "title": "Timestamp", 
                                "value": timestamp,
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": message,
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"✅ Slack alert sent: {message[:50]}...")
                return True
            else:
                self.logger.error(f"❌ Slack alert failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Slack alert error: {e}")
            return False
            
    def check_dts_problems(self) -> Dict:
        """Check for critical DTS problems and send urgent alerts"""
        if not self.supabase:
            return {"error": "No Supabase connection"}
            
        try:
            # Check recent stocks analyzed in last 4 hours
            cutoff_time = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Check analyzed_stocks table for DTS score issues
            result = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, squeeze_score, trend_score, created_at'
            ).gte('created_at', cutoff_time).execute()
            
            analysis = {
                "total_analyzed": len(result.data) if result.data else 0,
                "null_dts_scores": 0,
                "low_dts_scores": 0,
                "qualified_stocks": 0,
                "urgent_issues": []
            }
            
            if result.data:
                for stock in result.data:
                    ticker = stock.get('ticker', 'UNKNOWN')
                    dts_score = stock.get('dts_score')
                    
                    # Check for NULL/None DTS scores
                    if dts_score is None:
                        analysis["null_dts_scores"] += 1
                        analysis["urgent_issues"].append(f"NULL DTS: {ticker}")
                    elif dts_score < 60:
                        analysis["low_dts_scores"] += 1
                    elif dts_score >= 65:
                        analysis["qualified_stocks"] += 1
                        
            # Check V9B analysis for score scaling issues
            v9b_result = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, v9_combined_score, dts_score, created_at'
            ).gte('created_at', cutoff_time).execute()
            
            v9b_analysis = {
                "total_v9b_analyzed": len(v9b_result.data) if v9b_result.data else 0,
                "broken_v9b_scores": 0,
                "null_v9b_dts": 0
            }
            
            if v9b_result.data:
                for analysis_item in v9b_result.data:
                    ticker = analysis_item.get('ticker', 'UNKNOWN')
                    v9b_score = analysis_item.get('v9_combined_score', 0)
                    dts_score = analysis_item.get('dts_score')
                    
                    # Check for broken V9B score scaling (apply scaling before checking)
                    # Apply same scaling logic as DTS sync bridge
                    scaled_v9b = v9b_score * 100 if v9b_score and v9b_score < 10 else v9b_score
                    
                    # Only flag as urgent if scaled score is truly low AND DTS is also problematic
                    if scaled_v9b and scaled_v9b < 5.0 and (dts_score is None or dts_score < 30):
                        v9b_analysis["broken_v9b_scores"] += 1
                        analysis["urgent_issues"].append(f"LOW V9B: {ticker} (scaled: {scaled_v9b})")
                        
                    # Check for NULL DTS in V9B table
                    if dts_score is None:
                        v9b_analysis["null_v9b_dts"] += 1
                        
            # Combine analysis
            full_analysis = {**analysis, **v9b_analysis}
            
            # Send urgent alerts if critical issues found
            if analysis["urgent_issues"]:
                urgent_message = f"""🚨 URGENT DTS PROBLEMS DETECTED 🚨
                
📊 LAST 4 HOURS ANALYSIS:
• Total Stocks Analyzed: {analysis['total_analyzed']}
• NULL DTS Scores: {analysis['null_dts_scores']}
• Qualified Stocks: {analysis['qualified_stocks']}
• V9B Analyzed: {v9b_analysis['total_v9b_analyzed']}
• Broken V9B Scores: {v9b_analysis['broken_v9b_scores']}

🚨 URGENT ISSUES:
{chr(10).join(['• ' + issue for issue in analysis['urgent_issues'][:5]])}

🔧 ACTION NEEDED: Check SystemX scoring pipeline immediately!"""
                
                self.send_slack_alert(urgent_message, urgent=True)
                
            return full_analysis
            
        except Exception as e:
            error_msg = f"❌ DTS check failed: {e}"
            self.logger.error(error_msg)
            self.send_slack_alert(error_msg, urgent=True)
            return {"error": str(e)}
            
    def scan_24h_hot_stocks(self) -> Dict:
        """Scan for hot stocks in 24-hour window for Monday-Tuesday trading"""
        if not self.supabase:
            return {"error": "No Supabase connection"}
            
        try:
            # Check last 24 hours for hot stocks
            cutoff_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get high-scoring stocks from both tables
            analyzed_stocks = self.supabase.table('analyzed_stocks').select(
                'ticker, dts_score, squeeze_score, trend_score, created_at'
            ).gte('created_at', cutoff_time).gte('dts_score', 70).order('dts_score', desc=True).limit(10).execute()
            
            v9b_stocks = self.supabase.table('v9_multi_source_analysis').select(
                'ticker, v9_combined_score, dts_score, created_at'
            ).gte('created_at', cutoff_time).gte('v9_combined_score', 0.8).order('v9_combined_score', desc=True).limit(10).execute()
            
            hot_stocks = []
            
            # Process analyzed_stocks results
            if analyzed_stocks.data:
                for stock in analyzed_stocks.data:
                    hot_stocks.append({
                        "ticker": stock.get('ticker'),
                        "dts_score": stock.get('dts_score'),
                        "squeeze_score": stock.get('squeeze_score'),
                        "trend_score": stock.get('trend_score'),
                        "source": "analyzed_stocks",
                        "created_at": stock.get('created_at')
                    })
                    
            # Process V9B results with score scaling fix
            if v9b_stocks.data:
                for stock in v9b_stocks.data:
                    raw_v9b = stock.get('v9_combined_score', 0)
                    scaled_v9b = raw_v9b * 100 if raw_v9b < 10 else raw_v9b
                    
                    hot_stocks.append({
                        "ticker": stock.get('ticker'),
                        "v9b_score": scaled_v9b,
                        "dts_score": stock.get('dts_score'),
                        "source": "v9_multi_source_analysis",
                        "created_at": stock.get('created_at')
                    })
                    
            # Remove duplicates and sort by best scores
            unique_stocks = {}
            for stock in hot_stocks:
                ticker = stock['ticker']
                if ticker not in unique_stocks:
                    unique_stocks[ticker] = stock
                else:
                    # Keep the one with higher DTS score
                    current_dts = unique_stocks[ticker].get('dts_score', 0) or 0
                    new_dts = stock.get('dts_score', 0) or 0
                    if new_dts > current_dts:
                        unique_stocks[ticker] = stock
                        
            hot_stocks_list = list(unique_stocks.values())
            
            # Send Slack update if hot stocks found
            if hot_stocks_list:
                today = datetime.now().strftime('%A')  # Monday, Tuesday, etc.
                
                hot_stock_message = f"""🔥 24-HOUR HOT STOCKS DETECTED 🔥
                
📅 {today} Trading Opportunities:
• Total Hot Stocks Found: {len(hot_stocks_list)}
• Time Window: Last 24 hours
• Ready for Aggressive Trading

🎯 TOP HOT STOCKS:"""
                
                for i, stock in enumerate(hot_stocks_list[:5]):
                    ticker = stock['ticker']
                    dts = stock.get('dts_score', 'N/A')
                    v9b = stock.get('v9b_score', 'N/A')
                    squeeze = stock.get('squeeze_score', 'N/A')
                    
                    hot_stock_message += f"\n{i+1}. {ticker}: DTS={dts}, V9B={v9b}, Squeeze={squeeze}"
                    
                hot_stock_message += f"\n\n💰 SystemX configured for 50% aggressive trading on accounts 1&2!"
                
                self.send_slack_alert(hot_stock_message, urgent=False)
                
            return {
                "hot_stocks_found": len(hot_stocks_list),
                "stocks": hot_stocks_list,
                "scan_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"❌ Hot stock scan failed: {e}"
            self.logger.error(error_msg)
            self.send_slack_alert(error_msg, urgent=True)
            return {"error": str(e)}
            
    def check_systemx_health(self) -> Dict:
        """Check SystemX process health and recent activity"""
        try:
            health_status = {}
            
            # Check if SystemX process is running
            import subprocess
            result = subprocess.run(['pgrep', '-f', 'system_x.py'], capture_output=True, text=True)
            health_status["process_running"] = bool(result.stdout.strip())
            health_status["process_id"] = result.stdout.strip() if result.stdout.strip() else None
            
            # Check recent log activity
            log_file = 'logs/system-x-out.log'
            if os.path.exists(log_file):
                stat = os.stat(log_file)
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                time_since_update = datetime.now() - last_modified
                health_status["log_last_updated"] = last_modified.isoformat()
                health_status["minutes_since_log_update"] = int(time_since_update.total_seconds() / 60)
                health_status["log_activity_healthy"] = time_since_update.total_seconds() < 600  # 10 minutes
            else:
                health_status["log_last_updated"] = None
                health_status["log_activity_healthy"] = False
                
            # Check PM2 status
            try:
                pm2_result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
                if pm2_result.returncode == 0:
                    pm2_data = json.loads(pm2_result.stdout)
                    systemx_processes = [p for p in pm2_data if 'system-x' in p.get('name', '')]
                    health_status["pm2_processes"] = len(systemx_processes)
                    health_status["pm2_online"] = any(p.get('pm2_env', {}).get('status') == 'online' for p in systemx_processes)
                else:
                    health_status["pm2_processes"] = 0
                    health_status["pm2_online"] = False
            except:
                health_status["pm2_processes"] = 0
                health_status["pm2_online"] = False
                
            # Determine overall health
            overall_healthy = (
                health_status.get("process_running", False) and
                health_status.get("log_activity_healthy", False) and
                health_status.get("pm2_online", False)
            )
            health_status["overall_healthy"] = overall_healthy
            
            # Send alert if unhealthy
            if not overall_healthy:
                unhealthy_message = f"""⚠️ SYSTEMX HEALTH ISSUE DETECTED ⚠️
                
🔍 SYSTEM STATUS:
• Process Running: {'✅' if health_status.get('process_running') else '❌'}
• PM2 Online: {'✅' if health_status.get('pm2_online') else '❌'}
• Log Activity: {'✅' if health_status.get('log_activity_healthy') else '❌'}
• Minutes Since Log: {health_status.get('minutes_since_log_update', 'N/A')}

🔧 ACTION: Check SystemX status and restart if needed"""
                
                self.send_slack_alert(unhealthy_message, urgent=True)
                
            return health_status
            
        except Exception as e:
            error_msg = f"❌ Health check failed: {e}"
            self.logger.error(error_msg)
            return {"error": str(e)}
            
    def run_comprehensive_check(self):
        """Run all health checks and send summary"""
        self.logger.info("🔍 Starting comprehensive health check...")
        
        # Run all checks
        dts_check = self.check_dts_problems()
        hot_stocks = self.scan_24h_hot_stocks()
        system_health = self.check_systemx_health()
        
        # Create summary
        summary = f"""📊 SYSTEMX COMPREHENSIVE HEALTH REPORT 📊
        
⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 DTS ANALYSIS:
• Stocks Analyzed (4h): {dts_check.get('total_analyzed', 0)}
• NULL DTS Issues: {dts_check.get('null_dts_scores', 0)}
• Qualified Stocks: {dts_check.get('qualified_stocks', 0)}
• Urgent Issues: {len(dts_check.get('urgent_issues', []))}

🔥 HOT STOCKS (24h):
• Hot Stocks Found: {hot_stocks.get('hot_stocks_found', 0)}

🏥 SYSTEM HEALTH:
• Process Running: {'✅' if system_health.get('process_running') else '❌'}
• PM2 Status: {'✅' if system_health.get('pm2_online') else '❌'}
• Log Activity: {'✅' if system_health.get('log_activity_healthy') else '❌'}

🎯 OVERALL STATUS: {'✅ HEALTHY' if system_health.get('overall_healthy') and len(dts_check.get('urgent_issues', [])) == 0 else '⚠️ NEEDS ATTENTION'}"""
        
        self.send_slack_alert(summary, urgent=False)
        self.logger.info("✅ Comprehensive health check completed")
        
        return {
            "dts_check": dts_check,
            "hot_stocks": hot_stocks,
            "system_health": system_health,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main function for health monitoring"""
    print("🏥 SystemX Health Monitor Starting...")
    
    monitor = HealthMonitor()
    
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == '--dts-check':
                result = monitor.check_dts_problems()
                print(json.dumps(result, indent=2))
            elif command == '--hot-stocks':
                result = monitor.scan_24h_hot_stocks()
                print(json.dumps(result, indent=2))
            elif command == '--system-health':
                result = monitor.check_systemx_health()
                print(json.dumps(result, indent=2))
            elif command == '--continuous':
                print("🔄 Running continuous monitoring...")
                while True:
                    monitor.run_comprehensive_check()
                    time.sleep(300)  # Check every 5 minutes
            else:
                print("Usage: python health_monitor.py [--dts-check|--hot-stocks|--system-health|--continuous]")
        else:
            # Run single comprehensive check
            result = monitor.run_comprehensive_check()
            print(json.dumps(result, indent=2))
            
    except KeyboardInterrupt:
        print("\n🛑 Health monitor stopped by user")
    except Exception as e:
        print(f"❌ Health monitor error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()