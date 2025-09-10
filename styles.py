"""
DealerEdge Visual Styling
Complete CSS for the professional trading interface
"""

DEALEREDGE_CSS = """
<style>
    /* === DEALEREDGE BRAND COLORS === */
    :root {
        --primary: #1e3c72;
        --secondary: #2a5298;
        --accent: #667eea;
        --success: #11998e;
        --danger: #ff0844;
        --warning: #ff9800;
        --dark: #0f0c29;
    }
    
    /* === GLOBAL STYLES === */
    .stApp {
        background: linear-gradient(135deg, var(--dark) 0%, var(--primary) 50%, var(--secondary) 100%);
        background-attachment: fixed;
    }
    
    .main {
        background-color: transparent !important;
    }
    
    /* === FIX FOR TEXT VISIBILITY === */
    .stMarkdown, .stText, p, span, div, label {
        color: #ffffff !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    /* Fix for expander text */
    .streamlit-expanderHeader {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Fix for all text in expanders */
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] div,
    [data-testid="stExpander"] label {
        color: #ffffff !important;
    }
    
    /* Fix selectbox text */
    [data-testid="stSelectbox"] label {
        color: #ffffff !important;
    }
    
    /* Fix input fields */
    input {
        color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Force consistent text colors on metrics */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: bold !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    [data-testid="stMetricLabel"] {
        color: #e0e0e0 !important;
        font-weight: 600 !important;
    }
    
    /* === DEALEREDGE HEADER === */
    .dealeredge-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 3rem;
        border-radius: 30px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        position: relative;
        overflow: hidden;
        border: 2px solid var(--accent);
    }
    
    .dealeredge-header::before {
        content: "DEALEREDGE";
        position: absolute;
        font-size: 150px;
        opacity: 0.03;
        font-weight: bold;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-15deg);
        white-space: nowrap;
    }
    
    .dealeredge-header h1 {
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradient-shift 3s ease infinite;
    }
    
    @keyframes gradient-shift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* === ACTION BOXES === */
    .action-box {
        background: linear-gradient(135deg, var(--accent) 0%, var(--warning) 100%);
        border-radius: 20px;
        padding: 2.5rem;
        color: white;
        text-align: center;
        margin: 1.5rem 0;
        font-size: 1.6rem;
        font-weight: bold;
        box-shadow: 0 10px 40px rgba(102,126,234,0.4);
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .action-box h1, .action-box p {
        color: white !important;
    }
    
    .action-box::after {
        content: "🎯";
        position: absolute;
        font-size: 100px;
        opacity: 0.1;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
    }
    
    .action-box:hover {
        transform: translateY(-8px) scale(1.03);
        box-shadow: 0 15px 50px rgba(102,126,234,0.6);
    }
    
    /* === MM STATUS STYLES === */
    .mm-trapped {
        background: linear-gradient(135deg, var(--danger), #ff4563) !important;
        animation: emergency-pulse 0.5s infinite;
    }
    
    @keyframes emergency-pulse {
        0%, 100% { 
            box-shadow: 0 0 30px rgba(255,8,68,0.8);
            transform: scale(1);
        }
        50% { 
            box-shadow: 0 0 50px rgba(255,8,68,1);
            transform: scale(1.02);
        }
    }
    
    .mm-defending {
        background: linear-gradient(135deg, var(--success), #38ef7d) !important;
    }
    
    .mm-scrambling {
        background: linear-gradient(135deg, var(--warning), #f7b733) !important;
        animation: warning-blink 1s infinite;
    }
    
    @keyframes warning-blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.85; }
    }
    
    /* === DEALEREDGE BUTTONS === */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent) 0%, var(--secondary) 100%);
        color: white !important;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        font-weight: bold;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102,126,234,0.6);
    }
    
    /* === METRIC CARDS === */
    .metric-card {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: all 0.3s;
        border: 1px solid rgba(102,126,234,0.2);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        border-color: var(--accent);
    }
    
    /* === WIN STREAK ANIMATION === */
    .win-streak {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #1a1a1a;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        display: inline-block;
        font-weight: bold;
        animation: streak-glow 2s infinite;
        box-shadow: 0 0 30px rgba(255,215,0,0.5);
    }
    
    @keyframes streak-glow {
        0%, 100% { 
            box-shadow: 0 0 30px rgba(255,215,0,0.5);
            transform: scale(1);
        }
        50% { 
            box-shadow: 0 0 50px rgba(255,215,0,0.8);
            transform: scale(1.05);
        }
    }
    
    /* === PRESSURE MAP === */
    .mm-pressure-map {
        background: linear-gradient(135deg, var(--dark), #302b63, #24243e);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        position: relative;
        border: 1px solid var(--accent);
    }
    
    .mm-pressure-map h2, .mm-pressure-map h3, .mm-pressure-map p {
        color: white !important;
    }
    
    .pressure-level {
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 10px;
        position: relative;
        transition: all 0.3s;
        color: white !important;
    }
    
    .pressure-level:hover {
        transform: scale(1.02);
    }
    
    .high-pressure {
        background: linear-gradient(90deg, rgba(255,0,0,0.3), rgba(255,0,0,0.1));
        border: 2px solid var(--danger);
        animation: pulse-red 2s infinite;
        box-shadow: 0 0 20px rgba(255,0,0,0.3);
    }
    
    @keyframes pulse-red {
        0%, 100% { 
            box-shadow: 0 0 20px rgba(255,0,0,0.3);
        }
        50% { 
            box-shadow: 0 0 40px rgba(255,0,0,0.6);
        }
    }
    
    .current-price {
        background: linear-gradient(90deg, rgba(255,215,0,0.5), rgba(255,215,0,0.2));
        border: 2px solid #ffd700;
        font-weight: bold;
        box-shadow: 0 0 30px rgba(255,215,0,0.4);
        animation: golden-glow 2s infinite;
    }
    
    @keyframes golden-glow {
        0%, 100% { 
            box-shadow: 0 0 30px rgba(255,215,0,0.4);
        }
        50% { 
            box-shadow: 0 0 50px rgba(255,215,0,0.7);
        }
    }
    
    .low-pressure {
        background: linear-gradient(90deg, rgba(0,255,0,0.3), rgba(0,255,0,0.1));
        border: 2px solid var(--success);
        box-shadow: 0 0 20px rgba(0,255,0,0.3);
    }
    
    /* === SCROLLBAR STYLING === */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--accent), var(--secondary));
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, var(--secondary), var(--accent));
    }
</style>
"""

def apply_custom_css():
    """Apply the custom CSS to the Streamlit app"""
    import streamlit as st
    st.markdown(DEALEREDGE_CSS, unsafe_allow_html=True)
