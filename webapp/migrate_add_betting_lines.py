"""Migration script to add betting_lines column to Game table"""
import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
db_path = os.path.join(instance_dir, 'cascade.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    print("The database will be created automatically when the app starts.")
    exit(0)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if the column already exists
    cursor.execute("PRAGMA table_info(game)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'betting_lines' not in columns:
        print("Adding betting_lines column to game table...")
        cursor.execute("ALTER TABLE game ADD COLUMN betting_lines TEXT")
        conn.commit()
        print("Successfully added betting_lines column")
    else:
        print("betting_lines column already exists")
        
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

