import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models.user import User
from app.models.transaction import Transaction
from app.models.alert import ComplianceAlert
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.models.system_health import SystemHealth, SystemAlert
from app.models.system_metrics import SystemMetrics
from app.models.toxicity_history import ToxicityHistory
from app.models.user_sanction_match import UserSanctionMatch
import json
from datetime import datetime

def format_value(val):
    if val is None:
        return "NULL"
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val)

def display_table(db, table_name, model_class):
    print(f"\n{'='*80}")
    print(f"TABLE: {table_name.upper()}")
    print(f"{'='*80}")
    
    try:
        records = db.query(model_class).all()
        count = len(records)
        print(f"Total records: {count}\n")
        
        if count == 0:
            print("(No records found)\n")
            return
        
        # Get column names
        columns = model_class.__table__.columns.keys()
        
        # Print header
        header = " | ".join([f"{col[:15]:<15}" for col in columns[:10]])  # Limit to 10 cols for display
        print(header)
        print("-" * len(header))
        
        # Print data (limit to first 20 records for readability)
        for record in records[:20]:
            row = " | ".join([f"{str(format_value(getattr(record, col)))[:15]:<15}" for col in columns[:10]])
            print(row)
        
        if count > 20:
            print(f"\n... and {count - 20} more records")
        
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
    
    print()

# Main execution
db = SessionLocal()
try:
    print("\n" + "="*80)
    print("DATABASE CONTENTS - ALL TABLES")
    print("="*80)
    
    # Query all tables
    tables = [
        ("users", User),
        ("transactions", Transaction),
        ("compliance_alerts", ComplianceAlert),
        ("admins", Admin),
        ("audit_logs", AuditLog),
        ("toxicityhistory", ToxicityHistory),
        ("usersanctionmatches", UserSanctionMatch),
        ("system_metrics", SystemMetrics),
        ("system_health", SystemHealth),
        ("system_alerts", SystemAlert),
    ]
    
    for table_name, model_class in tables:
        display_table(db, table_name, model_class)
    
    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80 + "\n")
    
finally:
    db.close()