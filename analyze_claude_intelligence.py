#!/opt/homebrew/bin/python3.12
"""
ANALYZE CLAUDE TRADING INTELLIGENCE
Extract and examine Claude/Nano 4.1 analysis for integration opportunities
"""

import os
import re
import json
from datetime import datetime, timedelta
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

def extract_claude_signals(claude_text):
    """Extract actionable trading signals from Claude analysis"""
    if not claude_text:
        return {}
    
    signals = {
        'confidence_score': None,
        'support_levels': [],
        'resistance_levels': [],
        'stop_loss': None,
        'target_price': None,
        'risk_warnings': [],
        'position_size_rec': None,
        'entry_strategy': None,
        'volume_analysis': None
    }
    
    # Extract confidence score
    confidence_match = re.search(r'(?:confidence|score).*?(\d+(?:\.\d+)?)\s*[/]?\s*10', claude_text.lower())
    if confidence_match:
        signals['confidence_score'] = float(confidence_match.group(1))
    
    # Extract support levels
    support_matches = re.findall(r'support.*?\$(\d+(?:\.\d+)?)', claude_text.lower())
    signals['support_levels'] = [float(m) for m in support_matches]
    
    # Extract resistance levels
    resistance_matches = re.findall(r'resistance.*?\$(\d+(?:\.\d+)?)', claude_text.lower())
    signals['resistance_levels'] = [float(m) for m in resistance_matches]
    
    # Extract stop loss
    stop_matches = re.findall(r'stop.*?(?:loss)?.*?\$(\d+(?:\.\d+)?)', claude_text.lower())
    if stop_matches:
        signals['stop_loss'] = float(stop_matches[0])
    
    # Extract target price
    target_matches = re.findall(r'target.*?\$(\d+(?:\.\d+)?)', claude_text.lower())
    if target_matches:
        signals['target_price'] = float(target_matches[0])
    
    # Extract risk warnings
    risk_keywords = ['volatile', 'risky', 'caution', 'high risk', 'dangerous', 'unstable']
    for keyword in risk_keywords:
        if keyword in claude_text.lower():
            signals['risk_warnings'].append(keyword)
    
    # Extract position size recommendations
    size_match = re.search(r'(?:position|size).*?(\d+(?:\.\d+)?)\s*%', claude_text.lower())
    if size_match:
        signals['position_size_rec'] = float(size_match.group(1)) / 100
    
    # Extract volume analysis
    if any(word in claude_text.lower() for word in ['volume', 'institutional', 'retail']):
        signals['volume_analysis'] = 'present'
    
    return signals

def analyze_claude_intelligence():
    """Analyze Claude trading intelligence for hot stocks"""
    print("🧠 ANALYZING CLAUDE TRADING INTELLIGENCE")
    print("=" * 70)
    
    env_vars = load_environment()
    supabase = create_client(env_vars['SUPABASE_URL'], env_vars['SUPABASE_KEY'])
    
    # Get hot stocks with Claude analysis
    hot_stocks = ['NA', 'KLTO', 'KNW', 'CTXR', 'NCNA', 'MB']
    
    print(f"🔍 Examining Claude analysis for hot stocks: {', '.join(hot_stocks)}")
    
    try:
        result = supabase.table('v9_multi_source_analysis').select(
            'ticker, claude_analysis, v9_combined_score, dts_score, created_at'
        ).in_('ticker', hot_stocks).not_.is_('claude_analysis', 'null').order('created_at', desc=True).limit(20).execute()
        
        if result.data:
            print(f"\n📊 Found {len(result.data)} records with Claude analysis")
            
            claude_signals = {}
            
            for record in result.data:
                ticker = record['ticker']
                claude_text = record.get('claude_analysis', '')
                dts_score = record.get('dts_score', 0)
                v9b_score = record.get('v9_combined_score', 0)
                created = record.get('created_at', '')[:16]
                
                if claude_text and len(claude_text) > 100:  # Only analyze substantial content
                    signals = extract_claude_signals(claude_text)
                    claude_signals[ticker] = {
                        'signals': signals,
                        'dts_score': dts_score,
                        'v9b_score': v9b_score,
                        'created': created,
                        'full_analysis': claude_text
                    }
            
            # Display analysis results
            print(f"\n🎯 CLAUDE INTELLIGENCE ANALYSIS RESULTS:")
            print("-" * 50)
            
            for ticker, data in claude_signals.items():
                signals = data['signals']
                dts = data['dts_score']
                v9b = data['v9b_score']
                
                print(f"\n📈 {ticker} (DTS: {dts}, V9B: {v9b:.1f})")
                
                if signals['confidence_score']:
                    print(f"   🎯 Claude Confidence: {signals['confidence_score']}/10")
                
                if signals['support_levels']:
                    print(f"   📉 Support Levels: ${', $'.join(map(str, signals['support_levels']))}")
                
                if signals['resistance_levels']:
                    print(f"   📈 Resistance Levels: ${', $'.join(map(str, signals['resistance_levels']))}")
                
                if signals['stop_loss']:
                    print(f"   🛑 Stop Loss: ${signals['stop_loss']}")
                
                if signals['target_price']:
                    print(f"   🎯 Target Price: ${signals['target_price']}")
                
                if signals['position_size_rec']:
                    print(f"   💰 Position Size Rec: {signals['position_size_rec']*100:.1f}%")
                
                if signals['risk_warnings']:
                    print(f"   ⚠️ Risk Warnings: {', '.join(signals['risk_warnings'])}")
                
                if signals['volume_analysis']:
                    print(f"   📊 Volume Analysis: Available")
                
                # Show a snippet of the full analysis
                print(f"   📝 Analysis Snippet: {data['full_analysis'][:200]}...")
            
            # Analyze integration opportunities
            print(f"\n🔧 INTEGRATION OPPORTUNITIES:")
            print("-" * 35)
            
            total_with_confidence = sum(1 for data in claude_signals.values() if data['signals']['confidence_score'])
            total_with_levels = sum(1 for data in claude_signals.values() if data['signals']['support_levels'] or data['signals']['resistance_levels'])
            total_with_risk = sum(1 for data in claude_signals.values() if data['signals']['risk_warnings'])
            
            print(f"✅ Stocks with Claude confidence scores: {total_with_confidence}/{len(claude_signals)}")
            print(f"✅ Stocks with support/resistance levels: {total_with_levels}/{len(claude_signals)}")
            print(f"⚠️ Stocks with risk warnings: {total_with_risk}/{len(claude_signals)}")
            
            # Calculate potential improvements
            avg_confidence = sum(data['signals']['confidence_score'] or 0 for data in claude_signals.values()) / len(claude_signals)
            
            print(f"\n📊 INTELLIGENCE QUALITY METRICS:")
            print(f"   🎯 Average Claude Confidence: {avg_confidence:.1f}/10")
            print(f"   📈 Technical Analysis Coverage: {total_with_levels}/{len(claude_signals)} stocks")
            print(f"   ⚠️ Risk Management Coverage: {total_with_risk}/{len(claude_signals)} stocks")
            
            return claude_signals
        else:
            print("❌ No Claude analysis found for hot stocks")
            return {}
            
    except Exception as e:
        print(f"❌ Error analyzing Claude intelligence: {e}")
        return {}

def main():
    claude_data = analyze_claude_intelligence()
    
    if claude_data:
        print(f"\n🚀 RECOMMENDATION: INTEGRATE CLAUDE INTELLIGENCE")
        print(f"💡 This analysis could significantly improve trading performance!")
        print(f"🎯 Next steps: Implement Claude signal integration in SystemX")
    else:
        print(f"\n❌ Unable to analyze Claude intelligence")
    
    return claude_data

if __name__ == "__main__":
    main()