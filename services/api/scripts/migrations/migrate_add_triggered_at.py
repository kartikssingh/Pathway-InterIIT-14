"""
Migration script to add triggered_at column to compliance_alerts table
Run this if you have an existing database without the triggered_at column
"""
import sqlite3
import os
from datetime import datetime

# Get the database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db")

def migrate():
    """Add triggered_at column to compliance_alerts table"""
    print(f"Connecting to database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database does not exist yet. Run the application first to create it.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(compliance_alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "triggered_at" in columns:
            print("✓ Column 'triggered_at' already exists in compliance_alerts table")
        else:
            print("Adding 'triggered_at' column to compliance_alerts table...")
            cursor.execute("""
                ALTER TABLE compliance_alerts 
                ADD COLUMN triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            
            # Set triggered_at to created_at for existing records
            cursor.execute("""
                UPDATE compliance_alerts 
                SET triggered_at = created_at 
                WHERE triggered_at IS NULL
            """)
            
            conn.commit()
            print("✓ Successfully added 'triggered_at' column")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(compliance_alerts)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\nCurrent columns in compliance_alerts: {', '.join(columns)}")
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
