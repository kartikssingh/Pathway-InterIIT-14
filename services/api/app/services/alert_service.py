from sqlalchemy.orm import Session
from app.models.alert import ComplianceAlert
from app.models.user import User
from app.schemas.alert import ComplianceAlertCreate, ComplianceAlertUpdate
from typing import Optional


def get_alerts(
    db: Session, 
    skip: int = 0, 
    limit: int = 20,
    severity: Optional[str] = None,
    status: Optional[str] = None
):
    """Get compliance alerts with optional filters"""
    query = db.query(ComplianceAlert).join(User)
    
    if severity and severity != "all":
        query = query.filter(ComplianceAlert.severity == severity.lower())
    
    if status and status != "all":
        query = query.filter(ComplianceAlert.status == status.lower())
    
    total = query.count()
    alerts = query.order_by(ComplianceAlert.created_at.desc()).offset(skip).limit(limit).all()
    
    # Enrich with user names
    result = []
    for alert in alerts:
        alert_dict = {
            "id": alert.id,
            "alert_id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "transaction_id": alert.transaction_id,
            "user_id": alert.user_id,
            "user_name": alert.user.applicant_name if alert.user else None,
            "entity_id": alert.entity_id,
            "entity_type": alert.entity_type,
            "rps360": alert.rps360,
            "status": alert.status,
            "priority": alert.priority,
            "is_acknowledged": alert.is_acknowledged,
            "acknowledged_at": alert.acknowledged_at,
            "acknowledged_by": alert.acknowledged_by,
            "dismissal_reason": alert.dismissal_reason,
            "source": alert.source,
            "triggered_by": alert.triggered_by,
            "alert_metadata": alert.alert_metadata,
            "triggered_at": getattr(alert, 'triggered_at', None) or alert.created_at,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at
        }
        result.append(alert_dict)
    
    return {"total": total, "items": result}


def get_alert(db: Session, alert_id: int):
    """Get a specific alert by ID"""
    return db.query(ComplianceAlert).filter(ComplianceAlert.id == alert_id).first()


def create_alert(db: Session, alert: ComplianceAlertCreate):
    """Create a new compliance alert"""
    db_alert = ComplianceAlert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


def update_alert(db: Session, alert_id: int, alert_update: ComplianceAlertUpdate):
    """Update an alert's status, assignee, or notes"""
    db_alert = get_alert(db, alert_id)
    if not db_alert:
        return None
    
    update_data = alert_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_alert, field, value)
    
    db.commit()
    db.refresh(db_alert)
    return db_alert


def create_high_risk_transaction_alert(db: Session, transaction_id: int, user_id: int, 
                                      amount: float, currency: str, rps360: float,
                                      transaction_type: str = None):
    """Helper function to create alert for high-risk transactions"""
    alert = ComplianceAlertCreate(
        alert_type="transaction_alert",
        severity="high" if rps360 >= 70 else "medium",
        title="High Risk Transaction Detected",
        description=f"Transaction amount {currency} {amount} detected with risk score {rps360}",
        transaction_id=transaction_id,
        user_id=user_id,
        entity_id=str(transaction_id),
        entity_type="transaction",
        rps360=rps360,
        priority="high" if rps360 >= 70 else "medium",
        source="transaction_monitoring",
        triggered_by="automated_risk_detection"
    )
    return create_alert(db, alert)
