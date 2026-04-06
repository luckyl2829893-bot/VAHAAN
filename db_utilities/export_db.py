import sqlite3
import pandas as pd

conn = sqlite3.connect('arg_master_database.sqlite')

tables = ['citizens', 'vahan_registry', 'fastag_accounts', 'fastag_transactions', 'challans']

for t in tables:
    df = pd.read_sql(f'SELECT * FROM {t}', conn)
    df.to_csv(f'export_{t}.csv', index=False)
    print(f"{t}: {len(df)} rows")

# Also create the master summary CSV
print("\n--- Master Summary ---")
df = pd.read_csv('ARG_Proxy_Dataset_Master.csv')
print(f"ARG_Proxy_Dataset_Master.csv: {len(df)} rows")
print(df.head(10).to_string())

conn.close()
