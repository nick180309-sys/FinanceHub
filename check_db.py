import sqlite3

conn = sqlite3.connect('finance.db')
c = conn.cursor()

# Check all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

print('\nChecking transacoes table:')
try:
    c.execute('PRAGMA table_info(transacoes)')
    columns = c.fetchall()
    print('transacoes table columns:')
    for col in columns:
        print(f'  {col[1]}: {col[2]}')
except sqlite3.OperationalError as e:
    print(f'Error checking transacoes table: {e}')

print('\nChecking families table:')
try:
    c.execute('PRAGMA table_info(families)')
    columns = c.fetchall()
    print('families table columns:')
    for col in columns:
        print(f'  {col[1]}: {col[2]}')
except sqlite3.OperationalError as e:
    print(f'Error checking families table: {e}')

conn.close()