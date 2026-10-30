"""
Autonomous Text-to-SQL AI Agent Core (Multi-Turn Conversational Edition)
Orchestrates the complete pipeline with Single-Pass Unified Intent & SQL Synthesis:
1. Cached Schema Extraction (0.0ms)
2. Multi-Turn Conversation Memory Buffer for Follow-Up Entity Resolution
3. Single-Pass Consolidated Intent & Safe SQL Synthesis (Single LLM Call)
4. AST Safety Validation & Auto-LIMIT 100 Guardrail
5. Read-Only Database Execution with Autonomous Self-Correction Loop
6. Instant Deterministic Natural Language Insight (<10ms)
"""

import json
import re
from typing import Dict, Any, Optional, List

from sqlalchemy import inspect
from core.database import DatabaseManager, get_default_db_manager
from core.validator import validate_sql_query
from core.llm_client import call_llm
from core.prompts import (
    format_consolidated_prompt,
    format_self_correction_prompt,
    format_explainer_prompt
)

def generate_fallback_logic_steps(sql_query: str) -> List[str]:
    """Generates clean, professional English logic breakdown from SQL query structure."""
    if not sql_query:
        return []
    
    steps = []
    sql_upper = sql_query.upper()
    
    # 1. Tables & Joins
    if " JOIN " in sql_upper:
        tables = re.findall(r"(?:FROM|JOIN)\s+([`\"\w]+)", sql_query, re.IGNORECASE)
        clean_tables = [t.strip('`"') for t in tables if t.upper() not in ["SELECT", "WHERE"]]
        steps.append(f"🔗 Connects tables: {', '.join(clean_tables)} using relational foreign keys.")
    else:
        from_match = re.search(r"FROM\s+([`\"\w]+)", sql_query, re.IGNORECASE)
        t_name = from_match.group(1).strip('`"') if from_match else "target table"
        steps.append(f"📦 Scans records from the '{t_name}' table.")

    # 2. Filters / Where
    if " WHERE " in sql_upper:
        steps.append("🔍 Applies filtering criteria to isolate target matching records.")

    # 3. Aggregations / Grouping
    if any(fn in sql_upper for fn in ["COUNT(", "AVG(", "SUM(", "MIN(", "MAX(", "GROUP BY"]):
        steps.append("🧮 Computes analytical aggregate metrics and groups calculated values.")

    # 4. Sorting / Ordering
    if " ORDER BY " in sql_upper:
        if "DESC" in sql_upper:
            steps.append("⬇️ Sorts results in descending order to surface top values.")
        else:
            steps.append("⬆️ Sorts results in ascending order.")

    # 5. Limit
    if " LIMIT " in sql_upper:
        lim_match = re.search(r"LIMIT\s+(\d+)", sql_query, re.IGNORECASE)
        lim_num = lim_match.group(1) if lim_match else "specified"
        steps.append(f"🛑 Restricts output to top {lim_num} records.")

    return steps


class SQLAgent:
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        max_retries: int = 2,
        max_memory_turns: int = 5
    ):
        self.db = db_manager or get_default_db_manager()
        self.max_retries = max_retries
        self.max_memory_turns = max_memory_turns
        self.memory: List[Dict[str, Any]] = []

    def set_db_manager(self, db_manager: DatabaseManager):
        """Switches the active database manager and clears session memory."""
        self.db = db_manager
        self.clear_memory()

    def clear_memory(self):
        """Resets the conversation history buffer."""
        self.memory.clear()

    def run(
        self,
        user_query: str,
        history: Optional[List[Dict[str, Any]]] = None,
        deep_summary: bool = False,
        db_manager: Optional[DatabaseManager] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end pipeline for a user question with conversation memory.
        Supports multi-turn context resolution (e.g. "show their marks too").
        """
        logs = []
        active_db = db_manager or self.db
        schema = active_db.get_schema_representation()
        dialect = active_db.get_db_dialect()

        # Determine effective conversation history
        effective_history = history if history is not None else self.memory

        # -------------------------------------------------------------
        # STEP 1: Single-Pass Consolidated Intent Routing & SQL Synthesis
        # -------------------------------------------------------------
        logs.append({
            "step": "intent_and_sql_synthesis",
            "status": "running",
            "message": f"Analyzing inquiry against database schema & context in a single unified pass..."
        })
        
        prompt = format_consolidated_prompt(
            dialect=dialect,
            schema=schema,
            query=user_query,
            history=effective_history
        )
        
        logic_steps = []
        try:
            llm_res = call_llm(prompt, expect_json=True)
            category = llm_res.get("category", "DATA_QUERY") or "DATA_QUERY"
            direct_answer = (llm_res.get("direct_answer") or "").strip()
            sql_query = (llm_res.get("sql_query") or "").strip()
            explanation = (llm_res.get("explanation") or "").strip()
            raw_steps = llm_res.get("logic_steps")
            if isinstance(raw_steps, list):
                logic_steps = [str(s).strip() for s in raw_steps if str(s).strip()]
        except Exception as e:
            category = "DATA_QUERY"
            direct_answer = ""
            sql_query = ""
            explanation = str(e)
            logic_steps = []

        # 1A. Out of Scope Check
        if category == "OUT_OF_SCOPE":
            msg = direct_answer or "This inquiry is outside the scope of our database."
            logs.append({"step": "intent_routing", "status": "out_of_scope", "message": msg})
            return {
                "success": True,
                "status": "out_of_scope",
                "answer": msg,
                "sql_query": None,
                "columns": [],
                "data": [],
                "row_count": 0,
                "logs": logs,
                "history": effective_history
            }

        # 1B. Direct Schema/Metadata Inquiry
        if category == "SCHEMA_INFO":
            msg = direct_answer or "Inquiry answered directly from database schema structure."
            logs.append({"step": "intent_routing", "status": "passed", "message": "Schema metadata inquiry answered directly."})
            
            tables_info = []
            try:
                inspector = inspect(active_db.engine)
                for t in active_db.get_table_names():
                    cols = [c["name"] for c in inspector.get_columns(t)]
                    tables_info.append({"name": t, "columns": cols, "count": len(cols)})
            except Exception:
                pass

            return {
                "success": True,
                "status": "schema_info",
                "answer": msg,
                "tables_info": tables_info,
                "sql_query": None,
                "columns": [],
                "data": [],
                "row_count": 0,
                "logs": logs,
                "history": effective_history
            }

        logs.append({
            "step": "intent_and_sql_synthesis",
            "status": "passed",
            "message": f"Synthesized SQL query for {dialect} dialect."
        })

        if not sql_query:
            return {
                "success": False,
                "status": "llm_error",
                "answer": "Unable to synthesize a valid SQL query for this inquiry.",
                "sql_query": None,
                "columns": [],
                "data": [],
                "row_count": 0,
                "logs": logs,
                "history": effective_history
            }

        # -------------------------------------------------------------
        # STEP 2: Safety Guardrail Validation (AST & Auto-LIMIT)
        # -------------------------------------------------------------
        logs.append({"step": "safety_check", "status": "running", "message": f"Enforcing AST safety & read-only constraints for {dialect}..."})
        is_safe, clean_sql_or_error = validate_sql_query(sql_query, dialect=dialect)
        
        if not is_safe:
            logs.append({"step": "safety_check", "status": "failed", "message": clean_sql_or_error})
            return {
                "success": False,
                "status": "security_violation",
                "answer": f"Security Guardrail Violation: {clean_sql_or_error}",
                "sql_query": sql_query,
                "columns": [],
                "data": [],
                "row_count": 0,
                "logs": logs,
                "history": effective_history
            }

        clean_sql = clean_sql_or_error
        logs.append({"step": "safety_check", "status": "passed", "message": f"Verified safe: {clean_sql}"})

        # -------------------------------------------------------------
        # STEP 3: Read-Only Execution with Self-Correction Loop
        # -------------------------------------------------------------
        logs.append({"step": "db_execution", "status": "running", "message": f"Executing: {clean_sql}"})
        exec_result = active_db.execute_query(clean_sql)
        current_sql = clean_sql

        retries = 0
        while not exec_result["success"] and retries < self.max_retries:
            retries += 1
            error_msg = exec_result["error"]
            logs.append({
                "step": f"self_healing_attempt_{retries}",
                "status": "retrying",
                "message": f"Execution error: {error_msg}. Invoking autonomous self-correction loop..."
            })
            
            heal_prompt = format_self_correction_prompt(
                schema=schema,
                query=user_query,
                failed_sql=current_sql,
                error_msg=error_msg
            )
            
            try:
                heal_res = call_llm(heal_prompt, expect_json=True, use_cache=False)
                corrected_sql = (heal_res.get("corrected_sql") or "").strip()
                if heal_res.get("logic_steps") and isinstance(heal_res["logic_steps"], list):
                    logic_steps = [str(s).strip() for s in heal_res["logic_steps"] if str(s).strip()]
                
                is_safe, validated_heal_sql = validate_sql_query(corrected_sql, dialect=dialect)
                if not is_safe:
                    continue
                    
                current_sql = validated_heal_sql
                exec_result = active_db.execute_query(current_sql)
            except Exception as e:
                logs.append({
                    "step": f"self_healing_attempt_{retries}",
                    "status": "warning",
                    "message": f"Self-healing retry error: {str(e)}"
                })
                continue

        if not exec_result["success"]:
            logs.append({"step": "db_execution", "status": "failed", "message": exec_result["error"]})
            return {
                "success": False,
                "status": "execution_failed",
                "answer": f"Database execution error: {exec_result['error']}",
                "sql_query": current_sql,
                "columns": [],
                "data": [],
                "row_count": 0,
                "logs": logs,
                "history": effective_history
            }

        row_count = exec_result["row_count"]
        logs.append({"step": "db_execution", "status": "passed", "message": f"Retrieved {row_count} record(s)."})

        # -------------------------------------------------------------
        # STEP 4: Instant Deterministic Insight & Entity Clarification
        # -------------------------------------------------------------
        if row_count == 0:
            summary = "No matching records were found in the database for your inquiry."
        else:
            # Extract distinct person/table names for smart clarification
            distinct_names = []
            for r in exec_result["rows"]:
                for k, v in r.items():
                    if "name" in k.lower() and isinstance(v, str) and v not in distinct_names:
                        distinct_names.append(v)

            # Check if user asked for a list/rank/aggregation (e.g. 'top 3', 'all', 'highest', 'average')
            is_list_query = any(w in user_query.lower() for w in ["top", "all", "list", "highest", "lowest", "count", "average", "avg", "each", "every", "sum", "grade"])

            # Entity label (students for college DB, matching entries for dynamic tables)
            entity_label = "students" if "student" in schema.lower() else "matching entries"

            # Scenario A: Multiple ambiguous entities found ONLY when searching for a specific individual
            if len(distinct_names) > 1 and not is_list_query and any(w in user_query.lower() for w in ["name", "who", "where", "details", "search"]):
                summary = f"Found {len(distinct_names)} {entity_label} ({', '.join(distinct_names)}). Displaying all records below. You can clarify with a follow-up (e.g. 'show {distinct_names[0]}')."
            # Scenario B: Single partial match found (e.g. searched 'sneha', matched 'Sneha Reddy')
            elif len(distinct_names) == 1 and not is_list_query and any(w in distinct_names[0].lower() for w in user_query.lower().split() if len(w) > 2):
                matched_name = distinct_names[0]
                summary = f"Showing details for '{matched_name}' (matched from your search). Retrieved {row_count} matching record{'s' if row_count > 1 else ''}."
            else:
                base_insight = explanation if explanation else "Query executed successfully."
                summary = f"{base_insight} (Retrieved {row_count} matching record{'s' if row_count > 1 else ''})."

        # Optional Deep Summary
        if deep_summary and row_count > 0:
            logs.append({"step": "summary_generation", "status": "running", "message": "Synthesizing deep natural language analysis..."})
            try:
                rows_str = json.dumps(exec_result["rows"][:10], indent=2, default=str)
                explain_prompt = format_explainer_prompt(query=user_query, sql=current_sql, results=rows_str)
                deep_text = call_llm(explain_prompt, expect_json=False)
                if deep_text:
                    summary = deep_text
            except Exception:
                pass

        logs.append({"step": "completed", "status": "passed", "message": "Response delivered."})

        # Update Conversation Memory Buffer
        turn_record = {
            "user": user_query,
            "sql": current_sql,
            "summary": summary
        }
        effective_history.append(turn_record)
        if len(effective_history) > self.max_memory_turns:
            effective_history.pop(0)

        if not logic_steps:
            logic_steps = generate_fallback_logic_steps(current_sql)

        return {
            "success": True,
            "status": "success",
            "answer": summary,
            "sql_query": current_sql,
            "columns": exec_result["columns"],
            "data": exec_result["rows"],
            "row_count": row_count,
            "logs": logs,
            "history": effective_history,
            "logic_steps": logic_steps
        }

if __name__ == "__main__":
    print("=== TESTING MULTI-TURN CONVERSATIONAL AGENT ===")
    agent = SQLAgent()
    
    # Turn 1: Primary Query
    q1 = "Show top 3 students with highest marks"
    print(f"\n[Turn 1] User: '{q1}'")
    r1 = agent.run(q1)
    print(f"SQL 1: {r1['sql_query']}")
    print(f"Answer 1: {r1['answer']}")
    
    # Turn 2: Follow-up Query with Pronoun Reference ("their email addresses")
    q2 = "What are their email addresses?"
    print(f"\n[Turn 2] Follow-up: '{q2}'")
    r2 = agent.run(q2)
    print(f"SQL 2: {r2['sql_query']}")
    print(f"Answer 2: {r2['answer']}")
    print(f"Rows 2: {r2.get('row_count')}")
    print(f"Data: {r2.get('data')}")
