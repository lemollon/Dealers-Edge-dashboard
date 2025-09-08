"""
DealerEdge Scanner Module
Handles symbol lists and multi-threaded scanning
"""

import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
from config import SP500_SYMBOLS, FILTER_OPTIONS

class SymbolScanner:
    """Manages symbol lists and scanning operations"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.symbols = SP500_SYMBOLS
        
    def scan_multiple_symbols(self, symbols: List[str], 
                            progress_callback: Optional[Callable] = None,
                            min_confidence: float = 50) -> List[Dict]:
        """Scan multiple symbols for GEX opportunities"""
        results = []
        
        def process_symbol(symbol: str) -> Optional[Dict]:
            """Process a single symbol"""
            try:
                options_data = self.analyzer.get_options_chain(symbol)
                if options_data:
                    gex_profile = self.analyzer.calculate_gex_profile(options_data)
                    if gex_profile:
                        signals = self.analyzer.generate_all_signals(gex_profile, symbol)
                        filtered_signals = [s for s in signals 
                                          if s.get('confidence', 0) >= min_confidence]
                        
                        return {
                            'symbol': symbol,
                            'gex_profile': gex_profile,
                            'signals': filtered_signals if filtered_signals else signals,
                            'best_signal': filtered_signals[0] if filtered_signals else signals[0] if signals else None,
                            'opportunity_score': self.calculate_opportunity_score(gex_profile, filtered_signals)
                        }
                
                return {
                    'symbol': symbol,
                    'gex_profile': None,
                    'signals': [{
                        'type': 'WAIT',
                        'direction': 'NO DATA',
                        'confidence': 0,
                        'reasoning': 'Unable to fetch options data',
                        'position_size': 0
                    }],
                    'best_signal': None,
                    'opportunity_score': 0
                }
                
            except Exception as e:
                return None
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(process_symbol, symbol): symbol 
                              for symbol in symbols}
            
            completed = 0
            for future in as_completed(future_to_symbol):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except:
                    pass
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(symbols))
        
        results.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        return results
    
    def calculate_opportunity_score(self, gex_profile: Optional[Dict], 
                                   signals: List[Dict]) -> float:
        """Calculate opportunity score for ranking"""
        if not gex_profile:
            return 0
        
        score = 0
        
        dealer_pain = gex_profile.get('dealer_pain', 0)
        score += dealer_pain * 0.4
        
        if signals:
            best_confidence = max(s.get('confidence', 0) for s in signals)
            score += best_confidence * 0.4
        
        distance_to_flip = abs(gex_profile.get('distance_to_flip', 100))
        if distance_to_flip < 1:
            score += 10
        elif distance_to_flip < 2:
            score += 5
        
        toxicity = gex_profile.get('toxicity_score', 0)
        if toxicity > 50:
            score += 10
        elif toxicity > 0:
            score += 5
        
        return min(100, score)
    
    def filter_results_by_type(self, results: List[Dict], filter_type: str) -> List[Dict]:
        """Filter scan results by type"""
        if filter_type == "🔥 High Pain (>70)":
            return [r for r in results 
                   if r['gex_profile'] and r['gex_profile'].get('dealer_pain', 0) > 70]
        
        elif filter_type == "⚡ Squeeze Plays":
            return [r for r in results 
                   if r['best_signal'] and r['best_signal'].get('type') == 'SQUEEZE_PLAY']
        
        elif filter_type == "💰 Premium Selling":
            return [r for r in results 
                   if r['best_signal'] and r['best_signal'].get('type') == 'PREMIUM_SELLING']
        
        elif filter_type == "🦅 Iron Condors":
            return [r for r in results 
                   if r['best_signal'] and r['best_signal'].get('type') == 'IRON_CONDOR']
        
        elif filter_type == "📈 High Confidence (>75%)":
            return [r for r in results 
                   if r['best_signal'] and r['best_signal'].get('confidence', 0) > 75]
        
        elif filter_type == "🎯 Immediate Action":
            return [r for r in results 
                   if r['best_signal'] and 
                   r['best_signal'].get('confidence', 0) > 70 and
                   r['gex_profile'] and r['gex_profile'].get('dealer_pain', 0) > 60]
        
        else:
            return results
