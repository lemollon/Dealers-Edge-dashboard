"""
DealerEdge UI Components
Reusable UI elements and rendering functions
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
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
        """Render scanner results with clickable filter metrics"""
        
        # Calculate counts for different categories
        trapped = [r for r in results if r.get('mm_vulnerability', 0) > 80]
        scrambling = [r for r in results if 60 < r.get('mm_vulnerability', 0) <= 80]
        squeeze_ops = [r for r in results if any(p['type'] == 'GAMMA_SQUEEZE' for p in r.get('mm_patterns', []))]
        premium_ops = [r for r in results if r.get('best_signal') and r['best_signal'].get('type') == 'PREMIUM_SELLING']
        condor_ops = [r for r in results if r.get('best_signal') and r['best_signal'].get('type') == 'IRON_CONDOR']
        
        # Create clickable filter buttons
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button(f"🔥 Trapped ({len(trapped)})", 
                        key="filter_trapped",
                        help="Click to filter trapped MMs"):
                st.session_state.active_filter = 'trapped'
                st.rerun()
        
        with col2:
            if st.button(f"😰 Scrambling ({len(scrambling)})",
                        key="filter_scrambling", 
                        help="Click to filter scrambling MMs"):
                st.session_state.active_filter = 'scrambling'
                st.rerun()
        
        with col3:
            if st.button(f"⚡ Squeezes ({len(squeeze_ops)})",
                        key="filter_squeeze",
                        help="Click to filter squeeze plays"):
                st.session_state.active_filter = 'squeeze'
                st.rerun()
        
        with col4:
            if st.button(f"💰 Premium ({len(premium_ops)})",
                        key="filter_premium",
                        help="Click to filter premium selling"):
                st.session_state.active_filter = 'premium'
                st.rerun()
        
        with col5:
            if st.button(f"🦅 Condors ({len(condor_ops)})",
                        key="filter_condor",
                        help="Click to filter iron condors"):
                st.session_state.active_filter = 'condor'
                st.rerun()
        
        # Clear filter button
        if st.session_state.get('active_filter'):
            if st.button("❌ Clear Filter", key="clear_filter"):
                st.session_state.active_filter = None
                st.rerun()
        
        # Apply active filter
        if st.session_state.get('active_filter') == 'trapped':
            filtered = trapped
        elif st.session_state.get('active_filter') == 'scrambling':
            filtered = scrambling
        elif st.session_state.get('active_filter') == 'squeeze':
            filtered = squeeze_ops
        elif st.session_state.get('active_filter') == 'premium':
            filtered = premium_ops
        elif st.session_state.get('active_filter') == 'condor':
            filtered = condor_ops
        else:
            filtered = results
        
        st.markdown(f"### Showing {len(filtered)} opportunities")
        
        # Display opportunities with better styling
        for r in filtered[:20]:  # Show top 20
            symbol = r['symbol']
            mm_vulnerability = r.get('mm_vulnerability', 0)
            best_exploit = r.get('best_exploit')
            best_signal = r.get('best_signal')
            gex = r.get('gex_profile')
            
            # Determine urgency and styling
            if mm_vulnerability > 80:
                urgency_emoji = "🔥"
                urgency_color = "red"
                expanded = True
            elif mm_vulnerability > 60:
                urgency_emoji = "⚡"
                urgency_color = "orange"
                expanded = False
            else:
                urgency_emoji = "📊"
                urgency_color = "green"
                expanded = False
            
            # Create expandable card for each opportunity
            with st.expander(
                f"{urgency_emoji} **{symbol}** - Vulnerability: {mm_vulnerability:.0f} | "
                f"Score: {r.get('opportunity_score', 0):.0f}", 
                expanded=expanded
            ):
                # Show MM exploit if available
                if best_exploit:
                    st.error(f"🎯 **EXPLOIT**: {best_exploit['specific_trade']}")
                    st.write(f"**Expected Return**: {best_exploit.get('expected_return', 'N/A')}")
                    st.write(f"**Urgency**: {best_exploit.get('urgency', 'MODERATE')}")
                
                # Show best signal
                if best_signal:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        **Signal**: {best_signal.get('type', 'N/A')} - {best_signal.get('direction', 'N/A')}  
                        **Confidence**: {best_signal.get('confidence', 0):.0f}%  
                        **Entry**: {best_signal.get('entry', 'N/A')}  
                        **Target**: {best_signal.get('target', 'N/A')}  
                        **Stop**: {best_signal.get('stop', 'N/A')}  
                        **Expected Move**: {best_signal.get('expected_move', 0):.1f}%  
                        **Reasoning**: {best_signal.get('reasoning', 'No analysis available')}
                        """)
                    
                    with col2:
                        if st.button(f"Trade", key=f"scan_trade_{symbol}"):
                            if gex:
                                position = position_manager.add_position(
                                    symbol,
                                    gex.get('current_price', 100),
                                    best_signal.get('position_size', 1000) / gex.get('current_price', 100),
                                    best_signal.get('type', 'MANUAL'),
                                    best_signal
                                )
                                st.success(f"Position opened for {symbol}!")
                                st.rerun()
                        
                        if st.button(f"Alert", key=f"scan_alert_{symbol}"):
                            alert_msg = f"""
🔥 **MM VULNERABILITY ALERT** - {symbol}
Vulnerability: {mm_vulnerability:.0f}/100
{f"Exploit: {best_exploit['specific_trade']}" if best_exploit else ""}
{f"Expected: {best_exploit.get('expected_return', 'N/A')}" if best_exploit else ""}
{f"Signal: {best_signal['type']} - {best_signal['direction']}" if best_signal else ""}
"""
                            if alert_manager.send_discord_alert(alert_msg):
                                st.success("Alert sent!")
                
                # Show GEX metrics if available
                if gex:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Price", f"${gex.get('current_price', 0):.2f}")
                    
                    with col2:
                        st.metric("Net GEX", f"{gex.get('net_gex', 0)/1e9:.2f}B")
                    
                    with col3:
                        st.metric("Gamma Flip", f"${gex.get('gamma_flip', 0):.2f}")
                    
                    with col4:
                        st.metric("Dealer Pain", f"{gex.get('dealer_pain', 0):.0f}")
    
    def render_analysis_results(self, gex_profile: Dict, best_signal: Optional[Dict]):
        """Render deep analysis results"""
        if best_signal:
            dealer_pain = gex_profile.get('dealer_pain', 0)
            
            if dealer_pain > 80:
                status_class = 'mm-trapped'
                status_text = "MM TRAPPED - EXPLOIT NOW!"
            elif dealer_pain > 60:
                status_class = 'mm-scrambling'
                status_text = "MM SCRAMBLING"
            else:
                status_class = 'mm-defending'
                status_text = "MM IN CONTROL"
            
            st.markdown(f"""
            <div class="action-box {status_class}">
                <h1>🎯 {best_signal['direction']}</h1>
                <p>Pain: {dealer_pain:.0f}/100 | Confidence: {best_signal.get('confidence', 0):.0f}%</p>
                <p>{best_signal.get('entry', '')}</p>
                <p>{status_text}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display key metrics
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
            st.warning("No strike data available for charts")
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
        
        # MM Pressure heatmap (simplified)
        pressure_data = []
        for _, row in df.iterrows():
            if abs(row['net_gex']) > 1e8:  # Significant gamma
                pressure = abs(row['net_gex']) / 1e9
                pressure_data.append(dict(
                    x=[row['strike']],
                    y=[pressure],
                    marker=dict(
                        size=pressure * 10,
                        color='red' if row['strike'] < current_price else 'green'
                    )
                ))
        
        if pressure_data:
            for p in pressure_data:
                fig.add_trace(
                    go.Scatter(x=p['x'], y=p['y'], mode='markers',
                              marker=p['marker'], showlegend=False),
                    row=2, col=2
                )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"GEX Analysis - Net: {gex_profile['net_gex']/1e9:.2f}B | Dealer Pain: {gex_profile.get('dealer_pain', 0):.0f}",
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_pressure_map(self, gex_profile: Dict):
        """Render market maker pressure map visualization"""
        if not gex_profile or 'strike_data' not in gex_profile:
            st.warning("No data available for pressure map")
            return
        
        st.markdown("""
        <div class="mm-pressure-map">
            <h3>🎯 Market Maker Pressure Map</h3>
        </div>
        """, unsafe_allow_html=True)
        
        df = gex_profile['strike_data']
        current_price = gex_profile['current_price']
        gamma_flip = gex_profile['gamma_flip']
        
        # Get relevant strikes around current price
        relevant_strikes = df[
            (df['strike'] >= current_price * 0.95) & 
            (df['strike'] <= current_price * 1.05)
        ].sort_values('strike', ascending=False)
        
        # Display pressure levels
        for _, row in relevant_strikes.head(20).iterrows():
            strike = row['strike']
            net_gex = row['net_gex']
            
            # Determine pressure level and emoji
            if abs(net_gex) > 1e9:
                pressure_class = "high-pressure"
                emoji = "🔴"
                pressure_text = "HIGH GAMMA"
            elif abs(current_price - strike) < 1:
                pressure_class = "current-price"
                emoji = "📍"
                pressure_text = "AT PRICE"
            elif abs(strike - gamma_flip) < 1:
                emoji = "⚡"
                pressure_class = "current-price"
                pressure_text = "GAMMA FLIP"
            else:
                pressure_class = "low-pressure"
                emoji = "🟢"
                pressure_text = "LOW"
            
            st.markdown(f"""
            <div class="pressure-level {pressure_class}">
                {emoji} ${strike:.0f} | GEX: {net_gex/1e6:.0f}M | {pressure_text}
            </div>
            """, unsafe_allow_html=True)
        
        # Summary box
        dealer_pain = gex_profile.get('dealer_pain', 0)
        if dealer_pain > 80:
            status_msg = "🔥 EXTREME PRESSURE - Dealers trapped! EXPLOIT NOW!"
        elif dealer_pain > 60:
            status_msg = "⚠️ HIGH PRESSURE - Volatility incoming"
        else:
            status_msg = "✅ MANAGEABLE - Dealers in control"
        
        st.info(f"""
        **Pressure Status**: {status_msg}
        **Gamma Flip**: ${gamma_flip:.2f}
        **Current Price**: ${current_price:.2f}
        **Distance to Flip**: {gex_profile.get('distance_to_flip', 0):.1f}%
        **Pain Score**: {dealer_pain:.0f}/100
        """)
    
    def render_signal_card(self, signal: Dict, symbol: str, position_manager, alert_manager, index: int):
        """Render a single signal card with trade and alert buttons"""
        if not signal:
            return
        
        confidence = signal.get('confidence', 0)
        signal_type = signal.get('type', 'UNKNOWN')
        direction = signal.get('direction', 'N/A')
        
        # Determine emoji based on signal type
        emoji = SIGNAL_EMOJIS.get(signal_type, '📊')
        
        # Create card with signal details
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"""
                **{emoji} {signal_type}** - {direction}  
                **Confidence**: {confidence:.0f}%  
                **Entry**: {signal.get('entry', 'N/A')}  
                **Target**: {signal.get('target', 'N/A')}  
                **Stop**: {signal.get('stop', 'N/A')}  
                **Expected Move**: {signal.get('expected_move', 0):.1f}%  
                **Reasoning**: {signal.get('reasoning', 'No analysis available')[:200]}...
                """)
            
            with col2:
                if st.button("📈 Trade", key=f"trade_signal_{symbol}_{signal_type}_{index}"):
                    # Get current price from signal or default
                    current_price = signal.get('current_price', 100)
                    position_size = signal.get('position_size', 1000)
                    shares = position_size / current_price
                    
                    position = position_manager.add_position(
                        symbol,
                        current_price,
                        shares,
                        signal_type,
                        signal
                    )
                    
                    if position:
                        st.success(f"✅ Position opened for {symbol}!")
                        st.rerun()
                    else:
                        st.error("Failed to open position")
            
            with col3:
                if st.button("📢 Alert", key=f"alert_signal_{symbol}_{signal_type}_{index}"):
                    # Format alert message
                    alert_msg = f"""
📊 **SIGNAL ALERT** - {symbol}
Type: {signal_type}
Direction: {direction}
Confidence: {confidence:.0f}%
Entry: {signal.get('entry', 'N/A')}
Target: {signal.get('target', 'N/A')}
Stop: {signal.get('stop', 'N/A')}
Reasoning: {signal.get('reasoning', 'N/A')[:100]}...
"""
                    
                    if alert_manager.send_discord_alert(alert_msg):
                        st.success("✅ Alert sent to Discord!")
                    else:
                        st.error("Failed to send alert")
    
    def render_position_tracker(self, position_manager):
        """Render position tracking interface"""
        st.subheader("📊 Active Positions")
        active = position_manager.get_active_positions()
        
        if active:
            for position in active:
                self.render_position_card(position, position_manager)
        else:
            st.info("No active positions. Start scanning for opportunities!")
        
        # Show closed positions
        closed = position_manager.get_closed_positions()
        if closed:
            st.subheader("📜 Recent Closed Positions")
            
            for p in closed[-5:]:  # Show last 5
                pnl_emoji = "🟢" if p.get('final_pnl_percent', 0) > 0 else "🔴"
                
                st.write(f"""
                {pnl_emoji} **{p['symbol']}** - {p.get('strategy', 'UNKNOWN')}  
                P&L: ${p.get('final_pnl', 0):.2f} ({p.get('final_pnl_percent', 0):.1f}%)  
                Reason: {p.get('close_reason', 'Manual')}
                """)
    
    def render_position_card(self, position: Dict, position_manager):
        """Render a single position card"""
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        pnl = position.get('pnl', 0)
        pnl_percent = position.get('pnl_percent', 0)
        
        with col1:
            pnl_color = "🟢" if pnl > 0 else "🔴"
            st.markdown(f"""
            **{position['symbol']}** - {position.get('strategy', 'MANUAL')}  
            Entry: ${position['entry_price']:.2f} | Current: ${position.get('current_price', position['entry_price']):.2f}  
            {pnl_color} P&L: ${pnl:.2f} ({pnl_percent:.1f}%)
            """)
        
        with col2:
            target = position.get('target', 'N/A')
            st.metric("Target", target if isinstance(target, str) else f"${target:.2f}")
        
        with col3:
            stop = position.get('stop', 'N/A')
            st.metric("Stop", stop if isinstance(stop, str) else f"${stop:.2f}")
        
        with col4:
            if st.button(f"Close", key=f"close_{position['id']}"):
                closed = position_manager.manual_close_position(position['id'])
                if closed:
                    st.success(f"Closed: {closed['final_pnl_percent']:.1f}% return")
                    st.rerun()
                else:
                    st.error("Failed to close position")
    
    def render_performance_report(self, position_manager):
        """Render performance report"""
        summary = position_manager.get_position_summary()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total P&L", f"${summary['total_pnl']:,.2f}")
        
        with col2:
            st.metric("Active", summary['active_count'])
        
        with col3:
            st.metric("Closed", summary['closed_count'])
        
        with col4:
            st.metric("Win Rate", f"{summary['win_rate']:.1f}%")
        
        with col5:
            avg_win = summary.get('avg_win', 0)
            avg_loss = summary.get('avg_loss', 0)
            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss)
                st.metric("Profit Factor", f"{profit_factor:.2f}")
            else:
                st.metric("Profit Factor", "N/A")
        
        # Show performance by strategy
        if summary.get('by_strategy'):
            st.subheader("📊 Performance by Strategy")
            
            for strategy, stats in summary['by_strategy'].items():
                with st.expander(f"{strategy} - Win Rate: {stats['win_rate']:.1f}%"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Trades", stats['count'])
                    
                    with col2:
                        st.metric("Total P&L", f"${stats['total_pnl']:.2f}")
                    
                    with col3:
                        st.metric("Avg P&L", f"${stats['avg_pnl']:.2f}")
    
    def render_alert_configuration(self, alert_manager, analyzer, scanner):
        """Render alert configuration interface"""
        st.markdown("""
        ### ⚡ Auto-Scan Settings
        The system automatically scans for high-confidence MM exploitation opportunities
        and sends alerts to your Discord webhook.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_conf = st.slider("Minimum Confidence for Alerts", 0, 100, 65, 5)
            min_vulnerability = st.slider("Minimum MM Vulnerability", 0, 100, 70, 5)
            auto_scan_enabled = st.checkbox("Enable Auto-Scan (Every 2 Hours)", value=True)
        
        with col2:
            st.info(f"""
            **Current Settings:**
            - Min Confidence: {min_conf}%
            - Min MM Vulnerability: {min_vulnerability}
            - Auto-Scan: {'✅ Enabled' if auto_scan_enabled else '❌ Disabled'}
            - Scan Interval: 2 hours
            - Symbols: {len(scanner.symbols)}
            """)
            
            if st.button("🧪 Test Alert System"):
                test_msg = """
🧪 **TEST ALERT**
This is a test message from DealerEdge.
If you see this, your Discord webhook is working!
Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if alert_manager.send_discord_alert(test_msg):
                    st.success("✅ Test alert sent successfully!")
                else:
                    st.error("❌ Alert failed - check webhook URL in config")
        
        # Manual scan trigger
        if st.button("🚀 Run Auto-Scan Now", type="primary"):
            with st.spinner("Running automated scan for trapped MMs..."):
                # Scan high-priority symbols
                high_priority = scanner.get_high_mm_vulnerability_symbols()[:20]
                results = scanner.scan_multiple_symbols(high_priority, min_confidence=min_conf)
                
                # Filter for high vulnerability
                critical = [r for r in results if r.get('mm_vulnerability', 0) >= min_vulnerability]
                
                if critical:
                    st.success(f"Found {len(critical)} high vulnerability MMs!")
                    
                    # Send alerts for top 3
                    for r in critical[:3]:
                        alert_msg = f"""
🔥 **AUTO-SCAN ALERT** - {r['symbol']}
MM Vulnerability: {r.get('mm_vulnerability', 0):.0f}/100
Best Exploit: {r.get('best_exploit', {}).get('specific_trade', 'Monitor')}
Expected Return: {r.get('best_exploit', {}).get('expected_return', 'N/A')}
Confidence: {r.get('best_signal', {}).get('confidence', 0):.0f}%
"""
                        alert_manager.send_discord_alert(alert_msg)
                    
                    st.info(f"Sent {min(3, len(critical))} alerts to Discord")
                else:
                    st.info("No high vulnerability MMs found in this scan")
    
    def render_footer(self):
        """Render application footer"""
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h3 style="color: #667eea;">DealerEdge - Professional GEX Trading Platform</h3>
            <p style="color: #888;">⚠️ Trading involves substantial risk. Use proper position sizing.</p>
            <p style="color: #666;">Exploiting market maker hedging requirements since 2024</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_morning_report(self, analyzer):
        """Render morning market maker exploitation report header"""
        # This is just the header - the main logic is in main.py
        st.markdown("""
        <div class="mm-pressure-map">
            <h2>☀️ Morning MM Exploitation Report</h2>
            <p style="color: white;">Top opportunities to profit from trapped market makers</p>
        </div>
        """, unsafe_allow_html=True)
