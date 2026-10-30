"""
Prompt Templates Module (Unified High-Performance & Multi-Turn Conversational)
Features:
- Single-Pass Intent Router + Text-to-SQL Synthesis
- Multi-Turn Conversation Memory Context Resolution for follow-up questions
"""

from typing import List, Dict, Optional, Any

CONSOLIDATED_ROUTER_SQL_TEMPLATE = """You are an expert Relational Database AI Architect specialized in {db_dialect}.
Analyze the user's natural language inquiry against the provided Database Schema and recent conversation context.
Perform Intent Routing and Safe SQL Synthesis in a single deterministic pass.

### DATABASE SCHEMA:
{schema_description}
{conversation_context}
### USER INQUIRY:
"{user_query}"

### INSTRUCTIONS:
Classify the inquiry into exactly ONE of the following 3 categories:
1. "DATA_QUERY": The inquiry asks for actual records/rows stored in the database.
   - Synthesize a clean, optimal read-only SELECT query for {db_dialect}.
   - MULTI-TURN RESOLUTION: If the user refers to previous context (e.g. "their marks", "these students", "filter by second year", "show their email addresses too"), use the conversation history to resolve pronouns and produce a complete, standalone SQL query.
   - DIALECT COMPATIBILITY ({db_dialect}):
     * If MySQL: Use MySQL 8 syntax (e.g., `LIMIT n`, `CONCAT(a, b)` for string joining, backticks `` `col` `` if column/table has reserved words or spaces).
     * If SQLite: Use standard SQLite syntax (e.g., `LIMIT n`, `a || b` for string concatenation).
2. "SCHEMA_INFO": The inquiry asks about database metadata (e.g., "what tables exist?", "show columns in marks", "how many tables?").
   - Synthesize a beautifully structured, executive summary in `direct_answer`.
   - Clearly state the table names, number of columns, and highlight key business metrics/attributes. Never write a plain run-on sentence. Do NOT write an SQL query.
3. "OUT_OF_SCOPE": The inquiry is completely unrelated to this database (e.g., world history, weather, sports, general programming).
   - Synthesize a polite refusal in `direct_answer` explaining the database's specific scope.

### STRICT RULES FOR "DATA_QUERY":
1. ONLY generate SELECT queries. Never generate DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, or PRAGMA.
2. Use ONLY table and column names explicitly defined in the schema above.
3. For text and name searches:
   - Use case-insensitive partial matching with LIKE: `LOWER(name) LIKE '%val%'` so searching for a keyword/name matches full text.
   - Priority Sorting: When searching for an entity/name, prioritize exact full-name matches first, followed by prefix matches:
     `ORDER BY CASE WHEN LOWER(name) = LOWER('val') THEN 1 WHEN LOWER(name) LIKE LOWER('val %') THEN 2 ELSE 3 END, name ASC`
4. When joining tables, use explicit JOIN syntax with valid foreign keys.

### OUTPUT FORMAT (Strict JSON only, no markdown codeblocks):
{{
  "category": "DATA_QUERY" | "SCHEMA_INFO" | "OUT_OF_SCOPE",
  "sql_query": "SELECT ... (or empty string if not DATA_QUERY)",
  "direct_answer": "Direct answer if SCHEMA_INFO or OUT_OF_SCOPE, else empty string.",
  "explanation": "Concise 1-sentence explanation in clear English of what the query retrieves.",
  "logic_steps": [
    "Step 1: Description of tables joined or queried",
    "Step 2: Description of filters and conditions applied",
    "Step 3: Description of aggregations or computations",
    "Step 4: Description of sorting and limit"
  ]
}}
"""

SELF_CORRECTION_PROMPT_TEMPLATE = """You previously generated a SQL query that failed to execute on the database.
Your job is to analyze the database error and output a corrected SQL query.

### DATABASE SCHEMA:
{schema_description}

### ORIGINAL USER QUESTION:
"{user_query}"

### FAILED SQL QUERY:
{failed_sql}

### DATABASE ERROR MESSAGE:
{error_message}

### INSTRUCTIONS:
1. Identify why the error occurred (e.g., invalid column name, wrong table alias, ambiguous column).
2. Fix the query while adhering strictly to the schema.
3. Keep the query strictly read-only (SELECT only).
4. Provide plain-English step-by-step logic breakdown in logic_steps.

### OUTPUT FORMAT (Strict JSON only, no markdown backticks):
{{
  "corrected_sql": "SELECT ...",
  "fix_summary": "Concise explanation in clear English of what was corrected.",
  "logic_steps": [
    "Step 1...",
    "Step 2..."
  ]
}}
"""

EXPLAINER_PROMPT_TEMPLATE = """You are a helpful Data Analyst.
Explain the database query results to the user in a natural, polite, and concise manner in clear English.

### USER QUESTION:
"{user_query}"

### SQL QUERY EXECUTED:
{sql_query}

### RAW DATABASE RESULTS:
{raw_results}

### INSTRUCTIONS:
1. Provide a direct, polite answer in clear English explaining what the data reveals.
2. If the result is empty, inform the user politely that no matching records were found in the database.
3. Highlight key metrics, student names, departments, or marks clearly.
4. Keep the response crisp and professional.
"""

def format_conversation_history(history: Optional[List[Dict[str, Any]]]) -> str:
    """Formats the last 3 conversation turns into prompt context for entity resolution."""
    if not history:
        return ""
    lines = ["\n### RECENT CONVERSATION HISTORY (Context for follow-up inquiries):"]
    for turn in history[-3:]:
        user_q = turn.get("user", "")
        sql = turn.get("sql", "")
        summary = turn.get("summary", "")
        lines.append(f"- User asked: \"{user_q}\"")
        if sql:
            lines.append(f"  Generated SQL: {sql}")
        if summary:
            lines.append(f"  Summary: {summary}")
    lines.append("")
    return "\n".join(lines)

def format_consolidated_prompt(
    dialect: str,
    schema: str,
    query: str,
    history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Combines intent classification, schema context, and conversation history into a single prompt."""
    context_str = format_conversation_history(history)
    return CONSOLIDATED_ROUTER_SQL_TEMPLATE.format(
        db_dialect=dialect,
        schema_description=schema,
        conversation_context=context_str,
        user_query=query
    )

def format_self_correction_prompt(schema: str, query: str, failed_sql: str, error_msg: str) -> str:
    return SELF_CORRECTION_PROMPT_TEMPLATE.format(
        schema_description=schema,
        user_query=query,
        failed_sql=failed_sql,
        error_message=error_msg
    )

def format_explainer_prompt(query: str, sql: str, results: str) -> str:
    return EXPLAINER_PROMPT_TEMPLATE.format(
        user_query=query,
        sql_query=sql,
        raw_results=results
    )
