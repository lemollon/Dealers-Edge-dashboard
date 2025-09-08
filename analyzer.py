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
from config import STRATEGIES_CONFIG, RISK_FREE_RATE, TRADING_CAPITAL

warnings.filterwarnings('ignore')

class DealerEdgeAnalyzer:
    """Complete GEX analyzer with all trading strategies"""
    
    def __init__(self):
        self.risk_free_rate = RISK_FREE_RATE
        self.trading_capital = TRADING_CAPITAL
        self.strategies_config = STRATEGIES_CONFIG
        self.last_auto_scan = None
        self.auto_scan_interval = 2  # hours
        
    def black_scholes_gamma(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate Black-Scholes gamma for options"""
        try:
            if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
                return 0
            
            d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            return gamma if not np.isnan(gamma) else 0
        except:
            return 0
    
    def get_current_price(self, symbol: str) -> Optional[float]:
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
    
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """Get historical data for backtesting"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval="1h")
            return hist if len(hist) > 0 else None
        except:
            return None
    
    def calculate_vix(self) -> float:
        """Get current VIX level"""
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="1d")
            if len(hist) > 0:
                return float(hist['Close'].iloc[-1])
            return 15.0
        except:
            return 15.0
    
    def get_options_chain(self, symbol: str, focus_weekly: bool = True) -> Optional[Dict]:
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
                    
                    calls = chain.calls.
