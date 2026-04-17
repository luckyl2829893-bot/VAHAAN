"""
migrate_sqlite_to_mysql.py  —  VAHAAN Migration Utility
==================================================================
Moves all data from a local SQLite database to a MySQL instance.
Ensure you have configured your .env file first.
"""

import sys
import os

# Add parent directory to path to import DBManager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arg_db_manager import DBManager, DB_TYPE
import sqlite3

def migrate():
    if DB_TYPE != "mysql":
        print("Error: DB_TYPE in .env is not set to 'mysql'. Set it to 'mysql' to migrate.")
        return

    sqlite_path = os.getenv("SQLITE_PATH", "arg_master_database.sqlite")
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database not found at {sqlite_path}")
        return

    print(f"Connecting to SQLite: {sqlite_path}")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    
    print("Connecting to MySQL...")
    my_conn = DBManager.get_connection()
    if not my_conn:
        print("Error: Could not connect to MySQL. Check your .env settings.")
        return

    # Ensure schema exists in MySQL
    print("Ensuring MySQL schema...")
    DBManager.ensure_schema()

    tables = ["citizens", "vahan_registry", "fastag_accounts", "fastag_transactions", "challans"]

    try:
        my_cursor = my_conn.cursor()
        
        # Disable foreign key checks for migration
        my_cursor.execute("SET FOREIGN_KEY_CHECKS=0")

        for table in tables:
            print(f"Migrating table: {table}...")
            
            # Fetch from SQLite
            sq_cursor = sq_conn.cursor()
            sq_cursor.execute(f"SELECT * FROM {table}")
            rows = sq_cursor.fetchall()
            
            if not rows:
                print(f"  - No data in {table}, skipping.")
                continue

            # Prepare MySQL insert
            columns = rows[0].keys()
            placeholders = ", ".join(["%s"] * len(columns))
            cols_str = ", ".join(columns)
            
            # Use INSERT IGNORE to avoid duplication issues
            insert_query = f"INSERT IGNORE INTO {table} ({cols_str}) VALUES ({placeholders})"
            
            data = [tuple(row) for row in rows]
            
            my_cursor.executemany(insert_query, data)
            print(f"  - Successfully migrated {len(data)} rows.")

        my_conn.commit()
        my_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        print("\nAll data migrated successfully!")

    except Exception as e:
        print(f"\nMigration failed: {e}")
        my_conn.rollback()
    finally:
        sq_conn.close()
        my_conn.close()

if __name__ == "__main__":
    migrate()
