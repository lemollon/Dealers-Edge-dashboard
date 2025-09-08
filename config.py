"""
DealerEdge Configuration File
Contains all constants, settings, and symbol lists
"""

# ============================================================================
# DISCORD WEBHOOK CONFIGURATION
# ============================================================================

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1408901307493777469/BWNr70coUxdgWCBSutC5pDWakBkRxM_lyQbUeh8_5A2zClecULeO909XBwQiwUY-DzId"

# ============================================================================
# TRADING PARAMETERS
# ============================================================================

TRADING_CAPITAL = 100000
RISK_FREE_RATE = 0.05

# ============================================================================
# STRATEGY CONFIGURATIONS
# ============================================================================

STRATEGIES_CONFIG = {
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

# ============================================================================
# SYMBOL LISTS - GUARANTEED 200+ SYMBOLS
# ============================================================================

CORE_ETFS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLC',
    'XLY', 'XLP', 'XLB', 'XLRE', 'XLU', 'VXX', 'GLD', 'SLV', 'TLT', 'XRT'
]

HIGH_LIQUIDITY_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B', 'UNH', 'JNJ',
    'JPM', 'V', 'PG', 'HD', 'CVX', 'MA', 'BAC', 'ABBV', 'PFE', 'KO',
    'AVGO', 'PEP', 'TMO', 'COST', 'MRK', 'WMT', 'CSCO', 'ACN', 'DHR', 'NEE',
    'VZ', 'ABT', 'ADBE', 'ORCL', 'CRM', 'LLY', 'XOM', 'NKE', 'QCOM', 'TXN',
    'MDT', 'UPS', 'PM', 'T', 'LOW', 'HON', 'UNP', 'IBM', 'C', 'GS',
    'CAT', 'SPGI', 'INTC', 'INTU', 'ISRG', 'RTX', 'AXP', 'BKNG', 'NOW', 'DE',
    'PLD', 'TJX', 'GE', 'AMD', 'MU', 'SYK', 'BLK', 'MDLZ', 'ADI', 'GILD',
    'LRCX', 'KLAC', 'PYPL', 'REGN', 'ATVI', 'FISV', 'CI', 'SO', 'ZTS', 'DUK',
    'BSX', 'CSX', 'CL', 'MMC', 'ITW', 'BMY', 'AON', 'EQIX', 'APD', 'SNPS',
    'SHW', 'CME', 'FCX', 'PGR', 'MSI', 'ICE', 'USB', 'NSC', 'COP', 'EMR',
    'HUM', 'TFC', 'WM', 'F', 'ADP', 'GM', 'GD', 'CDNS', 'MCD', 'EOG',
    'FDX', 'BDX', 'TGT', 'BIIB', 'CVS', 'NOC', 'D', 'ECL', 'EL', 'WFC'
]

HIGH_OPTIONS_VOLUME_STOCKS = [
    'COIN', 'PLTR', 'SOFI', 'NIO', 'RIVN', 'LCID', 'GME', 'AMC', 'BB', 'MARA',
    'RIOT', 'SQ', 'NFLX', 'DIS', 'BA', 'AAL', 'DAL', 'CCL', 'RCL', 'MGM',
    'WYNN', 'PENN', 'DKNG', 'CHPT', 'PLUG', 'FCEL', 'HOOD', 'RBLX', 'SNAP', 'PINS',
    'UBER', 'LYFT', 'ABNB', 'DASH', 'SNOW', 'NET', 'DDOG', 'CRWD', 'ZM', 'ROKU'
]

SP500_ADDITIONAL = [
    'PSA', 'SLB', 'KMB', 'DG', 'ADSK', 'MRNA', 'CCI', 'ILMN', 'GIS', 'MCHP',
    'EXC', 'A', 'SBUX', 'JCI', 'CMG', 'KHC', 'ANET', 'MNST', 'CTAS', 'PAYX',
    'PNC', 'ROST', 'ORLY', 'ROP', 'HCA', 'MAR', 'AFL', 'CTSH', 'FAST', 'ODFL',
    'AEP', 'SPG', 'CARR', 'AIG', 'FTNT', 'EA', 'VRSK', 'ALL', 'BK', 'AZO',
    'MCK', 'OTIS', 'DLR', 'PCAR', 'IQV', 'NXPI', 'WLTW', 'PSX', 'O', 'PRU',
    'TEL', 'CTVA', 'XEL', 'WELL', 'DLTR', 'AVB', 'STZ', 'CBRE', 'EBAY', 'PPG',
    'IDXX', 'VRTX', 'AMT', 'AMGN', 'TROW', 'GPN', 'RSG', 'MSCI', 'EW', 'MTB',
    'DD', 'AMAT', 'INFO', 'ALB', 'DOW', 'LHX', 'KEYS', 'GLW', 'ANSS', 'CDW'
]

BACKUP_SYMBOLS = [
    'SCHW', 'CB', 'MET', 'TRV', 'PRU', 'AFL', 'ALL', 'HIG', 'PFG', 'L',
    'RE', 'CINF', 'WRB', 'AIZ', 'ERIE', 'KMPR', 'RNR', 'AJG', 'BRO', 'MMC'
]

# Build complete symbol list (200+)
def get_all_symbols():
    """Get complete list of 200+ symbols"""
    all_symbols = []
    all_symbols.extend(CORE_ETFS)
    all_symbols.extend(HIGH_LIQUIDITY_STOCKS)
    all_symbols.extend(HIGH_OPTIONS_VOLUME_STOCKS)
    all_symbols.extend(SP500_ADDITIONAL)
    
    # Remove duplicates
    seen = set()
    unique_symbols = []
    for symbol in all_symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique_symbols.append(symbol)
    
    # Ensure we have at least 200
    while len(unique_symbols) < 200:
        for symbol in BACKUP_SYMBOLS:
            if symbol not in unique_symbols:
                unique_symbols.append(symbol)
            if len(unique_symbols) >= 200:
                break
    
    return unique_symbols[:250]  # Return up to 250

SP500_SYMBOLS = get_all_symbols()

# ============================================================================
# AUTO-SCAN CONFIGURATION
# ============================================================================

AUTO_SCAN_INTERVAL = 2  # hours
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 16
MIN_CONFIDENCE_DEFAULT = 65

# ============================================================================
# UI CONFIGURATION
# ============================================================================

PAGE_CONFIG = {
    "page_title": "🎯 DealerEdge - GEX Trading Platform",
    "page_icon": "🎯",
    "layout": "wide",
    "initial_sidebar_state": "collapsed"
}

FILTER_OPTIONS = [
    "ALL 200+", 
    "🔥 High Pain (>70)", 
    "⚡ Squeeze Plays", 
    "💰 Premium Selling",
    "🦅 Iron Condors",
    "📈 High Confidence (>75%)",
    "🎯 Immediate Action"
]

SIGNAL_EMOJIS = {
    'SQUEEZE_PLAY': '⚡',
    'PREMIUM_SELLING': '💰',
    'IRON_CONDOR': '🦅',
    'VOLATILITY': '🌊',
    'WAIT': '⏳'
}

DEALER_PAIN_THRESHOLDS = {
    'trapped': 80,
    'scrambling': 60,
    'vulnerable': 40,
    'neutral': 0
}
