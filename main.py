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
                signals = analyzer.generate_all_signals(gex_profile, symbol)
                best_signal = signals[0] if signals else None
                
                ui.render_analysis_results(gex_profile, best_signal)
                ui.render_gex_charts(gex_profile)

# Tab 3: Positions
with tabs[2]:
    st.header("📊 Position Tracking")
    
    closed = position_manager.update_positions()
    if closed:
        for p in closed:
            st.info(f"Auto-closed {p['symbol']}: {p['close_reason']} - P&L: {p['final_pnl_percent']:.1f}%")
    
    ui.render_position_tracker(position_manager)

# Tab 4: Auto-Alerts
with tabs[3]:
    st.header("⚡ Automated Alert Configuration")
    ui.render_alert_configuration(alert_manager, analyzer, scanner)

# Tab 5: Report
with tabs[4]:
    st.header("📈 Performance Report")
    ui.render_performance_report(position_manager)

# Footer
ui.render_footer()
