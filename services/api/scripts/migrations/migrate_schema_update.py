"""
Migration script to update compliance_alerts table structure
This migrates from the old schema to the new one:
- Rename 'type' to 'alert_type' 
- Add 'rps360', 'entity_id', 'entity_type', 'priority', 'source', 'triggered_by', 'alert_metadata'
- Add acknowledgment fields
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db")

def migrate():
    """Update compliance_alerts table structure"""
    print(f"Connecting to database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database does not exist yet.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get current columns
        cursor.execute("PRAGMA table_info(compliance_alerts)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print("\n=== Current Schema ===")
        for col_name in columns:
            print(f"  - {col_name}")
        
        # Create new table with updated schema
        print("\n=== Creating new table structure ===")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_alerts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                transaction_id INTEGER,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                title VARCHAR(255) NOT NULL,
                description TEXT,
                entity_id VARCHAR(100),
                entity_type VARCHAR(50),
                rps360 REAL DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'active',
                priority VARCHAR(20) DEFAULT 'medium',
                is_acknowledged BOOLEAN DEFAULT 0,
                acknowledged_at DATETIME,
                acknowledged_by VARCHAR(100),
                dismissal_reason TEXT,
                source VARCHAR(100),
                triggered_by VARCHAR(100),
                alert_metadata TEXT,
                triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE SET NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
            )
        """)
        
        # Copy data from old table to new table
        print("=== Migrating data ===")
        cursor.execute("""
            INSERT INTO compliance_alerts_new (
                id, user_id, transaction_id, alert_type, severity, title, 
                description, status, triggered_at, created_at, updated_at
            )
            SELECT 
                id, user_id, transaction_id, 
                COALESCE(type, 'system_alert') as alert_type,
                LOWER(COALESCE(severity, 'medium')) as severity,
                COALESCE(title, 'Alert') as title,
                description,
                LOWER(COALESCE(status, 'active')) as status,
                COALESCE(triggered_at, created_at) as triggered_at,
                created_at,
                updated_at
            FROM compliance_alerts
        """)
        
        # Drop old table and rename new one
        print("=== Replacing old table ===")
        cursor.execute("DROP TABLE compliance_alerts")
        cursor.execute("ALTER TABLE compliance_alerts_new RENAME TO compliance_alerts")
        
        conn.commit()
        print("✓ Successfully migrated compliance_alerts table")
        
        # Verify the new schema
        cursor.execute("PRAGMA table_info(compliance_alerts)")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"\n=== New Schema ===")
        for col in new_columns:
            print(f"  - {col}")
        
        # Check record count
        cursor.execute("SELECT COUNT(*) FROM compliance_alerts")
        count = cursor.fetchone()[0]
        print(f"\n✓ Migrated {count} records successfully")
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
