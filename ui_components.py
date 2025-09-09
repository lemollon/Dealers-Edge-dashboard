def render_scan_results(self, results: List[Dict], filter_type: str, 
                       position_manager, alert_manager):
    """Render scanner results with clickable filter metrics"""
    
    # Calculate counts
    trapped = [r for r in results if r.get('gex_profile') and r['gex_profile'].get('dealer_pain', 0) > 80]
    scrambling = [r for r in results if r.get('gex_profile') and 60 < r['gex_profile'].get('dealer_pain', 0) <= 80]
    squeeze_ops = [r for r in results if r.get('best_signal') and r['best_signal'].get('type') == 'SQUEEZE_PLAY']
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
        # Apply dropdown filter
        from scanner import SymbolScanner
        scanner = SymbolScanner(None)
        filtered = scanner.filter_results_by_type(results, filter_type)
    
    st.markdown(f"### Showing {len(filtered)} opportunities")
    
    # Display opportunities with better styling
    for r in filtered[:20]:
        if r.get('best_signal'):
            symbol = r['symbol']
            signal = r['best_signal']
            gex = r.get('gex_profile')
            
            confidence = signal.get('confidence', 0)
            dealer_pain = gex.get('dealer_pain', 0) if gex else 0
            
            # Determine card style based on signal type
            if signal.get('type') == 'SQUEEZE_PLAY':
                card_style = "squeeze-row"
            elif signal.get('type') == 'PREMIUM_SELLING':
                card_style = "premium-row"
            else:
                card_style = "wait-row"
            
            # Create expandable card for each opportunity
            with st.expander(f"{SIGNAL_EMOJIS.get(signal.get('type', 'WAIT'), '📊')} **{symbol}** - Confidence: {confidence:.0f}% | Pain: {dealer_pain:.0f}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    **Direction**: {signal.get('direction', 'N/A')}  
                    **Entry**: {signal.get('entry', 'N/A')}  
                    **Target**: {signal.get('target', 'N/A')}  
                    **Stop**: {signal.get('stop', 'N/A')}  
                    **Expected Move**: {signal.get('expected_move', 0):.1f}%  
                    **Time Horizon**: {signal.get('time_horizon', 'N/A')}  
                    
                    **Reasoning**: {signal.get('reasoning', 'No analysis available')}
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
                    
                    if st.button(f"Alert", key=f"alert_{symbol}"):
                        alert_msg = alert_manager.format_discord_alert(symbol, gex, signal)
                        if alert_manager.send_discord_alert(alert_msg):
                            st.success("Alert sent!")

def render_morning_report(self, analyzer):
    """Render morning market maker exploitation report"""
    st.markdown("""
    <div class="mm-pressure-map">
        <h2>☀️ Morning MM Exploitation Report</h2>
        <p style="color: white;">Top opportunities to profit from trapped market makers</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current time
    now = datetime.now()
    
    # Top 5 symbols with highest dealer pain
    st.subheader("🎯 Top 5 MM Vulnerability Targets")
    
    top_symbols = ['SPY', 'QQQ', 'IWM', 'AAPL', 'TSLA']  # Default symbols
    
    for i, symbol in enumerate(top_symbols, 1):
        with st.spinner(f"Analyzing {symbol}..."):
            options_data = analyzer.get_options_chain(symbol)
            if options_data:
                gex_profile = analyzer.calculate_gex_profile(options_data)
                if gex_profile:
                    dealer_pain = gex_profile.get('dealer_pain', 0)
                    net_gex = gex_profile.get('net_gex', 0)
                    
                    if dealer_pain > 70:
                        emoji = "🔥"
                        status = "TRAPPED - EXPLOIT NOW"
                    elif dealer_pain > 50:
                        emoji = "⚡"
                        status = "VULNERABLE"
                    else:
                        emoji = "✅"
                        status = "STABLE"
                    
                    st.markdown(f"""
                    **{i}. {emoji} {symbol}** - Pain Score: {dealer_pain:.0f}/100
                    - Net GEX: {net_gex/1e9:.2f}B
                    - Status: {status}
                    - Gamma Flip: ${gex_profile.get('gamma_flip', 0):.2f}
                    """)
    
    # Market events that affect MMs
    st.subheader("📰 MM-Impacting Events Today")
    
    events = [
        {"time": "8:30 AM", "event": "CPI Data", "impact": "HIGH", "note": "Volatility spike expected, MMs vulnerable"},
        {"time": "10:00 AM", "event": "Consumer Sentiment", "impact": "MEDIUM", "note": "Could trigger rehedging"},
        {"time": "2:00 PM", "event": "Fed Minutes", "impact": "HIGH", "note": "Major gamma exposure shifts likely"},
        {"time": "3:30 PM", "event": "MOC Imbalances", "impact": "MEDIUM", "note": "Watch for MM capitulation"}
    ]
    
    for event in events:
        impact_color = "🔴" if event['impact'] == "HIGH" else "🟡"
        st.markdown(f"""
        {impact_color} **{event['time']}** - {event['event']}
        - Impact: {event['impact']}
        - MM Note: {event['note']}
        """)
    
    # Key levels to watch
    st.subheader("🎯 Critical MM Defense Levels")
    
    st.info("""
    **SPY Key Levels:**
    - Call Wall: $450 (MMs defend here)
    - Gamma Flip: $445 (Regime change point)
    - Put Wall: $440 (Support level)
    
    **Strategy Today:**
    - Above flip: Sell premium to retail
    - Below flip: Buy protection, MMs scrambling
    - Near flip: Maximum volatility, best opportunities
    """)
