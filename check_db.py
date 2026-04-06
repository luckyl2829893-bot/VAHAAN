import sqlite3
import os

DB_PATH = "arg_master_database.sqlite"

def get_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(citizens)")
    cols = c.fetchall()
    print("Citizens table columns:")
    for col in cols:
        print(col)
    conn.close()

if __name__ == "__main__":
    get_schema()
