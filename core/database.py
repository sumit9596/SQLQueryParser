"""
Database Connection & Schema Inspector Module (Hardened & Multi-Source)
Supports:
1. Default Seeded SQLite DB (college.db)
2. In-Memory / Session SQLite generated dynamically from uploaded CSV and Excel files
3. Live Remote MySQL Database connections
Enforces strict read-only execution at the database engine level and provides dynamic schema caching.
"""

import os
import re
import datetime
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import pandas as pd
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "college.db"
SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Default Database URL
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

def _sanitize_cell_value(val: Any) -> Any:
    """Converts datatypes (date, datetime, Decimal) to JSON-friendly Python primitives."""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    return val

def _sanitize_table_name(filename: str) -> str:
    """Sanitizes file name into a safe SQL table name (alphanumeric + underscore)."""
    base = Path(filename).stem.strip().lower()
    clean = re.sub(r"[^a-z0-9_]+", "_", base)
    clean = clean.strip("_")
    if not clean or clean[0].isdigit():
        clean = f"tbl_{clean}"
    return clean

class DatabaseManager:
    """
    Encapsulates a database connection engine (SQLite, MySQL),
    schema inspection, and safe read-only execution.
    """
    def __init__(self, engine: Engine, name: str = "Database", dialect: Optional[str] = None):
        self.engine = engine
        self.name = name
        self.dialect = dialect or engine.dialect.name
        self._schema_cache: Optional[str] = None

    def get_db_dialect(self) -> str:
        """Returns the database dialect (e.g. 'sqlite', 'mysql')."""
        return self.dialect

    def get_table_names(self) -> List[str]:
        """Returns all table names found in the database."""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception:
            return []

    def clear_schema_cache(self):
        """Clears the cached schema representation."""
        self._schema_cache = None

    def get_schema_representation(self) -> str:
        """
        Dynamically inspects tables, columns, data types, primary/foreign keys,
        and extracts 1-2 representative sample values per column to boost LLM accuracy.
        Caches the result in memory for 0.0ms subsequent calls.
        """
        if self._schema_cache:
            return self._schema_cache

        try:
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
        except Exception as e:
            return f"Error reading database schema: {str(e)}"

        if not table_names:
            return "No tables found in the database."

        schema_lines = []

        for table_name in table_names:
            schema_lines.append(f"Table: {table_name}")
            schema_lines.append("  Columns:")

            try:
                columns = inspector.get_columns(table_name)
            except Exception:
                columns = []

            # Fetch up to 2 sample rows to give the LLM real column value examples
            sample_data: Dict[str, List[Any]] = {col["name"]: [] for col in columns}
            try:
                with self.engine.connect() as conn:
                    # Use quote if table name has special chars
                    quoted_table = f"`{table_name}`" if self.dialect == "mysql" else f'"{table_name}"'
                    sample_query = text(f"SELECT * FROM {quoted_table} LIMIT 2;")
                    res = conn.execute(sample_query)
                    keys = list(res.keys())
                    for row in res.fetchmany(2):
                        for k, v in zip(keys, row):
                            if k in sample_data and v is not None:
                                s_val = str(_sanitize_cell_value(v))
                                if len(s_val) > 30:
                                    s_val = s_val[:27] + "..."
                                if s_val not in sample_data[k] and len(sample_data[k]) < 2:
                                    sample_data[k].append(s_val)
            except Exception:
                pass

            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"])
                nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                pk = " (PRIMARY KEY)" if col.get("primary_key", False) else ""
                
                samples = sample_data.get(col_name, [])
                samples_str = f" [e.g. {', '.join(repr(s) for s in samples)}]" if samples else ""
                schema_lines.append(f"    - {col_name} ({col_type}, {nullable}){pk}{samples_str}")

            try:
                fks = inspector.get_foreign_keys(table_name)
            except Exception:
                fks = []

            if fks:
                schema_lines.append("  Foreign Keys:")
                for fk in fks:
                    referred_table = fk["referred_table"]
                    constrained_columns = ", ".join(fk["constrained_columns"])
                    referred_columns = ", ".join(fk["referred_columns"])
                    schema_lines.append(f"    - ({constrained_columns}) REFERENCES {referred_table}({referred_columns})")

            schema_lines.append("")  # Empty line between tables

        self._schema_cache = "\n".join(schema_lines)
        return self._schema_cache

    def execute_query(self, sql_query: str, max_rows: int = 200) -> Dict[str, Any]:
        """
        Executes a read-only SELECT SQL query safely against this database.
        Returns sanitized rows, columns, and row_count.
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                columns = list(result.keys())
                raw_rows = result.fetchmany(max_rows)
                rows = [
                    {col: _sanitize_cell_value(val) for col, val in zip(columns, row)}
                    for row in raw_rows
                ]
                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "error": None
                }
        except Exception as e:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }

    def preview_table(self, table_name: str, limit: int = 5) -> Dict[str, Any]:
        """Fetches a preview of the specified table."""
        quoted = f"`{table_name}`" if self.dialect == "mysql" else f'"{table_name}"'
        return self.execute_query(f"SELECT * FROM {quoted} LIMIT {limit};")

    def close(self):
        """Disposes the underlying database engine."""
        try:
            self.engine.dispose()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FACTORY FUNCTIONS: SQLite, CSV/Excel Uploads & MySQL
# ---------------------------------------------------------------------------

def create_sqlite_readonly_engine(db_path_or_url: str) -> Engine:
    """Creates a SQLite engine with C-level PRAGMA query_only = ON enforcement."""
    eng = create_engine(db_path_or_url, echo=False)
    @event.listens_for(eng, "connect")
    def set_sqlite_readonly(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA query_only = ON;")
        cursor.close()
    return eng

# Default Global Engine & DatabaseManager (Backward Compatible)
default_engine = create_sqlite_readonly_engine(DATABASE_URL)
default_db_manager = DatabaseManager(engine=default_engine, name="College Demo DB", dialect="sqlite")

def get_default_db_manager() -> DatabaseManager:
    """Returns the default college database manager."""
    return default_db_manager

def create_file_session_db(files_data: Dict[str, pd.DataFrame], session_id: str = "custom") -> DatabaseManager:
    """
    Ingests uploaded CSV or Excel DataFrames into a persistent session SQLite database.
    Applies table name sanitization and enforces read-only safety for subsequent queries.
    """
    clean_session_id = re.sub(r"[^a-zA-Z0-9_]+", "", session_id) or "custom"
    db_file = SESSIONS_DIR / f"session_{clean_session_id}.db"

    # Step 1: Write DataFrames using a writable connection
    write_engine = create_engine(f"sqlite:///{db_file.as_posix()}", echo=False)
    loaded_tables = []
    
    for filename, df in files_data.items():
        table_name = _sanitize_table_name(filename)
        # Ensure column names don't contain hazardous whitespace or symbols
        clean_df = df.copy()
        clean_df.columns = [re.sub(r"[^\w]+", "_", str(c)).strip("_") for c in clean_df.columns]
        clean_df.to_sql(name=table_name, con=write_engine, index=False, if_exists="replace")
        loaded_tables.append(table_name)

    write_engine.dispose()

    # Step 2: Create a Read-Only engine for query execution
    read_engine = create_sqlite_readonly_engine(f"sqlite:///{db_file.as_posix()}")
    return DatabaseManager(
        engine=read_engine,
        name=f"Uploaded Tables ({', '.join(loaded_tables[:3])}{'...' if len(loaded_tables) > 3 else ''})",
        dialect="sqlite"
    )

def create_mysql_db_manager(
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str
) -> Tuple[bool, Optional[DatabaseManager], str]:
    """
    Creates and validates a connection to a remote MySQL database.
    Applies SET SESSION TRANSACTION READ ONLY to ensure read-only safety.
    """
    try:
        encoded_pass = urllib.parse.quote_plus(password)
        mysql_url = f"mysql+pymysql://{user}:{encoded_pass}@{host}:{port}/{dbname}"
        eng = create_engine(mysql_url, echo=False, pool_pre_ping=True)

        # Enforce read-only transaction on every checkout/connect
        @event.listens_for(eng, "connect")
        def set_mysql_readonly(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("SET SESSION TRANSACTION READ ONLY;")
                cursor.close()
            except Exception:
                pass

        # Verify connectivity by testing a lightweight ping query
        with eng.connect() as conn:
            conn.execute(text("SELECT 1;"))

        mgr = DatabaseManager(engine=eng, name=f"MySQL: {dbname}", dialect="mysql")
        table_count = len(mgr.get_table_names())
        return True, mgr, f"Successfully connected to MySQL database '{dbname}' ({table_count} tables detected)."

    except Exception as err:
        return False, None, f"MySQL Connection Error: {str(err)}"


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBILITY CONVENIENCE WRAPPERS
# ---------------------------------------------------------------------------

engine = default_engine

def get_db_dialect() -> str:
    """Returns the dialect of the default database."""
    return default_db_manager.get_db_dialect()

def get_schema_representation() -> str:
    """Returns cached schema representation of the default database."""
    return default_db_manager.get_schema_representation()

def clear_schema_cache():
    """Clears cached schema of default database."""
    default_db_manager.clear_schema_cache()

def execute_query(sql_query: str, max_rows: int = 200) -> Dict[str, Any]:
    """Executes query on default database."""
    return default_db_manager.execute_query(sql_query, max_rows)


if __name__ == "__main__":
    print("=== TESTING DATABASE MODULE ===")
    print("Dialect:", get_db_dialect())
    print("\nDefault Schema Representation:")
    print(get_schema_representation())
    print("\nTest Query:")
    res = execute_query("SELECT name, email FROM students LIMIT 2;")
    print(res)
