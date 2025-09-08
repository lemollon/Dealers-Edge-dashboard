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
    
    /* === BUTTONS === */
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
    
    /* === WIN STREAK === */
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
</style>
"""

def apply_custom_css():
    """Apply the custom CSS to the Streamlit app"""
    import streamlit as st
    st.markdown(DEALEREDGE_CSS, unsafe_allow_html=True)
