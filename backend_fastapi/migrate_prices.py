#!/usr/bin/env python3
"""Migrate price history from old database to new database."""
import sqlite3
import sys
from pathlib import Path

# Find the old database (check git)
try:
    import subprocess
    result = subprocess.run(
        ['git', 'show', 'HEAD:backend_fastapi/db.sqlite3'],
        cwd='/home/jordanh/Documents/agile_predict',
        capture_output=True,
        timeout=10
    )
    if result.returncode == 0:
        # Write git version to temp file
        old_db_path = '/tmp/old_db.sqlite3'
        with open(old_db_path, 'wb') as f:
            f.write(result.stdout)
        print(f"✅ Extracted database from git")
    else:
        print("❌ Could not get database from git history")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Now migrate
old_db = sqlite3.connect(old_db_path)
new_db = sqlite3.connect('db.sqlite3')

old_cursor = old_db.cursor()
new_cursor = new_db.cursor()

# Get all price history from old database
old_cursor.execute('SELECT date_time, day_ahead, agile FROM forecasting_pricehistory ORDER BY date_time')
records = old_cursor.fetchall()

print(f'Found {len(records)} price records to migrate')

if records:
    new_cursor.executemany('INSERT INTO forecasting_pricehistory (date_time, day_ahead, agile) VALUES (?, ?, ?)', records)
    new_db.commit()
    print(f'✅ Migrated {len(records)} price records')

new_cursor.execute('SELECT COUNT(*) FROM forecasting_pricehistory')
count = new_cursor.fetchone()[0]
print(f'Verification: {count} price records in new database')

old_db.close()
new_db.close()
