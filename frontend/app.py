"""
Live SQL Parser - Streamlit front end

Single-file UI. The search bar (typing + live voice dictation) is a small
custom component written in plain HTML/JS; it is generated next to this file
in a `_voice_bar/` folder on first run, so nothing extra needs installing.
The old `streamlit_mic_recorder` package is no longer required.
"""

import sys
import os
import io
import uuid
import importlib
from html import escape as esc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from sqlalchemy import inspect as sa_inspect
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Live SQL Parser",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# ------------------------------------------------------------------
# Backend imports. Hot reload is opt-in (set DEV_RELOAD=1) because
# reloading on every rerun is slow and breaks objects kept in session.
# ------------------------------------------------------------------
_import_error = None
try:
    import core.prompts
    import core.database
    import core.validator
    import core.agent

    if os.getenv("DEV_RELOAD") == "1":
        for _m in (core.prompts, core.database, core.validator, core.agent):
            importlib.reload(_m)

    from core.agent import SQLAgent
    from core.database import (
        DatabaseManager,
        get_default_db_manager,
        create_file_session_db,
        create_mysql_db_manager,
    )
    local_agent_available = True
except Exception as e:
    local_agent_available = False
    _import_error = e

if not local_agent_available:
    st.error(f"Could not load the query engine (`core` package): {_import_error}")
    st.stop()


def get_local_agent(db_manager: "DatabaseManager" = None):
    try:
        return SQLAgent(db_manager=db_manager)
    except Exception as e:
        st.session_state["agent_error"] = str(e)
        return None


def execute_agent_query(user_prompt: str, history=None, db_manager: "DatabaseManager" = None):
    agent = get_local_agent(db_manager=db_manager)
    if agent:
        import inspect as pyinspect
        params = pyinspect.signature(agent.run).parameters
        kwargs = {}
        if "history" in params:
            kwargs["history"] = history
        if "db_manager" in params:
            kwargs["db_manager"] = db_manager
        return agent.run(user_prompt, **kwargs)

    try:
        res = requests.post(
            f"{BACKEND_URL}/ask",
            json={"query": user_prompt, "history": history},
            timeout=30,
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    detail = st.session_state.get("agent_error")
    return {
        "success": False,
        "status": "error",
        "answer": "The query engine isn't reachable."
                  + (f" Details: {detail}" if detail else " Check that the backend is running."),
        "sql_query": None,
        "data": [],
    }


def format_sql(query: str, dialect: str = "sqlite") -> str:
    if not query:
        return ""
    try:
        import sqlglot
        glot_dialect = "mysql" if "mysql" in dialect.lower() else "sqlite"
        res = sqlglot.transpile(query, read=glot_dialect, write=glot_dialect, pretty=True)
        if res and res[0]:
            return res[0]
    except Exception:
        pass
    return query


# ------------------------------------------------------------------
# Search bar component: typing + live voice dictation
# ------------------------------------------------------------------
VOICE_BAR_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --rose:#f43f5e; --rose-deep:#e11d48; --ink:#0f172a; --muted:#64748b; }
  * { box-sizing:border-box; }
  html,body { margin:0; background:transparent; font-family:'Figtree',-apple-system,BlinkMacSystemFont,sans-serif; }
  body { padding:6px 8px 26px; }

  .bar {
    display:flex; align-items:center; gap:8px;
    background:rgba(255,255,255,.88);
    border:1.5px solid rgba(255,255,255,.95);
    border-radius:30px; padding:8px 8px 8px 22px;
    box-shadow:0 12px 30px rgba(148,163,184,.14), 0 2px 6px rgba(0,0,0,.03);
    transition:border-color .2s, box-shadow .2s, background .2s;
  }
  .bar:hover, .bar:focus-within {
    background:#fff; border-color:rgba(244,63,94,.45);
    box-shadow:0 16px 40px rgba(244,63,94,.16), 0 0 0 3px rgba(244,63,94,.09);
  }
  .bar.listening {
    background:#fff; border-color:var(--rose);
    box-shadow:0 16px 40px rgba(244,63,94,.2), 0 0 0 4px rgba(244,63,94,.1);
  }

  textarea {
    flex:1; min-width:0; resize:none; border:none; outline:none; background:transparent;
    font:500 1.04rem/1.45 'Figtree',sans-serif; color:var(--ink); caret-color:var(--rose);
    padding:9px 0; height:42px; max-height:120px; overflow-y:auto;
  }
  textarea::placeholder { color:#94a3b8; font-weight:400; }

  button { font-family:inherit; cursor:pointer; border:none; background:none; }
  button:focus-visible { outline:2px solid var(--rose); outline-offset:2px; }

  .icon {
    width:42px; height:42px; border-radius:50%; flex:none;
    display:flex; align-items:center; justify-content:center;
    color:#475569; background:#f1f5f9; transition:background .15s, color .15s, transform .15s;
  }
  .icon:hover { background:#e2e8f0; color:var(--ink); }
  .icon svg { width:19px; height:19px; }
  .icon.confirm { background:var(--rose); color:#fff; box-shadow:0 6px 16px rgba(244,63,94,.35); }
  .icon.confirm:hover { background:var(--rose-deep); color:#fff; transform:scale(1.04); }

  .lang {
    flex:none; font-size:.78rem; font-weight:700; color:#475569;
    padding:6px 10px; border-radius:999px; background:transparent; border:1px solid #e2e8f0;
  }
  .lang:hover { background:#f8fafc; color:var(--ink); }

  .send {
    flex:none; height:42px; padding:0 22px; border-radius:999px;
    background:linear-gradient(135deg,#f43f5e,#ec4899); color:#fff;
    font-weight:700; font-size:.92rem; box-shadow:0 6px 18px rgba(244,63,94,.32);
    transition:transform .15s, box-shadow .15s, opacity .15s;
  }
  .send:hover { transform:translateY(-1px); box-shadow:0 10px 22px rgba(244,63,94,.42); }
  .send:disabled { opacity:.45; cursor:default; transform:none; box-shadow:none; }

  /* live level bars, only while dictating */
  .wave { display:none; align-items:center; gap:3px; height:22px; flex:none; margin-left:-6px; }
  .wave i { width:3px; height:100%; border-radius:3px; background:var(--rose); transform-origin:center;
            animation:lvl 1s ease-in-out infinite; }
  .wave i:nth-child(2){animation-delay:.15s} .wave i:nth-child(3){animation-delay:.3s}
  .wave i:nth-child(4){animation-delay:.12s} .wave i:nth-child(5){animation-delay:.27s}
  @keyframes lvl { 0%,100%{transform:scaleY(.25)} 50%{transform:scaleY(1)} }
  @media (prefers-reduced-motion: reduce) { .wave i { animation:none; transform:scaleY(.6); } }

  .listening .wave { display:flex; }
  .listening .send, .listening #mic, .listening .lang, .listening #clear { display:none; }
  .bar:not(.listening) #cancel, .bar:not(.listening) #ok { display:none; }

  .hint { min-height:18px; margin:8px 0 0 22px; font-size:.82rem; color:var(--muted); font-weight:500; }
  .hint.err { color:var(--rose-deep); }

  @media (max-width:520px) { .lang { display:none; } .send { padding:0 16px; } }
</style></head>
<body>
  <div class="bar" id="bar">
    <div class="wave" id="wave"><i></i><i></i><i></i><i></i><i></i></div>
    <textarea id="q" rows="1" spellcheck="false"></textarea>
    <button class="icon" id="clear" type="button" title="Clear text" aria-label="Clear text" style="display:none;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
    </button>
    <button class="lang" id="lang" type="button" title="Dictation language">EN</button>
    <button class="icon" id="mic" type="button" title="Dictate" aria-label="Dictate">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2.5" width="6" height="11.5" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3.5"/></svg>
    </button>
    <button class="icon" id="cancel" type="button" title="Discard dictation (Esc)" aria-label="Discard dictation">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>
    <button class="icon confirm" id="ok" type="button" title="Done, keep this text (Enter)" aria-label="Done">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
    </button>
    <button class="send" id="send" type="button">Send</button>
  </div>
  <div class="hint" id="hint"></div>

<script>
  const $ = id => document.getElementById(id);
  const q = $('q'), bar = $('bar'), hint = $('hint'), mic = $('mic'), clearBtn = $('clear'), langBtn = $('lang'), sendBtn = $('send');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let lastPrefill = null, rec = null, want = false, base = '', committed = '', lang = 'en-IN';

  function post(type, data) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data || {}), '*');
  }
  function fit() { post('streamlit:setFrameHeight', { height: document.documentElement.scrollHeight }); }
  function autosize() {
    q.style.height = 'auto';
    q.style.height = Math.max(42, Math.min(q.scrollHeight, 120)) + 'px';
    sendBtn.disabled = !q.value.trim();
    if (clearBtn) {
      clearBtn.style.display = (!want && q.value.trim().length > 0) ? 'flex' : 'none';
    }
    fit();
  }
  function setHint(t, err) { hint.textContent = t || ''; hint.className = 'hint' + (err ? ' err' : ''); }

  function submit() {
    const t = q.value.trim();
    if (!t) return;
    post('streamlit:setComponentValue', {
      value: { text: t, id: Date.now() + '-' + Math.random().toString(36).slice(2) },
      dataType: 'json'
    });
  }

  function show(interim) {
    q.value = [base, committed.trim(), interim.trim()].filter(Boolean).join(' ');
    autosize();
    q.scrollTop = q.scrollHeight;
  }

  function startListening() {
    if (!SR) {
      setHint('Voice input requires a Chromium browser (Chrome, Edge, Brave).', true);
      return;
    }
    if (want) return;
    base = q.value.trim(); committed = ''; want = true;
    bar.classList.add('listening');
    setHint('Listening. Speak your question, then tap the tick when you are done.');
    rec = new SR();
    rec.lang = lang; rec.continuous = true; rec.interimResults = true;
    rec.onresult = e => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) committed += r[0].transcript + ' '; else interim += r[0].transcript;
      }
      show(interim);
    };
    rec.onerror = e => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        stopListening(false);
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const isHttps = window.location.protocol === 'https:';
        if (!isLocal && !isHttps) {
          setHint('Microphone requires localhost or HTTPS. Browsers block speech dictation on non-secure Wi-Fi IP addresses.', true);
        } else {
          setHint('Microphone is blocked. Allow mic access for this site in the browser address bar.', true);
        }
      } else if (e.error === 'audio-capture') {
        stopListening(false);
        setHint('No microphone found.', true);
      } else if (e.error === 'network') {
        stopListening(false);
        setHint('Speech service needs an internet connection.', true);
      }
    };
    rec.onend = () => { if (want) { try { rec.start(); } catch (_) {} } };
    try { rec.start(); } catch (_) {}
    q.focus();
  }

  function stopListening(keep) {
    want = false;
    if (rec) { rec.onresult = null; rec.onend = null; try { rec.stop(); } catch (_) {} }
    bar.classList.remove('listening');
    if (!keep) { q.value = base; }
    if (keep) setHint('');
    else if (!hint.classList.contains('err')) setHint('');
    autosize();
    q.focus();
  }

  mic.addEventListener('click', startListening);
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      q.value = '';
      base = '';
      committed = '';
      autosize();
      q.focus();
      post('streamlit:setComponentValue', {
        value: { text: '', id: 'clear-' + Date.now() },
        dataType: 'json'
      });
    });
  }
  $('ok').addEventListener('click', () => stopListening(true));
  $('cancel').addEventListener('click', () => stopListening(false));
  sendBtn.addEventListener('click', submit);
  langBtn.addEventListener('click', () => {
    lang = lang === 'en-IN' ? 'hi-IN' : 'en-IN';
    langBtn.textContent = lang === 'en-IN' ? 'EN' : 'हिं';
  });
  q.addEventListener('input', autosize);
  q.addEventListener('keydown', e => {
    if (e.key === 'Escape' && want) { e.preventDefault(); stopListening(false); }
    else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (want) stopListening(true); else submit();
    }
  });

  window.addEventListener('message', ev => {
    if (!ev.data || ev.data.type !== 'streamlit:render') return;
    const a = ev.data.args || {};
    q.placeholder = a.placeholder || 'Ask a question';
    if (a.prefill !== lastPrefill && !want) { q.value = a.prefill || ''; }
    lastPrefill = a.prefill;
    if (!SR) {
      mic.title = 'Voice recognition requires Chrome, Edge, or Brave browser';
      mic.style.opacity = '0.4';
      mic.style.cursor = 'not-allowed';
      langBtn.style.display = 'none';
    }
    autosize();
  });
  new ResizeObserver(fit).observe(document.body);
  post('streamlit:componentReady', { apiVersion: 1 });
  autosize();
</script>
</body></html>
"""

_COMP_DIR = Path(__file__).resolve().parent / "_voice_bar"
_COMP_DIR.mkdir(exist_ok=True)
_comp_file = _COMP_DIR / "index.html"
if not _comp_file.exists() or _comp_file.read_text(encoding="utf-8") != VOICE_BAR_HTML:
    _comp_file.write_text(VOICE_BAR_HTML, encoding="utf-8")

query_bar = components.declare_component("sql_query_bar", path=str(_COMP_DIR))

# ------------------------------------------------------------------
# Styles (page background unchanged)
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

:root, [data-testid="stAppViewContainer"], html, body {
    color-scheme: light !important;
    --text-color: #0f172a !important;
    --background-color: #fbfbfe !important;
}

html, body, [data-testid="stAppViewContainer"], .main {
    font-family: 'Figtree', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: radial-gradient(at 10% 20%, #ffe8ec 0px, transparent 55%),
                radial-gradient(at 90% 15%, #e8f0fe 0px, transparent 50%),
                radial-gradient(at 50% 85%, #fff1f5 0px, transparent 60%),
                radial-gradient(at 85% 90%, #f0fdf4 0px, transparent 45%),
                #fafafc !important;
    color: #0f172a !important;
}

#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; }
header[data-testid="stHeader"] { background: transparent !important; color: #0f172a !important; height: 2.5rem !important; }
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important; visibility: visible !important; color: #0f172a !important;
    background: rgba(255,255,255,.95) !important; border-radius: 999px !important;
    box-shadow: 0 4px 14px rgba(0,0,0,.08) !important; border: 1px solid rgba(226,232,240,.9) !important;
    z-index: 999999 !important;
}

.block-container { max-width: 920px !important; padding-top: 1.8rem !important; padding-bottom: 3.5rem !important; }

/* Brand */
.brand-capsule {
    display: inline-flex; align-items: center; gap: 9px;
    background: rgba(255,255,255,.85); backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,.95); padding: 8px 18px; border-radius: 999px;
    box-shadow: 0 4px 16px rgba(0,0,0,.04);
}
.brand-sparkle { font-size: 1.05rem; color: #f43f5e; font-weight: 800; }
.brand-title { font-weight: 700; font-size: .95rem; color: #0f172a; letter-spacing: -.01em; }

/* Hero */
.hero { padding: 2.2rem 0 1.4rem 0; }
.hero h1 {
    font-family: 'Fraunces', Georgia, serif !important;
    font-size: 3rem; font-weight: 700; line-height: 1.08; letter-spacing: -.025em;
    color: #0f172a; margin: 0 0 .85rem 0; padding: 0; max-width: 640px;
}
.hero p { font-size: 1.06rem; line-height: 1.6; color: #475569; font-weight: 500; max-width: 600px; margin: 0 0 1.3rem 0; }
.source-line { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: .88rem; color: #334155; font-weight: 600; }
.source-line .live { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; }
.dialect-badge {
    background: rgba(99,102,241,.1); color: #4f46e5; font-weight: 700; font-size: .75rem;
    padding: 3px 9px; border-radius: 6px; border: 1px solid rgba(99,102,241,.25);
}
.source-line .sep { color: #cbd5e1; }

/* Buttons / chips */
.stButton button {
    background: rgba(255,255,255,.72) !important; backdrop-filter: blur(14px) !important;
    border: 1px solid rgba(255,255,255,.95) !important; color: #334155 !important;
    font-weight: 600 !important; font-size: .85rem !important; border-radius: 999px !important;
    padding: 7px 16px !important; box-shadow: 0 4px 12px rgba(148,163,184,.07) !important;
    transition: all .2s ease !important;
}
.stButton button:hover {
    background: #fff !important; color: #0f172a !important; border-color: rgba(244,63,94,.35) !important;
    transform: translateY(-1px) !important; box-shadow: 0 8px 18px rgba(244,63,94,.13) !important;
}

/* Popover + tabs */
[data-testid="stPopoverBody"] {
    background: #fff !important; border: 1px solid rgba(226,232,240,.95) !important;
    border-radius: 20px !important; padding: 20px !important;
    box-shadow: 0 25px 60px rgba(148,163,184,.2) !important; color: #0f172a !important;
}
button[data-baseweb="tab"] {
    background: #f1f5f9 !important; color: #0f172a !important; font-weight: 700 !important;
    font-size: .88rem !important; border-radius: 999px !important; padding: 8px 18px !important;
    border: 1px solid #e2e8f0 !important; margin-right: 6px !important; opacity: 1 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg,#f43f5e,#ec4899) !important; color: #fff !important;
    border: none !important; box-shadow: 0 4px 12px rgba(244,63,94,.3) !important;
}
button[data-baseweb="tab"]:hover { background: #e2e8f0 !important; }
button[data-baseweb="tab"][aria-selected="true"]:hover { background: linear-gradient(135deg,#f43f5e,#ec4899) !important; }

[data-testid="stDataFrame"], div[data-testid="stTable"] {
    background: #fff !important; border-radius: 14px !important; border: 1px solid #e2e8f0 !important; overflow: hidden !important;
}

/* Result card (top level only, so nested cards stay flat) */
.main div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,.8) !important; backdrop-filter: blur(28px) !important;
    border: 1px solid rgba(255,255,255,.95) !important; border-radius: 24px !important;
    padding: 18px 22px !important; box-shadow: 0 15px 35px rgba(148,163,184,.12) !important;
    margin-top: 1.2rem !important;
}
.main div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(248,250,252,.85) !important; border-radius: 16px !important;
    box-shadow: none !important; margin-top: .6rem !important; padding: 14px 16px !important;
    border: 1px solid #e2e8f0 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,.75) !important; backdrop-filter: blur(28px) !important;
    border-right: 1px solid rgba(226,232,240,.85) !important;
}
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,.8) !important; border-radius: 14px !important;
    border: 1.5px dashed #cbd5e1 !important; padding: 10px !important;
}

/* Answer + steps */
.answer-box { border-left: 4px solid #f43f5e; background: rgba(244,63,94,.05); border-radius: 14px; padding: 14px 18px; margin-bottom: 16px; }
.answer-label { font-weight: 700; color: #e11d48; font-size: .86rem; margin-bottom: 4px; }
.answer-text { color: #0f172a; font-size: 1.04rem; line-height: 1.55; font-weight: 500; }
.step-line { background: rgba(241,245,249,.75); border-left: 3px solid #6366f1; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; font-size: .9rem; color: #0f172a; font-weight: 500; }

.schema-col-wrap { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 10px; }
.col-chip { background: #f8fafc; color: #1e293b; border: 1px solid #e2e8f0; padding: 4px 11px; border-radius: 8px; font-size: .83rem; font-weight: 600; }
.small-muted { font-size: .82rem; color: #64748b; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------
_defaults = {
    "query_input": "", "auto_run": False, "last_result": None, "chat_history": [],
    "active_source": "college", "uploaded_db": None, "mysql_db": None,
    "last_bar_id": None, "sid": uuid.uuid4().hex[:10],
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)


def reset_conversation():
    st.session_state["chat_history"] = []
    st.session_state["last_result"] = None
    st.session_state["query_input"] = ""
    try:
        agent = get_local_agent(db_manager=get_active_db())
        if agent and hasattr(agent, "clear_memory"):
            agent.clear_memory()
    except Exception:
        pass


def get_active_db():
    src = st.session_state.get("active_source", "college")
    if src == "upload" and st.session_state.get("uploaded_db"):
        return st.session_state["uploaded_db"]
    if src == "mysql" and st.session_state.get("mysql_db"):
        return st.session_state["mysql_db"]
    return get_default_db_manager()


def ask(text: str):
    st.session_state["query_input"] = text
    st.session_state["auto_run"] = True
    st.rerun()


def render_database_source_selector(key_prefix="main"):
    tab_demo, tab_upload, tab_mysql = st.tabs(["College demo", "Upload files", "MySQL"])

    with tab_demo:
        st.markdown("<div style='font-size:.92rem; font-weight:700; color:#1e293b; margin-top:6px;'>College demo (SQLite)</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-muted' style='margin-bottom:12px;'>Sample data with <code>students</code>, <code>departments</code> and <code>marks</code>.</div>", unsafe_allow_html=True)
        if st.session_state.get("active_source") == "college":
            st.success("This is the active database.")
        elif st.button("Use the college demo", key=f"{key_prefix}_switch_college", width="stretch"):
            st.session_state["active_source"] = "college"
            reset_conversation()
            st.rerun()

    with tab_upload:
        st.markdown("<div style='font-size:.92rem; font-weight:700; color:#1e293b; margin-top:6px;'>Bring your own tables</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-muted' style='margin-bottom:10px;'>Drop in CSV or Excel files. Each file (or sheet) becomes a table, kept in memory for this session only.</div>", unsafe_allow_html=True)
        up_files = st.file_uploader(
            "Choose CSV or Excel files", type=["csv", "xlsx", "xls"],
            accept_multiple_files=True, key=f"{key_prefix}_file_uploader", label_visibility="collapsed",
        )
        if up_files:
            if st.button(f"Load {len(up_files)} file(s)", key=f"{key_prefix}_ingest_btn", width="stretch"):
                with st.spinner("Building tables..."):
                    files_dict = {}
                    for uf in up_files:
                        try:
                            lower = uf.name.lower()
                            if lower.endswith(".csv"):
                                try:
                                    df = pd.read_csv(uf, encoding="utf-8", encoding_errors="replace")
                                except Exception:
                                    uf.seek(0)
                                    df = pd.read_csv(uf, encoding="latin1", encoding_errors="replace")
                                files_dict[uf.name] = df
                            else:
                                xl = pd.ExcelFile(uf, engine="openpyxl")
                                if len(xl.sheet_names) == 1:
                                    files_dict[uf.name] = pd.read_excel(uf, sheet_name=xl.sheet_names[0], engine="openpyxl")
                                else:
                                    stem = Path(uf.name).stem
                                    for s in xl.sheet_names:
                                        files_dict[f"{stem}_{s}"] = pd.read_excel(uf, sheet_name=s, engine="openpyxl")
                        except Exception as err:
                            st.error(f"Couldn't read {uf.name}: {err}")
                    if files_dict:
                        st.session_state["uploaded_db"] = create_file_session_db(
                            files_dict, session_id=f"user_{st.session_state['sid']}"
                        )
                        st.session_state["active_source"] = "upload"
                        reset_conversation()
                        st.toast("Tables loaded.")
                        st.rerun()
        if st.session_state.get("active_source") == "upload" and st.session_state.get("uploaded_db"):
            st.success(f"Active: {st.session_state['uploaded_db'].name}")
            if st.button("Reset to College Demo", key=f"{key_prefix}_clear_uploaded", width="stretch"):
                st.session_state["uploaded_db"] = None
                st.session_state["active_source"] = "college"
                reset_conversation()
                st.rerun()

    with tab_mysql:
        st.markdown("<div style='font-size:.92rem; font-weight:700; color:#1e293b; margin-top:6px;'>Connect to MySQL</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-muted' style='margin-bottom:8px;'>Connections run in read-only mode.</div>", unsafe_allow_html=True)
        with st.form(f"{key_prefix}_mysql_form"):
            m_host = st.text_input("Host", value="localhost", key=f"{key_prefix}_mhost")
            m_port = st.number_input("Port", value=3306, step=1, format="%d", key=f"{key_prefix}_mport")
            m_user = st.text_input("User", value="root", key=f"{key_prefix}_muser")
            m_pass = st.text_input("Password", type="password", key=f"{key_prefix}_mpass")
            m_db = st.text_input("Database name", placeholder="e.g. ecommerce", key=f"{key_prefix}_mdb")
            m_submit = st.form_submit_button("Connect", width="stretch")
            if m_submit:
                if not m_db.strip():
                    st.error("Enter a database name.")
                else:
                    clean_host = m_host.strip()
                    if clean_host.startswith("localhost") and len(clean_host) > 9 and not clean_host.startswith("localhost:"):
                        clean_host = clean_host[9:].strip()
                    for prefix in ("https://", "http://"):
                        if clean_host.startswith(prefix):
                            clean_host = clean_host[len(prefix):].strip()
                    with st.spinner(f"Connecting to {m_db}..."):
                        ok, mgr, msg = create_mysql_db_manager(
                            host=clean_host, port=int(m_port), user=m_user.strip(),
                            password=m_pass, dbname=m_db.strip(),
                        )
                        if ok and mgr:
                            st.session_state["mysql_db"] = mgr
                            st.session_state["active_source"] = "mysql"
                            reset_conversation()
                            st.toast("Connected to MySQL.")
                            st.rerun()
                        else:
                            st.error(msg)
        if st.session_state.get("active_source") == "mysql" and st.session_state.get("mysql_db"):
            st.success(f"Active: {st.session_state['mysql_db'].name}")
            if st.button("Disconnect MySQL", key=f"{key_prefix}_disconnect_mysql", width="stretch"):
                st.session_state["mysql_db"] = None
                st.session_state["active_source"] = "college"
                reset_conversation()
                st.rerun()


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='margin:0 0 2px 0; color:#0f172a;'>Data sources</h3>", unsafe_allow_html=True)
    st.markdown("<p class='small-muted' style='margin-bottom:14px;'>Pick where your questions should run.</p>", unsafe_allow_html=True)
    render_database_source_selector(key_prefix="sidebar")

active_db = get_active_db()
active_name = active_db.name
active_dialect = active_db.get_db_dialect().upper()
tables_found = active_db.get_table_names()
current_source = st.session_state.get("active_source", "college")

# ------------------------------------------------------------------
# Top row: Brand & Database Controls
# ------------------------------------------------------------------
n_tables = len(tables_found)
top_c1, top_c2, top_c3 = st.columns([1.3, 1.1, 1.1])
with top_c1:
    st.markdown('<div class="brand-capsule"><span class="brand-sparkle">✦</span><span class="brand-title">Live SQL Parser</span></div>', unsafe_allow_html=True)
with top_c2:
    with st.popover(f"📂 {active_name}", width="stretch"):
        st.markdown("<h4 style='margin-top:0; color:#0f172a;'>Switch database</h4>", unsafe_allow_html=True)
        render_database_source_selector(key_prefix="main_nav")
with top_c3:
    with st.popover(f"🔍 Browse tables ({n_tables})", width="stretch"):
        st.markdown(f"<h3 style='margin-top:0; color:#0f172a;'>{esc(str(active_name))}</h3>", unsafe_allow_html=True)
        if not tables_found:
            st.info("This database has no tables yet. Upload a CSV or Excel file, or connect MySQL, from the sidebar.")
        else:
            shown = tables_found[:6]
            extra = n_tables - len(shown)
            st.markdown(f"<p class='small-muted'>{n_tables} table(s)" + (f", showing the first {len(shown)}" if extra > 0 else "") + ".</p>", unsafe_allow_html=True)
            tabs = st.tabs([t.title().replace("_", " ") for t in shown])
            for tab, t_name in zip(tabs, shown):
                with tab:
                    res_p = active_db.preview_table(t_name, limit=5)
                    if res_p["success"]:
                        cols_str = ", ".join(f"<code>{esc(str(c))}</code>" for c in res_p["columns"][:8])
                        st.markdown(f"<div class='small-muted' style='margin-bottom:8px;'>Columns: {cols_str}</div>", unsafe_allow_html=True)
                        st.dataframe(pd.DataFrame(res_p["rows"]), width="stretch")
                    else:
                        st.warning(f"Couldn't preview {t_name}: {res_p.get('error')}")

# ------------------------------------------------------------------
# Hero
# ------------------------------------------------------------------
st.markdown(f"""
<div class="hero">
    <h1>Ask your database anything.</h1>
    <p>Write your question in plain English or Hindi. You get an immediate answer, full data rows, and verified SQL.</p>
    <div class="source-line">
        <span class="live"></span>
        <span>Connected to <strong>{esc(str(active_name))}</strong></span>
        <span class="dialect-badge">{esc(active_dialect)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Quick questions
# ------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

if current_source == "college":
    chips = [
        ("Student (Roll 5)", "Show student with roll number 5 and his marks"),
        ("Top 3 Students", "Show top 3 students with highest marks"),
        ("Computer Science", "List all students in Computer Science department"),
        ("Subject Averages", "Show average marks for each subject"),
    ]
else:
    t1 = tables_found[0] if tables_found else "table"
    t2 = tables_found[1] if len(tables_found) > 1 else t1
    chips = [
        (f"Top rows: {t1[:12]}", f"Show top 5 records from {t1}"),
        (f"Count: {t1[:12]}", f"Count the total number of records in {t1}"),
        (f"Sample: {t2[:12]}", f"Show 5 sample rows from {t2}"),
        ("Schema Overview", "What tables and columns exist in this database?"),
    ]
for col, (label, prompt) in zip((c1, c2, c3, c4), chips):
    with col:
        if st.button(label, width="stretch", key=f"chip_{label}"):
            ask(prompt)

# ------------------------------------------------------------------
# Conversation context
# ------------------------------------------------------------------
if st.session_state["chat_history"]:
    col_mem, col_rst = st.columns([4, 1.2])
    with col_mem:
        n = len(st.session_state["chat_history"])
        st.markdown(
            f"<div class='small-muted' style='padding:8px 0 4px 6px; font-size:.85rem;'>"
            f"Remembering {n} earlier turn{'s' if n != 1 else ''}, so you can follow up with things like "
            f"<em>show their marks</em> or <em>only the top ten</em>.</div>",
            unsafe_allow_html=True,
        )
    with col_rst:
        if st.button("Start fresh", key="clear_ctx", width="stretch"):
            reset_conversation()
            agent = get_local_agent(db_manager=active_db)
            if agent:
                agent.clear_memory()
            st.rerun()

    with st.expander(f"Recent questions ({len(st.session_state['chat_history'])})", expanded=False):
        for h_idx, h in enumerate(reversed(st.session_state["chat_history"])):
            q_num = len(st.session_state["chat_history"]) - h_idx
            q_text = h.get("user", "")
            q_summary = h.get("summary", "")
            hq1, hq2 = st.columns([4, 1.2])
            with hq1:
                st.markdown(f"**Q{q_num}:** {esc(q_text)}")
                if q_summary:
                    st.markdown(f"<div class='small-muted' style='margin-bottom:6px;'>{esc(q_summary)}</div>", unsafe_allow_html=True)
            with hq2:
                if st.button("↺ Ask again", key=f"reask_{h_idx}_{q_num}", width="stretch"):
                    ask(q_text)
            if h_idx < len(st.session_state["chat_history"]) - 1:
                st.markdown("<hr style='margin:4px 0 8px 0; border:none; border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Search bar (type or dictate)
# ------------------------------------------------------------------
payload = query_bar(
    prefill=st.session_state["query_input"],
    placeholder=f"Ask about {active_name}, or tap the mic and say it",
    key="sql_query_bar",
    default=None,
)
if payload and payload.get("id") != st.session_state["last_bar_id"]:
    st.session_state["last_bar_id"] = payload["id"]
    st.session_state["query_input"] = payload["text"]
    if payload.get("text", "").strip():
        st.session_state["auto_run"] = True
    else:
        st.session_state["auto_run"] = False

# ------------------------------------------------------------------
# Run query
# ------------------------------------------------------------------
if st.session_state.get("auto_run") and st.session_state["query_input"].strip():
    st.session_state["auto_run"] = False
    active_query = st.session_state["query_input"].strip()
    with st.spinner("Working on it..."):
        import time
        t0 = time.time()
        res = execute_agent_query(active_query, history=st.session_state["chat_history"], db_manager=active_db)
        res["execution_time"] = round(time.time() - t0, 2)
        st.session_state["last_result"] = res
        if res.get("success"):
            st.session_state["chat_history"] = res.get("history", st.session_state["chat_history"])

# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------
result = st.session_state.get("last_result")
if result:
    status = result.get("status")
    answer = result.get("answer", "") or ""
    sql = result.get("sql_query")
    data = result.get("data", [])
    exec_time = result.get("execution_time")

    with st.container(border=True):
        if status == "out_of_scope":
            st.warning(answer)
        elif status == "security_violation":
            st.error(f"🛡️ Guardrail Blocked: {answer}")
            st.caption("Only safe, read-only queries (SELECT) are permitted. Table alterations or mutations are restricted.")
        elif not result.get("success"):
            st.error(answer)
        elif status == "schema_info":
            st.markdown(
                f"<div class='answer-box'><div class='answer-label'>About this database</div>"
                f"<div class='answer-text'>{esc(answer)}</div></div>",
                unsafe_allow_html=True,
            )
            tables_info = result.get("tables_info")
            if not tables_info:
                try:
                    insp = sa_inspect(active_db.engine)
                    tables_info = [{"name": t, "columns": [c["name"] for c in insp.get_columns(t)]} for t in active_db.get_table_names()]
                except Exception:
                    tables_info = []

            for t_idx, t_data in enumerate(tables_info or []):
                t_name, t_cols = t_data["name"], t_data["columns"]
                with st.container(border=True):
                    h1, h2 = st.columns([3, 1])
                    with h1:
                        st.markdown(f"<div style='font-weight:700; font-size:1.05rem; color:#0f172a;'><code>{esc(str(t_name))}</code></div>", unsafe_allow_html=True)
                    with h2:
                        st.markdown(f"<div class='small-muted' style='text-align:right; font-weight:600;'>{len(t_cols)} columns</div>", unsafe_allow_html=True)
                    chips_html = "".join(f"<span class='col-chip'>{esc(str(c))}</span>" for c in t_cols)
                    st.markdown(f"<div class='schema-col-wrap'>{chips_html}</div>", unsafe_allow_html=True)

                    s1, s2, s3 = st.columns(3)
                    with s1:
                        if st.button("First 5 rows", key=f"sq_top_{t_name}_{t_idx}", width="stretch"):
                            ask(f"Show top 5 records from {t_name}")
                    with s2:
                        num_cols = [c for c in t_cols if any(k in c.lower() for k in ["price", "cost", "sold", "marks", "stock", "quantity", "amount", "salary"])]
                        if num_cols:
                            if st.button(f"Highest {num_cols[0][:10]}", key=f"sq_num_{t_name}_{t_idx}", width="stretch"):
                                ask(f"Show top 5 records with highest {num_cols[0]} in {t_name}")
                    with s3:
                        cat_cols = [c for c in t_cols if any(k in c.lower() for k in ["cat", "dept", "status", "type", "supplier", "gender"])]
                        if cat_cols:
                            if st.button(f"Group by {cat_cols[0][:10]}", key=f"sq_cat_{t_name}_{t_idx}", width="stretch"):
                                ask(f"Count total records grouped by {cat_cols[0]} in {t_name}")
                        elif st.button("Row count", key=f"sq_cnt_{t_name}_{t_idx}", width="stretch"):
                            ask(f"Count total records in {t_name}")
        else:
            # 1. Answer Box
            meta_pill = f" <span style='font-size:.78rem; font-weight:600; color:#64748b; margin-left:8px;'>• {exec_time}s</span>" if exec_time else ""
            st.markdown(
                f"<div class='answer-box'><div class='answer-label'>Answer{meta_pill}</div>"
                f"<div class='answer-text'>{esc(answer)}</div></div>",
                unsafe_allow_html=True,
            )

            # 2. Results Data Table (Directly below Answer)
            if data:
                df = pd.DataFrame(data)
                row_label = f"{len(df):,} row{'s' if len(df) != 1 else ''}"
                st.markdown(f"#### Results ({row_label})")
                st.dataframe(df, width="stretch")

                e1, e2 = st.columns(2)
                with e1:
                    st.download_button(
                        "Download CSV", data=df.to_csv(index=False).encode("utf-8"),
                        file_name="query_results.csv", mime="text/csv", width="stretch",
                    )
                with e2:
                    try:
                        buf = io.BytesIO()
                        df.to_excel(buf, index=False, engine="openpyxl")
                        st.download_button(
                            "Download Excel", data=buf.getvalue(), file_name="query_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch",
                        )
                    except Exception:
                        pass
            elif result.get("success"):
                st.info("The query ran fine but returned no rows. Try loosening a filter.")

            # 3. Bottom Expanders (Closed by default - exactly per user instruction)
            if sql:
                with st.expander("Show the SQL", expanded=False):
                    formatted_sql = format_sql(sql, dialect=active_dialect)
                    st.code(formatted_sql, language="sql")

            logic_steps = result.get("logic_steps") or []
            if logic_steps:
                with st.expander("How this query works", expanded=False):
                    for step_text in logic_steps:
                        st.markdown(f"<div class='step-line'>{esc(str(step_text))}</div>", unsafe_allow_html=True)