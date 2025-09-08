"""
DealerEdge Analyzer Module
Core GEX calculation and signal generation engine
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date, timedelta
from scipy.stats import norm
import warnings
from typing import Dict, List, Tuple, Optional
import requests

warnings.filterwarnings('ignore')

class DealerEdgeAnalyzer:
    """Complete GEX analyzer with all trading strategies"""
    
    def __init__(self):
        self.risk_free_rate = 0.05
        self.trading_capital = 100000
        self.strategies_config = {
            'squeeze_plays': {
                'negative_gex_threshold_spy': -1e9,
                'negative_gex_threshold_qqq': -500e6,
                'positive_gex_threshold_spy': 2e9,
                'positive_gex_threshold_qqq': 1e9,
                'flip_distance_threshold': 1.5,
                'dte_range': [0, 7],
                'confidence_threshold': 65
            },
            'premium_selling': {
                'positive_gex_threshold': 3e9,
                'wall_strength_threshold': 500e6,
                'wall_distance_range': [1, 5],
                'put_distance_range': [1, 8],
                'dte_range_calls': [0, 2],
                'dte_range_puts': [2, 5]
            },
            'iron_condor': {
                'min_gex_threshold': 1e9,
                'min_wall_spread': 3,
                'dte_range': [5, 10],
                'iv_rank_threshold': 50
            },
            'risk_management': {
                'max_position_size_squeeze': 0.03,
                'max_position_size_premium': 0.05,
                'max_position_size_condor': 0.02,
                'stop_loss_percentage': 0.50,
                'profit_target_long': 1.00,
                'profit_target_short': 0.50
            }
        }
        self.last_auto_scan = None
        self.auto_scan_interval = 2
        
    def black_scholes_gamma(self, S, K, T, r, sigma):
        """Calculate Black-Scholes gamma for options"""
        try:
            if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
                return 0
            
            d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            return gamma if not np.isnan(gamma) else 0
        except:
            return 0
    
    def get_current_price(self, symbol):
        """Get current stock price from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if len(hist) > 0:
                return float(hist['Close'].iloc[-1])
            
            hist = ticker.history(period="5d")
            if len(hist) > 0:
                return float(hist['Close'].iloc[-1])
            
            return None
        except:
            return None
    
    def get_historical_data(self, symbol, period="1mo"):
        """Get historical data for backtesting"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval="1h")
            return hist if len(hist) > 0 else None
        except:
            return None
    
    def calculate_vix(self):
        """Get current VIX level"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if len(hist) > 0:
                return float(hist['Close'].iloc[-1])
            return 15.0
        except:
            return 15.0
    
    def get_options_chain(self, symbol, focus_weekly=True):
        """Get complete options chain from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            exp_dates = ticker.options
            
            if not exp_dates:
                return None
            
            current_price = self.get_current_price(symbol)
            if current_price is None:
                return None
            
            all_chains = {}
            today = date.today()
            
            for exp_date in exp_dates[:15]:
                try:
                    exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    dte = (exp_dt.date() - today).days
                    
                    if dte <= 0 or dte > 14:
                        continue
                    
                    if symbol in ['SPY', 'QQQ', 'IWM'] and dte <= 5:
                        pass
                    elif dte <= 7:
                        pass
                    elif not focus_weekly and dte <= 14:
                        pass
                    else:
                        continue
                    
                    chain = ticker.option_chain(exp_date)
                    
                    calls = chain.calls.copy()
                    calls = calls[calls['openInterest'] > 0]
                    
                    puts = chain.puts.copy()
                    puts = puts[puts['openInterest'] > 0]
                    
                    if len(calls) == 0 and len(puts) == 0:
                        continue
                    
                    T = dte / 365.0
                    
                    calls['gamma'] = calls.apply(
                        lambda row: self.black_scholes_gamma(
                            current_price, 
                            row['strike'], 
                            T, 
                            self.risk_free_rate,
                            max(row['impliedVolatility'], 0.15) if pd.notna(row['impliedVolatility']) else 0.30
                        ), axis=1
                    )
                    
                    puts['gamma'] = puts.apply(
                        lambda row: self.black_scholes_gamma(
                            current_price,
                            row['strike'],
                            T,
                            self.risk_free_rate,
                            max(row['impliedVolatility'], 0.15) if pd.notna(row['impliedVolatility']) else 0.30
                        ), axis=1
                    )
                    
                    calls['gex'] = current_price * calls['gamma'] * calls['openInterest'] * 100
                    puts['gex'] = -current_price * puts['gamma'] * puts['openInterest'] * 100
                    
                    calls['gex'] = calls['gex'].fillna(0)
                    puts['gex'] = puts['gex'].fillna(0)
                    
                    all_chains[exp_date] = {
                        'calls': calls,
                        'puts': puts,
                        'dte': dte,
                        'expiration': exp_dt,
                        'is_daily': dte <= 5 and symbol in ['SPY', 'QQQ', 'IWM']
                    }
                    
                except:
                    continue
            
            return {
                'chains': all_chains,
                'current_price': current_price,
                'symbol': symbol,
                'data_timestamp': datetime.now()
            }
            
        except:
            return None
    
    def calculate_gex_profile(self, options_data):
        """Calculate complete GEX profile from options data"""
        try:
            if not options_data or 'chains' not in options_data:
                return None
            
            current_price = options_data['current_price']
            chains = options_data['chains']
            
            if not chains:
                return None
            
            strike_data = {}
            total_options_volume = 0
            
            for exp_date, chain_data in chains.items():
                calls = chain_data['calls']
                puts = chain_data['puts']
                
                total_options_volume += calls['volume'].fillna(0).sum()
                total_options_volume += puts['volume'].fillna(0).sum()
                
                for _, call in calls.iterrows():
                    strike = float(call['strike'])
                    gex = float(call['gex']) if pd.notna(call['gex']) else 0
                    oi = int(call['openInterest']) if pd.notna(call['openInterest']) else 0
                    volume = int(call.get('volume', 0)) if pd.notna(call.get('volume', 0)) else 0
                    
                    if strike not in strike_data:
                        strike_data[strike] = {
                            'call_gex': 0, 'put_gex': 0,
                            'call_oi': 0, 'put_oi': 0,
                            'call_volume': 0, 'put_volume': 0
                        }
                    
                    strike_data[strike]['call_gex'] += gex
                    strike_data[strike]['call_oi'] += oi
                    strike_data[strike]['call_volume'] += volume
                
                for _, put in puts.iterrows():
                    strike = float(put['strike'])
                    gex = float(put['gex']) if pd.notna(put['gex']) else 0
                    oi = int(put['openInterest']) if pd.notna(put['openInterest']) else 0
                    volume = int(put.get('volume', 0)) if pd.notna(put.get('volume', 0)) else 0
                    
                    if strike not in strike_data:
                        strike_data[strike] = {
                            'call_gex': 0, 'put_gex': 0,
                            'call_oi': 0, 'put_oi': 0,
                            'call_volume': 0, 'put_volume': 0
                        }
                    
                    strike_data[strike]['put_gex'] += gex
                    strike_data[strike]['put_oi'] += oi
                    strike_data[strike]['put_volume'] += volume
            
            df = pd.DataFrame.from_dict(strike_data, orient='index')
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'strike'}, inplace=True)
            df = df.sort_values('strike').reset_index(drop=True)
            
            df['net_gex'] = df['call_gex'] + df['put_gex']
            df['cumulative_gex'] = df['net_gex'].cumsum()
            
            gamma_flip = self.find_gamma_flip(df, current_price)
            
            call_walls = df[df['call_gex'] > 0].nlargest(5, 'call_gex')
            put_walls = df[df['put_gex'] < 0].nsmallest(5, 'put_gex')
            
            total_call_gex = float(df['call_gex'].sum())
            total_put_gex = float(df['put_gex'].sum())
            net_gex = total_call_gex + total_put_gex
            total_oi = int(df['call_oi'].sum() + df['put_oi'].sum())
            
            distance_to_flip = ((current_price - gamma_flip) / current_price) * 100
            
            mm_behavior = self.analyze_market_maker_behavior(df, current_price, chains)
            toxicity_score = self.calculate_flow_toxicity(chains, total_options_volume)
            dealer_pain = self.calculate_dealer_pain(net_gex, distance_to_flip, mm_behavior)
            mm_status = self.determine_mm_status(net_gex, dealer_pain, distance_to_flip)
            
            vix = self.calculate_vix()
            
            if net_gex < -1e9:
                regime = "EXTREME_VOLATILITY"
            elif net_gex < 0:
                regime = "NORMAL_VOLATILITY"
            else:
                regime = "LOW_VOLATILITY"
            
            return {
                'strike_data': df,
                'current_price': current_price,
                'gamma_flip': gamma_flip,
                'net_gex': net_gex,
                'total_call_gex': total_call_gex,
                'total_put_gex': total_put_gex,
                'call_walls': call_walls,
                'put_walls': put_walls,
                'total_volume': int(total_options_volume),
                'total_oi': total_oi,
                'distance_to_flip': distance_to_flip,
                'mm_behavior': mm_behavior,
                'toxicity_score': toxicity_score,
                'dealer_pain': dealer_pain,
                'mm_status': mm_status,
                'vix': vix,
                'regime': regime,
                'data_timestamp': options_data.get('data_timestamp', datetime.now())
            }
            
        except:
            return None
    
    def find_gamma_flip(self, df, current_price):
        """Find the gamma flip point"""
        try:
            for i in range(len(df) - 1):
                curr = df.iloc[i]['cumulative_gex']
                next_val = df.iloc[i + 1]['cumulative_gex']
                
                if (curr <= 0 <= next_val) or (curr >= 0 >= next_val):
                    curr_strike = df.iloc[i]['strike']
                    next_strike = df.iloc[i + 1]['strike']
                    
                    if next_val != curr:
                        ratio = abs(curr) / abs(next_val - curr)
                        flip = curr_strike + ratio * (next_strike - curr_strike)
                        return flip
            
            min_idx = df['cumulative_gex'].abs().idxmin()
            return df.loc[min_idx, 'strike']
            
        except:
            return current_price
    
    def analyze_market_maker_behavior(self, strike_df, current_price, chains):
        """Analyze market maker positioning and behavior"""
        try:
            atm_strikes = strike_df[
                (strike_df['strike'] >= current_price * 0.98) &
                (strike_df['strike'] <= current_price * 1.02)
            ]
            
            delta_neutral_score = 0
            if len(atm_strikes) > 0:
                straddle_activity = atm_strikes['call_volume'].sum() + atm_strikes['put_volume'].sum()
                total_volume = strike_df['call_volume'].sum() + strike_df['put_volume'].sum()
                delta_neutral_score = (straddle_activity / max(total_volume, 1)) * 100
            
            pin_risk = 0
            near_strikes = strike_df[
                (strike_df['strike'] >= current_price * 0.99) &
                (strike_df['strike'] <= current_price * 1.01)
            ]
            if len(near_strikes) > 0:
                near_gamma = near_strikes['call_gex'].sum() + abs(near_strikes['put_gex'].sum())
                total_gamma = abs(strike_df['call_gex'].sum()) + abs(strike_df['put_gex'].sum())
                pin_risk = (near_gamma / max(total_gamma, 1)) * 100
            
            spread_activity = 0
            for exp_date, chain_data in chains.items():
                calls = chain_data['calls']
                if len(calls) > 0 and len(calls) > 5:
                    high_oi_strikes = calls[calls['openInterest'] > calls['openInterest'].quantile(0.8)]
                    spread_activity += len(high_oi_strikes)
            
            vol_oi_ratio = 0
            total_volume = strike_df['call_volume'].sum() + strike_df['put_volume'].sum()
            total_oi = strike_df['call_oi'].sum() + strike_df['put_oi'].sum()
            if total_oi > 0:
                vol_oi_ratio = total_volume / total_oi
            
            return {
                'delta_neutral_score': min(100, delta_neutral_score),
                'pin_risk': min(100, pin_risk),
                'spread_activity': spread_activity,
                'vol_oi_ratio': vol_oi_ratio,
                'institutional_flow': vol_oi_ratio > 0.5
            }
            
        except:
            return {
                'delta_neutral_score': 0,
                'pin_risk': 0,
                'spread_activity': 0,
                'vol_oi_ratio': 0,
                'institutional_flow': False
            }
    
    def calculate_flow_toxicity(self, chains, total_volume):
        """Calculate flow toxicity score"""
        try:
            score = 0
            
            large_trades = 0
            weekly_preference = 0
            otm_activity = 0
            small_lots = 0
            
            for exp_date, chain_data in chains.items():
                calls = chain_data['calls']
                puts = chain_data['puts']
                dte = chain_data['dte']
                
                large_call_oi = len(calls[calls['openInterest'] > 1000])
                large_put_oi = len(puts[puts['openInterest'] > 1000])
                large_trades += large_call_oi + large_put_oi
                
                if dte <= 7:
                    weekly_vol = calls['volume'].fillna(0).sum() + puts['volume'].fillna(0).sum()
                    weekly_preference += weekly_vol
                
                if len(calls) > 0:
                    current_price = calls['strike'].median()
                    far_otm_calls = len(calls[calls['strike'] > current_price * 1.1])
                    far_otm_puts = len(puts[puts['strike'] < current_price * 0.9])
                    otm_activity += far_otm_calls + far_otm_puts
                
                small_call_vol = len(calls[calls['volume'].fillna(0) < 10])
                small_put_vol = len(puts[puts['volume'].fillna(0) < 10])
                small_lots += small_call_vol + small_put_vol
            
            if large_trades > 5:
                score += 20
            if total_volume > 0 and weekly_preference / max(total_volume, 1) > 0.7:
                score -= 20
            if otm_activity > 10:
                score -= 15
            if small_lots > 20:
                score -= 10
            
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 10 or 15 <= current_hour <= 16:
                score += 10
            
            return max(-100, min(100, score))
            
        except:
            return 0
    
    def calculate_dealer_pain(self, net_gex, distance_to_flip, mm_behavior):
        """Calculate dealer pain score"""
        pain = 0
        
        if net_gex < 0:
            pain += min(50, abs(net_gex / 1e9) * 10)
        
        if abs(distance_to_flip) < 1:
            pain += 30
        elif abs(distance_to_flip) < 2:
            pain += 20
        
        if mm_behavior.get('pin_risk', 0) > 70:
            pain += 20
        
        if mm_behavior.get('institutional_flow', False):
            pain += 10
        
        return min(100, pain)
    
    def determine_mm_status(self, net_gex, dealer_pain, distance_to_flip):
        """Determine market maker status"""
        if dealer_pain > 80:
            return "🔥 TRAPPED SHORT"
        elif dealer_pain > 60:
            return "😰 SCRAMBLING"
        elif net_gex > 3e9:
            return "🛡️ DEFENDING"
        elif abs(distance_to_flip) < 1:
            return "⚠️ VULNERABLE"
        else:
            return "😌 NEUTRAL"
    
    def generate_all_signals(self, gex_profile, symbol):
        """Generate all trading signals"""
        signals = []
        
        if not gex_profile:
            return [{
                'type': 'WAIT',
                'direction': 'NO DATA',
                'strategy_type': 'ALERT',
                'confidence': 0,
                'entry': 'Data unavailable',
                'target': 'N/A',
                'stop': 'N/A',
                'dte': 'N/A',
                'size': '0%',
                'reasoning': 'Unable to fetch options data',
                'regime': 'Unknown',
                'expected_move': 0,
                'time_horizon': 'N/A',
                'win_rate': 0,
                'position_size': 0
            }]
        
        squeeze_signals = self.generate_squeeze_signals(gex_profile, symbol)
        premium_signals = self.generate_premium_signals(gex_profile)
        condor_signals = self.generate_condor_signals(gex_profile)
        
        signals.extend(squeeze_signals)
        signals.extend(premium_signals)
        signals.extend(condor_signals)
        
        if not signals:
            dealer_pain = gex_profile.get('dealer_pain', 50)
            current_price = gex_profile.get('current_price', 100)
            
            if dealer_pain > 60:
                signals.append({
                    'type': 'VOLATILITY',
                    'direction': 'BUY STRADDLE',
                    'strategy_type': 'VOLATILITY PLAY',
                    'confidence': 60,
                    'entry': f'Buy ${current_price:.2f} straddle',
                    'target': '2% move either direction',
                    'stop': 'Next day close',
                    'dte': '1-3 DTE',
                    'size': '2%',
                    'reasoning': f'MMs under pressure (pain: {dealer_pain:.0f})',
                    'regime': 'Volatile',
                    'expected_move': 2.0,
                    'time_horizon': '1-2 days',
                    'win_rate': 55,
                    'position_size': self.trading_capital * 0.02
                })
            else:
                signals.append({
                    'type': 'WAIT',
                    'direction': 'SET ALERT',
                    'strategy_type': 'MONITORING',
                    'confidence': 40,
                    'entry': f'Alert at gamma flip',
                    'target': 'Wait for setup',
                    'stop': 'N/A',
                    'dte': 'N/A',
                    'size': '0%',
                    'reasoning': 'MMs neutral - wait for opportunity',
                    'regime': 'Neutral',
                    'expected_move': 0,
                    'time_horizon': 'N/A',
                    'win_rate': 0,
                    'position_size': 0
                })
        
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return signals
    
    def generate_squeeze_signals(self, gex_profile, symbol):
        """Generate squeeze play signals - Complete implementation"""
        signals = []
        config = self.strategies_config['squeeze_plays']
        
        net_gex = gex_profile['net_gex']
        distance_to_flip = gex_profile['distance_to_flip']
        current_price = gex_profile['current_price']
        gamma_flip = gex_profile['gamma_flip']
        dealer_pain = gex_profile.get('dealer_pain', 0)
        
        if net_gex < 0:
            strategy_direction = "LONG STRATEGIES"
            regime_desc = "Volatility Amplification Environment"
        else:
            strategy_direction = "PREMIUM COLLECTION"
            regime_desc = "Volatility Suppression Environment"
        
        neg_threshold = config['negative_gex_threshold_spy'] if symbol == 'SPY' else config['negative_gex_threshold_qqq']
        pos_threshold = config['positive_gex_threshold_spy'] if symbol == 'SPY' else config['positive_gex_threshold_qqq']
        
        if net_gex < neg_threshold or dealer_pain > 70:
            confidence = min(95, 65 + dealer_pain/4 + abs(distance_to_flip) * 2)
            confidence = round(confidence, 2)
            
            target_strike = gamma_flip if gamma_flip > current_price else current_price * 1.01
            
            signals.append({
                'type': 'SQUEEZE_PLAY',
                'direction': 'BUY CALLS',
                'strategy_type': strategy_direction,
                'confidence': confidence,
                'entry': f"Buy ${target_strike:.2f} calls NOW",
                'target': f"${current_price * 1.02:.2f}",
                'stop': f"${current_price * 0.98:.2f}",
                'dte': f"{config['dte_range'][0]}-{config['dte_range'][1]} DTE",
                'size': f"{self.strategies_config['risk_management']['max_position_size_squeeze']*100:.0f}%",
                'reasoning': f"MMs trapped with {net_gex/1e6:.0f}M negative gamma, dealer pain {dealer_pain:.0f}",
                'regime': regime_desc,
                'expected_move': abs(distance_to_flip) + 1.0,
                'time_horizon': "1-4 hours",
                'win_rate': 65,
                'position_size': self.trading_capital * self.strategies_config['risk_management']['max_position_size_squeeze']
            })
        
        if net_gex > pos_threshold and abs(distance_to_flip) < 0.5:
            confidence = min(75, 60 + (net_gex/pos_threshold) * 10 + (0.5 - abs(distance_to_flip)) * 20)
            confidence = round(confidence, 2)
            
            signals.append({
                'type': 'SQUEEZE_PLAY',
                'direction': 'BUY PUTS',
                'strategy_type': strategy_direction,
                'confidence': confidence,
                'entry': f"Buy puts at/below ${gamma_flip:.2f}",
                'target': f"${current_price * 0.97:.2f}",
                'stop': f"${current_price * 1.02:.2f}",
                'dte': "3-7 DTE",
                'size': f"{self.strategies_config['risk_management']['max_position_size_squeeze']*100:.0f}%",
                'reasoning': f"High positive GEX: {net_gex/1e6:.0f}M near flip point",
                'regime': regime_desc,
                'expected_move': 2.0,
                'time_horizon': "2-6 hours",
                'win_rate': 55,
                'position_size': self.trading_capital * self.strategies_config['risk_management']['max_position_size_squeeze']
            })
        
        return signals
    
    def generate_premium_signals(self, gex_profile):
        """Generate premium selling signals - Complete implementation"""
        signals = []
        config = self.strategies_config['premium_selling']
        
        net_gex = gex_profile['net_gex']
        current_price = gex_profile['current_price']
        call_walls = gex_profile['call_walls']
        put_walls = gex_profile['put_walls']
        
        strategy_direction = "PREMIUM COLLECTION"
        regime_desc = "Volatility Suppression Environment"
        
        if net_gex > config['positive_gex_threshold'] and len(call_walls) > 0:
            strongest_call = call_walls.iloc[0]
            wall_distance = ((strongest_call['strike'] - current_price) / current_price) * 100
            
            if config['wall_distance_range'][0] < wall_distance < config['wall_distance_range'][1]:
                wall_strength = strongest_call['call_gex']
                confidence = min(80, 60 + (wall_strength/config['wall_strength_threshold']) * 10)
                confidence = round(confidence, 2)
                
                signals.append({
                    'type': 'PREMIUM_SELLING',
                    'direction': 'SELL CALLS',
                    'strategy_type': strategy_direction,
                    'confidence': confidence,
                    'entry': f"Sell calls at ${strongest_call['strike']:.2f}",
                    'target': "50% profit or expiration",
                    'stop': f"Price crosses ${strongest_call['strike']:.2f}",
                    'dte': f"{config['dte_range_calls'][0]}-{config['dte_range_calls'][1]} DTE",
                    'size': f"{self.strategies_config['risk_management']['max_position_size_premium']*100:.0f}%",
                    'reasoning': f"Strong call wall ({wall_strength/1e6:.0f}M GEX) at {wall_distance:.1f}% above",
                    'regime': regime_desc,
                    'expected_move': wall_distance * 0.5,
                    'time_horizon': "1-2 days",
                    'win_rate': 70,
                    'position_size': self.trading_capital * self.strategies_config['risk_management']['max_position_size_premium']
                })
        
        if net_gex > 0 and len(put_walls) > 0:
            strongest_put = put_walls.iloc[0]
            wall_distance = ((current_price - strongest_put['strike']) / current_price) * 100
            
            if config['put_distance_range'][0] < wall_distance < config['put_distance_range'][1]:
                wall_strength = abs(strongest_put['put_gex'])
                confidence = min(75, 55 + (wall_strength/config['wall_strength_threshold']) * 10)
                confidence = round(confidence, 2)
                
                signals.append({
                    'type': 'PREMIUM_SELLING',
                    'direction': 'SELL PUTS',
                    'strategy_type': strategy_direction,
                    'confidence': confidence,
                    'entry': f"Sell puts at ${strongest_put['strike']:.2f}",
                    'target': "50% profit or expiration",
                    'stop': f"Price crosses ${strongest_put['strike']:.2f}",
                    'dte': f"{config['dte_range_puts'][0]}-{config['dte_range_puts'][1]} DTE",
                    'size': f"{self.strategies_config['risk_management']['max_position_size_premium']*100:.0f}%",
                    'reasoning': f"Strong put wall ({wall_strength/1e6:.0f}M GEX) at {wall_distance:.1f}% below",
                    'regime': regime_desc,
                    'expected_move': wall_distance * 0.3,
                    'time_horizon': "2-5 days",
                    'win_rate': 75,
                    'position_size': self.trading_capital * self.strategies_config['risk_management']['max_position_size_premium']
                })
        
        return signals
    
    def generate_condor_signals(self, gex_profile):
        """Generate iron condor signals - Complete implementation"""
        signals = []
        config = self.strategies_config['iron_condor']
        
        net_gex = gex_profile['net_gex']
        call_walls = gex_profile['call_walls']
        put_walls = gex_profile['put_walls']
        current_price = gex_profile['current_price']
        
        strategy_direction = "PREMIUM COLLECTION"
        regime_desc = "Range-bound Environment"
        
        if net_gex > config['min_gex_threshold'] and len(call_walls) > 0 and len(put_walls) > 0:
            call_strike = call_walls.iloc[0]['strike']
            put_strike = put_walls.iloc[0]['strike']
            
            range_width = ((call_strike - put_strike) / current_price) * 100
            
            if range_width > config['min_wall_spread']:
                call_gamma = gex_profile['total_call_gex']
                put_gamma = abs(gex_profile['total_put_gex'])
                
                if put_gamma > call_gamma:
                    wing_adjustment = "Wider put spread (bullish bias)"
                elif call_gamma > put_gamma:
                    wing_adjustment = "Wider call spread (bearish bias)"
                else:
                    wing_adjustment = "Balanced wings"
                
                confidence = min(85, 65 + (range_width - config['min_wall_spread']) * 2)
                confidence = round(confidence, 2)
                
                signals.append({
                    'type': 'IRON_CONDOR',
                    'direction': 'SELL CONDOR',
                    'strategy_type': strategy_direction,
                    'confidence': confidence,
                    'entry': f"Short {put_strike:.0f}P/{call_strike:.0f}C",
                    'wings': wing_adjustment,
                    'target': "25% profit or 50% of max profit",
                    'stop': "Short strike threatened",
                    'dte': f"{config['dte_range'][0]}-{config['dte_range'][1]} DTE",
                    'size': f"{self.strategies_config['risk_management']['max_position_size_condor']*100:.0f}%",
                    'reasoning': f"Clear {range_width:.1f}% range with {net_gex/1e6:.0f}M positive GEX",
                    'regime': regime_desc,
                    'expected_move': range_width * 0.2,
                    'time_horizon': "5-10 days",
                    'win_rate': 80,
                    'position_size': self.trading_capital * self.strategies_config['risk_management']['max_position_size_condor']
                })
        
        return signals
    
    def format_discord_alert(self, symbol, gex_profile, signal):
        """Format Discord alert"""
        if not gex_profile or not signal:
            return None
        
        confidence = signal.get('confidence', 0)
        if confidence > 80:
            rec_level = "⚡ HIGH RECOMMENDATION"
        elif confidence > 65:
            rec_level = "⚡ MODERATE RECOMMENDATION"
        else:
            rec_level = "📊 LOW CONFIDENCE"
        
        message = f"""
{rec_level} - {symbol}
{signal.get('direction', 'Action')}

📊 **Market Data**
Spot: ${gex_profile.get('current_price', 0):.2f}
Net GEX: {gex_profile.get('net_gex', 0)/1e9:.2f}B
Dealer Pain: {gex_profile.get('dealer_pain', 0):.0f}/100

💼 **Trade Details**
Entry: {signal.get('entry', 'N/A')}
Target: {signal.get('target', 'N/A')}
Confidence: {confidence}%

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return message[:2000]
    
    def send_discord_alert(self, message):
        """Send Discord alert"""
        try:
            webhook = "https://discord.com/api/webhooks/1408901307493777469/BWNr70coUxdgWCBSutC5pDWakBkRxM_lyQbUeh8_5A2zClecULeO909XBwQiwUY-DzId"
            payload = {'content': message}
            response = requests.post(webhook, json=payload, timeout=10)
            return response.status_code == 204
        except:
            return False
    
    def scan_multiple_symbols(self, symbols, progress_callback=None, min_confidence=50):
        """Scan multiple symbols"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        
        def process_symbol(symbol):
            try:
                options_data = self.get_options_chain(symbol)
                if options_data:
                    gex_profile = self.calculate_gex_profile(options_data)
                    if gex_profile:
                        signals = self.generate_all_signals(gex_profile, symbol)
                        filtered_signals = [s for s in signals if s.get('confidence', 0) >= min_confidence]
                        return {
                            'symbol': symbol,
                            'gex_profile': gex_profile,
                            'signals': filtered_signals if filtered_signals else signals,
                            'best_signal': filtered_signals[0] if filtered_signals else signals[0] if signals else None
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
                    'best_signal': None
                }
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(process_symbol, symbol): symbol for symbol in symbols}
            
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
        
        results.sort(key=lambda x: (
            x['gex_profile']['dealer_pain'] if x['gex_profile'] else 0,
            x['best_signal']['confidence'] if x['best_signal'] else 0
        ), reverse=True)
        
        return results
    
    def auto_scan_and_alert(self, symbols, min_confidence=65):
        """Auto scan and alert"""
        import time
        current_time = datetime.now()
        
        if current_time.hour < 9 or current_time.hour >= 16:
            return
        
        if self.last_auto_scan:
            time_diff = (current_time - self.last_auto_scan).total_seconds() / 3600
            if time_diff < self.auto_scan_interval:
                return
        
        results = self.scan_multiple_symbols(symbols, min_confidence=min_confidence)
        
        high_value_opportunities = []
        for r in results[:10]:
            if r['gex_profile'] and r['best_signal']:
                dealer_pain = r['gex_profile'].get('dealer_pain', 0)
                confidence = r['best_signal'].get('confidence', 0)
                
                if dealer_pain > 70 or confidence > min_confidence:
                    high_value_opportunities.append(r)
        
        for r in high_value_opportunities[:3]:
            alert_msg = self.format_discord_alert(
                r['symbol'],
                r['gex_profile'],
                r['best_signal']
            )
            if alert_msg:
                self.send_discord_alert(alert_msg)
                time.sleep(1)
        
        self.last_auto_scan = current_time
    
    def get_action_notes(self, gex_profile, signal):
        """Get action notes"""
        dealer_pain = gex_profile.get('dealer_pain', 0)
        net_gex = gex_profile.get('net_gex', 0)
        
        if dealer_pain > 80:
            return "explosive potential, dealers trapped and must capitulate"
        elif dealer_pain > 60:
            return "high volatility expected, dealers scrambling to hedge"
        elif net_gex < 0:
            return "negative gamma environment, moves will accelerate"
        elif net_gex > 3e9:
            return "extreme positive gamma, volatility suppressed"
        else:
            return "normal hedging activity, follow technical levels"
