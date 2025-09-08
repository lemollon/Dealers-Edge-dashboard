"""
DealerEdge Main Application
Professional GEX Trading Platform
"""

import streamlit as st
import warnings
from datetime import datetime
import time

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
    "📈 Report"
])

# Tab 1: Scanner
with tabs[0]:
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

# Tab 2: Analysis
with tabs[1]:
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
                st.session_state.current_analysis = gex_profile
                signals = analyzer.generate_all_signals(gex_profile, symbol)
                best_signal = signals[0] if signals else None
                
                # Display main analysis
                ui.render_analysis_results(gex_profile, best_signal)
                
                # Create sub-tabs for different visualizations
                viz_tabs = st.tabs(["📊 GEX Charts", "🎯 Pressure Map", "📋 Trade Signals"])
                
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
        if st.button("🔄 Refresh Positions"):
            position_manager.update_positions()
            st.rerun()
    
    with col2:
        if st.button("📊 Export History"):
            # Create CSV export
            import pandas as pd
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
            if st.checkbox("Confirm clear all closed positions"):
                position_manager.closed_positions = []
                st.success("History cleared")
                st.rerun()
    
    # Display positions
    ui.render_position_tracker(position_manager)

# Tab 4: Auto-Alerts
with tabs[3]:
    st.header("⚡ Automated Alert Configuration")
    ui.render_alert_configuration(alert_manager, analyzer, scanner)
    
    # Alert log
    st.subheader("📜 Alert History")
    if hasattr(alert_manager, 'alert_history') and alert_manager.alert_history:
        for alert in reversed(alert_manager.alert_history[-10:]):
            st.text(f"{alert.get('time', 'N/A')} - {alert.get('symbol', 'N/A')}: {alert.get('type', 'N/A')}")
    else:
        st.info("No alerts sent yet")

# Tab 5: Report
with tabs[4]:
    st.header("📈 Performance Report")
    
    # Overall performance
    ui.render_performance_report(position_manager)
    
    # Strategy breakdown
    st.subheader("📊 Strategy Performance")
    
    closed_positions = position_manager.get_closed_positions()
    if closed_positions:
        strategy_stats = {}
        
        for position in closed_positions:
            strategy = position.get('strategy', 'UNKNOWN')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'count': 0,
                    'wins': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0
                }
            
            strategy_stats[strategy]['count'] += 1
            if position.get('final_pnl', 0) > 0:
                strategy_stats[strategy]['wins'] += 1
            strategy_stats[strategy]['total_pnl'] += position.get('final_pnl', 0)
        
        # Calculate averages
        for strategy in strategy_stats:
            if strategy_stats[strategy]['count'] > 0:
                strategy_stats[strategy]['avg_pnl'] = (
                    strategy_stats[strategy]['total_pnl'] / 
                    strategy_stats[strategy]['count']
                )
        
        # Display metrics
        cols = st.columns(min(3, len(strategy_stats)))
        
        for i, (strategy, stats) in enumerate(strategy_stats.items()):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            
            with cols[i % 3]:
                st.metric(
                    strategy.replace('_', ' ').title(), 
                    f"{win_rate:.1f}% Win Rate",
                    f"Total: ${stats['total_pnl']:,.0f} | Avg: ${stats['avg_pnl']:,.0f}"
                )
        
        # Daily P&L chart if available
        if len(closed_positions) > 0:
            st.subheader("📈 P&L Progression")
            import pandas as pd
            import plotly.express as px
            
            # Create cumulative P&L
            pnl_data = []
            cumulative = 0
            for p in closed_positions:
                cumulative += p.get('final_pnl', 0)
                pnl_data.append({
                    'Date': p.get('exit_time', datetime.now()),
                    'Cumulative P&L': cumulative,
                    'Trade P&L': p.get('final_pnl', 0)
                })
            
            df = pd.DataFrame(pnl_data)
            
            fig = px.line(df, x='Date', y='Cumulative P&L', 
                         title='Cumulative P&L Over Time',
                         markers=True)
            fig.update_layout(template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No closed positions yet. Start trading to see performance metrics!")

# Footer
ui.render_footer()

# Auto-refresh for active positions
if len(position_manager.get_active_positions()) > 0:
    st.empty()  # Placeholder for auto-refresh
    time.sleep(30)  # Refresh every 30 seconds
    st.rerun()
