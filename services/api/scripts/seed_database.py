"""
Database Seed Script
Populates the database with meaningful dummy data for testing and development.
Run this script to populate an empty database or reset to default test data.

Usage: python scripts/seed_database.py
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import engine, SessionLocal, Base
from app.models.user import User
from app.models.transaction import Transaction
from app.models.alert import ComplianceAlert
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.models.system_health import SystemHealth, SystemAlert
from app.models.system_metrics import SystemMetrics
from app.models.toxicity_history import ToxicityHistory
from app.models.user_sanction_match import UserSanctionMatch

# Password hashes using bcrypt
# admin123 hash
ADMIN_PASSWORD_HASH = "$2b$12$spgE.7sEyp7Ei9au7fwdMuz13my.a2NT96XeGXdkuuFeyE7NXequK"
# superadmin123 hash
SUPERADMIN_PASSWORD_HASH = "$2b$12$5b0Jm4D9LgqXxv4SmEGDQOFqlGiJ1Y8YsJDErG6QLgm9XSH72Q7NW"


def clear_tables(db):
    """Clear all tables before seeding"""
    print("Clearing existing data...")
    try:
        # Delete in order to respect foreign keys
        db.execute(text("DELETE FROM audit_logs"))
        db.execute(text("DELETE FROM system_metrics"))
        db.execute(text("DELETE FROM system_alerts"))
        db.execute(text("DELETE FROM system_health"))
        db.execute(text("DELETE FROM usersanctionmatches"))
        db.execute(text("DELETE FROM toxicityhistory"))
        db.execute(text("DELETE FROM compliance_alerts"))
        db.execute(text("DELETE FROM transactions"))
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM admins"))
        db.commit()
        print("✓ Tables cleared")
    except Exception as e:
        db.rollback()
        print(f"Note: Some tables may not exist yet - {e}")


def seed_admins(db):
    """Seed admin users"""
    print("Seeding admins...")
    
    admins = [
        Admin(
            username="superadmin",
            email="superadmin@example.com",
            hashed_password=SUPERADMIN_PASSWORD_HASH,  # password: superadmin123
            role="superadmin",
            last_login_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Admin(
            username="admin",
            email="admin@example.com",
            hashed_password=ADMIN_PASSWORD_HASH,  # password: admin123
            role="admin",
            last_login_at=datetime.utcnow() - timedelta(days=1)
        ),
        Admin(
            username="admin1",
            email="admin1@example.com",
            hashed_password=ADMIN_PASSWORD_HASH,  # password: admin123
            role="admin",
            last_login_at=datetime.utcnow() - timedelta(days=1)
        ),
        Admin(
            username="admin2",
            email="admin2@example.com",
            hashed_password=ADMIN_PASSWORD_HASH,  # password: admin123
            role="admin",
            last_login_at=datetime.utcnow() - timedelta(hours=5)
        ),
    ]
    
    for admin in admins:
        db.add(admin)
    
    db.commit()
    print(f"✓ Created {len(admins)} admins")
    return admins


def seed_users(db):
    """Seed user accounts"""
    print("Seeding users...")
    
    users_data = [
        {
            "user_id": 1001,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "phone": "9876543210",
            "uin": "AAAA1234567890BBBB12",
            "occupation": "Software Engineer",
            "annual_income": 1200000.0,
            "kyc_status": "verified",
            "credit_score": 750,
            "current_rps_not": 0.15,
            "current_rps_360": 0.22,
            "risk_category": "low",
            "blacklisted": False,
        },
        {
            "user_id": 1002,
            "username": "jane_smith",
            "email": "jane.smith@example.com",
            "phone": "9876543211",
            "uin": "BBBB2345678901CCCC12",
            "occupation": "Business Owner",
            "annual_income": 2500000.0,
            "kyc_status": "verified",
            "credit_score": 680,
            "current_rps_not": 0.45,
            "current_rps_360": 0.52,
            "risk_category": "medium",
            "blacklisted": False,
        },
        {
            "user_id": 1003,
            "username": "robert_johnson",
            "email": "robert.johnson@example.com",
            "phone": "9876543212",
            "uin": "CCCC3456789012DDDD12",
            "occupation": "Trader",
            "annual_income": 5000000.0,
            "kyc_status": "verified",
            "credit_score": 550,
            "current_rps_not": 0.72,
            "current_rps_360": 0.78,
            "risk_category": "high",
            "blacklisted": False,
        },
        {
            "user_id": 1004,
            "username": "emily_brown",
            "email": "emily.brown@example.com",
            "phone": "9876543213",
            "uin": "DDDD4567890123EEEE12",
            "occupation": "Doctor",
            "annual_income": 3000000.0,
            "kyc_status": "verified",
            "credit_score": 800,
            "current_rps_not": 0.08,
            "current_rps_360": 0.12,
            "risk_category": "low",
            "blacklisted": False,
        },
        {
            "user_id": 1005,
            "username": "michael_wilson",
            "email": "michael.wilson@example.com",
            "phone": "9876543214",
            "uin": "EEEE5678901234FFFF12",
            "occupation": "Real Estate Agent",
            "annual_income": 1800000.0,
            "kyc_status": "pending",
            "credit_score": 620,
            "current_rps_not": 0.55,
            "current_rps_360": 0.61,
            "risk_category": "medium",
            "blacklisted": False,
        },
        {
            "user_id": 1006,
            "username": "sarah_davis",
            "email": "sarah.davis@example.com",
            "phone": "9876543215",
            "uin": "FFFF6789012345GGGG12",
            "occupation": "Consultant",
            "annual_income": 900000.0,
            "kyc_status": "verified",
            "credit_score": 720,
            "current_rps_not": 0.25,
            "current_rps_360": 0.30,
            "risk_category": "low",
            "blacklisted": False,
        },
        {
            "user_id": 1007,
            "username": "david_martinez",
            "email": "david.martinez@example.com",
            "phone": "9876543216",
            "uin": "GGGG7890123456HHHH12",
            "occupation": "Import/Export",
            "annual_income": 8000000.0,
            "kyc_status": "verified",
            "credit_score": 480,
            "current_rps_not": 0.85,
            "current_rps_360": 0.92,
            "risk_category": "critical",
            "blacklisted": True,
            "blacklisted_at": datetime.utcnow() - timedelta(days=5),
        },
        {
            "user_id": 1008,
            "username": "lisa_anderson",
            "email": "lisa.anderson@example.com",
            "phone": "9876543217",
            "uin": "HHHH8901234567IIII12",
            "occupation": "Accountant",
            "annual_income": 1100000.0,
            "kyc_status": "verified",
            "credit_score": 780,
            "current_rps_not": 0.10,
            "current_rps_360": 0.15,
            "risk_category": "low",
            "blacklisted": False,
        },
        {
            "user_id": 1009,
            "username": "james_taylor",
            "email": "james.taylor@example.com",
            "phone": "9876543218",
            "uin": "IIII9012345678JJJJ12",
            "occupation": "Crypto Trader",
            "annual_income": 15000000.0,
            "kyc_status": "under_review",
            "credit_score": 590,
            "current_rps_not": 0.68,
            "current_rps_360": 0.75,
            "risk_category": "high",
            "blacklisted": False,
        },
        {
            "user_id": 1010,
            "username": "amanda_thomas",
            "email": "amanda.thomas@example.com",
            "phone": "9876543219",
            "uin": "JJJJ0123456789KKKK12",
            "occupation": "Lawyer",
            "annual_income": 2200000.0,
            "kyc_status": "verified",
            "credit_score": 760,
            "current_rps_not": 0.18,
            "current_rps_360": 0.24,
            "risk_category": "low",
            "blacklisted": False,
        },
    ]
    
    users = []
    for data in users_data:
        user = User(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            phone=data["phone"],
            uin=data["uin"],
            occupation=data["occupation"],
            annual_income=data["annual_income"],
            kyc_status=data["kyc_status"],
            credit_score=data["credit_score"],
            current_rps_not=data["current_rps_not"],
            current_rps_360=data["current_rps_360"],
            risk_category=data["risk_category"],
            blacklisted=data["blacklisted"],
            blacklisted_at=data.get("blacklisted_at"),
            # Ensure user is at least 18 years old (born between 1960-2006)
            date_of_birth=datetime(1960, 1, 1) + timedelta(days=random.randint(0, 16800)),  # ~46 years range
            address=f"{random.randint(1, 999)} Main Street, City {random.randint(1, 50)}",
            kyc_verified_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)) if data["kyc_status"] == "verified" else None,
            last_rps_calculation=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            version=1,
        )
        users.append(user)
        db.add(user)
    
    db.commit()
    print(f"✓ Created {len(users)} users")
    return users


def seed_transactions(db, users):
    """Seed transactions"""
    print("Seeding transactions...")
    
    txn_types = ["TRANSFER", "DEPOSIT", "WITHDRAWAL", "PAYMENT", "REFUND"]
    currencies = ["INR", "USD", "EUR", "GBP"]
    
    transactions = []
    txn_id = 5001
    
    for user in users:
        # Create 5-20 transactions per user
        num_txns = random.randint(5, 20)
        for _ in range(num_txns):
            is_fraud = 1 if random.random() < 0.05 else 0  # 5% fraud rate
            
            txn = Transaction(
                transaction_id=txn_id,
                user_id=user.user_id,
                timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23)),
                amount=round(random.uniform(100, 500000), 2),
                currency=random.choice(currencies),
                txn_type=random.choice(txn_types),
                counterparty_id=random.choice([u.user_id for u in users if u.user_id != user.user_id]),
                is_fraud=is_fraud
            )
            transactions.append(txn)
            db.add(txn)
            txn_id += 1
    
    db.commit()
    print(f"✓ Created {len(transactions)} transactions")
    return transactions


def seed_alerts(db, users, transactions):
    """Seed compliance alerts"""
    print("Seeding compliance alerts...")
    
    alert_types = ["kyc_alert", "transaction_alert", "fraud_alert", "aml_alert", "sanction_alert", "behavioral_alert"]
    severities = ["low", "medium", "high", "critical"]
    statuses = ["active", "investigating", "resolved", "dismissed", "escalated"]
    
    alerts = []
    
    # Create alerts for high-risk users and fraud transactions
    for user in users:
        if user.risk_category in ["high", "critical"] or user.blacklisted:
            # Create 2-5 alerts for high-risk users
            for i in range(random.randint(2, 5)):
                alert = ComplianceAlert(
                    user_id=user.user_id,
                    alert_type=random.choice(alert_types),
                    severity=random.choice(["high", "critical"]),
                    title=f"Risk Alert: {user.username}",
                    description=f"User {user.username} flagged due to elevated risk profile. RPS 360 Score: {user.current_rps_360}",
                    entity_id=str(user.user_id),
                    entity_type="user",
                    rps360=user.current_rps_360,
                    status=random.choice(statuses),
                    priority=random.choice(["high", "critical"]),
                    source="risk_engine",
                    triggered_by="automated_scan",
                    is_acknowledged=random.choice([True, False]),
                    acknowledged_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)) if random.choice([True, False]) else None,
                    acknowledged_by=random.choice(["admin1", "admin2", None]),
                    triggered_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                )
                alerts.append(alert)
                db.add(alert)
    
    # Create alerts for fraud transactions
    fraud_txns = [t for t in transactions if t.is_fraud == 1]
    for txn in fraud_txns:
        alert = ComplianceAlert(
            user_id=txn.user_id,
            transaction_id=txn.transaction_id,
            alert_type="fraud_alert",
            severity="critical",
            title=f"Fraud Detected: Transaction {txn.transaction_id}",
            description=f"Suspicious transaction of {txn.currency} {txn.amount} detected. Transaction flagged as potential fraud.",
            entity_id=str(txn.transaction_id),
            entity_type="transaction",
            rps360=0.85,
            status=random.choice(["active", "investigating"]),
            priority="critical",
            source="fraud_detection",
            triggered_by="ml_model",
            is_acknowledged=False,
            triggered_at=txn.txn_timestamp + timedelta(minutes=random.randint(1, 60)),
        )
        alerts.append(alert)
        db.add(alert)
    
    # Create some random alerts for other users
    for user in random.sample(users, min(5, len(users))):
        alert = ComplianceAlert(
            user_id=user.user_id,
            alert_type=random.choice(alert_types),
            severity=random.choice(severities),
            title=f"Compliance Check: {user.username}",
            description=f"Routine compliance check for user {user.username}",
            entity_id=str(user.user_id),
            entity_type="user",
            rps360=user.current_rps_360,
            status="active",
            priority="medium",
            source="compliance_engine",
            triggered_by="scheduled_scan",
            is_acknowledged=False,
            triggered_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
        )
        alerts.append(alert)
        db.add(alert)
    
    db.commit()
    print(f"✓ Created {len(alerts)} compliance alerts")
    return alerts


def seed_audit_logs(db, admins):
    """Seed audit logs"""
    print("Seeding audit logs...")
    
    action_types = ["classify_alert", "dismiss_alert", "blacklist_user", "whitelist_user", "other"]
    target_types = ["user", "alert", "transaction"]
    
    logs = []
    for _ in range(50):
        admin = random.choice(admins)
        action_type = random.choice(action_types)
        target_type = random.choice(target_types)
        
        log = AuditLog(
            admin_id=admin.id,
            action_type=action_type,
            action_description=f"Admin {admin.username} performed {action_type} on {target_type}",
            target_type=target_type,
            target_id=random.randint(1, 100),
            target_identifier=f"{target_type}_{random.randint(1, 100)}",
            action_metadata={"reason": "Routine review", "notes": "No issues found"},
            ip_address=f"192.168.1.{random.randint(1, 255)}",
        )
        logs.append(log)
        db.add(log)
    
    db.commit()
    print(f"✓ Created {len(logs)} audit logs")
    return logs


def seed_system_health(db):
    """Seed system health records"""
    print("Seeding system health...")
    
    components = ["sanctions_api", "fraud_detection", "kyc_service", "database", "cache"]
    check_types = ["api_health", "service_health", "db_health"]
    
    records = []
    for component in components:
        for _ in range(3):
            status = random.choice(["healthy", "healthy", "healthy", "degraded"])  # Mostly healthy
            severity = "info" if status == "healthy" else "warning"
            
            record = SystemHealth(
                check_type=random.choice(check_types),
                component_name=component,
                status=status,
                severity=severity,
                response_time_ms=random.randint(50, 500),
                is_resolved=status == "healthy",
                detected_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
            )
            records.append(record)
            db.add(record)
    
    db.commit()
    print(f"✓ Created {len(records)} system health records")
    return records


def seed_system_metrics(db):
    """Seed system metrics"""
    print("Seeding system metrics...")
    
    metrics = []
    
    # Alert hit rate metrics
    for i in range(7):  # Last 7 days
        date = datetime.utcnow() - timedelta(days=i)
        
        metrics.append(SystemMetrics(
            metric_type="alert_hit_rate",
            metric_category="alert",
            metric_value=round(random.uniform(70, 90), 2),
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=date.replace(hour=0, minute=0, second=0),
            aggregation_period_end=date.replace(hour=23, minute=59, second=59),
            total_count=random.randint(50, 200),
            positive_count=random.randint(40, 180),
        ))
        
        metrics.append(SystemMetrics(
            metric_type="false_positive_rate",
            metric_category="alert",
            metric_value=round(random.uniform(10, 30), 2),
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=date.replace(hour=0, minute=0, second=0),
            aggregation_period_end=date.replace(hour=23, minute=59, second=59),
            total_count=random.randint(50, 200),
            negative_count=random.randint(5, 60),
        ))
        
        metrics.append(SystemMetrics(
            metric_type="api_response_time",
            metric_category="api",
            metric_value=round(random.uniform(100, 500), 2),
            metric_unit="milliseconds",
            time_window="daily",
            aggregation_period_start=date.replace(hour=0, minute=0, second=0),
            aggregation_period_end=date.replace(hour=23, minute=59, second=59),
        ))
    
    for m in metrics:
        db.add(m)
    
    db.commit()
    print(f"✓ Created {len(metrics)} system metrics")
    return metrics


def check_existing_data(db):
    """Check what data exists in the database"""
    print("\n📊 Checking existing data in database...\n")
    
    tables = [
        ("admins", Admin),
        ("users", User),
        ("transactions", Transaction),
        ("compliance_alerts", ComplianceAlert),
        ("audit_logs", AuditLog),
        ("system_health", SystemHealth),
        ("system_metrics", SystemMetrics),
    ]
    
    has_data = False
    for table_name, model in tables:
        try:
            count = db.query(model).count()
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {table_name}: {count} records")
            if count > 0:
                has_data = True
        except Exception as e:
            print(f"  ✗ {table_name}: Error - {e}")
    
    return has_data


def main():
    """Main function to seed the database"""
    print("=" * 60)
    print("DATABASE SEED SCRIPT")
    print("=" * 60)
    
    # Create tables if they don't exist
    print("\n📦 Ensuring tables exist...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created/verified")
    
    db = SessionLocal()
    
    try:
        # Check existing data
        has_data = check_existing_data(db)
        
        if has_data:
            print("\n⚠️  Database already has data!")
            response = input("Do you want to clear and reseed? (y/N): ").strip().lower()
            if response != 'y':
                print("Aborting. No changes made.")
                return
        
        print("\n🌱 Seeding database with dummy data...\n")
        
        # Clear existing data
        clear_tables(db)
        
        # Seed in order of dependencies
        admins = seed_admins(db)
        users = seed_users(db)
        transactions = seed_transactions(db, users)
        alerts = seed_alerts(db, users, transactions)
        seed_audit_logs(db, admins)
        seed_system_health(db)
        seed_system_metrics(db)
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        
        # Show summary
        print("\n📋 SUMMARY:")
        check_existing_data(db)
        
        print("\n🔐 LOGIN CREDENTIALS:")
        print("  Username: superadmin | Password: superadmin123 | Role: superadmin")
        print("  Username: admin      | Password: admin123      | Role: admin")
        print("  Username: admin1     | Password: admin123      | Role: admin")
        print("  Username: admin2     | Password: admin123      | Role: admin")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

