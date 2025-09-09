"""
DealerEdge Main Application
Professional GEX Trading Platform
"""

import streamlit as st
import warnings
from datetime import datetime, timedelta
import time
import pandas as pd
import plotly.express as px
import requests
import json

# Import all modules
from config import *
from styles import apply_custom_css
from analyzer import DealerEdgeAnalyzer
from position_manager import PositionManager
from scanner import SymbolScanner
from alerts import AlertManager
from ui_components import UIComponents

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

analyzer = get_analyzer()
position_manager = get_position_manager()
scanner = get_scanner()
alert_manager = get_alert_manager()
ui = get_ui_components()

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

# Helper Functions for New Features

def get_financial_news():
    """Get real financial news from free sources"""
    try:
        # Using RSS feeds as they're free and don't require API keys
        import feedparser
        
        feeds = {
            'MarketWatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse',
            'Reuters': 'https://feeds.reuters.com/reuters/businessNews',
            'CNBC': 'https://www.cnbc.com/id/10001147/device/rss/rss.html'
        }
        
        all_news = []
        for source, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:  # Get top 3 from each source
                    all_news.append({
                        'source': source,
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.get('published', 'N/A'),
                        'summary': entry.get('summary', '')[:200]
                    })
            except:
                continue
        
        return all_news[:5]  # Return top 5 news items
    except:
        return []

def scan_0dte_options(analyzer, symbols=['SPY', 'QQQ', 'IWM']):
    """Scan for 0DTE (same-day expiry) opportunities"""
    results = []
    
    for symbol in symbols:
        try:
            options_data = analyzer.get_options_chain(symbol)
            if options_data and 'chains' in options_data:
                for exp_date, chain_data in options_data['chains'].items():
                    if chain_data['dte'] == 0:  # 0DTE options
                        calls = chain_data['calls']
                        puts = chain_data['puts']
                        
                        # Find high gamma strikes
                        high_gamma_calls = calls[calls['gamma'] > calls['gamma'].quantile(0.9)]
                        high_gamma_puts = puts[puts['gamma'] > puts['gamma'].quantile(0.9)]
                        
                        if not high_gamma_calls.empty or not high_gamma_puts.empty:
                            results.append({
                                'symbol': symbol,
                                'expiry': exp_date,
                                'high_gamma_strikes': {
                                    'calls': high_gamma_calls['strike'].tolist() if not high_gamma_calls.empty else [],
                                    'puts': high_gamma_puts['strike'].tolist() if not high_gamma_puts.empty else []
                                },
                                'current_price': options_data['current_price']
                            })
        except:
            continue
    
    return results

def calculate_max_pain(options_data):
    """Calculate max pain strike where most options expire worthless"""
    if not options_data or 'chains' not in options_data:
        return None
    
    pain_by_strike = {}
    
    for exp_date, chain_data in options_data['chains'].items():
        if chain_data['dte'] <= 1:  # Focus on near-term expiries
            calls = chain_data['calls']
            puts = chain_data['puts']
            
            for strike in pd.concat([calls['strike'], puts['strike']]).unique():
                total_pain = 0
                
                # Calculate pain for calls
                call_pain = calls[calls['strike'] < strike]['openInterest'].sum() * (strike - calls[calls['strike'] < strike]['strike']).sum()
                
                # Calculate pain for puts  
                put_pain = puts[puts['strike'] > strike]['openInterest'].sum() * (puts[puts['strike'] > strike]['strike'] - strike).sum()
                
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
        
        # Check if price crossed gamma flip
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
    
    # Update last values
    st.session_state.last_gamma_flip[symbol] = {
        'price': current_price,
        'gamma_flip': gamma_flip,
        'timestamp': datetime.now()
    }

def run_backtest(analyzer, symbol, strategy, days=30):
    """Run backtest on historical data"""
    historical = analyzer.get_historical_data(symbol, period=f"{days}d")
    
    if historical is None or historical.empty:
        return None
    
    trades = []
    for i in range(len(historical) - 1):
        # Simulate getting GEX at each point
        # This is simplified - real backtest would need historical options data
        price = historical['Close'].iloc[i]
        next_price = historical['Close'].iloc[i + 1]
        
        # Simple momentum strategy for demonstration
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
    
    return None

# Header
position_summary = position_manager.get_position_summary()
ui.render_header(
    win_streak=st.session_state.win_streak,
    total_pnl=position_summary['total_pnl'],
    active_positions=position_summary['active_count']
)

# Main tabs
tabs = st.tabs([
    "☀️ Morning Report",
    "🔍 Scanner",
    "🎯 Analysis", 
    "📊 Positions",
    "⚡ Auto-Alerts",
    "📈 Report",
    "🧠 MM Patterns",
    "🔥 0DTE",  # New
    "📐 Backtest",  # New
    "💀 Max Pain"  # New
])

# Tab 1: Morning Report (Enhanced with real news)
with tabs[0]:
    st.header("☀️ Morning MM Exploitation Report")
    
    # Time and market status
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30)
    market_close = now.replace(hour=16, minute=0)
    
    if now < market_open:
        st.info(f"⏰ Market opens in {(market_open - now).seconds // 60} minutes")
    elif now > market_close:
        st.info("🌙 Market closed - Analyzing after-hours positioning")
    else:
        st.success("✅ Market Open - Hunt for trapped MMs!")
    
    # Real News Section
    st.subheader("📰 Real-Time Financial News")
    
    news_col1, news_col2 = st.columns([3, 1])
    
    with news_col1:
        st.caption("Latest market-moving news that affects MM behavior")
    
    with news_col2:
        if st.button("🔄 Refresh News"):
            st.session_state.news_cache = {}
    
    # Get and display real news
    if 'today_news' not in st.session_state.news_cache:
        with st.spinner("Fetching latest news..."):
            news = get_financial_news()
            st.session_state.news_cache['today_news'] = news
    else:
        news = st.session_state.news_cache['today_news']
    
    if news:
        for item in news:
            with st.expander(f"📰 {item['source']}: {item['title'][:80]}..."):
                st.write(item['summary'])
                st.caption(f"Published: {item['published']}")
                st.markdown(f"[Read More]({item['link']})")
    
    # Quick morning scan
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🎯 Top 5 MM Vulnerability Targets")
    
    with col2:
        if st.button("🔄 Refresh Report", type="primary"):
            st.session_state.morning_report_data = None
            st.rerun()
    
    # [Rest of morning report code remains the same...]
    # Scan top symbols for MM vulnerabilities
    morning_symbols = ['SPY', 'QQQ', 'IWM', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'META']
    
    if not st.session_state.morning_report_data:
        morning_data = []
        progress_bar = st.progress(0)
        
        for i, symbol in enumerate(morning_symbols[:5]):
            progress_bar.progress((i + 1) / 5)
            
            with st.spinner(f"Analyzing {symbol}..."):
                options_data = analyzer.get_options_chain(symbol)
                if options_data:
                    gex_profile = analyzer.calculate_gex_profile(options_data)
                    if gex_profile:
                        # Check for gamma flip cross
                        check_gamma_flip_cross(symbol, gex_profile['current_price'], gex_profile['gamma_flip'])
                        
                        signals = analyzer.generate_all_signals(gex_profile, symbol)
                        morning_data.append({
                            'symbol': symbol,
                            'gex_profile': gex_profile,
                            'best_signal': signals[0] if signals else None,
                            'max_pain': calculate_max_pain(options_data)
                        })
        
        st.session_state.morning_report_data = morning_data
        progress_bar.empty()
    
    # Display morning targets
    if st.session_state.morning_report_data:
        for i, data in enumerate(st.session_state.morning_report_data, 1):
            gex = data['gex_profile']
            signal = data['best_signal']
            dealer_pain = gex.get('dealer_pain', 0)
            
            if dealer_pain > 70:
                emoji = "🔥"
                status = "TRAPPED - EXPLOIT NOW"
                
                # Auto-alert for trapped MMs
                if i == 1:  # Alert for top opportunity
                    alert_msg = f"""
🔥 **MM TRAPPED ALERT** - {data['symbol']}
Dealer Pain: {dealer_pain:.0f}/100
Action: {signal['direction'] if signal else 'Monitor'}
Confidence: {signal['confidence'] if signal else 0:.0f}%
"""
                    alert_manager.send_discord_alert(alert_msg)
            elif dealer_pain > 50:
                emoji = "⚡"
                status = "VULNERABLE"
            else:
                emoji = "✅"
                status = "DEFENDED"
            
            with st.expander(f"{i}. {emoji} **{data['symbol']}** - Pain: {dealer_pain:.0f}/100 - {status}", expanded=(dealer_pain > 70)):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Net GEX", f"{gex['net_gex']/1e9:.2f}B")
                    st.metric("Gamma Flip", f"${gex['gamma_flip']:.2f}")
                
                with col2:
                    st.metric("Current", f"${gex['current_price']:.2f}")
                    st.metric("Max Pain", f"${data['max_pain']:.2f}" if data['max_pain'] else "N/A")
                
                with col3:
                    if signal:
                        st.write(f"**Action**: {signal['direction']}")
                        st.write(f"**Confidence**: {signal['confidence']:.0f}%")
                        
                        if st.button(f"Execute Trade", key=f"morning_{data['symbol']}"):
                            position = position_manager.add_position(
                                data['symbol'],
                                gex['current_price'],
                                signal.get('position_size', 1000) / gex['current_price'],
                                signal['type'],
                                signal
                            )
                            st.success(f"Position opened for {data['symbol']}!")

# Tab 2: Scanner (remains the same)
with tabs[1]:
    st.header("🔍 Market Maker Vulnerability Scanner")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        filter_type = st.selectbox("Filter View", FILTER_OPTIONS)
    
    with col2:
        min_confidence = st.slider("Min Conf %", 0, 100, MIN_CONFIDENCE_DEFAULT, 5)
    
    with col3:
        auto_alert = st.checkbox("Alert on Find", value=True)
    
    with col4:
        scan_btn = st.button("🚀 SCAN ALL", type="primary", use_container_width=True)
    
    if scan_btn:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"🔍 Scanning: {current}/{total} symbols...")
        
        with st.spinner("🎯 Hunting for trapped market makers..."):
            scan_results = scanner.scan_multiple_symbols(
                scanner.symbols, 
                update_progress, 
                min_confidence=min_confidence
            )
            st.session_state.scan_results = scan_results
            st.session_state.last_scan_time = datetime.now()
        
        progress_bar.progress(1.0)
        status_text.success(f"✅ Scanned {len(scanner.symbols)} symbols!")
        
        if auto_alert and scan_results:
            high_value = [r for r in scan_results 
                         if r.get('opportunity_score', 0) > 70][:3]
            
            alerts_sent = alert_manager.send_batch_alerts(high_value)
            if alerts_sent > 0:
                st.success(f"✅ Sent {alerts_sent} alerts")
    
    if st.session_state.scan_results:
        ui.render_scan_results(
            st.session_state.scan_results,
            filter_type,
            position_manager,
            alert_manager
        )

# Tab 3: Analysis (with gamma flip monitoring)
with tabs[2]:
    st.header("🎯 Deep Market Maker Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        symbol = st.text_input("Symbol", value="SPY").upper().strip()
    
    with col2:
        if st.button("🔄 Analyze", use_container_width=True):
            st.rerun()
    
    if symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            options_data = analyzer.get_options_chain(symbol)
        
        if options_data:
            gex_profile = analyzer.calculate_gex_profile(options_data)
            
            if gex_profile:
                # Monitor gamma flip crossing
                check_gamma_flip_cross(symbol, gex_profile['current_price'], gex_profile['gamma_flip'])
                
                st.session_state.current_analysis = gex_profile
                signals = analyzer.generate_all_signals(gex_profile, symbol)
                best_signal = signals[0] if signals else None
                
                # Display main analysis
                ui.render_analysis_results(gex_profile, best_signal)
                
                # Create sub-tabs for different visualizations
                viz_tabs = st.tabs(["📊 GEX Charts", "🎯 Pressure Map", "📋 Trade Signals", "💀 Max Pain"])
                
                with viz_tabs[0]:
                    ui.render_gex_charts(gex_profile)
                
                with viz_tabs[1]:
                    ui.render_pressure_map(gex_profile)
                
                with viz_tabs[2]:
                    st.subheader("📋 All Trade Signals")
                    for i, signal in enumerate(signals[:5]):
                        if signal:
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                confidence = signal.get('confidence', 0)
                                emoji = SIGNAL_EMOJIS.get(signal.get('type', 'WAIT'), '📊')
                                
                                st.markdown(f"""
                                **{emoji} {signal.get('type', '')}** - {signal.get('direction', '')}  
                                Confidence: {confidence:.0f}% | {signal.get('reasoning', '')[:100]}...  
                                Entry: {signal.get('entry', 'N/A')} | Target: {signal.get('target', 'N/A')}
                                """)
                            
                            with col2:
                                if st.button("Trade", key=f"trade_{signal.get('type', '')}_{i}"):
                                    position = position_manager.add_position(
                                        symbol,
                                        gex_profile.get('current_price', 100),
                                        signal.get('position_size', 1000) / gex_profile.get('current_price', 100),
                                        signal.get('type', 'MANUAL'),
                                        signal
                                    )
                                    st.success("Position opened!")
                                    st.rerun()
                            
                            with col3:
                                if st.button("Alert", key=f"alert_{signal.get('type', '')}_{i}"):
                                    alert_msg = alert_manager.format_discord_alert(symbol, gex_profile, signal)
                                    if alert_manager.send_discord_alert(alert_msg):
                                        st.success("Alert sent!")
                
                with viz_tabs[3]:
                    st.subheader("💀 Max Pain Analysis")
                    max_pain = calculate_max_pain(options_data)
                    
                    if max_pain:
                        current = gex_profile['current_price']
                        distance = ((max_pain - current) / current) * 100
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Max Pain Strike", f"${max_pain:.2f}")
                        
                        with col2:
                            st.metric("Current Price", f"${current:.2f}")
                        
                        with col3:
                            st.metric("Distance", f"{distance:.1f}%")
                        
                        if abs(distance) < 1:
                            st.warning("⚠️ Price near max pain - expect pinning!")
                        elif distance > 0:
                            st.info(f"Price {distance:.1f}% below max pain - upward pressure")
                        else:
                            st.info(f"Price {abs(distance):.1f}% above max pain - downward pressure")

# Tab 4: Positions (remains the same)
with tabs[3]:
    st.header("📊 Position Tracking")
    
    closed = position_manager.update_positions()
    if closed:
        for p in closed:
            st.info(f"Auto-closed {p['symbol']}: {p['close_reason']} - P&L: {p['final_pnl_percent']:.1f}%")
            if p['final_pnl_percent'] > 0:
                st.session_state.win_streak += 1
            else:
                st.session_state.win_streak = 0
    
    ui.render_position_tracker(position_manager)

# Tab 5: Auto-Alerts (remains the same)
with tabs[4]:
    st.header("⚡ Automated Alert Configuration")
    ui.render_alert_configuration(alert_manager, analyzer, scanner)

# Tab 6: Report (remains the same)
with tabs[5]:
    st.header("📈 Performance Report")
    ui.render_performance_report(position_manager)
    
    closed_positions = position_manager.get_closed_positions()
    if closed_positions:
        # [Performance metrics code remains the same...]
        pass

# Tab 7: MM Patterns (remains the same)
with tabs[6]:
    st.header("🧠 Market Maker Behavior Patterns")
    # [Pattern content remains the same...]

# Tab 8: 0DTE Scanner (NEW)
with tabs[7]:
    st.header("🔥 0DTE High Gamma Scanner")
    
    st.info("""
    0DTE (Zero Days to Expiration) options have the highest gamma sensitivity.
    Small price moves create explosive MM hedging requirements.
    """)
    
    if st.button("🔍 Scan 0DTE Opportunities", type="primary"):
        with st.spinner("Scanning for 0DTE high gamma..."):
            dte_results = scan_0dte_options(analyzer)
            
            if dte_results:
                for result in dte_results:
                    st.subheader(f"📍 {result['symbol']}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Current Price**: ${result['current_price']:.2f}")
                        if result['high_gamma_strikes']['calls']:
                            st.write(f"**High Gamma Calls**: {', '.join([f'${s:.0f}' for s in result['high_gamma_strikes']['calls'][:3]])}")
                    
                    with col2:
                        st.write(f"**Expiry**: Today!")
                        if result['high_gamma_strikes']['puts']:
                            st.write(f"**High Gamma Puts**: {', '.join([f'${s:.0f}' for s in result['high_gamma_strikes']['puts'][:3]])}")
                    
                    # Send alert for high gamma
                    if result['high_gamma_strikes']['calls'] or result['high_gamma_strikes']['puts']:
                        alert_msg = f"""
🔥 **0DTE HIGH GAMMA ALERT** - {result['symbol']}
Current: ${result['current_price']:.2f}
High Gamma Strikes: {', '.join([f'${s:.0f}' for s in (result['high_gamma_strikes']['calls'] + result['high_gamma_strikes']['puts'])[:5]])}
Action: Watch for explosive moves near these strikes!
"""
                        alert_manager.send_discord_alert(alert_msg)
            else:
                st.info("No significant 0DTE opportunities found")

# Tab 9: Backtesting (NEW)
with tabs[8]:
    st.header("📐 Strategy Backtesting")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        backtest_symbol = st.text_input("Symbol for Backtest", "SPY")
    
    with col2:
        backtest_strategy = st.selectbox("Strategy", ["SQUEEZE_PLAY", "PREMIUM_SELLING", "IRON_CONDOR"])
    
    with col3:
        backtest_days = st.slider("Days to Test", 7, 90, 30)
    
    if st.button("Run Backtest"):
        with st.spinner(f"Running {backtest_days}-day backtest..."):
            results = run_backtest(analyzer, backtest_symbol, backtest_strategy, backtest_days)
            
            if results:
                st.session_state.backtest_results = results
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Trades", results['total_trades'])
                
                with col2:
                    st.metric("Win Rate", f"{results['win_rate']:.1f}%")
                
                with col3:
                    st.metric("Avg Return", f"{results['avg_return']:.2f}%")
                
                with col4:
                    st.metric("Total Return", f"{results['total_return']:.2f}%")
                
                st.success(f"Backtest complete for {backtest_symbol}")
            else:
                st.error("Unable to run backtest - insufficient data")

# Tab 10: Max Pain Calculator (NEW)
with tabs[9]:
    st.header("💀 Max Pain Calculator")
    
    st.info("""
    Max Pain is the strike price where the most options expire worthless.
    Market makers often try to pin the price here by expiration.
    """)
    
    pain_symbol = st.text_input("Symbol for Max Pain", "SPY", key="pain_symbol")
    
    if st.button("Calculate Max Pain"):
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
                    
                    # Strategy based on max pain
                    st.subheader("📋 Max Pain Strategy")
                    
                    if abs(distance) < 1:
                        st.warning("🎯 Price at max pain - Sell straddles/strangles")
                        strategy = "SELL_PREMIUM"
                    elif distance > 3:
                        st.info("📈 Price well below max pain - Bullish bias")
                        strategy = "BUY_CALLS"
                    elif distance < -3:
                        st.info("📉 Price well above max pain - Bearish bias")
                        strategy = "BUY_PUTS"
                    else:
                        st.info("➡️ Price moving toward max pain")
                        strategy = "WAIT"
                    
                    # Send Discord alert
                    alert_msg = f"""
💀 **MAX PAIN ALERT** - {pain_symbol}
Max Pain: ${max_pain:.2f}
Current: ${current_price:.2f}
Distance: {distance:.1f}%
Strategy: {strategy}
"""
                    if st.button("Send Max Pain Alert"):
                        if alert_manager.send_discord_alert(alert_msg):
                            st.success("Alert sent to Discord!")

# Footer
ui.render_footer()

# Auto-refresh for active positions
if len(position_manager.get_active_positions()) > 0:
    time.sleep(30)
    st.rerun()
