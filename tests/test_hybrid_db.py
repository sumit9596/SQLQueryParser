"""
Unit & Integration Test for Hybrid Dynamic Database Switching (CSV/Excel & Dialects)
Tests:
1. Dynamic CSV loading into session SQLite database
2. Agent querying dynamic table schema
3. Read-only protection on custom session database
4. Safe SQLGlot AST validation for SQLite and MySQL dialects
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from core.database import (
    create_file_session_db,
    get_default_db_manager,
    DatabaseManager
)
from core.validator import validate_sql_query
from core.agent import SQLAgent

def test_dynamic_csv_session():
    print("--- [1] Creating Mock Sales & Products Data ---")
    sales_df = pd.DataFrame({
        "order_id": [101, 102, 103, 104, 105],
        "product_name": ["MacBook Pro", "Wireless Mouse", "Mechanical Keyboard", "Dell Monitor", "USB-C Hub"],
        "category": ["Electronics", "Accessories", "Accessories", "Electronics", "Accessories"],
        "price": [1999.99, 49.50, 120.00, 349.00, 35.00],
        "quantity": [2, 10, 5, 3, 12]
    })

    files = {"ecommerce_sales.csv": sales_df}
    session_mgr = create_file_session_db(files, session_id="test_sales_001")
    
    print("\n--- [2] Inspecting Dynamic Schema ---")
    schema_str = session_mgr.get_schema_representation()
    print(schema_str)
    assert "ecommerce_sales" in schema_str
    assert "product_name" in schema_str

    print("\n--- [3] Verifying Direct Read-Only Query on Dynamic DB ---")
    query_res = session_mgr.execute_query("SELECT product_name, price * quantity AS total_revenue FROM ecommerce_sales ORDER BY total_revenue DESC LIMIT 3;")
    print("Execution Result:", query_res)
    assert query_res["success"] is True
    assert query_res["row_count"] == 3
    assert query_res["rows"][0]["product_name"] == "MacBook Pro"

    print("\n--- [4] Verifying Read-Only Block on Dynamic DB ---")
    drop_res = session_mgr.execute_query("DROP TABLE ecommerce_sales;")
    print("Drop Attempt Result:", drop_res)
    assert drop_res["success"] is False, "Drop table should have been blocked by SQLite PRAGMA query_only = ON"
    print("[PASS] Read-only engine blocked destructive modification!")

    print("\n--- [5] Testing Dialect-Aware AST Validation ---")
    # SQLite dialect
    is_safe, sql_sqlite = validate_sql_query("SELECT product_name FROM ecommerce_sales LIMIT 5;", dialect="sqlite")
    assert is_safe is True
    print(f"[PASS] SQLite validation: {sql_sqlite}")

    # MySQL dialect
    is_safe, sql_mysql = validate_sql_query("SELECT CONCAT(product_name, ' - ', category) AS item_desc FROM ecommerce_sales LIMIT 5;", dialect="mysql")
    assert is_safe is True
    print(f"[PASS] MySQL validation: {sql_mysql}")

    # Dangerous query rejection
    is_safe, err = validate_sql_query("DELETE FROM ecommerce_sales WHERE price < 50;", dialect="mysql")
    assert is_safe is False
    print(f"[PASS] Malicious DML rejected: {err}")

    print("\n=== ALL HYBRID DB UNIT TESTS PASSED ===")

if __name__ == "__main__":
    test_dynamic_csv_session()
