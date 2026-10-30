# Autonomous Text-to-SQL AI Agent

An enterprise-ready **Natural Language to SQL (Text-to-SQL)** AI engine built with **Python, FastAPI, SQLAlchemy, Google Gemini, and Streamlit**. It translates natural language questions into secure, optimized SQL queries with automated dynamic schema extraction, safety AST guardrails, self-healing error correction, and multi-format result visualization.

---

## 🌟 Key Features

1. **Dynamic Schema-Grounding**: Uses SQLAlchemy to inspect database tables, columns, and foreign keys at runtime—eliminating hardcoded schemas and hallucinated columns.
2. **Relevance & Intent Gatekeeper**: Pre-generation check that detects out-of-scope inquiries (e.g. general knowledge, sports) and safely rejects them before querying the database.
3. **AST Safety Guardrail**: Evaluates queries with `sqlglot` to enforce strictly read-only `SELECT` queries, instantly blocking `DROP`, `DELETE`, `UPDATE`, and multi-statement injections.
4. **Self-Healing Execution Loop**: Automatically captures SQL execution errors (syntax errors, column mismatches) and feeds them back to the LLM to auto-correct and retry without crashing.
5. **Decoupled Architecture**: Built as a microservice with a **FastAPI backend** and an interactive **Streamlit frontend**.

---

## 🏗️ Architecture

```
User Inquiry ("Roll no 5 ka data do")
        │
        ▼
   Streamlit UI
        │ (HTTP POST /ask)
        ▼
  FastAPI Gateway
        │
 ┌──────┴─────────────────────────────────────────────┐
 │  AI Agent Pipeline                                 │
 │  1. Schema Extractor (SQLAlchemy inspect)          │
 │  2. Gatekeeper (Intent & Out-of-Scope Filter)      │
 │  3. SQL Generator (Dialect-Specific Prompt)        │
 │  4. Safety Guardrail (sqlglot AST validation)      │
 │  5. Database Executor (SQLite / MySQL)             │
 │  6. Self-Correction Loop (Feedback retry on error) │
 │  7. Natural Language Explainer & Insight Engine    │
 └──────┬─────────────────────────────────────────────┘
        ▼
  Structured Response: Natural Language Summary + SQL Code + Data Table + Chart
```

---

## 🚀 Quickstart Guide

### 1. Clone & Setup Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Copy `.env.example` to `.env` and insert your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///data/college.db
```

### 4. Initialize Database
```bash
python data/seed_db.py
```

### 5. Run the Application
You can run both or either of the following:

**Option A: Run Streamlit Directly (Auto-loads local agent)**
```bash
streamlit run frontend/app.py
```

**Option B: Run Full Microservices (FastAPI + Streamlit)**
* Terminal 1 (Backend API):
  ```bash
  uvicorn backend.main:app --reload --port 8000
  ```
* Terminal 2 (Frontend UI):
  ```bash
  streamlit run frontend/app.py
  ```

---

## 📁 Project Structure

```
SQLQueryParser/
├── .env.example              # Configuration template
├── README.md                 # Complete documentation
├── requirements.txt          # Python dependencies
│
├── core/                     # Core Pure-Python AI Engine
│   ├── database.py           # SQLAlchemy Connection & Dynamic Schema Inspector
│   ├── validator.py          # SQL AST Safety Guardrail
│   ├── prompts.py            # Centralized Prompt Templates
│   ├── llm_client.py         # Gemini API Wrapper & JSON Parser
│   └── agent.py              # Orchestration Pipeline & Self-Healing Loop
│
├── data/
│   ├── seed_db.py            # Database generator with Departments, Students, Marks
│   └── college.db            # SQLite database file
│
├── docs/
│   └── PROMPTS_AND_EXPLANATION.md # In-depth documentation of all prompts & modules
│
├── backend/                  # FastAPI Microservice
│   ├── main.py               # REST API Endpoints (/health, /schema, /ask)
│   └── schemas.py            # Pydantic Request/Response models
│
└── frontend/                 # Streamlit UI
    └── app.py                # Dashboard with table view, SQL trace, and charts
```
