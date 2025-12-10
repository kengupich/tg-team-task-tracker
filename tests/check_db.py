#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('task_management.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("📊 Database tables:")
for t in tables:
    print(f"  ✅ {t[0]}")

# Check groups table
print("\n📌 Groups table schema:")
cursor.execute("PRAGMA table_info(groups)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

# Check tasks table schema
print("\n📝 Tasks table schema:")
cursor.execute("PRAGMA table_info(tasks)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

# Check task_media table schema
print("\n🎬 Task Media table schema:")
cursor.execute("PRAGMA table_info(task_media)")
for row in cursor.fetchall():
    print(f"  - {row[1]} ({row[2]})")

conn.close()
print("\n✅ Database verified!")
