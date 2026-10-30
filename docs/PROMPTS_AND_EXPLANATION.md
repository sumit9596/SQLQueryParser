# Prompts & Architecture Explanation Document

Yeh document project ke har ek prompt aur code module ki deep explanation provide karta hai. Isko padhkar aapko pata chalega ki backend me har ek LLM call kyu ho rahi hai aur code kaise kaam kar raha hai.

---

## 1. Pipeline Overview (Hamara System Kaise Kaam Karega)

Jab user koi sawal puchega, toh pipeline 4 major steps follow karegi:

1. **Step 1: Gatekeeper / Relevance Check (Prompt 1)**
   * *Kyu zaroori hai:* User agar random sawal puche (jaise "What is the capital of India?"), toh bina database query run kiye AI turant user ko politely bata de ki yeh data DB me nahi hai.
2. **Step 2: SQL Generation (Prompt 2)**
   * *Kyu zaroori hai:* Database ka dynamic schema (tables, columns, types) LLM ko bhej kar exact SQL query banwana.
3. **Step 3: SQL Safety Validation (Python Code: `sqlglot`)**
   * *Kyu zaroori hai:* LLM se aayi query ko check karna ki koi `DROP`, `DELETE`, `UPDATE` jaisi dangerous commands toh nahi hain.
4. **Step 4: Execution & Self-Correction Loop (Prompt 3)**
   * *Kyu zaroori hai:* Agar query run karte waqt database error de (jaise spelling mistake ya wrong join), toh application crash hone ke bajaye error LLM ko bhej kar query ko self-heal (theek) karwaya jaye.
5. **Step 5: Natural Language Explanation (Prompt 4)**
   * *Kyu zaroori hai:* Raw rows/columns ko user-friendly readable summary me convert karna.

---

## 2. Prompt 1: The Gatekeeper (Relevance Check)

* **Target Module:** `core/agent.py` -> `check_relevance()`
* **Maksad:** Hallucination aur unnecessary DB load ko rokna.

### Prompt Template:
```text
You are an intelligent Database Gatekeeper.
Your job is to determine whether the user's question can be answered using the provided Database Schema.

### DATABASE SCHEMA:
{schema_description}

### USER INQUIRY:
"{user_query}"

### INSTRUCTIONS:
1. Carefully compare the entities and attributes in the inquiry with the available tables and columns.
2. If the inquiry is completely unrelated to the database (e.g., general knowledge, weather, unrelated sports or celebrities), return is_relevant: false.
3. If the inquiry can be answered or reasonably queried against this schema, return is_relevant: true.

### OUTPUT FORMAT (Strict JSON only, no markdown formatting):
{{
  "is_relevant": true,
  "reason": "Brief explanation of why it is or is not relevant."
}}
```

---

## 3. Prompt 2: Text-to-SQL Generator

* **Target Module:** `core/agent.py` -> `generate_sql()`
* **Maksad:** Schema ke context ko samajh kar 100% syntactically correct SQL query banana.

### Prompt Template:
```text
You are a Senior SQL Architect specialized in {db_dialect}.
Convert the user's natural language question into a clean, optimized SQL query based ONLY on the provided schema.

### DATABASE SCHEMA:
{schema_description}

### USER QUESTION:
"{user_query}"

### RULES:
1. ONLY generate SELECT queries. Never generate DROP, DELETE, UPDATE, INSERT, ALTER or TRUNCATE.
2. Use ONLY table and column names explicitly defined in the schema. Do not make up non-existent columns.
3. For string comparisons, use case-insensitive logic (e.g. LOWER(name) = LOWER('john') or LIKE).
4. When joining tables, use explicit JOIN syntax with correct foreign keys.
5. Provide a short explanation of what the query does.

### OUTPUT FORMAT (Strict JSON only, no markdown codeblocks):
{{
  "sql_query": "SELECT ...",
  "explanation": "Clear explanation of the SQL logic."
}}
```

---

## 4. Prompt 3: Self-Correction Loop (Self-Healing Agent)

* **Target Module:** `core/agent.py` -> `heal_sql_query()`
* **Maksad:** Agar database execution me error aaye, toh application crash hone se bachana aur query ko theek karna.

### Prompt Template:
```text
You previously generated a SQL query that failed to execute on the database.
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
1. Identify why the error occurred (e.g. invalid column name, wrong table alias, ambiguous column).
2. Fix the query while adhering strictly to the schema.
3. Keep the query read-only (SELECT only).

### OUTPUT FORMAT (Strict JSON only):
{{
  "corrected_sql": "SELECT ...",
  "fix_summary": "Explanation of what was fixed."
}}
```

---

## 5. Prompt 4: Natural Language Explainer & Insight Summarizer

* **Target Module:** `core/agent.py` -> `explain_results()`
* **Maksad:** Raw SQL rows ko human-readable response me convert karna.

### Prompt Template:
```text
You are a helpful Data Analyst.
Explain the database query results to the user in a natural, polite, and concise manner.

### USER QUESTION:
"{user_query}"

### SQL QUERY EXECUTED:
{sql_query}

### RAW DATABASE RESULTS:
{raw_results}

### INSTRUCTIONS:
1. Provide a direct and clear answer to the user's question based on the raw results.
2. If the result is empty, inform the user politely that no matching records were found.
3. You may use bullet points for lists.
4. Keep the response crisp and professional.
```
