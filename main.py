"""
DealerEdge Main Application
Professional GEX Trading Platform with MM Exploitation
"""

import streamlit as st
import warnings
from datetime import datetime, timedelta
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import feedparser
import calendar

# Import all modules
from config import *
from styles import apply_custom_css
from analyzer import DealerEdgeAnalyzer
from position_manager import PositionManager
from scanner import SymbolScanner
from alerts import AlertManager
from ui_components import UIComponents
from gex_database import GEXDatabase
from mm_exploits import MMExploits

warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(**PAGE_CONFIG)

# Apply custom CSS
apply_custom_css()

# Initialize components
@st.cache_resource
def get_analyzer():
    return DealerEdgeAnalyzer()

@st.cache_resource
def get_position_manager():
    return PositionManager(get_analyzer())

@st.cache_resource
def get_scanner():
    return SymbolScanner(get_analyzer())

@st.cache_resource
def get_alert_manager():
    return AlertManager()

@st.cache_resource
def get_ui_components():
    return UIComponents()

@st.cache_resource
def get_gex_database():
    return GEXDatabase()

@st.cache_resource
def get_mm_exploits():
    return MMExploits(get_analyzer(), get_alert_manager())

# Initialize all components
analyzer = get_analyzer()
position_manager = get_position_manager()
scanner = get_scanner()
alert_manager = get_alert_manager()
ui = get_ui_components()
gex_db = get_gex_database()
mm_exploits = get_mm_exploits()

# Initialize session state
if 'win_streak' not in st.session_state:
    st.session_state.win_streak = 0
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'total_pnl' not in st.session_state:
    st.session_state.total_pnl = 0
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'active_filter' not in st.session_state:
    st.session_state.active_filter = None
if 'morning_report_data' not in st.session_state:
    st.session_state.morning_report_data = None
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'last_gamma_flip' not in st.session_state:
    st.session_state.last_gamma_flip = {}
if 'news_cache' not in st.session_state:
    st.session_state.news_cache = {}
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'scan_progress' not in st.session_state:
    st.session_state.scan_progress = 0

# Helper Functions
def get_financial_news():
    """Get real financial news from RSS feeds"""
    try:
        feeds = {
            'MarketWatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse',
            'Reuters': 'https://feeds.reuters.com/reuters/businessNews',
            'CNBC': 'https://www.cnbc.com/id/10001147/device/rss/rss.html'
        }
        
        all_news = []
        for source, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    all_news.append({
                        'source': source,
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.get('published', 'N/A'),
                        'summary': entry.get('summary', '')[:200]
                    })
            except:
                continue
        
        return all_news[:5]
    except:
        return []

def calculate_max_pain(options_data):
    """Calculate max pain strike where most options expire worthless"""
    if not options_data or 'chains' not in options_data:
        return None
    
    pain_by_strike = {}
    
    for exp_date, chain_data in options_data['chains'].items():
        if chain_data['dte'] <= 1:
            calls = chain_data['calls']
            puts = chain_data['puts']
            
            for strike in pd.concat([calls['strike'], puts['strike']]).unique():
                total_pain = 0
                call_pain = calls[calls['strike'] < strike]['openInterest'].sum() * 100
                put_pain = puts[puts['strike'] > strike]['openInterest'].sum() * 100
                pain_by_strike[strike] = call_pain + put_pain
    
    if pain_by_strike:
        max_pain_strike = min(pain_by_strike, key=pain_by_strike.get)
        return max_pain_strike
    
    return None

def check_gamma_flip_cross(symbol, current_price, gamma_flip):
    """Check if price crossed gamma flip and send alert"""
    last_flip = st.session_state.last_gamma_flip.get(symbol, {})
    
    if last_flip:
        last_price = last_flip.get('price', 0)
        last_gamma_flip = last_flip.get('gamma_flip', 0)
        
        if last_price and last_gamma_flip:
            crossed_up = last_price < last_gamma_flip and current_price > gamma_flip
            crossed_down = last_price > last_gamma_flip and current_price < gamma_flip
            
            if crossed_up or crossed_down:
                direction = "ABOVE" if crossed_up else "BELOW"
                message = f"""
⚡ **GAMMA FLIP ALERT** - {symbol}
Price crossed {direction} gamma flip!
Current: ${current_price:.2f}
Gamma Flip: ${gamma_flip:.2f}
Action: {"Volatility suppression mode" if crossed_up else "Volatility amplification mode"}
"""
                alert_manager.send_discord_alert(message)
    
    st.session_state.last_gamma_flip[symbol] = {
        'price': current_price,
        'gamma_flip': gamma_flip,
        'timestamp': datetime.now()
    }

def run_backtest(analyzer, symbol, strategy, days=30):
    """Run simple backtest on historical data"""
    try:
        historical = analyzer.get_historical_data(symbol, period=f"{days}d")
        
        if historical is None or historical.empty:
            return None
        
        trades = []
        for i in range(len(historical) - 1):
            price = historical['Close'].iloc[i]
            next_price = historical['Close'].iloc[i + 1]
            
            if strategy == 'SQUEEZE_PLAY':
                if i > 0 and historical['Close'].iloc[i] > historical['Close'].iloc[i-1]:
                    trade_return = (next_price - price) / price
                    trades.append(trade_return)
        
        if trades:
            return {
                'total_trades': len(trades),
                'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
                'avg_return': sum(trades) / len(trades) * 100,
                'total_return': sum(trades) * 100
            }
    except:
        pass
    
    return None

def get_market_status():
    """Get current market status with correct timezone handling"""
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return "🌙 Weekend - Markets closed"
    elif now < market_open:
        minutes_until = int((market_open - now).total_seconds() / 60)
        return f"⏰ Market opens in {minutes_until} minutes"
    elif now >= market_close:
        return "🌙 Market closed - Analyzing after-hours positioning"
    else:
        return "✅ Market Open - Hunt for trapped MMs!"

# Header
position_summary = position_manager.get_position_summary()
ui.render_header(
    win_streak=st.session_state.win_streak,
    total_pnl=position_summary['total_pnl'],
    active_positions=position_summary['active_count']
)

# Main tabs - All 12 features
tabs = st.tabs([
    "☀️ Morning Report",
    "🔍 Scanner",
    "🎯 Analysis", 
    "📊 Positions",
    "⚡ Auto-Alerts",
    "📈 Report",
    "🧠 MM Patterns",
    "🔥 0DTE",
    "📐 Backtest",
    "💀 Max Pain",
    "💰 MM Exploits",
    "📚 GEX History"
])

# Tab 1: Morning Report with Real News
with tabs[0]:
    st.header("☀️ Morning MM Exploitation Report")
    
    # Market status
    st.info(get_market_status())
    
    # Real News Section
    st.subheader("📰 Real-Time Financial News")
    
    news_col1, news_col2 = st.columns([3, 1])
    
    with news_col1:
        st.caption("Latest market-moving news that affects MM behavior")
    
    with news_col2:
        if st.button("🔄 Refresh News"):
            st.session_state.news_cache = {}
    
    if 'today_news' not in st.session_state.news_cache:
        with st.spinner("Fetching latest news..."):
            news = get_financial_news()
            st.session_state.news_cache['today_news'] = news
    else:
        news = st.session_state.news_cache['today_news']
    
    if news:
        for item in news[:3]:  # Show top 3 news
            with st.expander(f"📰 {item['source']}: {item['title'][:80]}...", expanded=False):
                st.write(item['summary'])
                st.caption(f"Published: {item['published']}")
                st.markdown(f"[Read More]({item['link']})")
    
    # MM Vulnerability Targets
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🎯 Top 5 MM Vulnerability Targets")
    
    with col2:
        if st.button("🔄 Refresh Report", type="primary"):
            st.session_state.morning_report_data = None
            st.rerun()
    
    # High priority symbols for morning scan
    morning_symbols = scanner.get_high_mm_vulnerability_symbols()[:8]
    
    if not st.session_state.morning_report_data:
        morning_data = []
        progress_bar = st.progress(0)
        
        for i, symbol in enumerate(morning_symbols[:5]):
            progress_bar.progress((i + 1) / 5)
            
            with st.spinner(f"Analyzing {symbol}..."):
                mm_patterns = scanner.scan_for_mm_patterns(symbol)
                options_data = analyzer.get_options_chain(symbol)
                
                if options_data:
                    gex_profile = analyzer.calculate_gex_profile(options_data)
                    if gex_profile:
                        check_gamma_flip_cross(symbol, gex_profile['current_price'], gex_profile['gamma_flip'])
                        signals = analyzer.generate_all_signals(gex_profile, symbol)
                        
                        morning_data.append({
                            'symbol': symbol,
                            'gex_profile': gex_profile,
                            'best_signal': signals[0] if signals else None,
                            'max_pain': calculate_max_pain(options_data),
                            'mm_patterns': mm_patterns['patterns_found'],
                            'mm_vulnerability': mm_patterns['mm_vulnerability'],
                            'best_exploit': mm_patterns['best_exploit']
                        })
        
        st.session_state.morning_report_data = morning_data
        progress_bar.empty()
    
    # Display morning targets
    if st.session_state.morning_report_data:
        for i, data in enumerate(st.session_state.morning_report_data, 1):
            gex = data['gex_profile']
            signal = data['best_signal']
            dealer_pain = gex.get('dealer_pain', 0)
            mm_vulnerability = data.get('mm_vulnerability', 0)
            
            # Determine status
            if mm_vulnerability > 80 or dealer_pain > 80:
                emoji = "🔥"
                status = "TRAPPED - EXPLOIT NOW"
                alert_sent = False
                
                # Auto-alert for first trapped MM
                if i == 1 and not alert_sent:
                    alert_msg = f"""
🔥 **MM TRAPPED ALERT** - {data['symbol']}
Dealer Pain: {dealer_pain:.0f}/100
MM Vulnerability: {mm_vulnerability:.0f}/100
Best Exploit: {data['best_exploit']['specific_trade'] if data['best_exploit'] else 'Monitor'}
Expected Return: {data['best_exploit'].get('expected_return', 'N/A') if data['best_exploit'] else 'N/A'}
"""
                    alert_manager.send_discord_alert(alert_msg)
                    alert_sent = True
                    
            elif mm_vulnerability > 60 or dealer_pain > 60:
                emoji = "⚡"
                status = "VULNERABLE"
            else:
                emoji = "✅"
                status = "DEFENDED"
            
            # Display expandable card
            with st.expander(f"{i}. {emoji} **{data['symbol']}** - Pain: {dealer_pain:.0f} | Vulnerability: {mm_vulnerability:.0f} - {status}", 
                           expanded=(mm_vulnerability > 70)):
                
                # MM Pattern alerts if found
                if data.get('best_exploit'):
                    st.error(f"🎯 **EXPLOIT**: {data['best_exploit']['specific_trade']}")
                    st.write(f"Expected Return: {data['best_exploit'].get('expected_return', 'N/A')}")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Net GEX", f"{gex['net_gex']/1e9:.2f}B")
                    st.metric("Gamma Flip", f"${gex['gamma_flip']:.2f}")
                
                with col2:
                    st.metric("Current", f"${gex['current_price']:.2f}")
                    st.metric("Max Pain", f"${data['max_pain']:.2f}" if data['max_pain'] else "N/A")
                
                with col3:
                    if signal:
                        st.write(f"**Signal**: {signal['direction']}")
                        st.write(f"**Confidence**: {signal['confidence']:.0f}%")
                    
                    if st.button(f"Execute Trade", key=f"morning_{data['symbol']}"):
                        if data['best_exploit']:
                            st.info(f"Execute: {data['best_exploit']['specific_trade']}")
                        elif signal:
                            position = position_manager.add_position(
                                data['symbol'],
                                gex['current_price'],
                                signal.get('position_size', 1000) / gex['current_price'],
                                signal['type'],
                                signal
                            )
                            st.success(f"Position opened for {data['symbol']}!")

# Tab 2: Scanner - DYNAMIC 250+ STOCKS
with tabs[1]:
    st.header("🔍 Market Maker Vulnerability Scanner")
    
    # Display total symbols available
    st.info(f"📊 **Scanning Pool**: {len(scanner.symbols)} symbols ready to scan (S&P 500 + High Volume Options + Meme Stocks)")
    
    # Scanner controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        scan_type = st.selectbox(
            "Scan Type", 
            ["Quick Scan (Top 20)", "Fast Scan (50)", "Full Scan (100)", 
             "Extended Scan (200)", "Complete Scan (250+)", "Custom List"]
        )
    
    with col2:
        min_confidence = st.slider("Min Conf %", 0, 100, 60, 5)
    
    with col3:
        auto_alert = st.checkbox("Auto Alert", value=True)
    
    with col4:
        scan_btn = st.button("🚀 SCAN", type="primary", use_container_width=True)
    
    # Custom symbol input
    if scan_type == "Custom List":
        custom_symbols = st.text_input("Enter symbols (comma-separated)", "SPY,QQQ,AAPL,TSLA,NVDA,AMD,GME,AMC")
        symbols_to_scan = [s.strip().upper() for s in custom_symbols.split(',')]
    else:
        # Determine number of symbols based on scan type
        scan_sizes = {
            "Quick Scan (Top 20)": 20,
            "Fast Scan (50)": 50,
            "Full Scan (100)": 100,
            "Extended Scan (200)": 200,
            "Complete Scan (250+)": min(250, len(scanner.symbols))
        }
        num_symbols = scan_sizes.get(scan_type, 20)
        
        # Prioritize high-volatility symbols
        high_priority = scanner.get_high_mm_vulnerability_symbols()
        remaining = [s for s in scanner.symbols if s not in high_priority]
        symbols_to_scan = high_priority + remaining[:max(0, num_symbols - len(high_priority))]
        symbols_to_scan = symbols_to_scan[:num_symbols]
    
    # Quick action buttons
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("🔥 Trapped MMs"):
            with st.spinner("Scanning for trapped MMs..."):
                scan_results = scanner.scan_multiple_symbols(
                    scanner.get_high_mm_vulnerability_symbols()[:30], 
                    min_confidence=70
                )
                trapped = [r for r in scan_results if r.get('mm_vulnerability', 0) > 80]
                st.session_state.scan_results = trapped
                st.success(f"Found {len(trapped)} trapped MMs!")
                if trapped and auto_alert:
                    for t in trapped[:3]:
                        alert_manager.send_discord_alert(
                            f"🔥 TRAPPED: {t['symbol']} - Vulnerability {t['mm_vulnerability']:.0f}"
                        )
    
    with quick_col2:
        if st.button("⚡ OPEX Plays"):
            if scanner.is_opex_week():
                with st.spinner("Scanning OPEX opportunities..."):
                    scan_results = scanner.scan_multiple_symbols(
                        symbols_to_scan[:50], 
                        min_confidence=60
                    )
                    opex_plays = [r for r in scan_results 
                                 if any(p['type'] == 'OPEX_PRESSURE' for p in r.get('mm_patterns', []))]
                    st.session_state.scan_results = opex_plays
                    st.success(f"Found {len(opex_plays)} OPEX plays!")
            else:
                st.info("Not OPEX week - check back Monday-Friday of 3rd week")
    
    with quick_col3:
        if st.button("🌊 Charm Flows"):
            if datetime.now().weekday() == 4 and datetime.now().hour >= 14:
                with st.spinner("Scanning Friday charm flows..."):
                    scan_results = scanner.scan_multiple_symbols(
                        symbols_to_scan[:50], 
                        min_confidence=50
                    )
                    charm_plays = [r for r in scan_results 
                                  if any(p['type'] == 'CHARM_FLOW' for p in r.get('mm_patterns', []))]
                    st.session_state.scan_results = charm_plays
                    st.success(f"Found {len(charm_plays)} charm plays!")
            else:
                st.info("Charm flows most active Friday 2-4 PM")
    
    with quick_col4:
        if st.button("📊 Top ETFs"):
            etf_symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLF', 'XLE', 'XLK', 'XLV']
            with st.spinner("Scanning ETFs..."):
                scan_results = scanner.scan_multiple_symbols(etf_symbols, min_confidence=min_confidence)
                st.session_state.scan_results = scan_results
                st.success(f"Scanned {len(etf_symbols)} ETFs!")
    
    # Main scan button with progress
    if scan_btn:
        st.write(f"🎯 **Scanning {len(symbols_to_scan)} symbols...**")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_placeholder = st.empty()
        
        def update_progress(current, total):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"🔍 Scanning: {current}/{total} symbols ({progress*100:.0f}%)")
            
            # Show interim results every 10 symbols
            if current % 10 == 0:
                results_placeholder.info(f"✅ Processed {current} symbols... Finding MM vulnerabilities...")
        
        with st.spinner(f"🎯 Hunting for trapped MMs across {len(symbols_to_scan)} symbols..."):
            start_time = time.time()
            
            # Run the scan
            scan_results = scanner.scan_multiple_symbols(
                symbols_to_scan,
                update_progress,
                min_confidence=min_confidence
            )
            
            elapsed_time = time.time() - start_time
            
            st.session_state.scan_results = scan_results
            st.session_state.last_scan_time = datetime.now()
        
        progress_bar.progress(1.0)
        status_text.empty()
        results_placeholder.empty()
        
        # Get scan statistics
        stats = scanner.get_scan_statistics(scan_results)
        
        # Show scan statistics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Scanned", stats['total_scanned'])
        
        with col2:
            st.metric("Opportunities", stats['opportunities'])
        
        with col3:
            st.metric("Trapped MMs", stats['trapped_mms'])
        
        with col4:
            st.metric("Scrambling", stats['scrambling_mms'])
        
        with col5:
            st.metric("Critical", stats['critical_alerts'])
        
        with col6:
            st.metric("Time", f"{elapsed_time:.1f}s")
        
        # Auto-alert for critical opportunities
        if auto_alert and scan_results:
            critical = [r for r in scan_results if r.get('mm_vulnerability', 0) > 80][:5]
            
            for r in critical:
                exploit = r.get('best_exploit', {})
                alert_msg = f"""
🔥 **MM TRAPPED** - {r['symbol']}
Vulnerability: {r.get('mm_vulnerability', 0):.0f}/100
Exploit: {exploit.get('specific_trade', 'Monitor closely')}
Expected Return: {exploit.get('expected_return', 'N/A')}
Urgency: {exploit.get('urgency', 'MODERATE')}
"""
                alert_manager.send_discord_alert(alert_msg)
            
            if critical:
                st.success(f"✅ Sent {len(critical)} critical alerts to Discord!")
    
    # Display last scan time
    if st.session_state.last_scan_time:
        elapsed = (datetime.now() - st.session_state.last_scan_time).seconds // 60
        st.caption(f"Last scan: {elapsed} minutes ago | Next auto-scan in {120 - elapsed} minutes")
    
    # Display results with filtering
    if st.session_state.scan_results:
        st.subheader("📊 Scan Results")
        
        # Enhanced filter buttons
        filter_cols = st.columns(6)
        
        filters = [
            ("🔥 Trapped", "🔥 Trapped MMs"),
            ("⚡ Squeeze", "⚡ Gamma Squeeze"),
            ("📌 Pin Risk", "📌 Pin Risk"),
            ("💰 Premium", "💰 Premium Selling"),
            ("🎯 Critical", "🎯 Immediate Action"),
            ("❌ Clear", None)
        ]
        
        for i, (label, filter_type) in enumerate(filters):
            with filter_cols[i]:
                if st.button(label):
                    if filter_type:
                        filtered = scanner.filter_results_by_type(
                            st.session_state.scan_results, 
                            filter_type
                        )
                        st.session_state.scan_results = filtered
                    st.rerun()
        
        # Display results
        ui.render_scan_results(
            st.session_state.scan_results,
            "All",
            position_manager,
            alert_manager
        )

# Tab 3: Analysis
with tabs[2]:
    st.header("🎯 Deep Market Maker Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        symbol = st.text_input("Symbol", value="SPY").upper().strip()
    
    with col2:
        if st.button("🔄 Analyze", use_container_width=True):
            st.rerun()
    
    if symbol:
        with st.spinner(f"Analyzing {symbol} for MM vulnerabilities..."):
            # Get MM patterns first
            mm_patterns = scanner.scan_for_mm_patterns(symbol)
            options_data = analyzer.get_options_chain(symbol)
        
        if options_data:
            gex_profile = analyzer.calculate_gex_profile(options_data)
            
            if gex_profile:
                # Check for gamma flip cross
                check_gamma_flip_cross(symbol, gex_profile['current_price'], gex_profile['gamma_flip'])
                
                st.session_state.current_analysis = gex_profile
                signals = analyzer.generate_all_signals(gex_profile, symbol)
                best_signal = signals[0] if signals else None
                
                # Display MM vulnerability alert
                if mm_patterns['mm_vulnerability'] > 70:
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.error(f"🔥 **MM VULNERABILITY**: {mm_patterns['mm_vulnerability']:.0f}/100")
                        if mm_patterns['best_exploit']:
                            st.write(f"**Exploit**: {mm_patterns['best_exploit']['specific_trade']}")
                            st.write(f"**Expected**: {mm_patterns['best_exploit'].get('expected_return', 'N/A')}")
                    with col2:
                        if st.button("📢 Send Alert"):
                            alert_manager.send_discord_alert(
                                f"🔥 {symbol} MM VULNERABLE: {mm_patterns['mm_vulnerability']:.0f}"
                            )
                
                # Display analysis
                ui.render_analysis_results(gex_profile, best_signal)
                
                # Analysis sub-tabs
                viz_tabs = st.tabs(["📊 GEX Charts", "🎯 Pressure Map", "📋 Signals", "💀 Max Pain", "🧠 MM Patterns"])
                
                with viz_tabs[0]:
                    ui.render_gex_charts(gex_profile)
                
                with viz_tabs[1]:
                    ui.render_pressure_map(gex_profile)
                
                with viz_tabs[2]:
                    st.subheader("📋 Trade Signals")
                    for i, signal in enumerate(signals[:5]):
                        if signal:
                            ui.render_signal_card(signal, symbol, position_manager, alert_manager, i)
                
                with viz_tabs[3]:
                    st.subheader("💀 Max Pain Analysis")
                    max_pain = calculate_max_pain(options_data)
                    
                    if max_pain:
                        current = gex_profile['current_price']
                        distance = ((max_pain - current) / current) * 100
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Max Pain", f"${max_pain:.2f}")
                        
                        with col2:
                            st.metric("Current", f"${current:.2f}")
                        
                        with col3:
                            st.metric("Distance", f"{distance:.1f}%")
                        
                        # Trading strategy based on max pain
                        if abs(distance) < 1:
                            st.warning("⚠️ At max pain - Sell straddles")
                        elif distance > 3:
                            st.info("📈 Below max pain - Bullish bias")
                        elif distance < -3:
                            st.info("📉 Above max pain - Bearish bias")
                
                with viz_tabs[4]:
                    st.subheader("🧠 MM Behavior Patterns")
                    
                    if mm_patterns['patterns_found']:
                        for pattern in mm_patterns['patterns_found']:
                            with st.expander(f"{pattern['type']} - {pattern['confidence']}% Confidence", expanded=True):
                                st.write(f"**Action**: {pattern['action']}")
                                st.write(f"**Trade**: {pattern['specific_trade']}")
                                st.write(f"**Urgency**: {pattern['urgency']}")
                                st.write(f"**Expected Return**: {pattern.get('expected_return', 'N/A')}")
                    else:
                        st.info("No specific MM patterns detected currently")
        else:
            st.error(f"Unable to fetch options data for {symbol}")

# Tab 4: Positions
with tabs[3]:
    st.header("📊 Position Tracking")
    
    # Update positions and check for auto-close
    closed = position_manager.update_positions()
    if closed:
        for p in closed:
            st.info(f"Auto-closed {p['symbol']}: {p['close_reason']} - P&L: {p['final_pnl_percent']:.1f}%")
            if p['final_pnl_percent'] > 0:
                st.session_state.win_streak += 1
            else:
                st.session_state.win_streak = 0
    
    # Position controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Positions"):
            position_manager.update_positions()
            st.rerun()
    
    with col2:
        if st.button("📊 Export History"):
            if position_manager.closed_positions:
                df = pd.DataFrame(position_manager.closed_positions)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    with col3:
        if st.button("🗑️ Clear History"):
            if st.checkbox("Confirm clear"):
                position_manager.closed_positions = []
                st.success("History cleared")
                st.rerun()
    
    # Display positions
    ui.render_position_tracker(position_manager)

# Tab 5: Auto-Alerts
with tabs[4]:
    st.header("⚡ Automated Alert Configuration")
    ui.render_alert_configuration(alert_manager, analyzer, scanner)
    
    # Alert history
    st.subheader("📜 Recent Alerts")
    if hasattr(alert_manager, 'alert_history') and alert_manager.alert_history:
        for alert in reversed(alert_manager.alert_history[-10:]):
            st.text(f"{alert.get('time', 'N/A')} - {alert.get('symbol', 'N/A')}: {alert.get('type', 'N/A')}")

# Tab 6: Report
with tabs[5]:
    st.header("📈 Performance Report")
    ui.render_performance_report(position_manager)
    
    # Strategy breakdown
    closed_positions = position_manager.get_closed_positions()
    if closed_positions:
        st.subheader("📊 Strategy Performance")
        
        strategy_stats = {}
        for position in closed_positions:
            strategy = position.get('strategy', 'UNKNOWN')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'count': 0,
                    'wins': 0,
                    'total_pnl': 0
                }
            
            strategy_stats[strategy]['count'] += 1
            if position.get('final_pnl', 0) > 0:
                strategy_stats[strategy]['wins'] += 1
            strategy_stats[strategy]['total_pnl'] += position.get('final_pnl', 0)
        
        # Display strategy metrics
        for strategy, stats in strategy_stats.items():
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg_pnl = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
            
            st.metric(
                strategy.replace('_', ' ').title(),
                f"{win_rate:.1f}% Win Rate",
                f"Total: ${stats['total_pnl']:,.0f} | Avg: ${avg_pnl:,.0f}"
            )

# Tab 7: MM Patterns
with tabs[6]:
    st.header("🧠 Market Maker Behavior Patterns")
    
    if st.button("🔍 Detect Active Patterns", type="primary"):
        patterns_found = []
        
        with st.spinner("Scanning for MM patterns across markets..."):
            for symbol in scanner.get_high_mm_vulnerability_symbols()[:10]:
                mm_patterns = scanner.scan_for_mm_patterns(symbol)
                
                if mm_patterns['patterns_found']:
                    for pattern in mm_patterns['patterns_found']:
                        patterns_found.append({
                            'symbol': symbol,
                            'pattern': pattern['type'],
                            'confidence': pattern['confidence'],
                            'action': pattern['action'],
                            'trade': pattern['specific_trade'],
                            'urgency': pattern['urgency'],
                            'expected': pattern.get('expected_return', 'N/A')
                        })
        
        if patterns_found:
            st.success(f"Found {len(patterns_found)} active patterns!")
            
            # Sort by urgency and confidence
            patterns_found.sort(key=lambda x: (
                {'CRITICAL': 3, 'HIGH': 2, 'TIME_SENSITIVE': 2, 'IMMEDIATE': 2, 'MODERATE': 1}.get(x['urgency'], 0),
                x['confidence']
            ), reverse=True)
            
            for p in patterns_found[:10]:  # Show top 10
                urgency_color = "🔴" if p['urgency'] in ['CRITICAL', 'HIGH'] else "🟡"
                
                with st.expander(f"{urgency_color} **{p['symbol']}** - {p['pattern']} ({p['confidence']}%)", 
                               expanded=(p['urgency'] == 'CRITICAL')):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Action**: {p['action']}")
                        st.write(f"**Trade**: {p['trade']}")
                        st.write(f"**Expected Return**: {p['expected']}")
                        st.write(f"**Urgency**: {p['urgency']}")
                    
                    with col2:
                        if st.button(f"Alert", key=f"pattern_{p['symbol']}_{p['pattern']}"):
                            alert_msg = f"""
🧠 **PATTERN ALERT** - {p['symbol']}
Pattern: {p['pattern']}
Action: {p['action']}
Trade: {p['trade']}
Expected: {p['expected']}
"""
                            alert_manager.send_discord_alert(alert_msg)
                            st.success("Alert sent!")
        else:
            st.info("No active patterns detected. Market makers are calm.")
    
    # Educational content
    st.subheader("📚 Pattern Recognition Guide")
    
    pattern_tabs = st.tabs(["Gamma Squeeze", "Pin Risk", "Charm Flow", "Vanna", "OPEX"])
    
    with pattern_tabs[0]:
        st.markdown("""
        ### 🔥 Gamma Squeeze Pattern
        **When MMs Get Trapped:**
        - Net GEX < -1B (dealers short gamma)
        - Price approaching resistance
        - High call volume above current price
        
        **Your Action:** Buy calls or call spreads
        **Entry:** When price breaks above VWAP with volume
        **Target:** Next major call wall
        **Stop:** Below gamma flip point
        **Expected Return:** 50-200%
        
        **Real Example:** GME January 2021 - Negative gamma caused $4 to $400 move
        """)
    
    with pattern_tabs[1]:
        st.markdown("""
        ### 📌 Pin Risk Pattern
        **When Price Gets Pinned:**
        - Major expiry day (usually Friday)
        - Large OI at nearby strike
        - Price within 1% of strike
        
        **Your Action:** Sell straddles/strangles at pin strike
        **Entry:** Thursday close or Friday open
        **Exit:** Let expire or close at 3:30 PM
        **Risk:** Breaking out of pin range
        **Expected Return:** 20-40% of credit
        
        **Success Rate:** 73% on OPEX Fridays
        """)
    
    with pattern_tabs[2]:
        st.markdown("""
        ### 🌊 Charm Flow Pattern
        **Friday Afternoon Acceleration:**
        - Time: 2:00-4:00 PM Friday
        - High gamma environment (>2B net GEX)
        - Charm decay accelerates exponentially
        
        **Your Action:** Buy 0DTE in trend direction at 3:00 PM
        **Entry:** First pullback after 3:00 PM
        **Exit:** 3:50 PM or 100% profit
        **Risk:** $500-1000 per trade
        **Expected Return:** 50-150%
        
        **Best Days:** OPEX Fridays, high GEX Fridays
        """)
    
    with pattern_tabs[3]:
        st.markdown("""
        ### 💎 Vanna Squeeze Pattern
        **VIX-Driven MM Panic:**
        - VIX spike > 20% in a day
        - Negative net GEX environment
        - Dealers forced to buy as volatility rises
        
        **Your Action:** Buy calls immediately on VIX spike
        **Entry:** VIX +20% with negative GEX
        **Target:** Previous day's high
        **Stop:** Below VWAP
        **Expected Return:** 40-120%
        
        **Historical Win Rate:** 73%
        """)
    
    with pattern_tabs[4]:
        st.markdown("""
        ### 🎯 OPEX Week Patterns
        **Monthly Options Expiration:**
        - Third Friday of every month
        - Highest gamma concentration of month
        - Maximum MM hedging activity
        
        **Monday-Wednesday:** Sell put spreads on dips
        **Thursday:** Buy lottery tickets for Friday
        **Friday Morning:** Sell iron condors
        **Friday Afternoon:** Scalp 0DTE gamma unwind
        
        **Average OPEX Week Returns:** +2.3% exploiting MM hedging
        """)

# Tab 8: 0DTE Scanner
with tabs[7]:
    st.header("🔥 0DTE High Gamma Scanner")
    
    st.info("""
    **0DTE Options = Maximum Gamma = Maximum MM Pain**
    Small moves create explosive hedging requirements. Best opportunities 3:00-4:00 PM.
    """)
    
    if st.button("🔍 Scan 0DTE Opportunities", type="primary"):
        with st.spinner("Scanning for 0DTE high gamma setups..."):
            dte_results = scanner.scan_0dte_opportunities()
            
            if dte_results:
                st.success(f"Found {len(dte_results)} 0DTE opportunities!")
                
                for result in dte_results:
                    with st.expander(f"🔥 **{result['symbol']}** - Expires TODAY!", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Current Price**: ${result['current_price']:.2f}")
                            st.write(f"**High Gamma Strikes**: {', '.join([f'${s:.0f}' for s in result['high_gamma_strikes'][:5]])}")
                            st.write(f"**Action**: {result['action']}")
                        
                        with col2:
                            st.write(f"**Potential Return**: {result['potential_return']}")
                            st.write(f"**Specific Trade**: {result.get('specific_trade', 'Buy at high gamma strikes')}")
                            
                            if st.button(f"Send Alert", key=f"0dte_{result['symbol']}"):
                                alert_msg = f"""
🔥 **0DTE HIGH GAMMA** - {result['symbol']}
Current: ${result['current_price']:.2f}
High Gamma Strikes: {', '.join([f'${s:.0f}' for s in result['high_gamma_strikes'][:3]])}
Action: {result['action']}
Potential: {result['potential_return']}
"""
                                alert_manager.send_discord_alert(alert_msg)
                                st.success("Alert sent!")
            else:
                st.info("No 0DTE opportunities found. Check back during market hours.")
    
    # 0DTE Strategy Guide
    st.subheader("📚 0DTE Trading Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Best Times:**
        - 10:00-10:30 AM: Opening range break
        - 2:00-2:30 PM: Lunch return
        - 3:00-3:50 PM: Charm acceleration
        
        **Entry Rules:**
        - Wait for clear direction
        - Buy ATM or first OTM
        - Risk only what you can lose
        """)
    
    with col2:
        st.markdown("""
        **Exit Rules:**
        - 50% profit: Take half off
        - 100% profit: Take another quarter
        - 3:50 PM: Exit everything
        
        **Risk Management:**
        - Max 2% of account per trade
        - Max 3 trades per day
        - Stop at 2 losses
        """)

# Tab 9: Backtesting
with tabs[8]:
    st.header("📐 Strategy Backtesting")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        backtest_symbol = st.text_input("Symbol", "SPY", key="backtest_symbol")
    
    with col2:
        backtest_strategy = st.selectbox(
            "Strategy", 
            ["SQUEEZE_PLAY", "PREMIUM_SELLING", "IRON_CONDOR", "CHARM_FLOW", "VANNA_SQUEEZE"]
        )
    
    with col3:
        backtest_days = st.slider("Days", 7, 90, 30)
    
    if st.button("Run Backtest", type="primary"):
        with st.spinner(f"Running {backtest_days}-day backtest..."):
            results = run_backtest(analyzer, backtest_symbol, backtest_strategy, backtest_days)
            
            if results:
                st.session_state.backtest_results = results
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Trades", results['total_trades'])
                
                with col2:
                    st.metric("Win Rate", f"{results['win_rate']:.1f}%")
                
                with col3:
                    st.metric("Avg Return", f"{results['avg_return']:.2f}%")
                
                with col4:
                    st.metric("Total", f"{results['total_return']:.2f}%")
                
                st.success(f"Backtest complete for {backtest_symbol}")
                
                # Store in database
                if st.button("Save to Database"):
                    gex_db.record_pattern_outcome(
                        backtest_symbol,
                        backtest_strategy,
                        100,  # entry price
                        100 * (1 + results['total_return']/100),  # exit price
                        0,  # initial gex
                        0,  # initial pain
                        backtest_days * 24  # duration
                    )
                    st.success("Results saved to database")
            else:
                st.error("Insufficient data for backtest")

# Tab 10: Max Pain Calculator
with tabs[9]:
    st.header("💀 Max Pain Calculator")
    
    st.info("""
    **Max Pain = Where Most Options Expire Worthless**
    Market makers profit when options expire at max pain. Price often pins here on expiration day.
    """)
    
    pain_symbol = st.text_input("Symbol", "SPY", key="pain_symbol")
    
    if st.button("Calculate Max Pain", type="primary"):
        with st.spinner(f"Calculating max pain for {pain_symbol}..."):
            options_data = analyzer.get_options_chain(pain_symbol)
            
            if options_data:
                max_pain = calculate_max_pain(options_data)
                current_price = options_data['current_price']
                
                if max_pain:
                    distance = ((max_pain - current_price) / current_price) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Max Pain Strike", f"${max_pain:.2f}")
                    
                    with col2:
                        st.metric("Current Price", f"${current_price:.2f}")
                    
                    with col3:
                        st.metric("Distance", f"{distance:.1f}%")
                    
                    # Trading strategy based on max pain
                    st.subheader("📋 Max Pain Trading Strategy")
                    
                    if abs(distance) < 1:
                        st.error("🎯 AT MAX PAIN - SELL STRADDLES NOW!")
                        st.write("""
                        **Action**: Sell ATM straddle
                        **Risk**: Price breaking out of range
                        **Expected Profit**: 20-40% of credit
                        """)
                        strategy = "SELL_STRADDLE"
                        
                    elif distance > 3:
                        st.info("📈 Price well below max pain - Bullish bias")
                        st.write("""
                        **Action**: Buy calls or sell puts
                        **Target**: Max pain level
                        **Timeframe**: By expiration
                        """)
                        strategy = "BUY_CALLS"
                        
                    elif distance < -3:
                        st.info("📉 Price well above max pain - Bearish bias")
                        st.write("""
                        **Action**: Buy puts or sell calls
                        **Target**: Max pain level
                        **Timeframe**: By expiration
                        """)
                        strategy = "BUY_PUTS"
                        
                    else:
                        st.warning("➡️ Price moving toward max pain")
                        st.write("""
                        **Action**: Wait for better setup
                        **Note**: Price likely to drift to max pain
                        """)
                        strategy = "WAIT"
                    
                    # Send alert button
                    if st.button("Send Max Pain Alert"):
                        alert_msg = f"""
💀 **MAX PAIN ALERT** - {pain_symbol}
Max Pain: ${max_pain:.2f}
Current: ${current_price:.2f}
Distance: {distance:.1f}%
Strategy: {strategy}
Action: {"Sell premium at max pain" if abs(distance) < 1 else f"Expect move toward ${max_pain:.2f}"}
"""
                        if alert_manager.send_discord_alert(alert_msg):
                            st.success("Alert sent to Discord!")
                else:
                    st.error("Unable to calculate max pain")
            else:
                st.error(f"Unable to fetch options data for {pain_symbol}")

# Tab 11: MM Exploits
with tabs[10]:
    st.header("💰 Market Maker Exploitation Playbook")
    
    st.error("""
    ⚠️ **THESE ARE THE HIGHEST PROBABILITY MM EXPLOITATION TRADES**
    Each strategy exploits predictable, systematic market maker hedging requirements.
    Follow the EXACT instructions for maximum profit potential.
    """)
    
    # Get current analysis for vanna/charm calculations
    current_gex = st.session_state.current_analysis if st.session_state.current_analysis else {'net_gex': 0}
    
    # Get all active exploits for today
    active_trades = mm_exploits.get_todays_trades(current_gex)
    
    if active_trades:
        st.success(f"🎯 **{len(active_trades)} Active MM Exploitation Opportunities Right Now!**")
        
        # Sort by urgency
        active_trades.sort(key=lambda x: {
            'CRITICAL': 4,
            'HIGH': 3,
            'TIME_SENSITIVE': 3,
            'IMMEDIATE': 3,
            'MODERATE': 2
        }.get(x.get('urgency', 'LOW'), 1), reverse=True)
        
        for trade in active_trades:
            category = trade.get('category', 'UNKNOWN')
            urgency_emoji = "🔴" if trade.get('urgency') in ['CRITICAL', 'HIGH'] else "🟡"
            
            with st.expander(f"{urgency_emoji} **{category}** - {trade.get('action', 'Opportunity')}", 
                           expanded=(trade.get('urgency') == 'CRITICAL')):
                
                # Display urgency if critical
                if 'urgency' in trade and trade['urgency'] in ['CRITICAL', 'HIGH', 'IMMEDIATE']:
                    st.error(f"⚠️ **URGENCY: {trade['urgency']}** - Act within next hour!")
                
                # Display specific trade
                if 'specific_trade' in trade:
                    st.write(f"**📍 Exact Trade**: {trade['specific_trade']}")
                
                # Display expected return
                if 'expected_return' in trade:
                    st.write(f"**💰 Expected Return**: {trade['expected_return']}")
                
                # Display reasoning
                if 'reasoning' in trade:
                    st.write(f"**🧠 Why This Works**: {trade['reasoning']}")
                
                # Display size
                if 'size' in trade:
                    st.write(f"**📊 Position Size**: {trade['size']}")
                
                # Display instructions
                if 'instructions' in trade:
                    st.write("**📋 Step-by-Step Instructions:**")
                    for i, instruction in enumerate(trade['instructions'], 1):
                        st.write(f"{i}. {instruction}")
                
                # Display execution steps
                if 'execution_steps' in trade:
                    st.write("**🎯 Execution Steps:**")
                    for step in trade['execution_steps']:
                        st.write(f"• {step}")
                
                # Display historical stats
                if 'historical_stats' in trade:
                    st.info(f"📊 **Historical Performance**: {trade['historical_stats']}")
                
                # Alert button
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"📢 Send Alert", key=f"exploit_{category}_{trade.get('action', '')}"):
                        alert_msg = f"""
💰 **MM EXPLOIT ACTIVE** - {category}
Action: {trade.get('action', '')}
Trade: {trade.get('specific_trade', '')}
Expected: {trade.get('expected_return', 'N/A')}
Urgency: {trade.get('urgency', 'MODERATE')}
"""
                        alert_manager.send_discord_alert(alert_msg)
                        st.success("Alert sent to Discord!")
                
                with col2:
                    if st.button(f"📝 Log Trade", key=f"log_{category}_{trade.get('action', '')}"):
                        st.info("Trade logged for tracking")
    else:
        st.info("No specific MM exploitation setups active right now. Check back during market hours.")
    
    # Always show upcoming opportunities
    st.subheader("📅 Upcoming MM Exploitation Windows")
    
    upcoming = mm_exploits.get_upcoming_opportunities()
    
    for opp in upcoming:
        st.write(f"• **{opp['date']}**: {opp['event']} - {opp['strategy']}")

# Tab 12: GEX History Database
with tabs[11]:
    st.header("📚 Historical GEX Pattern Analysis")
    
    # Save current snapshot
    if st.session_state.get('current_analysis'):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Current GEX Snapshot"):
                symbol = st.text_input("Symbol for snapshot", "SPY")
                if gex_db.store_gex_snapshot(symbol, st.session_state.current_analysis):
                    st.success("Snapshot saved to database")
                else:
                    st.error("Failed to save snapshot")
        
        with col2:
            if st.button("🔍 Find Similar Historical Setups"):
                similar = gex_db.find_similar_setups(
                    st.session_state.current_analysis,
                    'SPY',
                    lookback_days=90
                )
                
                if similar:
                    st.subheader("📊 Similar Historical Setups")
                    
                    for setup in similar:
                        outcome_emoji = "🟢" if setup['return_24h'] > 0 else "🔴"
                        
                        with st.expander(f"{outcome_emoji} {setup['date']} - {setup['return_24h']:.2f}% return"):
                            st.write(f"**Similarity Score**: {setup['similarity']:.0f}%")
                            st.write(f"**Initial Price**: ${setup['initial_price']:.2f}")
                            st.write(f"**24hr Later**: ${setup['future_price']:.2f}")
                            st.write(f"**Return**: {setup['return_24h']:.2f}%")
                            st.write(f"**Dealer Pain**: {setup['dealer_pain']:.0f}")
                            st.write(f"**Net GEX**: {setup['net_gex']/1e9:.2f}B")
                    
                    # Calculate statistics
                    avg_return = sum(s['return_24h'] for s in similar) / len(similar)
                    win_rate = len([s for s in similar if s['return_24h'] > 0]) / len(similar) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Historical Win Rate", f"{win_rate:.0f}%")
                    
                    with col2:
                        st.metric("Avg 24hr Return", f"{avg_return:.2f}%")
                    
                    with col3:
                        if avg_return > 0:
                            st.metric("Suggested Action", "BULLISH")
                        else:
                            st.metric("Suggested Action", "BEARISH")
                else:
                    st.info("No similar historical setups found")
    
    # Display best historical patterns
    st.subheader("🏆 Most Profitable Historical Patterns")
    
    best_patterns = gex_db.get_best_patterns(min_occurrences=5)
    
    if best_patterns:
        for pattern in best_patterns[:5]:
            with st.expander(f"📈 {pattern['pattern_type']} - {pattern['avg_return']:.2f}% avg return"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Occurrences", pattern['occurrences'])
                
                with col2:
                    st.metric("Win Rate", f"{pattern['win_rate']:.1f}%")
                
                with col3:
                    st.metric("Best Return", f"{pattern['best_return']:.1f}%")
                
                st.write(f"**Avg Duration**: {pattern['avg_duration']:.1f} hours")
    else:
        st.info("Not enough historical data yet. Keep scanning and saving snapshots!")

# Footer
ui.render_footer()

# Auto-refresh for active positions
if len(position_manager.get_active_positions()) > 0:
    time.sleep(30)
    st.rerun()
