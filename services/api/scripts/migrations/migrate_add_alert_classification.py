"""
Migration script to add alert classification fields (is_true_positive, reviewed_at, reviewed_by)
to the compliance_alerts table.

This allows admins to mark alerts as true positive or false positive.
Works with PostgreSQL database.
"""

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    # Try psycopg2-binary if psycopg2 is not available
    import psycopg2
    from psycopg2 import sql

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get PostgreSQL connection from environment variables"""
    
    # Parse the DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_NAME"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"]
    )


def migrate_add_alert_classification():
    """Add alert classification columns to compliance_alerts table"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"📁 Connected to database")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'compliance_alerts'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        new_columns = []
        if 'is_true_positive' not in columns:
            new_columns.append(('is_true_positive', 'BOOLEAN'))
        if 'reviewed_at' not in columns:
            new_columns.append(('reviewed_at', 'TIMESTAMP'))
        if 'reviewed_by' not in columns:
            new_columns.append(('reviewed_by', 'VARCHAR(100)'))
        
        if not new_columns:
            print("✅ All columns already exist. No migration needed.")
            return True
        
        print(f"\n🔄 Adding {len(new_columns)} new column(s) to compliance_alerts table...")
        
        # Add each missing column
        for column_name, column_type in new_columns:
            print(f"   Adding column: {column_name} ({column_type})")
            cursor.execute(f"""
                ALTER TABLE compliance_alerts 
                ADD COLUMN {column_name} {column_type}
            """)
        
        conn.commit()
        
        # Verify columns were added
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'compliance_alerts'
        """)
        updated_columns = [row[0] for row in cursor.fetchall()]
        
        print("\n✅ Migration completed successfully!")
        print(f"📊 Total columns in compliance_alerts: {len(updated_columns)}")
        print("\nNew columns added:")
        for column_name, column_type in new_columns:
            if column_name in updated_columns:
                print(f"   ✓ {column_name}")
            else:
                print(f"   ✗ {column_name} (failed)")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("ALERT CLASSIFICATION MIGRATION")
    print("=" * 60)
    print("\nThis will add the following columns to compliance_alerts:")
    print("  - is_true_positive (BOOLEAN): Track if alert is positive or negative")
    print("  - reviewed_at (DATETIME): When alert was classified")
    print("  - reviewed_by (VARCHAR): Admin who classified the alert")
    print("\n" + "=" * 60)
    
    success = migrate_add_alert_classification()
    
    if success:
        print("\n🎉 Migration successful! You can now mark alerts as positive/negative.")
    else:
        print("\n⚠️  Migration failed. Please check the errors above.")
