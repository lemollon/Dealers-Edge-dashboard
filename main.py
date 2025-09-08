"""
DealerEdge Main Application
Professional GEX Trading Platform
"""

import streamlit as st
import warnings
from datetime import datetime

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
if 'alerts_config' not in st.session_state:
    st.session_state.alerts_config = {
        'min_confidence': MIN_CONFIDENCE_DEFAULT,
        'auto_scan': False,
        'scan_interval': 2
    }
if 'custom_symbols' not in st.session_state:
    st.session_state.custom_symbols = []

# Header
position_summary = position_manager.get_position_summary()
ui.render_header(
    win_streak=st.session_state.win_streak,
    total_pnl=position_summary['total_pnl'],
    active_positions=position_summary['active_count']
)

# Main tabs
tabs = st.tabs([
    "🔍 Scanner",
    "🎯 Analysis", 
    "📊 Positions",
    "⚡ Auto-Alerts",
    "📈 Report",
    "⚙️ Settings"
])

# Tab 1: Scanner
with tabs[0]:
    st.header("🔍 Market Maker Vulnerability Scanner")
    
    # Scanner controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        filter_type = st.selectbox("Filter View", FILTER_OPTIONS)
    
    with col2:
        min_confidence = st.slider("Min Conf %", 0, 100, MIN_CONFIDENCE_DEFAULT, 5)
    
    with col3:
        auto_alert = st.checkbox("Alert on Find", value=True)
    
    with col4:
        scan_btn = st.button("🚀 SCAN ALL", type="primary", use_container_width=True)
    
    # Quick scan options
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    
    with quick_col1:
        if st.button("🔥 Scan High Volume Only"):
            with st.spinner("Scanning high volume symbols..."):
                high_vol_symbols = scanner.get_high_volume_symbols()
                scan_results = scanner.scan_multiple_symbols(
                    high_vol_symbols,
                    min_confidence=min_confidence
                )
                st.session_state.scan_results = scan_results
                st.success(f"✅ Scanned {len(high_vol_symbols)} high volume symbols!")
    
    with quick_col2:
        if st.button("📊 Scan ETFs Only"):
            with st.spinner("Scanning ETFs..."):
                etf_symbols = [s for s in scanner.symbols if s in CORE_ETFS]
                scan_results = scanner.scan_multiple_symbols(
                    etf_symbols,
                    min_confidence=min_confidence
                )
                st.session_state.scan_results = scan_results
                st.success(f"✅ Scanned {len(etf_symbols)} ETFs!")
    
    with quick_col3:
        if st.button("⭐ Scan Custom List"):
            if st.session_state.custom_symbols:
                with st.spinner("Scanning custom list..."):
                    scan_results = scanner.scan_multiple_symbols(
                        st.session_state.custom_symbols,
                        min_confidence=min_confidence
                    )
                    st.session_state.scan_results = scan_results
                    st.success(f"✅ Scanned {len(st.session_state.custom_symbols)} custom symbols!")
            else:
                st.warning("No custom symbols defined. Add them in Settings tab.")
    
    # Main scan
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
        
        progress_bar.progress(1.0)
        status_text.success(f"✅ Scanned {len(scanner.symbols)} symbols!")
        
        if auto_alert and scan_results:
            high_value = [r for r in scan_results 
                         if r.get('opportunity_score', 0) > 70][:3]
            
            alerts_sent = alert_manager.send_batch_alerts(high_value)
            if alerts_sent > 0:
                st.success(f"✅ Sent {alerts_sent} alerts to Discord")
    
    # Display results
    if st.session_state.scan_results:
        ui.render_scan_results(
            st.session_state.scan_results,
            filter_type,
            position_manager,
            alert_manager
        )

# Tab 2: Analysis
with tabs[1]:
    st.header("🎯 Deep Market Maker Analysis")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        symbol = st.text_input("Symbol", value="SPY").upper().strip()
    
    with col2:
        analysis_type = st.selectbox("Analysis", ["Quick", "Deep", "Historical"])
    
    with col3:
        if st.button("🔄 Analyze", use_container_width=True):
            st.rerun()
    
    if symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            options_data = analyzer.get_options_chain(symbol)
        
        if options_data:
            gex_profile = analyzer.calculate_gex_profile(options_data)
            
            if gex_profile:
                signals = analyzer.generate_all_signals(gex_profile, symbol)
                best_signal = signals[0] if signals else None
                
                # Display results
                ui.render_analysis_results(gex_profile, best_signal)
                
                # Charts
                chart_tabs = st.tabs(["GEX Profile", "Pressure Map", "Historical"])
                
                with chart_tabs[0]:
                    ui.render_gex_charts(gex_profile)
                
                with chart_tabs[1]:
                    ui.render_pressure_map(gex_profile)
                
                with chart_tabs[2]:
                    if analysis_type in ["Deep", "Historical"]:
                        historical_data = analyzer.get_historical_data(symbol)
                        if historical_data is not None:
                            ui.render_historical_analysis(historical_data, gex_profile)
                
                # Trade recommendations
                st.subheader("📋 All Trade Signals")
                for i, signal in enumerate(signals[:5]):
                    ui.render_signal_card(signal, symbol, position_manager, alert_manager, i)
        else:
            st.error(f"Unable to fetch options data for {symbol}")

# Tab 3: Positions
with tabs[2]:
    st.header("📊 Position Tracking")
    
    # Update positions (checks for auto-close)
    closed = position_manager.update_positions()
    if closed:
        for p in closed:
            st.info(f"Auto-closed {p['symbol']}: {p['close_reason']} - P&L: {p['final_pnl_percent']:.1f}%")
            # Update win streak
            if p['final_pnl_percent'] > 0:
                st.session_state.win_streak += 1
            else:
                st.session_state.win_streak = 0
    
    # Position controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Update All Positions"):
            position_manager.update_positions()
            st.rerun()
    
    with col2:
        if st.button("📊 Export Positions"):
            ui.export_positions(position_manager)
    
    with col3:
        if st.button("🗑️ Clear Closed"):
            position_manager.closed_positions = []
            st.success("Cleared closed positions history")
    
    # Display positions
    ui.render_position_tracker(position_manager)

# Tab 4: Auto-Alerts
with tabs[3]:
    st.header("⚡ Automated Alert Configuration")
    ui.render_alert_configuration(alert_manager, analyzer, scanner)
    
    # Alert history
    st.subheader("📜 Recent Alerts")
    if hasattr(alert_manager, 'alert_history'):
        for alert in alert_manager.alert_history[-10:]:
            st.text(f"{alert['time']} - {alert['symbol']}: {alert['type']}")

# Tab 5: Report
with tabs[4]:
    st.header("📈 Performance Report")
    
    # Performance metrics
    ui.render_performance_report(position_manager)
    
    # Strategy breakdown
    st.subheader("📊 Strategy Performance")
    strategy_metrics = position_manager.get_strategy_metrics()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Squeeze Plays", 
                 f"{strategy_metrics.get('SQUEEZE_PLAY', {}).get('win_rate', 0):.1f}%",
                 f"P&L: ${strategy_metrics.get('SQUEEZE_PLAY', {}).get('total_pnl', 0):,.0f}")
    
    with col2:
        st.metric("Premium Selling", 
                 f"{strategy_metrics.get('PREMIUM_SELLING', {}).get('win_rate', 0):.1f}%",
                 f"P&L: ${strategy_metrics.get('PREMIUM_SELLING', {}).get('total_pnl', 0):,.0f}")
    
    with col3:
        st.metric("Iron Condors", 
                 f"{strategy_metrics.get('IRON_CONDOR', {}).get('win_rate', 0):.1f}%",
                 f"P&L: ${strategy_metrics.get('IRON_CONDOR', {}).get('total_pnl', 0):,.0f}")
    
    # Charts
    if position_manager.closed_positions:
        ui.render_performance_charts(position_manager)

# Tab 6: Settings
with tabs[5]:
    st.header("⚙️ Settings")
    
    # Custom watchlist
    st.subheader("⭐ Custom Watchlist")
    
    custom_input = st.text_input("Add symbols (comma-separated)")
    if st.button("Add to Watchlist"):
        new_symbols = [s.strip().upper() for s in custom_input.split(',') if s.strip()]
        st.session_state.custom_symbols.extend(new_symbols)
        st.session_state.custom_symbols = list(set(st.session_state.custom_symbols))
        st.success(f"Added {len(new_symbols)} symbols")
    
    if st.session_state.custom_symbols:
        st.write("Current watchlist:", ', '.join(st.session_state.custom_symbols))
        if st.button("Clear Watchlist"):
            st.session_state.custom_symbols = []
            st.success("Watchlist cleared")
    
    # Risk settings
    st.subheader("💰 Risk Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_position_size = st.slider("Max Position Size (%)", 1, 10, 3)
        stop_loss = st.slider("Stop Loss (%)", 10, 50, 50)
    
    with col2:
        profit_target = st.slider("Profit Target (%)", 50, 200, 100)
        max_positions = st.slider("Max Open Positions", 1, 20, 5)
    
    if st.button("Save Settings"):
        # Update analyzer config
        analyzer.strategies_config['risk_management']['max_position_size_squeeze'] = max_position_size / 100
        analyzer.strategies_config['risk_management']['stop_loss_percentage'] = stop_loss / 100
        analyzer.strategies_config['risk_management']['profit_target_long'] = profit_target / 100
        st.success("Settings saved!")
    
    # Discord webhook test
    st.subheader("🔔 Discord Configuration")
    if st.button("Test Discord Webhook"):
        if alert_manager.send_test_alert():
            st.success("✅ Discord webhook is working!")
        else:
            st.error("❌ Discord webhook failed. Check configuration.")

# Footer
ui.render_footer()

# Auto-refresh for positions
if len(position_manager.get_active_positions()) > 0:
    time.sleep(30)  # Refresh every 30 seconds if positions are open
    st.rerun()
