"""
Live SQL Parser - Luxury Glassmorphic UI
Matches modern high-end Dribbble AI design with translucent frosted glass,
zero dark-mode clashes, permanently visible table tabs, and interactive hover glow.
"""

import sys
import os
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import requests
from sqlalchemy import inspect
from dotenv import load_dotenv

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

# Page Config
st.set_page_config(
    page_title="Live SQL Parser",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

import io

# Import local agent & database engine with hot-reload support
import importlib
try:
    import core.prompts
    import core.database
    import core.validator
    import core.agent
    importlib.reload(core.prompts)
    importlib.reload(core.database)
    importlib.reload(core.validator)
    importlib.reload(core.agent)
    from core.agent import SQLAgent
    from core.database import (
        DatabaseManager,
        get_default_db_manager,
        create_file_session_db,
        create_mysql_db_manager,
        execute_query
    )
    local_agent_available = True
except Exception:
    local_agent_available = False

def get_local_agent(db_manager: DatabaseManager = None):
    """Returns a freshly reloaded SQLAgent instance with active db_manager."""
    if local_agent_available:
        try:
            return SQLAgent(db_manager=db_manager)
        except Exception:
            pass
    return None

def execute_agent_query(user_prompt: str, history=None, db_manager: DatabaseManager = None):
    """Executes query with multi-turn conversation history and dynamic db_manager support."""
    agent = get_local_agent(db_manager=db_manager)
    if agent:
        import inspect
        sig = inspect.signature(agent.run)
        kwargs = {}
        if "history" in sig.parameters:
            kwargs["history"] = history
        if "db_manager" in sig.parameters:
            kwargs["db_manager"] = db_manager
        return agent.run(user_prompt, **kwargs)

    try:
        res = requests.post(
            f"{BACKEND_URL}/ask",
            json={"query": user_prompt, "history": history},
            timeout=3
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
        
    return {
        "success": False,
        "status": "error",
        "answer": "Unable to connect to intelligence engine.",
        "sql_query": None,
        "data": []
    }

# ==========================================
# ADVANCED GLASSMORPHIC CSS (Zero-Black Theme)
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

/* Force Light Theme at CSS Level */
:root, [data-testid="stAppViewContainer"], html, body {
    color-scheme: light !important;
    --text-color: #0f172a !important;
    --background-color: #fbfbfe !important;
    --secondary-background-color: rgba(255, 255, 255, 0.7) !important;
}

html, body, [data-testid="stAppViewContainer"], .main {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: radial-gradient(at 10% 20%, #ffe8ec 0px, transparent 55%),
                radial-gradient(at 90% 15%, #e8f0fe 0px, transparent 50%),
                radial-gradient(at 50% 85%, #fff1f5 0px, transparent 60%),
                radial-gradient(at 85% 90%, #f0fdf4 0px, transparent 45%),
                #fafafc !important;
    color: #0f172a !important;
}

/* Hide Streamlit Default Chrome while keeping sidebar toggle button visible */
#MainMenu, footer, [data-testid="stToolbar"] {
    display: none !important;
    visibility: hidden !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
    color: #0f172a !important;
    height: 2.5rem !important;
}

[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    color: #0f172a !important;
    background: rgba(255, 255, 255, 0.95) !important;
    border-radius: 999px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08) !important;
    border: 1px solid rgba(226, 232, 240, 0.9) !important;
    z-index: 999999 !important;
}

/* App Container Layout */
.block-container {
    max-width: 920px !important;
    padding-top: 1.8rem !important;
    padding-bottom: 3.5rem !important;
}

/* ========================================== */
/* TOP NAVIGATION ROW                         */
/* ========================================== */
.nav-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.8rem;
}
.brand-capsule {
    display: flex;
    align-items: center;
    gap: 9px;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.95);
    padding: 8px 18px;
    border-radius: 999px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}
.brand-sparkle {
    font-size: 1.1rem;
    color: #f43f5e;
    font-weight: 800;
}
.brand-title {
    font-weight: 700;
    font-size: 0.95rem;
    color: #0f172a;
    letter-spacing: -0.01em;
}
.connect-pill {
    display: flex;
    align-items: center;
    gap: 7px;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.95);
    padding: 8px 18px;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #334155;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}
.connect-pill span.dot {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 10px #10b981;
}

/* ========================================== */
/* HERO SECTION & 3D FLOATING ORB (FIXED)     */
/* ========================================== */
.hero-fixed-wrapper {
    position: fixed;
    top: 65px;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: 920px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 0;
    pointer-events: none;
    text-align: center;
}

.hero-spacer {
    height: 235px;
    width: 100%;
    pointer-events: none;
}

/* Ensure scrolling content floats above fixed hero with frosted glass */
[data-testid="stForm"],
[data-testid="stVerticalBlockBorderWrapper"],
.stButton,
div[data-testid="stPopover"],
div[data-testid="stHorizontalBlock"] {
    position: relative !important;
    z-index: 5 !important;
}

/* Pinned Sticky Top Nav */
div[data-testid="stHorizontalBlock"]:first-of-type {
    position: sticky !important;
    top: 0 !important;
    z-index: 9999 !important;
    background: rgba(250, 250, 252, 0.9) !important;
    backdrop-filter: blur(20px) !important;
    padding-top: 6px !important;
    padding-bottom: 6px !important;
}

.hero-headline {
    text-align: center;
    font-size: 2.6rem;
    font-weight: 700;
    color: #64748b;
    line-height: 1.3;
    margin-bottom: 0.2rem;
    letter-spacing: -0.025em;
}
.hero-headline strong {
    color: #0f172a;
    font-weight: 800;
}

.orb-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 1.4rem 0 1.8rem 0;
}
.orb-sphere {
    width: 195px;
    height: 195px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, 
                rgba(255, 255, 255, 0.98) 0%, 
                rgba(255, 192, 203, 0.78) 25%, 
                rgba(244, 114, 182, 0.68) 45%, 
                rgba(167, 139, 250, 0.72) 70%, 
                rgba(56, 189, 248, 0.82) 100%);
    box-shadow: 0 25px 60px rgba(244, 114, 182, 0.3),
                0 10px 25px rgba(167, 139, 250, 0.22),
                inset 0 -15px 30px rgba(14, 165, 233, 0.5),
                inset 0 15px 30px rgba(255, 255, 255, 0.9);
    position: relative;
    animation: floatOrb 5s ease-in-out infinite;
}
.orb-reflection {
    width: 135px;
    height: 16px;
    background: radial-gradient(ellipse at center, rgba(167, 139, 250, 0.3) 0%, rgba(244, 114, 182, 0.15) 40%, transparent 70%);
    border-radius: 50%;
    margin-top: 22px;
    filter: blur(5px);
    animation: scaleShadow 5s ease-in-out infinite;
}

@keyframes floatOrb {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-12px) rotate(2deg); }
}
@keyframes scaleShadow {
    0%, 100% { transform: scale(1); opacity: 0.65; }
    50% { transform: scale(0.85); opacity: 0.35; }
}

/* ========================================== */
/* INPUT CAPSULE - ZERO BLACK, TRANSLUCENT   */
/* ========================================== */
[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.65) !important;
    backdrop-filter: blur(28px) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.95) !important;
    border-radius: 28px !important;
    padding: 10px 18px 10px 22px !important;
    box-shadow: 0 15px 35px rgba(148, 163, 184, 0.1), 
                0 2px 6px rgba(0, 0, 0, 0.02) !important;
    margin-top: 0.5rem !important;
    margin-bottom: 1.5rem !important;
    transition: all 0.25s ease-in-out !important;
}

/* Glowing Hover State on Input Container */
[data-testid="stForm"]:hover,
[data-testid="stForm"]:focus-within {
    background: rgba(255, 255, 255, 0.85) !important;
    border: 1.5px solid rgba(244, 63, 94, 0.45) !important;
    box-shadow: 0 18px 45px rgba(244, 63, 94, 0.18), 
                0 0 0 3px rgba(244, 63, 94, 0.1) !important;
}

/* Eradicate ALL Black Backgrounds on Inner Inputs */
[data-testid="stTextInput"],
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="input"] > div,
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* The actual text input field */
[data-testid="stTextInput"] input,
div[data-baseweb="input"] input,
input[type="text"] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    font-size: 1.05rem !important;
    font-weight: 500 !important;
    color: #0f172a !important; /* Pitch Dark Charcoal */
    caret-color: #f43f5e !important;
    padding: 9px 0px !important;
    box-shadow: none !important;
    outline: none !important;
}

input::placeholder {
    color: #94a3b8 !important;
    font-weight: 400 !important;
    opacity: 1 !important;
}

/* Send Button */
[data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #f43f5e 0%, #ec4899 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 10px 24px !important;
    font-size: 0.92rem !important;
    box-shadow: 0 6px 18px rgba(244, 63, 94, 0.35) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 24px rgba(244, 63, 94, 0.45) !important;
}

/* ========================================== */
/* QUICK PILL CHIPS & HOVER EFFECTS          */
/* ========================================== */
.stButton button {
    background: rgba(255, 255, 255, 0.72) !important;
    backdrop-filter: blur(14px) !important;
    border: 1px solid rgba(255, 255, 255, 0.95) !important;
    color: #334155 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    border-radius: 999px !important;
    padding: 7px 16px !important;
    box-shadow: 0 4px 12px rgba(148, 163, 184, 0.07) !important;
    transition: all 0.2s ease !important;
}
.stButton button:hover {
    background: #ffffff !important;
    color: #0f172a !important;
    border-color: rgba(244, 63, 94, 0.35) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 18px rgba(244, 63, 94, 0.15) !important;
}

/* ========================================== */
/* TABLE EXPLORER TABS - PERMANENT VISIBILITY*/
/* ========================================== */
[data-testid="stPopoverBody"] {
    background: #ffffff !important;
    border: 1px solid rgba(226, 232, 240, 0.95) !important;
    border-radius: 20px !important;
    padding: 20px !important;
    box-shadow: 0 25px 60px rgba(148, 163, 184, 0.2) !important;
    color: #0f172a !important;
}

/* Fix Tab Header Buttons - Crystal Clear Dark Text */
button[data-baseweb="tab"] {
    background: #f1f5f9 !important;
    color: #0f172a !important; /* Pitch Dark Text */
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border-radius: 999px !important;
    padding: 8px 18px !important;
    border: 1px solid #e2e8f0 !important;
    margin-right: 6px !important;
    opacity: 1 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #f43f5e, #ec4899) !important;
    color: #ffffff !important; /* White on Active Rose Tab */
    border: none !important;
    box-shadow: 0 4px 12px rgba(244, 63, 94, 0.3) !important;
}

button[data-baseweb="tab"]:hover {
    background: #e2e8f0 !important;
    color: #0f172a !important;
}

/* DataFrame Table Styling */
[data-testid="stDataFrame"], div[data-testid="stTable"] {
    background: #ffffff !important;
    border-radius: 14px !important;
    border: 1px solid #e2e8f0 !important;
    overflow: hidden !important;
}

/* Result Card Container */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(28px) !important;
    border: 1px solid rgba(255, 255, 255, 0.95) !important;
    border-radius: 24px !important;
    padding: 18px 22px !important;
    box-shadow: 0 15px 35px rgba(148, 163, 184, 0.12) !important;
    margin-top: 1.5rem !important;
}

/* Sidebar Glassmorphism */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.75) !important;
    backdrop-filter: blur(28px) !important;
    border-right: 1px solid rgba(226, 232, 240, 0.85) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(226, 232, 240, 0.8) !important;
}
[data-testid="stSidebar"] [data-testid="stForm"] {
    border-radius: 16px !important;
    padding: 12px 14px !important;
}
[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.8) !important;
    border-radius: 14px !important;
    border: 1.5px dashed #cbd5e1 !important;
    padding: 10px !important;
}

/* Column Chips & Schema Pills */
.schema-col-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    margin-bottom: 10px;
}
.col-chip {
    background: #f8fafc;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.83rem;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    transition: all 0.2s ease;
    display: inline-block;
}
.col-chip:hover {
    background: #ffffff;
    border-color: #f43f5e;
    color: #f43f5e;
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "auto_run" not in st.session_state:
    st.session_state["auto_run"] = False
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "active_source" not in st.session_state:
    st.session_state["active_source"] = "college"
if "uploaded_db" not in st.session_state:
    st.session_state["uploaded_db"] = None
if "mysql_db" not in st.session_state:
    st.session_state["mysql_db"] = None

def get_active_db() -> DatabaseManager:
    """Returns the currently active DatabaseManager based on user selection."""
    src = st.session_state.get("active_source", "college")
    if src == "upload" and st.session_state.get("uploaded_db"):
        return st.session_state["uploaded_db"]
    if src == "mysql" and st.session_state.get("mysql_db"):
        return st.session_state["mysql_db"]
    return get_default_db_manager()

def render_database_source_selector(key_prefix: str = "main"):
    """Renders the 3 data source switcher tabs (Demo DB, Upload CSV/Excel, Connect MySQL)."""
    tab_demo, tab_upload, tab_mysql = st.tabs(["🏛️ College Demo", "📁 Upload Files", "🐬 Connect MySQL"])

    # 1. College Demo DB
    with tab_demo:
        st.markdown("<div style='font-size:0.9rem; font-weight:700; color:#1e293b; margin-top:6px;'>College Demo DB (SQLite)</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem; color:#64748b; margin-bottom:12px;'>Pre-loaded tables: <code>students</code>, <code>departments</code>, <code>marks</code></div>", unsafe_allow_html=True)
        
        if st.session_state.get("active_source") == "college":
            st.success("🟢 Currently Active Database")
        else:
            if st.button("Switch to College DB", key=f"{key_prefix}_switch_college", use_container_width=True):
                st.session_state["active_source"] = "college"
                st.session_state["chat_history"] = []
                st.session_state["last_result"] = None
                st.session_state["query_input"] = ""
                st.rerun()

    # 2. Upload CSV / Excel
    with tab_upload:
        st.markdown("<div style='font-size:0.9rem; font-weight:700; color:#1e293b; margin-top:6px;'>Drag & Drop Custom Tables</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem; color:#64748b; margin-bottom:10px;'>Upload CSV or Excel files. Tables are created instantly in session memory.</div>", unsafe_allow_html=True)
        
        up_files = st.file_uploader(
            "Choose CSV/Excel files",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            key=f"{key_prefix}_file_uploader",
            label_visibility="collapsed"
        )
        if up_files:
            st.markdown(f"<div style='font-size:0.82rem; color:#475569; margin-bottom:8px;'>Selected: <strong>{len(up_files)} file(s)</strong></div>", unsafe_allow_html=True)
            if st.button("🚀 Ingest & Activate Tables", key=f"{key_prefix}_ingest_btn", use_container_width=True):
                with st.spinner("Processing tables into session database..."):
                    files_dict = {}
                    for uf in up_files:
                        try:
                            lower_name = uf.name.lower()
                            if lower_name.endswith(".csv"):
                                files_dict[uf.name] = pd.read_csv(uf)
                            elif lower_name.endswith((".xlsx", ".xls")):
                                excel_file = pd.ExcelFile(uf, engine="openpyxl")
                                if len(excel_file.sheet_names) == 1:
                                    files_dict[uf.name] = excel_file.parse(excel_file.sheet_names[0])
                                else:
                                    base_stem = Path(uf.name).stem
                                    for s_name in excel_file.sheet_names:
                                        tbl_key = f"{base_stem}_{s_name}"
                                        files_dict[tbl_key] = excel_file.parse(s_name)
                        except Exception as read_err:
                            st.error(f"Error reading {uf.name}: {read_err}")
                    
                    if files_dict:
                        new_db = create_file_session_db(files_dict, session_id="user_session")
                        st.session_state["uploaded_db"] = new_db
                        st.session_state["active_source"] = "upload"
                        st.session_state["chat_history"] = []
                        st.session_state["last_result"] = None
                        st.session_state["query_input"] = ""
                        st.toast("✅ Tables ingested and activated!", icon="🚀")
                        st.rerun()

        if st.session_state.get("active_source") == "upload" and st.session_state.get("uploaded_db"):
            st.success(f"🟢 Active: {st.session_state['uploaded_db'].name}")

    # 3. Connect MySQL
    with tab_mysql:
        st.markdown("<div style='font-size:0.9rem; font-weight:700; color:#1e293b; margin-top:6px;'>Connect MySQL Database</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem; color:#64748b; margin-bottom:8px;'>Read-only transaction mode is strictly enforced.</div>", unsafe_allow_html=True)
        
        with st.form(f"{key_prefix}_mysql_form"):
            m_host = st.text_input("Host", value="localhost", key=f"{key_prefix}_mhost")
            m_port = st.number_input("Port", value=3306, step=1, key=f"{key_prefix}_mport")
            m_user = st.text_input("User", value="root", key=f"{key_prefix}_muser")
            m_pass = st.text_input("Password", type="password", key=f"{key_prefix}_mpass")
            m_db = st.text_input("Database Name", placeholder="e.g. ecommerce", key=f"{key_prefix}_mdb")
            m_submit = st.form_submit_button("🔌 Test & Connect", use_container_width=True)

            if m_submit:
                if not m_db.strip():
                    st.error("Please provide a database name.")
                else:
                    with st.spinner(f"Connecting to MySQL '{m_db}'..."):
                        ok, mgr, msg = create_mysql_db_manager(
                            host=m_host.strip(),
                            port=int(m_port),
                            user=m_user.strip(),
                            password=m_pass,
                            dbname=m_db.strip()
                        )
                        if ok and mgr:
                            st.session_state["mysql_db"] = mgr
                            st.session_state["active_source"] = "mysql"
                            st.session_state["chat_history"] = []
                            st.session_state["last_result"] = None
                            st.session_state["query_input"] = ""
                            st.toast("✅ Connected to MySQL!", icon="🐬")
                            st.rerun()
                        else:
                            st.error(msg)

        if st.session_state.get("active_source") == "mysql" and st.session_state.get("mysql_db"):
            st.success(f"🟢 Active: {st.session_state['mysql_db'].name}")

# ==========================================
# RENDER SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<div style='display:flex; align-items:center; gap:8px; margin-bottom:2px;'><span style='font-size:1.3rem; color:#f43f5e;'>🗄️</span><h3 style='margin:0; color:#0f172a;'>Data Sources</h3></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.82rem; color:#64748b; margin-bottom:14px;'>Connect live databases or bring your own tables.</p>", unsafe_allow_html=True)
    render_database_source_selector(key_prefix="sidebar")

# Re-resolve active database
active_db = get_active_db()
active_name = active_db.name
active_dialect = active_db.get_db_dialect().upper()

# ==========================================
# FLOATING TOP NAV (Dual Capsule: Brand + Source Popover)
# ==========================================
top_c1, top_c2 = st.columns([1, 1.4])
with top_c1:
    st.markdown("""
    <div class="brand-capsule" style="display:inline-flex;">
        <span class="brand-sparkle">✦</span>
        <span class="brand-title">Live SQL Parser</span>
    </div>
    """, unsafe_allow_html=True)

with top_c2:
    with st.popover(f"🗄️ Database: {active_name} ({active_dialect}) ▾", use_container_width=True):
        st.markdown("<h4 style='margin-top:0; color:#0f172a;'>🗄️ Change Active Database Source</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:0.84rem; color:#64748b;'>Select between the default demo database, your uploaded CSV/Excel files, or a live MySQL server:</p>", unsafe_allow_html=True)
        render_database_source_selector(key_prefix="main_nav")

# ==========================================
# 3D FLOATING ORB (FIXED BACKGROUND STAGE)
# ==========================================
st.markdown("""<div class="hero-fixed-wrapper">
<div class="orb-stage">
<div class="orb-sphere"></div>
<div class="orb-reflection"></div>
</div>
</div>
<div class="hero-spacer"></div>""", unsafe_allow_html=True)

# ==========================================
# QUICK ACTION PILL CHIPS & VIEW TABLES POPOVER
# ==========================================
tables_found = active_db.get_table_names()
current_source = st.session_state.get("active_source", "college")

c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.1])

if current_source == "college":
    with c1:
        if st.button("⚡ Roll 5 Profile", use_container_width=True):
            st.session_state["query_input"] = "Show student with roll number 5 and his marks"
            st.session_state["auto_run"] = True
            st.rerun()
    with c2:
        if st.button("📈 Top 3 Students", use_container_width=True):
            st.session_state["query_input"] = "Show top 3 students with highest marks"
            st.session_state["auto_run"] = True
            st.rerun()
    with c3:
        if st.button("🏢 CS Department", use_container_width=True):
            st.session_state["query_input"] = "List all students in Computer Science department"
            st.session_state["auto_run"] = True
            st.rerun()
    with c4:
        if st.button("📊 Subject Averages", use_container_width=True):
            st.session_state["query_input"] = "Show average marks for each subject"
            st.session_state["auto_run"] = True
            st.rerun()
else:
    # Custom DB / Uploaded tables dynamic action chips
    t1 = tables_found[0] if len(tables_found) > 0 else "table"
    t2 = tables_found[1] if len(tables_found) > 1 else t1
    with c1:
        if st.button(f"🔍 Top in {t1[:10]}", use_container_width=True):
            st.session_state["query_input"] = f"Show top 5 records from {t1}"
            st.session_state["auto_run"] = True
            st.rerun()
    with c2:
        if st.button(f"🔢 Count {t1[:10]}", use_container_width=True):
            st.session_state["query_input"] = f"Count the total number of records in {t1}"
            st.session_state["auto_run"] = True
            st.rerun()
    with c3:
        if st.button(f"📊 Sample {t2[:10]}", use_container_width=True):
            st.session_state["query_input"] = f"Show 5 sample rows from {t2}"
            st.session_state["auto_run"] = True
            st.rerun()
    with c4:
        if st.button("🗂️ View Schema", use_container_width=True):
            st.session_state["query_input"] = "What tables and columns exist in this database?"
            st.session_state["auto_run"] = True
            st.rerun()

with c5:
    with st.popover("🗂️ View Tables", use_container_width=True):
        st.markdown(f"<h3 style='margin-top:0; color:#0f172a;'>📋 {active_name} Schema</h3>", unsafe_allow_html=True)
        if not tables_found:
            st.info("No tables detected in the active database. Upload a CSV/Excel or connect MySQL from the sidebar.")
        else:
            st.markdown(f"<p style='color:#64748b; font-size:0.88rem;'>Discovered <strong>{len(tables_found)} table(s)</strong> in active database:</p>", unsafe_allow_html=True)
            preview_tables = tables_found[:6]
            tabs = st.tabs([t.title().replace("_", " ") for t in preview_tables])
            for tab, t_name in zip(tabs, preview_tables):
                with tab:
                    res_p = active_db.preview_table(t_name, limit=5)
                    if res_p["success"]:
                        cols_str = " &bull; ".join(f"<code>{c}</code>" for c in res_p["columns"][:8])
                        st.markdown(f"<div style='margin-bottom:8px; font-size:0.83rem; color:#475569;'><strong>Columns:</strong> {cols_str}</div>", unsafe_allow_html=True)
                        st.dataframe(pd.DataFrame(res_p["rows"]), use_container_width=True)
                    else:
                        st.warning(f"Unable to preview {t_name}: {res_p.get('error')}")

# ==========================================
# CONVERSATION MEMORY INDICATOR & CONTROLS
# ==========================================
if st.session_state["chat_history"]:
    col_mem, col_rst = st.columns([4, 1.2])
    with col_mem:
        st.markdown(
            f"<div style='font-size:0.83rem; color:#475569; padding: 6px 0 4px 6px;'>"
            f"🧠 <strong>Conversation Context:</strong> <code>{len(st.session_state['chat_history'])} turn(s) active</code> &bull; "
            f"You can ask follow-up questions (e.g. <em>'show their marks'</em>, <em>'filter by category'</em>)</div>",
            unsafe_allow_html=True
        )
    with col_rst:
        if st.button("🧹 Reset Context", key="clear_ctx", use_container_width=True):
            st.session_state["chat_history"] = []
            st.session_state["last_result"] = None
            st.session_state["query_input"] = ""
            agent = get_local_agent(db_manager=active_db)
            if agent:
                agent.clear_memory()
            st.rerun()

# ==========================================
# TRANSLUCENT FLOATING SEARCH CAPSULE (Hover Glow)
# ==========================================
with st.form("search_form", clear_on_submit=False):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query_text = st.text_input(
            label="Inquiry",
            label_visibility="collapsed",
            value=st.session_state["query_input"],
            placeholder=f"Ask anything about {active_name}..."
        )
    with col_btn:
        submit_btn = st.form_submit_button("Send ↗", use_container_width=True)

# ==========================================
# RESULTS DISPLAY & PERSISTENCE
# ==========================================
run_query = False
active_query = ""

if submit_btn and query_text.strip():
    run_query = True
    active_query = query_text.strip()
elif st.session_state.get("auto_run", False) and st.session_state.get("query_input", "").strip():
    run_query = True
    active_query = st.session_state["query_input"].strip()
    st.session_state["auto_run"] = False

if run_query and active_query:
    with st.spinner("Analyzing inquiry with conversation context..."):
        res = execute_agent_query(active_query, history=st.session_state["chat_history"], db_manager=active_db)
        st.session_state["last_result"] = res
        if res.get("success"):
            st.session_state["chat_history"] = res.get("history", st.session_state["chat_history"])

result = st.session_state.get("last_result")
if result:
    status = result.get("status")
    answer = result.get("answer", "")
    sql = result.get("sql_query")
    data = result.get("data", [])

    with st.container(border=True):
        if status == "out_of_scope":
            st.warning(f"💡 {answer}")
        elif status == "security_violation":
            st.error(f"🛡️ {answer}")
        elif not result.get("success"):
            st.error(f"⚠️ {answer}")
        elif status == "schema_info":
            # Luxury Architecture & Schema Overview
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(244,63,94,0.06), rgba(168,85,247,0.05)); border-left: 4px solid #f43f5e; border-radius: 14px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="display:flex; align-items:center; gap:8px; font-weight:700; color:#e11d48; font-size:0.95rem; margin-bottom:6px;">
                    <span>📋 Database Architecture & Schema</span>
                </div>
                <div style="color:#0f172a; font-size:1.02rem; line-height:1.6; font-weight:500;">
                    {answer}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Structured Visual Cards for each table
            tables_info = result.get("tables_info")
            if not tables_info:
                try:
                    inspector = inspect(active_db.engine)
                    tables_info = [{"name": t, "columns": [c["name"] for c in inspector.get_columns(t)]} for t in active_db.get_table_names()]
                except Exception:
                    tables_info = []

            if tables_info:
                st.markdown("<h4 style='color:#0f172a; margin-top:10px; margin-bottom:8px;'>🗂️ Discovered Tables & Columns</h4>", unsafe_allow_html=True)
                for t_idx, t_data in enumerate(tables_info):
                    t_name = t_data["name"]
                    t_cols = t_data["columns"]
                    
                    with st.container(border=True):
                        col_h1, col_h2 = st.columns([3, 1])
                        with col_h1:
                            st.markdown(f"<div style='font-weight:700; font-size:1.05rem; color:#0f172a;'>📦 <code>{t_name}</code></div>", unsafe_allow_html=True)
                        with col_h2:
                            st.markdown(f"<div style='text-align:right; font-size:0.82rem; color:#64748b; font-weight:600;'>{len(t_cols)} Columns</div>", unsafe_allow_html=True)

                        chips_html = "".join([f"<span class='col-chip'>🏷️ {c}</span>" for c in t_cols])
                        st.markdown(f"<div class='schema-col-wrap'>{chips_html}</div>", unsafe_allow_html=True)

                        # Quick One-Click Interactive Inquiries
                        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
                        st.markdown("<div style='font-size:0.8rem; font-weight:700; color:#475569; margin-bottom:6px;'>⚡ Quick One-Click Inquiries:</div>", unsafe_allow_html=True)
                        
                        sq1_col, sq2_col, sq3_col = st.columns(3)
                        with sq1_col:
                            if st.button(f"🔍 Top 5 Records", key=f"sq_top_{t_name}_{t_idx}", use_container_width=True):
                                st.session_state["query_input"] = f"Show top 5 records from {t_name}"
                                st.session_state["auto_run"] = True
                                st.rerun()
                        with sq2_col:
                            num_cols = [c for c in t_cols if any(k in c.lower() for k in ["price", "cost", "sold", "marks", "stock", "quantity", "amount", "salary"])]
                            target_num = num_cols[0] if num_cols else t_cols[0]
                            if st.button(f"📈 Highest {target_num[:10]}", key=f"sq_num_{t_name}_{t_idx}", use_container_width=True):
                                st.session_state["query_input"] = f"Show top 5 records with highest {target_num} in {t_name}"
                                st.session_state["auto_run"] = True
                                st.rerun()
                        with sq3_col:
                            cat_cols = [c for c in t_cols if any(k in c.lower() for k in ["cat", "dept", "status", "type", "supplier", "gender"])]
                            if cat_cols:
                                target_cat = cat_cols[0]
                                if st.button(f"📊 By {target_cat[:10]}", key=f"sq_cat_{t_name}_{t_idx}", use_container_width=True):
                                    st.session_state["query_input"] = f"Count total records grouped by {target_cat} in {t_name}"
                                    st.session_state["auto_run"] = True
                                    st.rerun()
                            else:
                                if st.button(f"🔢 Total Count", key=f"sq_cnt_{t_name}_{t_idx}", use_container_width=True):
                                    st.session_state["query_input"] = f"Count total records in {t_name}"
                                    st.session_state["auto_run"] = True
                                    st.rerun()
        else:
            # Luxury Insight Card for Data Queries
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(244,63,94,0.06), rgba(236,72,153,0.04)); border-left: 4px solid #f43f5e; border-radius: 14px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="display:flex; align-items:center; gap:6px; font-weight:700; color:#e11d48; font-size:0.92rem; margin-bottom:4px;">
                    <span>✦ Insight</span>
                </div>
                <div style="color: #0f172a; font-size: 1.02rem; line-height: 1.5; font-weight: 500;">
                    {answer}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Expandable SQL Code
            if sql:
                with st.expander("🛠️ View Verified SQL Query", expanded=False):
                    st.code(sql, language="sql")
                    
            # Tabular View & Data Export
            if data:
                st.markdown("#### 📋 Data Records")
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

                # Export buttons
                col_exp1, col_exp2 = st.columns([1, 1])
                with col_exp1:
                    st.download_button(
                        label="📥 Download as CSV",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name="query_results.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col_exp2:
                    try:
                        excel_buf = io.BytesIO()
                        df.to_excel(excel_buf, index=False, engine="openpyxl")
                        st.download_button(
                            label="📊 Download as Excel (.xlsx)",
                            data=excel_buf.getvalue(),
                            file_name="query_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except Exception:
                        pass
