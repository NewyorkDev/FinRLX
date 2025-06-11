#!/opt/homebrew/bin/python3.12
"""
AI INTELLIGENCE INTEGRATION FOR SYSTEMX
=======================================
Comprehensive AI intelligence using OpenAI Nano 4.1 and Claude Sonnet 3.5
for enhanced trading analysis and decision support.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import aiohttp
import openai
import anthropic
from dataclasses import dataclass
import re
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Enhanced trading signal with AI analysis"""
    ticker: str
    confidence_score: float  # 0-10
    buy_probability: float   # 0-1
    support_levels: List[float]
    resistance_levels: List[float]
    stop_loss: Optional[float]
    target_price: Optional[float]
    risk_warnings: List[str]
    position_size_rec: Optional[float]  # 0-1
    entry_strategy: str
    volume_analysis: Dict[str, Any]
    ai_reasoning: str
    model_used: str

class AIIntelligenceEngine:
    """Comprehensive AI intelligence engine for trading decisions"""
    
    def __init__(self):
        self.load_environment()
        self.setup_clients()
        self.trading_context = self._load_trading_context()
        
    def load_environment(self):
        """Load environment variables from the_end/.env file"""
        env_file = os.path.join(os.path.dirname(__file__), 'the_end', '.env')
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            logger.info("✅ Environment loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading environment: {e}")
            
    def setup_clients(self):
        """Initialize AI clients"""
        try:
            # OpenAI client
            self.openai_client = openai.OpenAI(
                api_key=os.getenv('OPENAI_API_KEY')
            )
            self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4.1-nano-2025-04-14')
            
            # Claude client
            self.claude_client = anthropic.Anthropic(
                api_key=os.getenv('CLAUDE_API_KEY')
            )
            self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
            self.claude_enabled = os.getenv('CLAUDE_ENABLED', 'true').lower() == 'true'
            
            logger.info(f"✅ AI clients initialized - OpenAI: {self.openai_model}, Claude: {self.claude_model}")
            
        except Exception as e:
            logger.error(f"❌ Error setting up AI clients: {e}")
            self.openai_client = None
            self.claude_client = None
    
    def _load_trading_context(self) -> str:
        """Load trading context and system information"""
        return """
        You are an expert AI trading analyst for SystemX, an autonomous trading system.
        
        SYSTEM CONTEXT:
        - Trading 3 Alpaca accounts with $30K each ($90K total)
        - Focus on V9B qualified stocks with DTS scores ≥65
        - Account Mode System: Recovery (<$26K), Normal ($26K-$33K), Peaking (≥$500 daily gains)
        - PDT protection with hard stops at $25K
        - Position sizing: 5% (Recovery), 15% (Normal), 8% (Peaking)
        - 5% stop loss, 10% take profit standard rules
        
        ANALYSIS REQUIREMENTS:
        - Provide confidence score 1-10 for day trading potential
        - Identify key support/resistance levels
        - Assess risk factors and volume patterns
        - Recommend position sizing adjustments
        - Consider current market conditions and volatility
        """
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_openai_analysis(self, ticker: str, market_data: Dict) -> Dict:
        """Get OpenAI Nano 4.1 analysis for a stock"""
        try:
            prompt = self._create_analysis_prompt(ticker, market_data)
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": self.trading_context},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            analysis_text = response.choices[0].message.content
            signals = self._extract_signals_from_text(analysis_text)
            
            return {
                'analysis': analysis_text,
                'signals': signals,
                'model': self.openai_model,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ OpenAI analysis error for {ticker}: {e}")
            return {}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_claude_analysis(self, ticker: str, market_data: Dict) -> Dict:
        """Get Claude Sonnet 3.5 analysis for a stock"""
        if not self.claude_enabled or not self.claude_client:
            return {}
            
        try:
            prompt = self._create_analysis_prompt(ticker, market_data)
            
            response = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=800,
                temperature=0.3,
                messages=[
                    {
                        "role": "user", 
                        "content": f"{self.trading_context}\n\n{prompt}"
                    }
                ]
            )
            
            analysis_text = response.content[0].text
            signals = self._extract_signals_from_text(analysis_text)
            
            return {
                'analysis': analysis_text,
                'signals': signals,
                'model': self.claude_model,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Claude analysis error for {ticker}: {e}")
            return {}
    
    def _create_analysis_prompt(self, ticker: str, market_data: Dict) -> str:
        """Create comprehensive analysis prompt"""
        current_price = market_data.get('current_price', 0)
        volume = market_data.get('volume', 0)
        dts_score = market_data.get('dts_score', 0)
        v9b_score = market_data.get('v9b_score', 0)
        
        prompt = f"""
        URGENT TRADING ANALYSIS REQUEST FOR {ticker}
        
        MARKET DATA:
        - Current Price: ${current_price:.2f}
        - Volume: {volume:,}
        - DTS Score: {dts_score:.1f}
        - V9B Score: {v9b_score:.1f}
        - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        REQUIRED ANALYSIS:
        1. Day Trading Confidence (1-10): Rate the probability of profitable day trading
        2. Support Levels: Identify 2-3 key support prices
        3. Resistance Levels: Identify 2-3 key resistance prices  
        4. Stop Loss: Recommend optimal stop loss price
        5. Target Price: Expected profit target for day trading
        6. Position Size: Recommended position size (5-15%)
        7. Risk Assessment: List specific risk factors
        8. Volume Analysis: Interpret current volume patterns
        9. Entry Strategy: Best entry timing and approach
        10. Overall Recommendation: BUY/HOLD/SELL with reasoning
        
        FORMAT YOUR RESPONSE WITH CLEAR NUMBERS AND PRICES.
        FOCUS ON ACTIONABLE DAY TRADING INSIGHTS.
        """
        
        return prompt
    
    def _extract_signals_from_text(self, analysis_text: str) -> Dict:
        """Extract trading signals from AI analysis text"""
        signals = {
            'confidence_score': None,
            'support_levels': [],
            'resistance_levels': [],
            'stop_loss': None,
            'target_price': None,
            'risk_warnings': [],
            'position_size_rec': None,
            'entry_strategy': '',
            'volume_analysis': {}
        }
        
        if not analysis_text:
            return signals
            
        # Extract confidence score (1-10)
        confidence_matches = re.findall(r'(?:confidence|score).*?(\d+(?:\.\d+)?)\s*[/]?\s*10', analysis_text.lower())
        if confidence_matches:
            signals['confidence_score'] = min(float(confidence_matches[0]), 10.0)
        
        # Extract support levels
        support_matches = re.findall(r'support.*?\$(\d+(?:\.\d+)?)', analysis_text.lower())
        signals['support_levels'] = [float(m) for m in support_matches[:3]]
        
        # Extract resistance levels
        resistance_matches = re.findall(r'resistance.*?\$(\d+(?:\.\d+)?)', analysis_text.lower())
        signals['resistance_levels'] = [float(m) for m in resistance_matches[:3]]
        
        # Extract stop loss
        stop_matches = re.findall(r'stop.*?(?:loss)?.*?\$(\d+(?:\.\d+)?)', analysis_text.lower())
        if stop_matches:
            signals['stop_loss'] = float(stop_matches[0])
            
        # Extract target price
        target_matches = re.findall(r'target.*?\$(\d+(?:\.\d+)?)', analysis_text.lower())
        if target_matches:
            signals['target_price'] = float(target_matches[0])
            
        # Extract position size
        size_matches = re.findall(r'(?:position|size).*?(\d+(?:\.\d+)?)\s*%', analysis_text.lower())
        if size_matches:
            signals['position_size_rec'] = min(float(size_matches[0]) / 100, 0.15)
            
        # Extract risk warnings
        risk_keywords = ['volatile', 'risky', 'caution', 'high risk', 'dangerous', 'unstable', 'bearish']
        for keyword in risk_keywords:
            if keyword in analysis_text.lower():
                signals['risk_warnings'].append(keyword)
                
        # Extract entry strategy
        if 'breakout' in analysis_text.lower():
            signals['entry_strategy'] = 'breakout'
        elif 'pullback' in analysis_text.lower():
            signals['entry_strategy'] = 'pullback'
        elif 'momentum' in analysis_text.lower():
            signals['entry_strategy'] = 'momentum'
        else:
            signals['entry_strategy'] = 'market'
            
        return signals
    
    async def get_enhanced_analysis(self, ticker: str, market_data: Dict) -> Optional[TradingSignal]:
        """Get comprehensive AI analysis from both models"""
        try:
            logger.info(f"🧠 Getting enhanced AI analysis for {ticker}")
            
            # Get analyses from both models
            tasks = []
            if self.openai_client:
                tasks.append(self.get_openai_analysis(ticker, market_data))
            if self.claude_client and self.claude_enabled:
                tasks.append(self.get_claude_analysis(ticker, market_data))
                
            if not tasks:
                logger.warning("❌ No AI clients available")
                return None
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            combined_signals = self._combine_ai_signals([r for r in results if isinstance(r, dict) and r])
            
            if not combined_signals:
                logger.warning(f"❌ No valid AI analysis for {ticker}")
                return None
                
            # Create enhanced trading signal
            trading_signal = TradingSignal(
                ticker=ticker,
                confidence_score=combined_signals.get('confidence_score', 5.0),
                buy_probability=combined_signals.get('buy_probability', 0.5),
                support_levels=combined_signals.get('support_levels', []),
                resistance_levels=combined_signals.get('resistance_levels', []),
                stop_loss=combined_signals.get('stop_loss'),
                target_price=combined_signals.get('target_price'),
                risk_warnings=combined_signals.get('risk_warnings', []),
                position_size_rec=combined_signals.get('position_size_rec'),
                entry_strategy=combined_signals.get('entry_strategy', 'market'),
                volume_analysis=combined_signals.get('volume_analysis', {}),
                ai_reasoning=combined_signals.get('reasoning', ''),
                model_used=combined_signals.get('models_used', 'combined')
            )
            
            logger.info(f"✅ Enhanced AI analysis complete for {ticker} - Confidence: {trading_signal.confidence_score}/10")
            return trading_signal
            
        except Exception as e:
            logger.error(f"❌ Enhanced analysis error for {ticker}: {e}")
            return None
    
    def _combine_ai_signals(self, ai_results: List[Dict]) -> Dict:
        """Intelligently combine signals from multiple AI models"""
        if not ai_results:
            return {}
            
        combined = {
            'confidence_score': 5.0,
            'buy_probability': 0.5,
            'support_levels': [],
            'resistance_levels': [],
            'risk_warnings': [],
            'reasoning': '',
            'models_used': []
        }
        
        confidence_scores = []
        all_support = []
        all_resistance = []
        all_risks = []
        all_reasoning = []
        
        for result in ai_results:
            if 'signals' in result:
                signals = result['signals']
                analysis = result.get('analysis', '')
                model = result.get('model', 'unknown')
                
                combined['models_used'].append(model)
                
                if signals.get('confidence_score'):
                    confidence_scores.append(signals['confidence_score'])
                    
                all_support.extend(signals.get('support_levels', []))
                all_resistance.extend(signals.get('resistance_levels', []))
                all_risks.extend(signals.get('risk_warnings', []))
                
                if analysis:
                    all_reasoning.append(f"{model}: {analysis[:200]}...")
                    
                # Take best single values
                if signals.get('stop_loss') and not combined.get('stop_loss'):
                    combined['stop_loss'] = signals['stop_loss']
                if signals.get('target_price') and not combined.get('target_price'):
                    combined['target_price'] = signals['target_price']
                if signals.get('position_size_rec') and not combined.get('position_size_rec'):
                    combined['position_size_rec'] = signals['position_size_rec']
                if signals.get('entry_strategy') and not combined.get('entry_strategy'):
                    combined['entry_strategy'] = signals['entry_strategy']
        
        # Calculate weighted averages
        if confidence_scores:
            combined['confidence_score'] = sum(confidence_scores) / len(confidence_scores)
            combined['buy_probability'] = max(0.0, min(1.0, combined['confidence_score'] / 10.0))
            
        # Deduplicate and sort levels
        if all_support:
            combined['support_levels'] = sorted(list(set(all_support)))[:3]
        if all_resistance:
            combined['resistance_levels'] = sorted(list(set(all_resistance)), reverse=True)[:3]
            
        # Combine risk warnings
        combined['risk_warnings'] = list(set(all_risks))
        
        # Combine reasoning
        combined['reasoning'] = " | ".join(all_reasoning)
        combined['models_used'] = ", ".join(combined['models_used'])
        
        return combined

    async def test_ai_integration(self) -> Dict[str, bool]:
        """Test AI integration with the configured APIs"""
        results = {
            'openai_available': False,
            'claude_available': False,
            'environment_loaded': bool(os.getenv('OPENAI_API_KEY')),
            'test_analysis_success': False
        }
        
        logger.info("🧪 Testing AI Integration...")
        
        # Test OpenAI
        if self.openai_client:
            try:
                test_data = {
                    'current_price': 100.0,
                    'volume': 1000000,
                    'dts_score': 75.0,
                    'v9b_score': 8.5
                }
                openai_result = await self.get_openai_analysis('AAPL', test_data)
                results['openai_available'] = bool(openai_result)
                logger.info(f"✅ OpenAI test: {'PASSED' if results['openai_available'] else 'FAILED'}")
            except Exception as e:
                logger.error(f"❌ OpenAI test failed: {e}")
        
        # Test Claude
        if self.claude_client and self.claude_enabled:
            try:
                test_data = {
                    'current_price': 100.0,
                    'volume': 1000000,
                    'dts_score': 75.0,
                    'v9b_score': 8.5
                }
                claude_result = await self.get_claude_analysis('AAPL', test_data)
                results['claude_available'] = bool(claude_result)
                logger.info(f"✅ Claude test: {'PASSED' if results['claude_available'] else 'FAILED'}")
            except Exception as e:
                logger.error(f"❌ Claude test failed: {e}")
        
        # Test full integration
        if results['openai_available'] or results['claude_available']:
            try:
                test_data = {
                    'current_price': 150.0,
                    'volume': 2000000,
                    'dts_score': 80.0,
                    'v9b_score': 9.0
                }
                enhanced_signal = await self.get_enhanced_analysis('TSLA', test_data)
                results['test_analysis_success'] = enhanced_signal is not None
                logger.info(f"✅ Enhanced analysis test: {'PASSED' if results['test_analysis_success'] else 'FAILED'}")
            except Exception as e:
                logger.error(f"❌ Enhanced analysis test failed: {e}")
        
        return results

async def main():
    """Test the AI intelligence integration"""
    print("🚀 TESTING AI INTELLIGENCE INTEGRATION")
    print("=" * 60)
    
    ai_engine = AIIntelligenceEngine()
    test_results = await ai_engine.test_ai_integration()
    
    print(f"\n📊 TEST RESULTS:")
    print(f"   Environment Loaded: {'✅' if test_results['environment_loaded'] else '❌'}")
    print(f"   OpenAI Available: {'✅' if test_results['openai_available'] else '❌'}")
    print(f"   Claude Available: {'✅' if test_results['claude_available'] else '❌'}")
    print(f"   Enhanced Analysis: {'✅' if test_results['test_analysis_success'] else '❌'}")
    
    success_count = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"\n🎯 OVERALL: {success_count}/{total_tests} tests passed")
    
    if success_count >= 3:
        print("🚀 AI INTELLIGENCE INTEGRATION READY FOR PRODUCTION!")
    else:
        print("⚠️  AI integration needs configuration fixes")
    
    # Demo enhanced analysis
    if test_results['test_analysis_success']:
        print(f"\n🧠 DEMO: Enhanced Analysis for Sample Stock")
        print("-" * 40)
        
        demo_data = {
            'current_price': 45.67,
            'volume': 1500000,
            'dts_score': 78.5,
            'v9b_score': 8.9
        }
        
        signal = await ai_engine.get_enhanced_analysis('DEMO', demo_data)
        if signal:
            print(f"   Ticker: {signal.ticker}")
            print(f"   Confidence: {signal.confidence_score:.1f}/10")
            print(f"   Buy Probability: {signal.buy_probability:.1%}")
            print(f"   Support Levels: {signal.support_levels}")
            print(f"   Resistance Levels: {signal.resistance_levels}")
            print(f"   Risk Warnings: {signal.risk_warnings}")
            print(f"   Position Size Rec: {signal.position_size_rec:.1%}" if signal.position_size_rec else "   Position Size Rec: Not specified")
            print(f"   Models Used: {signal.model_used}")

if __name__ == "__main__":
    asyncio.run(main())