"""
Pydantic Request & Response Models for FastAPI
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question from the user", example="Roll number 5 ka data do")
    history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Recent conversation turns for follow-up context resolution")

class StepLog(BaseModel):
    step: str
    status: str
    message: str

class QueryResponse(BaseModel):
    success: bool
    status: str
    answer: str
    sql_query: Optional[str] = None
    columns: List[str] = []
    data: List[Dict[str, Any]] = []
    row_count: int = 0
    logs: List[StepLog] = []
    history: Optional[List[Dict[str, Any]]] = []

class SchemaResponse(BaseModel):
    dialect: str
    schema_text: str
