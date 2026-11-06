import os
import sqlite3
import pandas as pd
from datetime import datetime

# Path setup for testing
DATA_DIR = os.environ.get("GADO_DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "gado_familia_sql_v2.db")

def create_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inspect_db():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in DB:", [t['name'] for t in tables])

    for table in tables:
        t_name = table['name']
        print(f"\nTable: {t_name}")
        cursor.execute(f"PRAGMA table_info({t_name});")
        columns = cursor.fetchall()
        print("Columns:", [c['name'] for c in columns])

        cursor.execute(f"SELECT * FROM {t_name} LIMIT 3;")
        rows = cursor.fetchall()
        print(f"Sample data ({len(rows)} rows):")
        for row in rows:
            print(dict(row))
    conn.close()

if __name__ == "__main__":
    inspect_db()
