"""
DealerEdge UI Components
Reusable UI elements and rendering functions
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Dict, List, Optional
from config import SIGNAL_EMOJIS, FILTER_OPTIONS

class UIComponents:
    """Handles all UI rendering components"""
    
    def render_header(self, win_streak: int, total_pnl: float, active_positions: int):
        """Render main application header"""
        st.markdown(f"""
        <div class="dealeredge-header">
            <h1 style="font-size: 3.5rem; margin: 0; font-weight: 900;">
                DEALEREDGE
            </h1>
            <p style="font-size: 1.4rem; margin-top: 0.5rem; opacity: 0.9; letter-spacing: 2px;">
                PROFESSIONAL GEX TRADING PLATFORM
            </p>
            <div class="win-streak">
                🔥 Win Streak: {win_streak} | 
                💰 Total P&L: ${total_pnl:,.0f} |
                📊 Active: {active_positions}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_scan_results(self, results: List[Dict], filter_type: str, 
                           position_manager, alert_manager):
        """Render scanner results"""
        from scanner import SymbolScanner
        scanner = SymbolScanner(None)
        filtered = scanner.filter_results_by_type(results, filter_type)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        trapped = sum(1 for r in results 
                     if r.get('gex_profile') and r['gex_profile'].get('dealer_pain', 0) > 80)
        scrambling = sum(1 for r in results 
                        if r.get('gex_profile') and 60 < r['gex_profile'].get('dealer_pain', 0) <= 80)
        squeeze_ops = sum(1 for r in results 
                         if r.get('best_signal') and r['best_signal'].get('type') == 'SQUEEZE_PLAY')
        premium_ops = sum(1 for r in results 
                         if r.get('best_signal') and r['best_signal'].get('type') == 'PREMIUM_SELLING')
        condor_ops = sum(1 for r in results 
                        if r.get('best_signal') and r['best_signal'].get('type') == 'IRON_CONDOR')
        
        with col1:
            st.metric("🔥 Trapped", trapped)
        with col2:
            st.metric("😰 Scrambling", scrambling)
        with col3:
            st.metric("⚡ Squeezes", squeeze_ops)
        with col4:
            st.metric("💰 Premium", premium_ops)
        with col5:
            st.metric("🦅 Condors", condor_ops)
        
        st.markdown(f"### Showing {len(filtered)} of {len(results)} opportunities")
        
        for r in filtered[:20]:
            if r.get('best_signal'):
                self.render_opportunity_card(r, position_manager, alert_manager)
    
    def render_opportunity_card(self, result: Dict, position_manager, alert_manager):
        """Render a single opportunity card"""
        symbol = result['symbol']
        signal = result.get('best_signal', {})
        gex = result.get('gex_profile')
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            confidence = signal.get('confidence', 0)
            dealer_pain = gex.get('dealer_pain', 0) if gex else 0
            
            emoji = SIGNAL_EMOJIS.get(signal.get('type', 'WAIT'), '📊')
            
            st.markdown(f"""
            **{emoji} {symbol}** - {signal.get('direction', 'N/A')}  
            Confidence: {confidence:.0f}% | Pain: {dealer_pain:.0f} | {signal.get('reasoning', '')[:80]}...
            """)
        
        with col2:
            if st.button(f"Trade", key=f"trade_{symbol}"):
                if gex:
                    position = position_manager.add_position(
                        symbol,
                        gex.get('current_price', 100),
                        signal.get('position_size', 1000) / gex.get('current_price', 100),
                        signal.get('type', 'MANUAL'),
                        signal
                    )
                    st.success(f"Position opened!")
        
        with col3:
            if st.button(f"Alert", key=f"alert_{symbol}"):
                alert_msg = alert_manager.format_discord_alert(symbol, gex, signal)
                if alert_manager.send_discord_alert(alert_msg):
                    st.success("Alert sent!")
    
    def render_analysis_results(self, gex_profile: Dict, best_signal: Optional[Dict]):
        """Render deep analysis results"""
        if best_signal:
            dealer_pain = gex_profile.get('dealer_pain', 0)
            
            if dealer_pain > 80:
                status_class = 'mm-trapped'
            elif dealer_pain > 60:
                status_class = 'mm-scrambling'
            else:
                status_class = 'mm-defending'
            
            st.markdown(f"""
            <div class="action-box {status_class}">
                <h1>🎯 {best_signal['direction']}</h1>
                <p>Pain: {dealer_pain:.0f}/100 | Confidence: {best_signal.get('confidence', 0):.0f}%</p>
                <p>{best_signal.get('entry', '')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Price", f"${gex_profile['current_price']:.2f}")
        with col2:
            st.metric("Net GEX", f"{gex_profile['net_gex']/1e9:.1f}B")
        with col3:
            st.metric("Gamma Flip", f"${gex_profile['gamma_flip']:.2f}")
        with col4:
            st.metric("Distance", f"{gex_profile['distance_to_flip']:.1f}%")
        with col5:
            st.metric("Dealer Pain", f"{gex_profile.get('dealer_pain', 0):.0f}")
        with col6:
            st.metric("VIX", f"{gex_profile.get('vix', 15):.1f}")
    
    def render_gex_charts(self, gex_profile: Dict):
        """Render GEX visualization charts"""
        if not gex_profile or 'strike_data' not in gex_profile:
            return
        
        df = gex_profile['strike_data']
        current_price = gex_profile['current_price']
        gamma_flip = gex_profile['gamma_flip']
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('GEX by Strike', 'Cumulative GEX', 'Call vs Put GEX', 'MM Pressure Map'),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # GEX by Strike
        fig.add_trace(
            go.Bar(x=df['strike'], y=df['net_gex']/1e6, name='Net GEX',
                  marker_color='blue'),
            row=1, col=1
        )
        fig.add_vline(x=current_price, line_dash="dash", line_color="yellow",
                     annotation_text="Current", row=1, col=1)
        fig.add_vline(x=gamma_flip, line_dash="dash", line_color="red",
                     annotation_text="Flip", row=1, col=1)
        
        # Cumulative GEX
        fig.add_trace(
            go.Scatter(x=df['strike'], y=df['cumulative_gex']/1e6, name='Cumulative',
                      mode='lines', line=dict(color='purple', width=2)),
            row=1, col=2
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=2)
        
        # Call vs Put GEX
        fig.add_trace(
            go.Bar(x=df['strike'], y=df['call_gex']/1e6, name='Call GEX',
                  marker_color='green'),
            row=2, col=1
        )
        fig.add_trace(
            go.Bar(x=df['strike'], y=df['put_gex']/1e6, name='Put GEX',
                  marker_color='red'),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"GEX Analysis - Net: {gex_profile['net_gex']/1e9:.2f}B",
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_position_tracker(self, position_manager):
        """Render position tracking interface"""
        st.subheader("Active Positions")
        active = position_manager.get_active_positions()
        
        if active:
            for position in active:
                self.render_position_card(position, position_manager)
        else:
            st.info("No active positions")
        
        if position_manager.get_closed_positions():
            st.subheader("Recent Closed Positions")
            for p in position_manager.get_closed_positions()[-5:]:
                st.write(f"{p['symbol']}: {p['final_pnl_percent']:.1f}% - {p['close_reason']}")
    
    def render_position_card(self, position: Dict, position_manager):
        """Render a single position card"""
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            pnl_color = "🟢" if position['pnl_percent'] > 0 else "🔴"
            st.markdown(f"""
            **{position['symbol']}** - {position['strategy']}  
            Entry: ${position['entry_price']:.2f} | Current: ${position['current_price']:.2f}  
            {pnl_color} P&L: ${position['pnl']:.2f} ({position['pnl_percent']:.1f}%)
            """)
        
        with col2:
            st.metric("Target", position['target'])
        
        with col3:
            st.metric("Stop", position['stop'])
        
        with col4:
            if st.button(f"Close", key=f"close_{position['id']}"):
                closed = position_manager.manual_close_position(position['id'])
                if closed:
                    st.success(f"Closed: {closed['final_pnl_percent']:.1f}% return")
                    st.rerun()
    
    def render_performance_report(self, position_manager):
        """Render performance report"""
        summary = position_manager.get_position_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total P&L", f"${summary['total_pnl']:,.2f}")
        
        with col2:
            st.metric("Active Positions", summary['active_count'])
        
        with col3:
            st.metric("Closed Positions", summary['closed_count'])
        
        with col4:
            st.metric("Win Rate", f"{summary['win_rate']:.1f}%")
    
    def render_alert_configuration(self, alert_manager, analyzer, scanner):
        """Render alert configuration interface"""
        st.markdown("""
        ### Auto-Scan Settings
        The system will automatically scan all 200+ symbols every 2 hours during market hours
        and send Discord alerts for high-confidence opportunities.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_conf = st.slider("Minimum Confidence for Alerts", 0, 100, 65, 5)
            auto_scan_enabled = st.checkbox("Enable Auto-Scan (Every 2 Hours)")
        
        with col2:
            st.info(f"""
            **Current Settings:**
            - Min Confidence: {min_conf}%
            - Auto-Scan: {'✅ Enabled' if auto_scan_enabled else '❌ Disabled'}
            - Scan Interval: 2 hours
            - Symbols: {len(scanner.symbols)}
            """)
            
            if st.button("Test Alert System"):
                if alert_manager.send_test_alert():
                    st.success("✅ Test alert sent successfully!")
                else:
                    st.error("❌ Alert failed - check webhook URL")
        
        if st.button("Run Auto-Scan Now", type="primary"):
            with st.spinner("Running automated scan..."):
                analyzer.auto_scan_and_alert(scanner.symbols[:50], min_confidence=min_conf)
                st.success("Auto-scan complete! Check Discord for alerts.")
    
    def render_footer(self):
        """Render application footer"""
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h3 style="color: #667eea;">DealerEdge - Professional GEX Trading Platform</h3>
            <p style="color: #888;">⚠️ Trading involves substantial risk. Paper trade first.</p>
        </div>
        """, unsafe_allow_html=True)
