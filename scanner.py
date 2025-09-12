"""
DealerEdge Scanner Module
Handles 250+ symbol scanning with MM vulnerability detection
"""

import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# Import S&P 500 symbols from config
from config import SP500_SYMBOLS, FILTER_OPTIONS

class SymbolScanner:
    """Manages symbol lists and scanning operations for MM exploitation"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.symbols = self.get_all_scannable_symbols()
        
    def get_all_scannable_symbols(self) -> List[str]:
        """Get comprehensive list of 250+ symbols to scan"""
        # Core ETFs (20)
        etfs = [
            'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 
            'XLP', 'XLB', 'XLY', 'XLU', 'XLRE', 'VXX', 'UVXY', 'SQQQ', 'TQQQ',
            'GLD', 'SLV'
        ]
        
        # High volume options stocks (50)
        high_volume = [
            'AAPL', 'TSLA', 'NVDA', 'AMD', 'META', 'AMZN', 'MSFT', 'GOOGL', 
            'NFLX', 'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'SOFI', 'PLTR', 
            'NIO', 'F', 'AAL', 'UAL', 'DAL', 'LUV', 'CCL', 'NCLH', 'RCL', 
            'DKNG', 'PENN', 'WYNN', 'MGM', 'CRM', 'ADBE', 'ORCL', 'IBM',
            'INTC', 'MU', 'QCOM', 'BABA', 'JD', 'PDD', 'SE', 'SHOP',
            'SQ', 'PYPL', 'V', 'MA', 'DIS', 'NTES', 'BIDU', 'COIN'
        ]
        
        # Meme stocks with high retail interest (20)
        meme_stocks = [
            'GME', 'AMC', 'BB', 'BBBY', 'NOK', 'CLOV', 'WISH', 'SPCE', 
            'TLRY', 'SNDL', 'ACB', 'RKT', 'MVIS', 'FUBO', 'PROG', 'ATER',
            'SDC', 'WKHS', 'RIDE', 'GOEV'
        ]
        
        # Additional high gamma stocks (30)
        high_gamma = [
            'UBER', 'LYFT', 'SNAP', 'PINS', 'TWTR', 'ROKU', 'ZM', 'DOCU',
            'CRWD', 'NET', 'DDOG', 'SNOW', 'U', 'RBLX', 'HOOD', 'AFRM',
            'UPST', 'CHPT', 'LCID', 'RIVN', 'FSR', 'XPEV', 'LI', 'BYDDY',
            'TM', 'HMC', 'STLA', 'GM', 'FCAU', 'RACE'
        ]
        
        # Energy and commodities (20)
        commodities = [
            'USO', 'UCO', 'SCO', 'UNG', 'BOIL', 'KOLD', 'GDX', 'GDXJ',
            'NUGT', 'DUST', 'JNUG', 'JDST', 'SLX', 'COPX', 'LIT', 'ICLN',
            'TAN', 'FAN', 'PBW', 'QCLN'
        ]
        
        # Biotech and pharma (20)
        biotech = [
            'XBI', 'IBB', 'LABU', 'LABD', 'MRNA', 'PFE', 'JNJ', 'LLY',
            'ABBV', 'MRK', 'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'ILMN',
            'TMO', 'DHR', 'ABT', 'BMY'
        ]
        
        # Financial sector (20)
        financials = [
            'BRK.B', 'UNH', 'JNJ', 'PG', 'HD', 'CVX', 'LLY', 'XOM',
            'WMT', 'KO', 'PEP', 'COST', 'MCD', 'NKE', 'LOW', 'TGT',
            'SBUX', 'CMG', 'YUM', 'QSR'
        ]
        
        # Tech giants and semiconductors (20)
        tech_semi = [
            'TSM', 'ASML', 'AVGO', 'TXN', 'LRCX', 'KLAC', 'AMAT', 'ADI',
            'MRVL', 'NXPI', 'MCHP', 'SWKS', 'QRVO', 'XLNX', 'MPWR', 'ENPH',
            'SEDG', 'FSLR', 'RUN', 'SPWR'
        ]
        
        # Combine all lists (total ~200 unique symbols)
        all_symbols = list(set(
            etfs + high_volume + meme_stocks + high_gamma + 
            commodities + biotech + financials + tech_semi + 
            SP500_SYMBOLS[:100]  # Add first 100 S&P 500 symbols
        ))
        
        # Ensure we have at least 250 symbols
        if len(all_symbols) < 250:
            # Add more S&P 500 symbols to reach 250
            remaining_sp500 = [s for s in SP500_SYMBOLS if s not in all_symbols]
            all_symbols.extend(remaining_sp500[:250 - len(all_symbols)])
        
        return sorted(all_symbols)[:300]  # Return up to 300 symbols
    
    def get_high_mm_vulnerability_symbols(self) -> List[str]:
        """Get symbols where MMs are most vulnerable (highest gamma exposure)"""
        return [
            'SPY', 'QQQ', 'IWM', 'TSLA', 'NVDA', 'AMD', 'AAPL', 'GME', 
            'AMC', 'META', 'AMZN', 'GOOGL', 'NFLX', 'SOFI', 'PLTR',
            'NIO', 'DKNG', 'COIN', 'HOOD', 'MARA'
        ]
    
    def scan_for_mm_patterns(self, symbol: str) -> Dict:
        """Scan single symbol for MM exploitation patterns"""
        patterns = {
            'symbol': symbol,
            'patterns_found': [],
            'mm_vulnerability': 0,
            'best_exploit': None
        }
        
        try:
            # Get options data
            options_data = self.analyzer.get_options_chain(symbol)
            if not options_data:
                return patterns
            
            # Calculate GEX profile
            gex_profile = self.analyzer.calculate_gex_profile(options_data)
            if not gex_profile:
                return patterns
            
            # Extract key metrics with safe defaults
            dealer_pain = gex_profile.get('dealer_pain', 0)
            net_gex = gex_profile.get('net_gex', 0)
            distance_to_flip = gex_profile.get('distance_to_flip', 0)
            current_price = gex_profile.get('current_price', 0)
            gamma_flip = gex_profile.get('gamma_flip', 0)
            vix = gex_profile.get('vix', 15)
            
            # Pattern 1: Trapped MM (extreme pain)
            if dealer_pain > 80:
                patterns['patterns_found'].append({
                    'type': 'TRAPPED_MM',
                    'confidence': min(95, dealer_pain),
                    'action': 'EXPLOIT_IMMEDIATELY',
                    'specific_trade': f'Buy 0DTE {"calls" if current_price < gamma_flip else "puts"} for explosive move',
                    'urgency': 'CRITICAL',
                    'expected_return': '100-300%'
                })
                patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], dealer_pain)
            
            # Pattern 2: Gamma Squeeze Setup
            if net_gex < -1e9 and abs(distance_to_flip) < 1:
                patterns['patterns_found'].append({
                    'type': 'GAMMA_SQUEEZE',
                    'confidence': 85,
                    'action': 'BUY_CALLS',
                    'specific_trade': 'Buy calls 1-2 strikes OTM, hold for squeeze',
                    'urgency': 'HIGH',
                    'expected_return': '50-200%'
                })
                patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], 85)
            
            # Pattern 3: Pin Risk (near gamma flip)
            if abs(distance_to_flip) < 0.3:
                patterns['patterns_found'].append({
                    'type': 'PIN_RISK',
                    'confidence': 75,
                    'action': 'SELL_PREMIUM',
                    'specific_trade': f'Sell straddle at ${gamma_flip:.0f} strike',
                    'urgency': 'MEDIUM',
                    'expected_return': '20-40%'
                })
                patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], 75)
            
            # Pattern 4: Charm Acceleration (Friday afternoon)
            if datetime.now().weekday() == 4 and datetime.now().hour >= 14:
                if abs(net_gex) > 2e9:
                    patterns['patterns_found'].append({
                        'type': 'CHARM_FLOW',
                        'confidence': 80,
                        'action': 'SCALP_0DTE',
                        'specific_trade': 'Buy 0DTE options at 3:00 PM in trend direction',
                        'urgency': 'TIME_SENSITIVE',
                        'expected_return': '50-150%'
                    })
                    patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], 80)
            
            # Pattern 5: OPEX Vulnerability
            if self.is_opex_week() and dealer_pain > 60:
                patterns['patterns_found'].append({
                    'type': 'OPEX_PRESSURE',
                    'confidence': 70,
                    'action': 'POSITION_FOR_UNWIND',
                    'specific_trade': 'Buy weekly options for Friday gamma unwind',
                    'urgency': 'MODERATE',
                    'expected_return': '30-100%'
                })
                patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], 70)
            
            # Pattern 6: Vanna Exposure (volatility sensitivity)
            if vix > 20 and net_gex < 0:
                patterns['patterns_found'].append({
                    'type': 'VANNA_SQUEEZE',
                    'confidence': 75,
                    'action': 'BUY_CALLS',
                    'specific_trade': 'VIX spike + negative gamma = violent rally incoming',
                    'urgency': 'HIGH',
                    'expected_return': '40-120%'
                })
                patterns['mm_vulnerability'] = max(patterns['mm_vulnerability'], 75)
            
            # Set best exploit - safe handling
            if patterns['patterns_found']:
                patterns['best_exploit'] = max(patterns['patterns_found'], 
                                              key=lambda x: x.get('confidence', 0))
            
            # Add GEX data to patterns
            patterns['gex_profile'] = gex_profile
            patterns['current_price'] = current_price
            patterns['net_gex'] = net_gex
            patterns['dealer_pain'] = dealer_pain
            
        except Exception as e:
            patterns['error'] = str(e)
        
        return patterns
    
    def scan_multiple_symbols(self, symbols: List[str], 
                            progress_callback: Optional[Callable] = None,
                            min_confidence: float = 50) -> List[Dict]:
        """Scan multiple symbols in parallel for MM exploitation opportunities"""
        results = []
        total_symbols = len(symbols)
        
        # Ensure we're scanning at least 250 symbols if requested
        if total_symbols < 250:
            # Add more symbols from our master list
            additional_symbols = [s for s in self.symbols if s not in symbols]
            symbols.extend(additional_symbols[:250 - total_symbols])
            total_symbols = len(symbols)
        
        def process_symbol(symbol: str) -> Optional[Dict]:
            """Process a single symbol for all MM patterns"""
            try:
                # Get MM patterns
                mm_patterns = self.scan_for_mm_patterns(symbol)
                
                # Get standard signals
                options_data = self.analyzer.get_options_chain(symbol)
                signals = []
                gex_profile = None
                
                if options_data:
                    gex_profile = self.analyzer.calculate_gex_profile(options_data)
                    if gex_profile:
                        signals = self.analyzer.generate_all_signals(gex_profile, symbol)
                        filtered_signals = [s for s in signals 
                                          if s.get('confidence', 0) >= min_confidence]
                        
                        # Use filtered signals if available, otherwise use all signals
                        signals = filtered_signals if filtered_signals else signals
                        
                        # Calculate opportunity score with MM vulnerability
                        opportunity_score = self.calculate_opportunity_score(
                            gex_profile, 
                            signals,
                            mm_patterns.get('mm_vulnerability', 0)
                        )
                        
                        return {
                            'symbol': symbol,
                            'gex_profile': gex_profile,
                            'signals': signals,
                            'best_signal': signals[0] if signals else None,
                            'opportunity_score': opportunity_score,
                            'mm_patterns': mm_patterns.get('patterns_found', []),
                            'mm_vulnerability': mm_patterns.get('mm_vulnerability', 0),
                            'best_exploit': mm_patterns.get('best_exploit')
                        }
                
                # Return basic result if no options data
                return {
                    'symbol': symbol,
                    'gex_profile': None,
                    'signals': [],
                    'best_signal': None,
                    'opportunity_score': mm_patterns.get('mm_vulnerability', 0) * 0.5,
                    'mm_patterns': mm_patterns.get('patterns_found', []),
                    'mm_vulnerability': mm_patterns.get('mm_vulnerability', 0),
                    'best_exploit': mm_patterns.get('best_exploit')
                }
                
            except Exception as e:
                return {
                    'symbol': symbol,
                    'error': str(e),
                    'opportunity_score': 0,
                    'mm_vulnerability': 0,
                    'mm_patterns': [],
                    'best_exploit': None
                }
        
        # Use ThreadPoolExecutor for parallel scanning
        with ThreadPoolExecutor(max_workers=25) as executor:  # Increased workers for speed
            future_to_symbol = {executor.submit(process_symbol, symbol): symbol 
                              for symbol in symbols}
            
            completed = 0
            for future in as_completed(future_to_symbol):
                try:
                    result = future.result(timeout=10)
                    if result and not result.get('error'):
                        results.append(result)
                except:
                    pass
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_symbols)
        
        # Sort by MM vulnerability first, then opportunity score
        results.sort(key=lambda x: (x.get('mm_vulnerability', 0), 
                                   x.get('opportunity_score', 0)), 
                    reverse=True)
        
        return results
    
    def calculate_opportunity_score(self, gex_profile: Optional[Dict], 
                                   signals: List[Dict],
                                   mm_vulnerability: float = 0) -> float:
        """Calculate opportunity score with MM vulnerability as primary factor"""
        if not gex_profile:
            return mm_vulnerability * 0.5
        
        score = 0
        
        # MM vulnerability is most important (40% weight)
        score += mm_vulnerability * 0.4
        
        # Dealer pain (20% weight)
        dealer_pain = gex_profile.get('dealer_pain', 0)
        score += dealer_pain * 0.2
        
        # Signal confidence (20% weight)
        if signals:
            best_confidence = max(s.get('confidence', 0) for s in signals)
            score += best_confidence * 0.2
        
        # Distance to gamma flip (10% weight)
        distance_to_flip = abs(gex_profile.get('distance_to_flip', 100))
        if distance_to_flip < 0.5:
            score += 10
        elif distance_to_flip < 1:
            score += 7
        elif distance_to_flip < 2:
            score += 3
        
        # Special events (10% weight)
        if self.is_opex_week():
            score += 5
        if self.is_quad_witching_week():
            score += 5
        if datetime.now().weekday() == 4 and datetime.now().hour >= 14:  # Friday PM
            score += 3
        
        return min(100, score)
    
    def is_opex_week(self) -> bool:
        """Check if current week is OPEX week"""
        try:
            today = datetime.now()
            # Get third Friday of month
            first_day = datetime(today.year, today.month, 1)
            first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
            if first_friday.day <= 7:
                first_friday += timedelta(days=7)
            third_friday = first_friday + timedelta(weeks=2)
            
            # Check if within 5 days of OPEX
            days_to_opex = (third_friday.date() - today.date()).days
            return 0 <= days_to_opex <= 5
        except:
            return False
    
    def is_quad_witching_week(self) -> bool:
        """Check if current week is quad witching"""
        try:
            today = datetime.now()
            if today.month in [3, 6, 9, 12]:
                return self.is_opex_week()
            return False
        except:
            return False
    
    def scan_0dte_opportunities(self) -> List[Dict]:
        """Scan for 0DTE opportunities across high-gamma symbols"""
        opportunities = []
        priority_symbols = self.get_high_mm_vulnerability_symbols()
        
        for symbol in priority_symbols:
            try:
                options_data = self.analyzer.get_options_chain(symbol)
                if options_data and 'chains' in options_data:
                    for exp_date, chain_data in options_data['chains'].items():
                        if chain_data.get('dte', 1) == 0:  # 0DTE options
                            calls = chain_data.get('calls', pd.DataFrame())
                            puts = chain_data.get('puts', pd.DataFrame())
                            
                            if not calls.empty or not puts.empty:
                                # Find high gamma strikes
                                high_gamma_strikes = []
                                
                                if not calls.empty and 'gamma' in calls.columns:
                                    high_gamma_calls = calls[calls['gamma'] > calls['gamma'].quantile(0.9)]
                                    if not high_gamma_calls.empty:
                                        high_gamma_strikes.extend(high_gamma_calls['strike'].tolist())
                                
                                if not puts.empty and 'gamma' in puts.columns:
                                    high_gamma_puts = puts[puts['gamma'] > puts['gamma'].quantile(0.9)]
                                    if not high_gamma_puts.empty:
                                        high_gamma_strikes.extend(high_gamma_puts['strike'].tolist())
                                
                                if high_gamma_strikes:
                                    opportunities.append({
                                        'symbol': symbol,
                                        'expiry': exp_date,
                                        'high_gamma_strikes': high_gamma_strikes[:5],  # Top 5 strikes
                                        'current_price': options_data.get('current_price', 0),
                                        'action': 'Monitor for 3PM charm acceleration',
                                        'potential_return': '50-200%',
                                        'specific_trade': f'Buy 0DTE at strikes: {", ".join([f"${s:.0f}" for s in high_gamma_strikes[:3]])}'
                                    })
            except:
                continue
        
        return opportunities
    
    def get_realtime_mm_alerts(self, symbols: List[str]) -> List[Dict]:
        """Get real-time MM vulnerability alerts for quick monitoring"""
        alerts = []
        
        for symbol in symbols[:30]:  # Check top 30 for speed
            patterns = self.scan_for_mm_patterns(symbol)
            
            if patterns.get('mm_vulnerability', 0) > 80:
                best_exploit = patterns.get('best_exploit', {})
                alerts.append({
                    'symbol': symbol,
                    'alert_type': 'CRITICAL',
                    'message': f"🔥 {symbol}: MM TRAPPED - Pain {patterns.get('mm_vulnerability', 0):.0f}",
                    'action': best_exploit.get('specific_trade', 'Monitor closely') if best_exploit else 'Monitor closely',
                    'expected_return': best_exploit.get('expected_return', 'N/A') if best_exploit else 'N/A',
                    'timestamp': datetime.now()
                })
            
            elif patterns.get('mm_vulnerability', 0) > 70:
                alerts.append({
                    'symbol': symbol,
                    'alert_type': 'WARNING',
                    'message': f"⚠️ {symbol}: MM Vulnerable - Pain {patterns.get('mm_vulnerability', 0):.0f}",
                    'action': 'Prepare to exploit',
                    'expected_return': '20-50%',
                    'timestamp': datetime.now()
                })
        
        return alerts
    
    def filter_results_by_type(self, results: List[Dict], filter_type: str) -> List[Dict]:
        """Enhanced filtering with MM patterns and vulnerability levels"""
        if filter_type == "🔥 Trapped MMs":
            return [r for r in results 
                   if r.get('mm_vulnerability', 0) > 80]
        
        elif filter_type == "😰 Scrambling MMs":
            return [r for r in results 
                   if 60 < r.get('mm_vulnerability', 0) <= 80]
        
        elif filter_type == "⚡ Gamma Squeeze":
            return [r for r in results 
                   if any(p.get('type') == 'GAMMA_SQUEEZE' for p in r.get('mm_patterns', []))]
        
        elif filter_type == "📌 Pin Risk":
            return [r for r in results 
                   if any(p.get('type') == 'PIN_RISK' for p in r.get('mm_patterns', []))]
        
        elif filter_type == "🌊 Charm Flow":
            return [r for r in results 
                   if any(p.get('type') == 'CHARM_FLOW' for p in r.get('mm_patterns', []))]
        
        elif filter_type == "🎯 OPEX Plays":
            return [r for r in results 
                   if any(p.get('type') == 'OPEX_PRESSURE' for p in r.get('mm_patterns', []))]
        
        elif filter_type == "💎 Vanna Squeeze":
            return [r for r in results 
                   if any(p.get('type') == 'VANNA_SQUEEZE' for p in r.get('mm_patterns', []))]
        
        elif filter_type == "💰 Premium Selling":
            return [r for r in results 
                   if r.get('best_signal') and r['best_signal'].get('type') == 'PREMIUM_SELLING']
        
        elif filter_type == "🦅 Iron Condors":
            return [r for r in results 
                   if r.get('best_signal') and r['best_signal'].get('type') == 'IRON_CONDOR']
        
        elif filter_type == "📈 High Confidence (>75%)":
            return [r for r in results 
                   if r.get('best_signal') and r['best_signal'].get('confidence', 0) > 75]
        
        elif filter_type == "🎯 Immediate Action":
            return [r for r in results 
                   if r.get('best_exploit') and r.get('best_exploit', {}).get('urgency') in ['HIGH', 'CRITICAL', 'TIME_SENSITIVE']]
        
        elif filter_type == "🔥 High Pain (>70)":
            return [r for r in results 
                   if r.get('gex_profile') and r['gex_profile'].get('dealer_pain', 0) > 70]
        
        else:  # Show all
            return results
    
    def get_scan_statistics(self, results: List[Dict]) -> Dict:
        """Get statistics from scan results with bulletproof error handling"""
        if not results:
            return {
                'total_scanned': 0,
                'opportunities': 0,
                'trapped_mms': 0,
                'scrambling_mms': 0,
                'avg_vulnerability': 0,
                'critical_alerts': 0,
                'high_confidence': 0
            }
        
        try:
            # Helper functions for safe nested dictionary access
            def safe_get_urgency(result):
                """Safely get urgency from best_exploit"""
                try:
                    best_exploit = result.get('best_exploit')
                    if best_exploit and isinstance(best_exploit, dict):
                        return best_exploit.get('urgency')
                    return None
                except (AttributeError, TypeError, KeyError):
                    return None
            
            def safe_get_confidence(result):
                """Safely get confidence from best_signal"""
                try:
                    best_signal = result.get('best_signal')
                    if best_signal and isinstance(best_signal, dict):
                        return best_signal.get('confidence', 0)
                    return 0
                except (AttributeError, TypeError, KeyError):
                    return 0
            
            # Calculate statistics with safe operations
            total_scanned = len(results)
            opportunities = 0
            trapped_mms = 0
            scrambling_mms = 0
            vulnerability_sum = 0
            critical_alerts = 0
            high_confidence = 0
            
            for result in results:
                try:
                    # Opportunity score check
                    opp_score = result.get('opportunity_score', 0)
                    if isinstance(opp_score, (int, float)) and opp_score > 50:
                        opportunities += 1
                    
                    # MM vulnerability checks
                    mm_vuln = result.get('mm_vulnerability', 0)
                    if isinstance(mm_vuln, (int, float)):
                        vulnerability_sum += mm_vuln
                        if mm_vuln > 80:
                            trapped_mms += 1
                        elif 60 < mm_vuln <= 80:
                            scrambling_mms += 1
                    
                    # Critical alerts check
                    urgency = safe_get_urgency(result)
                    if urgency in ['CRITICAL', 'HIGH', 'TIME_SENSITIVE']:
                        critical_alerts += 1
                    
                    # High confidence check
                    confidence = safe_get_confidence(result)
                    if isinstance(confidence, (int, float)) and confidence > 75:
                        high_confidence += 1
                        
                except (AttributeError, TypeError, KeyError):
                    # Skip problematic results
                    continue
            
            # Calculate average vulnerability safely
            avg_vulnerability = (vulnerability_sum / total_scanned) if total_scanned > 0 else 0
            
            return {
                'total_scanned': total_scanned,
                'opportunities': opportunities,
                'trapped_mms': trapped_mms,
                'scrambling_mms': scrambling_mms,
                'avg_vulnerability': round(avg_vulnerability, 1),
                'critical_alerts': critical_alerts,
                'high_confidence': high_confidence
            }
            
        except Exception as e:
            # Ultimate fallback - return safe defaults with error info
            return {
                'total_scanned': len(results) if results else 0,
                'opportunities': 0,
                'trapped_mms': 0,
                'scrambling_mms': 0,
                'avg_vulnerability': 0,
                'critical_alerts': 0,
                'high_confidence': 0,
                'error': f"Statistics calculation error: {str(e)}"
            }
