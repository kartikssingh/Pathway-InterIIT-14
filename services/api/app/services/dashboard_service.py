from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from app.models import user, transaction
from app.models.alert import ComplianceAlert
# from app.models.case import InvestigationCase, AccountHold
from app.schemas import dashboard
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import uuid


def get_summary(db: Session) -> dashboard.DashboardSummary:
    """Get overall dashboard summary statistics"""
    total_users = db.query(user.User).count()
    
    # Count total transactions (new schema: individual transaction records)
    total_transactions = db.query(transaction.Transaction).count()
    
    blacklisted_users = db.query(user.User).filter(user.User.blacklisted == True).count()
    high_risk_users = db.query(user.User).filter(user.User.current_rps_360 >= 0.6).count()
    
    # RPS scores are stored as 0-1 in database, multiply by 100 for percentage display
    # Ensure we handle None values properly
    avg_score = db.query(func.avg(user.User.current_rps_360)).filter(user.User.current_rps_360.isnot(None)).scalar()
    average_i360_score = float(avg_score) if avg_score is not None else 0.0
    
    # Total volume from individual transactions
    total_volume = db.query(func.sum(transaction.Transaction.amount)).scalar()
    total_volume = float(total_volume) if total_volume else 0.0
    
    avg_i_not = db.query(func.avg(user.User.current_rps_not)).filter(user.User.current_rps_not.isnot(None)).scalar()
    average_i_not_score = float(avg_i_not * 100) if avg_i_not is not None else 0.0
    
    return dashboard.DashboardSummary(
        total_users=total_users,
        total_transactions=total_transactions,
        blacklisted_users=blacklisted_users,
        high_risk_users=high_risk_users,
        average_i360_score=round(average_i360_score, 2),
        total_volume=round(total_volume, 2),
        average_i_not_score=round(average_i_not_score, 2)
    )


def get_risk_distribution(db: Session) -> dashboard.RiskDistribution:
    """Get risk distribution across all users"""
    # Risk category is now a string field
    low_risk = db.query(user.User).filter(user.User.risk_category == 'low').count()
    medium_risk = db.query(user.User).filter(user.User.risk_category == 'medium').count()
    high_risk = db.query(user.User).filter(user.User.risk_category == 'high').count()
    critical_risk = db.query(user.User).filter(user.User.risk_category == 'critical').count()
    
    return dashboard.RiskDistribution(
        low_risk=low_risk,
        medium_risk=medium_risk,
        high_risk=high_risk,
        critical_risk=critical_risk
    )


def get_flagged_transactions(db: Session, limit: int = 10) -> list:
    """Get transactions flagged as fraudulent or high-value suspicious transactions."""
    # Get fraud-flagged transactions first
    flagged = (
        db.query(transaction.Transaction)
        .join(user.User, transaction.Transaction.user_id == user.User.user_id)
        .filter(transaction.Transaction.is_fraud == 1)
        .order_by(desc(transaction.Transaction.amount))
        .limit(limit)
        .all()
    )
    
    # If not enough fraud transactions, supplement with high-value transactions
    if len(flagged) < limit:
        remaining = limit - len(flagged)
        high_value = (
            db.query(transaction.Transaction)
            .join(user.User, transaction.Transaction.user_id == user.User.user_id)
            .filter(transaction.Transaction.is_fraud != 1)
            .order_by(desc(transaction.Transaction.amount))
            .limit(remaining)
            .all()
        )
        flagged.extend(high_value)
    
    result = []
    for tx_record in flagged:
        result.append({
            "transaction_id": tx_record.transaction_id,
            "user_id": tx_record.user_id,
            "user_name": tx_record.user.username if tx_record.user else None,
            "amount": tx_record.amount,
            "currency": tx_record.currency or "INR",
            "suspicious_score": 100 if tx_record.is_fraud == 1 else min(100, (tx_record.amount or 0) / 10000),
            "transaction_type": tx_record.txn_type,
            "is_fraud": tx_record.is_fraud,
            "created_at": tx_record.txn_timestamp.isoformat() if tx_record.txn_timestamp else ""
        })
    
    return result


def get_critical_alerts(
    db: Session, 
    limit: int = 10, 
    severity: Optional[str] = None, 
    hours: int = 24
) -> List[dashboard.CriticalAlert]:
    """Get critical alerts with optional filtering"""
    # Calculate time threshold (use timezone-aware datetime for proper DB comparison)
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Build query (use left outer join since user_id is nullable)
    query = db.query(ComplianceAlert).outerjoin(
        user.User, ComplianceAlert.user_id == user.User.user_id
    )
    
    # Use created_at for time filtering (triggered_at will be used in response mapping)
    query = query.filter(ComplianceAlert.created_at >= time_threshold)
    
    # Apply severity filter
    if severity and severity.upper() != "ALL":
        query = query.filter(ComplianceAlert.severity == severity.lower())
    
    # Order by time and limit
    alerts = query.order_by(desc(ComplianceAlert.created_at)).limit(limit).all()
    
    result = []
    now = datetime.now(timezone.utc)
    for alert in alerts:
        # Use triggered_at if available, fallback to created_at
        alert_time = getattr(alert, 'triggered_at', None) or alert.created_at
        time_diff = (now - alert_time).total_seconds()
        
        # Parse metadata JSON if present
        metadata = {}
        if alert.alert_metadata:
            try:
                import json
                metadata = json.loads(alert.alert_metadata)
            except:
                metadata = {}
        
        result.append(dashboard.CriticalAlert(
            id=f"alert_{alert.id}",
            alert_type=alert.alert_type,
            severity=alert.severity,
            description=alert.description or "",
            user_id=alert.user_id if alert.user_id else 0,
            user_name=alert.user.username if alert.user else None,
            transaction_id=alert.transaction_id if hasattr(alert, 'transaction_id') else None,
            amount=alert.transaction.amount if alert.transaction else None,
            triggered_at=alert_time.isoformat(),
            time_ago_seconds=int(time_diff),
            is_acknowledged=alert.is_acknowledged,
            assigned_to=None  # Not in new schema
        ))
    
    return result


def get_live_alerts(
    db: Session, 
    limit: int = 20, 
    since: Optional[datetime] = None
) -> List[dashboard.LiveAlert]:
    """Get live alert feed"""
    query = db.query(ComplianceAlert)
    
    # Apply time filter if provided (use created_at for filtering)
    if since:
        query = query.filter(ComplianceAlert.created_at > since)
    
    # Order by time and limit
    alerts = query.order_by(desc(ComplianceAlert.created_at)).limit(limit).all()
    
    result = []
    for alert in alerts:
        # Use triggered_at if available, fallback to created_at
        alert_time = getattr(alert, 'triggered_at', None) or alert.created_at
        result.append(dashboard.LiveAlert(
            id=f"alert_{alert.id}",
            severity=alert.severity,
            triggered_at=alert_time.isoformat(),
            time_display=alert_time.strftime("%H:%M:%S")
        ))
    
    return result


def get_alert_trend(
    db: Session,
    period: str = "1h",
    interval: str = "5m",
    severity: Optional[str] = None
) -> dashboard.AlertTrendResponse:
    """Get alert trend data for visualization"""
    # Parse period to get time range
    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    interval_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1)
    }
    
    time_range = period_map.get(period, timedelta(hours=1))
    interval_delta = interval_map.get(interval, timedelta(minutes=5))
    
    start_time = datetime.now(timezone.utc) - time_range
    
    # Get all alerts in the time range (use created_at for filtering)
    query = db.query(ComplianceAlert).filter(ComplianceAlert.created_at >= start_time)
    
    if severity and severity.lower() != "all":
        query = query.filter(ComplianceAlert.severity == severity.lower())
    
    alerts = query.all()
    
    # Generate time buckets
    data_points = []
    current_time = start_time
    total_alerts = 0
    
    while current_time <= datetime.now(timezone.utc):
        next_time = current_time + interval_delta
        
        # Count alerts in this bucket (use triggered_at if available)
        bucket_alerts = []
        for a in alerts:
            alert_time = getattr(a, 'triggered_at', None) or a.created_at
            if current_time <= alert_time < next_time:
                bucket_alerts.append(a)
        
        critical_count = sum(1 for a in bucket_alerts if a.severity == "critical")
        high_count = sum(1 for a in bucket_alerts if a.severity == "high")
        medium_count = sum(1 for a in bucket_alerts if a.severity == "medium")
        low_count = sum(1 for a in bucket_alerts if a.severity == "low")
        
        count = len(bucket_alerts)
        total_alerts += count
        
        data_points.append(dashboard.AlertTrendDataPoint(
            timestamp=current_time.isoformat(),
            count=count,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count
        ))
        
        current_time = next_time
    
    avg_per_interval = total_alerts / len(data_points) if data_points else 0
    
    return dashboard.AlertTrendResponse(
        period=period,
        interval=interval,
        data_points=data_points,
        total_alerts=total_alerts,
        avg_per_interval=round(avg_per_interval, 1)
    )


def dismiss_alert(
    db: Session,
    alert_id: str,
    reason: Optional[str] = None,
    notes: Optional[str] = None,
    dismissed_by: str = "admin_user"
) -> dashboard.AlertDismissResponse:
    """Dismiss/acknowledge an alert"""
    # Extract numeric ID from "alert_123" format
    numeric_id = int(alert_id.replace("alert_", "")) if alert_id.startswith("alert_") else int(alert_id)
    
    alert = db.query(ComplianceAlert).filter(ComplianceAlert.id == numeric_id).first()
    
    if not alert:
        raise ValueError(f"Alert {alert_id} not found")
    
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = dismissed_by
    alert.dismissal_reason = reason if reason else notes  # Store notes in dismissal_reason if reason not provided
    alert.status = "dismissed"
    
    db.commit()
    
    return dashboard.AlertDismissResponse(
        success=True,
        alert_id=f"alert_{numeric_id}",
        dismissed_at=alert.acknowledged_at.isoformat(),
        dismissed_by=dismissed_by
    )


# def create_investigation_case(
#     db: Session,
#     case_data: dashboard.CaseCreateRequest
# ) -> dashboard.CaseCreateResponse:
#     """Create a new investigation case"""
#     # Generate case ID
#     case_count = db.query(InvestigationCase).count()
#     case_id = f"CASE-{datetime.utcnow().year}-{(case_count + 1):05d}"
#     
#     # Verify user exists
#     user_exists = db.query(user.User).filter(user.User.id == case_data.user_id).first()
#     if not user_exists:
#         raise ValueError(f"User {case_data.user_id} not found")
#     
#     # Create case
#     new_case = InvestigationCase(
#         id=case_id,
#         title=case_data.title,
#         description=case_data.description,
#         user_id=case_data.user_id,
#         priority=case_data.priority,
#         status="OPEN",
#         assigned_to=case_data.assigned_to,
#         transaction_ids=case_data.transaction_ids,
#         alert_ids=case_data.alert_ids
#     )
#     
#     db.add(new_case)
#     db.commit()
#     db.refresh(new_case)
#     
#     return dashboard.CaseCreateResponse(
#         success=True,
#         case_id=case_id,
#         created_at=new_case.created_at.isoformat(),
#         status=new_case.status,
#         assigned_to=new_case.assigned_to
#     )


# def place_account_hold(
#     db: Session,
#     user_id: int,
#     hold_data: dashboard.AccountHoldRequest,
#     placed_by: str = "admin_user"
# ) -> dashboard.AccountHoldResponse:
#     """Place a hold on a user account"""
#     # Verify user exists
#     user_exists = db.query(user.User).filter(user.User.id == user_id).first()
#     if not user_exists:
#         raise ValueError(f"User {user_id} not found")
#     
#     # Check for existing active hold
#     existing_hold = db.query(AccountHold).filter(
#         AccountHold.user_id == user_id,
#         AccountHold.status == "ACTIVE"
#     ).first()
#     
#     if existing_hold:
#         raise ValueError(f"User {user_id} already has an active hold")
#     
#     # Generate hold ID
#     hold_count = db.query(AccountHold).count()
#     hold_id = f"HOLD-{datetime.utcnow().year}-{(hold_count + 1):05d}"
#     
#     # Calculate expiry time
#     hold_expires_at = None
#     if hold_data.duration_hours:
#         hold_expires_at = datetime.utcnow() + timedelta(hours=hold_data.duration_hours)
#     
#     # Create hold
#     new_hold = AccountHold(
#         id=hold_id,
#         user_id=user_id,
#         reason=hold_data.reason,
#         hold_type=hold_data.hold_type,
#         status="ACTIVE",
#         notes=hold_data.notes,
#         hold_expires_at=hold_expires_at,
#         placed_by=placed_by
#     )
#     
#     db.add(new_hold)
#     db.commit()
#     db.refresh(new_hold)
#     
#     return dashboard.AccountHoldResponse(
#         success=True,
#         user_id=user_id,
#         hold_id=hold_id,
#         hold_placed_at=new_hold.hold_placed_at.isoformat(),
#         hold_expires_at=new_hold.hold_expires_at.isoformat() if new_hold.hold_expires_at else None,
#         hold_type=new_hold.hold_type,
#         status=new_hold.status
#     )
