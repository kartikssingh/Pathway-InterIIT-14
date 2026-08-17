"""
Database Connection Test Script
Tests PostgreSQL connection and verifies data
"""

from app.db import engine, SessionLocal
from sqlalchemy import text
import sys

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("✓ Database connection successful!")
            print(f"✓ PostgreSQL Version: {version}\n")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_tables():
    """Check if all tables exist"""
    expected_tables = [
        'users',
        'transactions', 
        'compliance_alerts',
        'investigation_cases',
        'account_holds',
        'organization_settings',
        'notification_settings'
    ]
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            print("📊 Database Tables:")
            for table in tables:
                status = "✓" if table in expected_tables else "?"
                print(f"  {status} {table}")
            
            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"\n⚠ Missing tables: {missing}")
                return False
            
            print(f"\n✓ All {len(expected_tables)} required tables exist!\n")
            return True
    except Exception as e:
        print(f"✗ Error checking tables: {e}")
        return False

def check_data():
    """Verify data in key tables"""
    queries = {
        "Users": "SELECT COUNT(*) FROM users;",
        "Transactions": "SELECT COUNT(*) FROM transactions;",
        "Compliance Alerts": "SELECT COUNT(*) FROM compliance_alerts;",
        "Investigation Cases": "SELECT COUNT(*) FROM investigation_cases;",
        "Account Holds": "SELECT COUNT(*) FROM account_holds;",
        "Notification Settings": "SELECT COUNT(*) FROM notification_settings;",
    }
    
    try:
        with engine.connect() as connection:
            print("📈 Data Summary:")
            total_records = 0
            for table_name, query in queries.items():
                result = connection.execute(text(query))
                count = result.fetchone()[0]
                total_records += count
                print(f"  {table_name:25} {count:>5} records")
            
            print(f"\n✓ Total records across all tables: {total_records}\n")
            return True
    except Exception as e:
        print(f"✗ Error checking data: {e}")
        return False

def show_sample_data():
    """Display sample data from users table"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT entity_id, applicant_name, risk_level, kyc_status, account_status 
                FROM users 
                LIMIT 5;
            """))
            
            print("👥 Sample Users:")
            print(f"  {'Entity ID':<18} {'Name':<20} {'Risk':<10} {'KYC':<15} {'Status':<15}")
            print("  " + "-" * 80)
            
            for row in result:
                print(f"  {row[0]:<18} {row[1]:<20} {row[2]:<10} {row[3]:<15} {row[4]:<15}")
            
            print()
            return True
    except Exception as e:
        print(f"✗ Error fetching sample data: {e}")
        return False

def main():
    """Run all tests"""
    print("="*80)
    print("🔍 PostgreSQL Database Verification")
    print("="*80 + "\n")
    
    tests = [
        ("Connection Test", test_connection),
        ("Table Verification", check_tables),
        ("Data Count Check", check_data),
        ("Sample Data Display", show_sample_data)
    ]
    
    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append(success)
    
    print("="*80)
    if all(results):
        print("✓ All tests passed! Database is ready to use.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("="*80)
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
