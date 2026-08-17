"""
Quick test to verify FastAPI can connect to PostgreSQL
"""
from app.db import SessionLocal, engine
from sqlalchemy import text

def test_fastapi_connection():
    print("Testing FastAPI database connection...\n")
    
    try:
        # Test engine connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Engine connection successful")
        
        # Test session
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"✓ Session connection successful")
            print(f"✓ Found {count} users in database")
        finally:
            db.close()
        
        print("\n✅ FastAPI is ready to use the PostgreSQL database!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_fastapi_connection()
