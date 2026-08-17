"""
Comprehensive Database Population Script
Populates ALL tables with realistic data following schema constraints and relationships.

Usage: python scripts/populate_all_tables.py
"""

import sys
import os
from datetime import datetime, timedelta
import random
import hashlib
import json

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


def generate_hash(data: str) -> str:
    """Generate SHA256 hash (64 characters)"""
    return hashlib.sha256(data.encode()).hexdigest()


def generate_pathway_timestamp() -> int:
    """Generate Pathway timestamp (milliseconds since epoch)"""
    return int(datetime.utcnow().timestamp() * 1000)


def clear_tables(db):
    """Clear all tables before seeding (in correct order to respect foreign keys)"""
    print("Clearing existing data...")
    try:
        # Delete in order to respect foreign keys
        db.execute(text("DELETE FROM audit_logs"))
        db.execute(text("DELETE FROM system_alerts"))
        db.execute(text("DELETE FROM system_metrics"))
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
        Admin(
            username="admin3",
            email="admin3@example.com",
            hashed_password=ADMIN_PASSWORD_HASH,  # password: admin123
            role="admin",
            last_login_at=datetime.utcnow() - timedelta(days=2)
        ),
    ]
    
    for admin in admins:
        db.add(admin)
    
    db.commit()
    print(f"✓ Created {len(admins)} admins")
    return admins


def seed_users(db):
    """Seed user accounts with all required fields and constraints"""
    print("Seeding users...")
    
    occupations = [
        "Software Engineer", "Business Owner", "Trader", "Doctor", "Real Estate Agent",
        "Consultant", "Import/Export", "Accountant", "Crypto Trader", "Lawyer",
        "Investment Banker", "Entrepreneur", "Financial Advisor", "Merchant", "Freelancer"
    ]
    
    risk_categories = ["low", "medium", "high", "critical"]
    kyc_statuses = ["verified", "pending", "under_review", "rejected"]
    
    users = []
    user_id = 1001
    
    # Create 25 users with varied profiles
    for i in range(25):
        # Ensure user is at least 18 years old (born between 1960-2006)
        birth_year = random.randint(1960, 2006)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        date_of_birth = datetime(birth_year, birth_month, birth_day)
        
        # Generate UIN (20 characters)
        uin = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))}"
        uin_hash = generate_hash(uin)
        
        # Generate signature hash
        signature_data = f"user_{user_id}_{random.randint(1000, 9999)}"
        signature_hash = generate_hash(signature_data)
        
        # Credit score between 300-900 (constraint)
        credit_score = random.randint(300, 900)
        
        # Risk scores (0.0 to 1.0)
        current_rps_not = round(random.uniform(0.0, 1.0), 2)
        current_rps_360 = round(random.uniform(0.0, 1.0), 2)
        
        # Determine risk category based on scores
        if current_rps_360 < 0.2:
            risk_category = "low"
        elif current_rps_360 < 0.5:
            risk_category = "medium"
        elif current_rps_360 < 0.8:
            risk_category = "high"
        else:
            risk_category = "critical"
        
        # KYC status
        kyc_status = random.choice(kyc_statuses)
        
        # Blacklist some high-risk users
        blacklisted = risk_category == "critical" and random.random() < 0.3
        
        # Annual income
        annual_income = round(random.uniform(500000, 20000000), 2)
        
        # Pathway fields
        pathway_time = generate_pathway_timestamp() - random.randint(0, 86400000)  # Last 24 hours
        pathway_diff = random.randint(0, 10)
        
        user = User(
            user_id=user_id,
            username=f"user_{user_id}",
            email=f"user{user_id}@example.com",
            phone=f"9{random.randint(100000000, 999999999)}",
            uin=uin,
            uin_hash=uin_hash,
            profile_pic=f"https://example.com/profiles/{user_id}.jpg",
            date_of_birth=date_of_birth,
            address=f"{random.randint(1, 999)} {random.choice(['Main', 'Park', 'Oak', 'Elm'])} Street, {random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata'])}",
            occupation=random.choice(occupations),
            annual_income=annual_income,
            kyc_status=kyc_status,
            kyc_verified_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)) if kyc_status == "verified" else None,
            signature_hash=signature_hash,
            credit_score=credit_score,
            current_rps_not=current_rps_not,
            current_rps_360=current_rps_360,
            last_rps_calculation=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            risk_category=risk_category,
            blacklisted=blacklisted,
            blacklisted_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)) if blacklisted else None,
            version=1,
            time=pathway_time,
            diff=pathway_diff,
        )
        users.append(user)
        db.add(user)
        user_id += 1
    
    db.commit()
    print(f"✓ Created {len(users)} users")
    return users


def seed_transactions(db, users):
    """Seed transactions linked to users"""
    print("Seeding transactions...")
    
    if not users:
        print("⚠️  No users found. Cannot create transactions.")
        return []
    
    txn_types = ["TRANSFER", "DEPOSIT", "WITHDRAWAL", "PAYMENT", "REFUND", "EXCHANGE"]
    currencies = ["INR", "USD", "EUR", "GBP", "JPY"]
    
    transactions = []
    txn_id = 5001
    
    try:
        for user in users:
            # Create 3-15 transactions per user
            num_txns = random.randint(3, 15)
            for _ in range(num_txns):
                # 5% fraud rate
                is_fraud = 1 if random.random() < 0.05 else 0
                
                # Transaction timestamp (last 90 days)
                txn_timestamp = datetime.utcnow() - timedelta(
                    days=random.randint(0, 90),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Amount based on user's income (with fallback)
                if user.annual_income and user.annual_income > 0:
                    base_amount = user.annual_income / 365 / 10  # Rough daily income / 10
                    amount = round(random.uniform(base_amount * 0.1, base_amount * 5), 2)
                else:
                    # Fallback if annual_income is None or 0
                    amount = round(random.uniform(1000, 100000), 2)
                
                # Counterparty (another user)
                other_users = [u for u in users if u.user_id != user.user_id]
                counterparty_id = random.choice(other_users).user_id if other_users else None
                
                txn = Transaction(
                    transaction_id=txn_id,
                    user_id=user.user_id,
                    txn_timestamp=txn_timestamp,
                    amount=amount,
                    currency=random.choice(currencies),
                    txn_type=random.choice(txn_types),
                    counterparty_id=counterparty_id,
                    is_fraud=is_fraud
                )
                transactions.append(txn)
                db.add(txn)
                txn_id += 1
        
        db.commit()
        print(f"✓ Created {len(transactions)} transactions")
        return transactions
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating transactions: {e}")
        import traceback
        traceback.print_exc()
        raise


def seed_toxicity_history(db, users):
    """Seed toxicity history for users"""
    print("Seeding toxicity history...")
    
    history_records = []
    
    for user in users:
        # Create 1-5 history records per user
        num_records = random.randint(1, 5)
        for i in range(num_records):
            # Historical scores (can be different from current)
            rps_not = round(random.uniform(0.0, 1.0), 2)
            rps_360 = round(random.uniform(0.0, 1.0), 2)
            sanction_score = round(random.uniform(0.0, 1.0), 2)
            news_score = round(random.uniform(0.0, 1.0), 2)
            transaction_score = round(random.uniform(0.0, 1.0), 2)
            portfolio_score = round(random.uniform(0.0, 1.0), 2)
            
            calculation_triggers = ["scheduled", "transaction_update", "manual_recalc", "risk_alert"]
            
            pathway_time = generate_pathway_timestamp() - random.randint(0, 259200000)  # Last 3 days
            pathway_diff = random.randint(0, 5)
            
            record = ToxicityHistory(
                user_id=user.user_id,
                rps_not=rps_not,
                rps_360=rps_360,
                sanction_score=sanction_score,
                news_score=news_score,
                transaction_score=transaction_score,
                portfolio_score=portfolio_score,
                calculated_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                calculation_trigger=random.choice(calculation_triggers),
                time=pathway_time,
                diff=pathway_diff,
            )
            history_records.append(record)
            db.add(record)
    
    db.commit()
    print(f"✓ Created {len(history_records)} toxicity history records")
    return history_records


def seed_sanction_matches(db, users):
    """Seed sanction matches for users"""
    print("Seeding sanction matches...")
    
    matches = []
    
    # Some users have sanction matches (10-20% of users)
    users_with_matches = random.sample(users, min(len(users) // 5, len(users)))
    
    sanction_names = [
        "John Smith", "Ahmed Hassan", "Maria Rodriguez", "Vladimir Petrov",
        "Chen Wei", "Mohammed Ali", "Robert Johnson", "Sarah Williams"
    ]
    
    for user in users_with_matches:
        match_found = random.choice([True, False])
        match_confidence = round(random.uniform(0.0, 1.0), 2) if match_found else round(random.uniform(0.0, 0.3), 2)
        matched_entity_name = random.choice(sanction_names) if match_found else None
        
        pathway_time = generate_pathway_timestamp() - random.randint(0, 172800000)  # Last 2 days
        pathway_diff = random.randint(0, 3)
        
        match = UserSanctionMatch(
            user_id=user.user_id,
            match_found=match_found,
            match_confidence=match_confidence,
            matched_entity_name=matched_entity_name,
            checked_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            time=pathway_time,
            diff=pathway_diff,
        )
        matches.append(match)
        db.add(match)
    
    db.commit()
    print(f"✓ Created {len(matches)} sanction matches")
    return matches


def seed_alerts(db, users, transactions):
    """Seed compliance alerts linked to users and transactions"""
    print("Seeding compliance alerts...")
    
    alert_types = ["kyc_alert", "transaction_alert", "fraud_alert", "aml_alert", "sanction_alert", "behavioral_alert"]
    severities = ["low", "medium", "high", "critical"]
    statuses = ["active", "investigating", "resolved", "dismissed", "escalated"]
    priorities = ["low", "medium", "high", "critical"]
    sources = ["risk_engine", "fraud_detection", "compliance_engine", "ml_model", "manual_review"]
    triggers = ["automated_scan", "scheduled_scan", "ml_model", "admin_action", "threshold_breach"]
    
    alerts = []
    
    # Create alerts for high-risk users
    for user in users:
        if user.risk_category in ["high", "critical"] or user.blacklisted:
            # Create 2-5 alerts for high-risk users
            for _ in range(random.randint(2, 5)):
                alert = ComplianceAlert(
                    user_id=user.user_id,
                    alert_type=random.choice(alert_types),
                    severity=random.choice(["high", "critical"]),
                    title=f"Risk Alert: {user.username}",
                    description=f"User {user.username} flagged due to elevated risk profile. RPS 360 Score: {user.current_rps_360:.2f}",
                    entity_id=str(user.user_id),
                    entity_type="user",
                    rps360=user.current_rps_360,
                    status=random.choice(statuses),
                    priority=random.choice(["high", "critical"]),
                    source=random.choice(sources),
                    triggered_by=random.choice(triggers),
                    is_acknowledged=random.choice([True, False]),
                    acknowledged_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)) if random.choice([True, False]) else None,
                    acknowledged_by=random.choice(["admin1", "admin2", "admin3", None]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
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
            description=f"Suspicious transaction of {txn.currency} {txn.amount:,.2f} detected. Transaction flagged as potential fraud.",
            entity_id=str(txn.transaction_id),
            entity_type="transaction",
            rps360=0.85,
            status=random.choice(["active", "investigating"]),
            priority="critical",
            source="fraud_detection",
            triggered_by="ml_model",
            is_acknowledged=False,
            created_at=txn.txn_timestamp + timedelta(minutes=random.randint(1, 60)),
        )
        alerts.append(alert)
        db.add(alert)
    
    # Create some random alerts for other users
    for user in random.sample(users, min(10, len(users))):
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
            priority=random.choice(priorities),
            source=random.choice(sources),
            triggered_by=random.choice(triggers),
            is_acknowledged=False,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
        )
        alerts.append(alert)
        db.add(alert)
    
    db.commit()
    print(f"✓ Created {len(alerts)} compliance alerts")
    return alerts


def seed_audit_logs(db, admins, users, alerts):
    """Seed audit logs linked to admins"""
    print("Seeding audit logs...")
    
    action_types = [
        "classify_alert", "dismiss_alert", "escalate_alert",
        "blacklist_user", "whitelist_user", "flag_user", "unflag_user",
        "block_transaction", "approve_transaction", "update_system_alert",
        "resolve_health_check", "other"
    ]
    target_types = ["user", "alert", "transaction", "system"]
    
    logs = []
    
    # Create audit logs for admin actions on alerts
    for alert in random.sample(alerts, min(20, len(alerts))):
        admin = random.choice(admins)
        action_type = random.choice(["classify_alert", "dismiss_alert", "escalate_alert"])
        
        log = AuditLog(
            admin_id=admin.id,
            action_type=action_type,
            action_description=f"Admin {admin.username} performed {action_type} on alert {alert.id}",
            target_type="alert",
            target_id=alert.id,
            target_identifier=f"alert_{alert.id}",
            action_metadata={
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "reason": "Routine review",
                "notes": "Action taken based on risk assessment"
            },
            ip_address=f"192.168.1.{random.randint(1, 255)}",
        )
        logs.append(log)
        db.add(log)
    
    # Create audit logs for user actions
    for user in random.sample(users, min(15, len(users))):
        admin = random.choice(admins)
        if user.blacklisted:
            action_type = "blacklist_user"
        else:
            action_type = random.choice(["flag_user", "whitelist_user", "other"])
        
        log = AuditLog(
            admin_id=admin.id,
            action_type=action_type,
            action_description=f"Admin {admin.username} performed {action_type} on user {user.user_id}",
            target_type="user",
            target_id=user.user_id,
            target_identifier=f"user_{user.user_id}",
            action_metadata={
                "user_id": user.user_id,
                "username": user.username,
                "risk_category": user.risk_category,
                "reason": "Risk assessment review"
            },
            ip_address=f"192.168.1.{random.randint(1, 255)}",
        )
        logs.append(log)
        db.add(log)
    
    # Create some general audit logs
    for _ in range(20):
        admin = random.choice(admins)
        action_type = random.choice(action_types)
        target_type = random.choice(target_types)
        
        log = AuditLog(
            admin_id=admin.id,
            action_type=action_type,
            action_description=f"Admin {admin.username} performed {action_type} on {target_type}",
            target_type=target_type,
            target_id=random.randint(1, 1000),
            target_identifier=f"{target_type}_{random.randint(1, 1000)}",
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
    
    components = ["sanctions_api", "fraud_detection", "kyc_service", "database", "cache", "transaction_parser"]
    check_types = ["api_health", "parser_health", "db_health", "service_health"]
    statuses = ["healthy", "degraded", "failed", "recovering"]
    severities = ["info", "warning", "error", "critical"]
    error_types = ["connection_timeout", "parse_error", "api_rate_limit", "database_connection_failed", None]
    
    records = []
    
    for component in components:
        for _ in range(random.randint(2, 5)):
            # Mostly healthy (80% healthy, 20% issues)
            if random.random() < 0.8:
                status = "healthy"
                severity = "info"
                error_type = None
                is_resolved = True
            else:
                status = random.choice(["degraded", "failed", "recovering"])
                severity = random.choice(["warning", "error", "critical"])
                error_type = random.choice(error_types)
                is_resolved = random.choice([True, False])
            
            record = SystemHealth(
                check_type=random.choice(check_types),
                component_name=component,
                status=status,
                severity=severity,
                error_type=error_type,
                error_message=f"Error in {component}" if error_type else None,
                response_time_ms=random.randint(50, 1000),
                retry_count=random.randint(0, 3) if error_type else 0,
                is_resolved=is_resolved,
                resolved_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)) if is_resolved else None,
                auto_recovered=is_resolved and random.choice([True, False]),
                detected_at=datetime.utcnow() - timedelta(hours=random.randint(0, 48)),
                last_occurrence=datetime.utcnow() - timedelta(hours=random.randint(0, 24)),
                user_impact=random.choice(["none", "low", "medium", "high"]) if status != "healthy" else "none",
            )
            records.append(record)
            db.add(record)
    
    db.commit()
    print(f"✓ Created {len(records)} system health records")
    return records


def seed_system_alerts(db, system_health_records):
    """Seed system alerts"""
    print("Seeding system alerts...")
    
    alert_types = ["high_error_rate", "api_downtime", "anomaly_detected", "threshold_breach"]
    severities = ["warning", "error", "critical"]
    statuses = ["active", "acknowledged", "resolved", "false_alarm"]
    
    alerts = []
    
    # Create alerts for failed/degraded system health
    for health in system_health_records:
        if health.status in ["failed", "degraded"]:
            alert = SystemAlert(
                alert_type="api_downtime" if "api" in health.component_name else "anomaly_detected",
                title=f"{health.component_name} - {health.status}",
                description=f"Component {health.component_name} is experiencing issues: {health.status}",
                severity=health.severity,
                component=health.component_name,
                metric_type=health.check_type,
                threshold_value="100%",
                actual_value=health.status,
                alert_data={
                    "check_type": health.check_type,
                    "error_type": health.error_type,
                    "response_time_ms": health.response_time_ms
                },
                status=random.choice(statuses),
                acknowledged_by=random.choice(["superadmin", "admin1", None]),
                acknowledged_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)) if random.choice([True, False]) else None,
                resolved_at=datetime.utcnow() - timedelta(hours=random.randint(1, 6)) if health.is_resolved else None,
                triggered_at=health.detected_at,
            )
            alerts.append(alert)
            db.add(alert)
    
    # Create some general system alerts
    for _ in range(5):
        alert = SystemAlert(
            alert_type=random.choice(alert_types),
            title=f"System Alert: {random.choice(['High Error Rate', 'Performance Degradation', 'Anomaly Detected'])}",
            description=f"System monitoring detected an anomaly requiring attention",
            severity=random.choice(severities),
            component=random.choice(["system", "database", "api_gateway"]),
            metric_type=random.choice(["error_rate", "response_time", "throughput"]),
            threshold_value=str(random.randint(80, 95)),
            actual_value=str(random.randint(95, 100)),
            alert_data={"timestamp": datetime.utcnow().isoformat()},
            status=random.choice(statuses),
            triggered_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
        )
        alerts.append(alert)
        db.add(alert)
    
    db.commit()
    print(f"✓ Created {len(alerts)} system alerts")
    return alerts


def seed_system_metrics(db):
    """Seed system metrics"""
    print("Seeding system metrics...")
    
    metrics = []
    
    # Generate metrics for last 14 days
    for i in range(14):
        date = datetime.utcnow() - timedelta(days=i)
        period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = date.replace(hour=23, minute=59, second=59, microsecond=0)
        
        # Alert hit rate
        total_alerts = random.randint(50, 300)
        positive_count = random.randint(int(total_alerts * 0.6), int(total_alerts * 0.9))
        hit_rate = round((positive_count / total_alerts) * 100, 2)
        
        metrics.append(SystemMetrics(
            metric_type="alert_hit_rate",
            metric_category="alert",
            metric_value=hit_rate,
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=period_start,
            aggregation_period_end=period_end,
            total_count=total_alerts,
            positive_count=positive_count,
            negative_count=total_alerts - positive_count,
            recorded_at=period_end,
        ))
        
        # False positive rate
        false_positives = random.randint(5, 50)
        false_positive_rate = round((false_positives / total_alerts) * 100, 2)
        
        metrics.append(SystemMetrics(
            metric_type="false_positive_rate",
            metric_category="alert",
            metric_value=false_positive_rate,
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=period_start,
            aggregation_period_end=period_end,
            total_count=total_alerts,
            negative_count=false_positives,
            recorded_at=period_end,
        ))
        
        # API response time
        metrics.append(SystemMetrics(
            metric_type="api_response_time",
            metric_category="api",
            metric_value=round(random.uniform(100, 800), 2),
            metric_unit="milliseconds",
            time_window="daily",
            aggregation_period_start=period_start,
            aggregation_period_end=period_end,
            recorded_at=period_end,
        ))
        
        # API error rate
        error_rate = round(random.uniform(0.1, 5.0), 2)
        metrics.append(SystemMetrics(
            metric_type="api_error_rate",
            metric_category="api",
            metric_value=error_rate,
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=period_start,
            aggregation_period_end=period_end,
            is_anomaly=error_rate > 3.0,
            anomaly_threshold=3.0 if error_rate > 3.0 else None,
            recorded_at=period_end,
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
        ("toxicityhistory", ToxicityHistory),
        ("usersanctionmatches", UserSanctionMatch),
        ("system_health", SystemHealth),
        ("system_alerts", SystemAlert),
        ("system_metrics", SystemMetrics),
    ]
    
    has_data = False
    total_records = 0
    for table_name, model in tables:
        try:
            count = db.query(model).count()
            status = "✓" if count > 0 else "✗"
            print(f"  {status} {table_name:25} {count:>6} records")
            if count > 0:
                has_data = True
                total_records += count
        except Exception as e:
            print(f"  ✗ {table_name:25} Error - {e}")
    
    print(f"\n  Total records across all tables: {total_records}")
    return has_data


def main():
    """Main function to populate the database"""
    print("=" * 80)
    print("COMPREHENSIVE DATABASE POPULATION SCRIPT")
    print("=" * 80)
    
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
            response = input("Do you want to clear and repopulate? (y/N): ").strip().lower()
            if response != 'y':
                print("Aborting. No changes made.")
                return
        
        print("\n🌱 Populating database with realistic data...\n")
        
        # Clear existing data
        clear_tables(db)
        
        # Seed in order of dependencies
        admins = seed_admins(db)
        if not admins:
            raise Exception("Failed to create admins")
        
        users = seed_users(db)
        if not users:
            raise Exception("Failed to create users. Cannot proceed with transactions.")
        
        print(f"✓ Verified {len(users)} users exist before creating transactions")
        transactions = seed_transactions(db, users)
        if not transactions:
            print("⚠️  Warning: No transactions were created!")
        else:
            print(f"✓ Verified {len(transactions)} transactions created successfully")
        
        toxicity_history = seed_toxicity_history(db, users)
        sanction_matches = seed_sanction_matches(db, users)
        alerts = seed_alerts(db, users, transactions)
        audit_logs = seed_audit_logs(db, admins, users, alerts)
        system_health = seed_system_health(db)
        system_alerts = seed_system_alerts(db, system_health)
        system_metrics = seed_system_metrics(db)
        
        print("\n" + "=" * 80)
        print("✅ DATABASE POPULATED SUCCESSFULLY!")
        print("=" * 80)
        
        # Verify transactions were actually saved
        txn_count = db.query(Transaction).count()
        user_count = db.query(User).count()
        print(f"\n🔍 Verification: {user_count} users, {txn_count} transactions in database")
        
        if txn_count == 0 and user_count > 0:
            print("⚠️  WARNING: Users exist but no transactions found!")
            print("   This might indicate an issue with transaction creation.")
        
        # Show summary
        print("\n📋 SUMMARY:")
        check_existing_data(db)
        
        print("\n🔐 LOGIN CREDENTIALS:")
        print("  Username: superadmin | Password: superadmin123 | Role: superadmin")
        print("  Username: admin      | Password: admin123      | Role: admin")
        print("  Username: admin1     | Password: admin123      | Role: admin")
        print("  Username: admin2     | Password: admin123      | Role: admin")
        print("  Username: admin3     | Password: admin123      | Role: admin")
        
        print("\n✅ All tables populated with realistic data following schema constraints!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error populating database: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

