import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.database import parse_pasted_data, create_file_session_db


def test_parse_tsv():
    tsv = "id\tname\tsalary\n1\tAarav\t75000\n2\tSneha\t82000"
    df = parse_pasted_data(tsv)
    assert list(df.columns) == ["id", "name", "salary"]
    assert len(df) == 2
    assert df.iloc[0]["name"] == "Aarav"


def test_parse_csv():
    csv_str = "emp_id, full_name, dept\n101, Rohan Sharma, Sales\n102, Priya Patel, Marketing"
    df = parse_pasted_data(csv_str)
    assert list(df.columns) == ["emp_id", "full_name", "dept"]
    assert len(df) == 2


def test_parse_markdown_table():
    md = """
    | product_id | product_name | price |
    |---|---|---|
    | P10 | Wireless Mouse | 25.5 |
    | P20 | Mechanical Keyboard | 89.9 |
    """
    df = parse_pasted_data(md)
    assert list(df.columns) == ["product_id", "product_name", "price"]
    assert len(df) == 2
    assert df.iloc[1]["product_name"] == "Mechanical Keyboard"


def test_create_session_db_from_pasted():
    raw_data = "colA\tcolB\n10\t20\n30\t40"
    df = parse_pasted_data(raw_data)
    db = create_file_session_db({"pasted_test": df}, session_id="test_paste_session")
    schema = db.get_schema_representation()
    assert "pasted_test" in schema
    res = db.execute_query("SELECT colA, colB FROM pasted_test WHERE colA = 10")
    assert res["success"] is True
    assert len(res["rows"]) == 1
    assert res["rows"][0]["colA"] == 10


if __name__ == "__main__":
    test_parse_tsv()
    test_parse_csv()
    test_parse_markdown_table()
    test_create_session_db_from_pasted()
    print("All pasted data tests passed successfully!")
