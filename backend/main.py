"""
FastAPI Server Gateway for Text-to-SQL AI Agent
Exposes REST endpoints for client applications (Streamlit, React, or mobile).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas import (
    QueryRequest, 
    QueryResponse, 
    SchemaResponse, 
    MySQLConnectRequest, 
    MySQLConnectResponse, 
    ActiveDBResponse
)
from core.database import (
    get_schema_representation, 
    get_db_dialect, 
    create_mysql_db_manager, 
    get_default_db_manager
)
from core.agent import SQLAgent

app = FastAPI(
    title="Autonomous Text-to-SQL AI Agent API",
    description="Enterprise-grade natural language interface for relational databases.",
    version="1.0.0"
)

# Enable safe CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Instantiate the Agent
agent = SQLAgent()

@app.get("/health")
def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "healthy", "service": "Text-to-SQL AI Engine"}

@app.get("/schema", response_model=SchemaResponse)
def get_schema():
    """Returns the dynamically extracted database schema of the active database."""
    try:
        schema_text = agent.db.get_schema_representation()
        dialect = agent.db.get_db_dialect()
        return SchemaResponse(dialect=dialect, schema_text=schema_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/databases", response_model=ActiveDBResponse)
def get_active_database():
    """Returns metadata about the currently active database and tables."""
    return ActiveDBResponse(
        active_database=agent.db.name,
        dialect=agent.db.dialect,
        tables=agent.db.get_table_names()
    )

@app.post("/connect-mysql", response_model=MySQLConnectResponse)
def connect_mysql(payload: MySQLConnectRequest):
    """
    Connects to a remote MySQL database in read-only mode and
    switches the AI Agent to query it.
    """
    ok, mgr, msg = create_mysql_db_manager(
        host=payload.host,
        port=payload.port,
        user=payload.user,
        password=payload.password,
        dbname=payload.dbname
    )
    if not ok or not mgr:
        raise HTTPException(status_code=400, detail=msg)
    
    agent.set_db_manager(mgr)
    return MySQLConnectResponse(
        success=True,
        message=msg,
        active_database=mgr.name,
        dialect=mgr.dialect,
        tables=mgr.get_table_names()
    )

@app.post("/reset-db")
def reset_to_default_db():
    """Resets the agent back to the default SQLite College database."""
    agent.set_db_manager(get_default_db_manager())
    return {"message": "Reset to default College database", "active_database": agent.db.name}

@app.post("/ask", response_model=QueryResponse)
def ask_query(payload: QueryRequest):
    """
    Main endpoint: Accepts a natural language question and runs
    the complete SQL Agent pipeline (relevance -> SQL -> validation -> execution -> summary).
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        result = agent.run(payload.query, history=payload.history)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal agent execution error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
