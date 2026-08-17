"""
Compliance alerts routes - matching core_schema.sql
Provides endpoints for managing compliance_alerts table
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timezone

from app.db import get_db
from app.models.alert import ComplianceAlert
from app.models.user import User
from app.schemas.alert import (
    ComplianceAlertCreate, ComplianceAlertUpdate, ComplianceAlertRead
)
from app.models.admin import Admin
from app.services.auth_dependencies import require_admin, get_client_ip
from app.services.auth_service import AuthService

router = APIRouter(prefix="/compliance", tags=["Compliance Alerts"])


# ==================== Alert List Response Schema ====================

from pydantic import BaseModel
from typing import List as ListType


class AlertListResponse(BaseModel):
    """Response schema for paginated alert list"""
    total: int
    items: ListType[ComplianceAlertRead]
    limit: int
    offset: int


# ==================== Endpoints ====================

@router.get("/alerts", response_model=AlertListResponse)
def get_compliance_alerts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical, all)"),
    status: Optional[str] = Query(None, description="Filter by status (active, investigating, resolved, dismissed, escalated)"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db)
):
    """
    Get compliance alerts with filtering and pagination.
    
    This replaces the old 'unclassified' endpoint - use status='active' for pending alerts.
    """
    query = db.query(ComplianceAlert).outerjoin(
        User, ComplianceAlert.user_id == User.user_id
    )
    
    # Apply filters
    if severity and severity.lower() != "all":
        query = query.filter(ComplianceAlert.severity == severity.lower())
    
    if status and status.lower() != "all":
        query = query.filter(ComplianceAlert.status == status.lower())
    
    if alert_type:
        query = query.filter(ComplianceAlert.alert_type == alert_type)
    
    if user_id:
        query = query.filter(ComplianceAlert.user_id == user_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    alerts = query.order_by(desc(ComplianceAlert.created_at)).offset(offset).limit(limit).all()
    
    # Build response
    items = []
    for alert in alerts:
        alert_dict = {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "user_id": alert.user_id,
            "user_name": alert.user.username if alert.user else None,
            "transaction_id": alert.transaction_id,
            "entity_id": alert.entity_id,
            "entity_type": alert.entity_type,
            "rps360": alert.rps360,
            "priority": alert.priority,
            "source": alert.source,
            "triggered_by": alert.triggered_by,
            "alert_metadata": alert.alert_metadata,
            "triggered_at": alert.triggered_at,
            "status": alert.status,
            "is_acknowledged": alert.is_acknowledged,
            "acknowledged_at": alert.acknowledged_at,
            "acknowledged_by": alert.acknowledged_by,
            "dismissal_reason": alert.dismissal_reason,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at
        }
        items.append(ComplianceAlertRead(**alert_dict))
    
    return AlertListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset
    )


# NOTE: the literal `/alerts/top` route must stay above `/alerts/{alert_id}`.
# FastAPI matches in declaration order, so with the dynamic route first a GET on
# /compliance/alerts/top was matched against `alert_id: int` and returned 422.
@router.get("/alerts/top")
def get_top_alerts(
    k: int = Query(10, ge=1, le=100, description="Number of top alerts to return"),
    status: Optional[str] = Query("active", description="Filter by status (active, investigating, all)"),
    db: Session = Depends(get_db)
):
    """
    Get top K most critical compliance alerts.
    
    Alerts are ranked by:
    1. Severity (critical > high > medium > low)
    2. Recency (most recent first)
    
    - **k**: Number of alerts to return (1-100, default 10)
    - **status**: Filter by status (active, investigating, or all for pending alerts)
    """
    from sqlalchemy import case
    
    # Define severity ordering (higher = more critical)
    severity_order = case(
        (ComplianceAlert.severity == 'critical', 4),
        (ComplianceAlert.severity == 'high', 3),
        (ComplianceAlert.severity == 'medium', 2),
        (ComplianceAlert.severity == 'low', 1),
        else_=0
    )
    
    query = db.query(ComplianceAlert).outerjoin(
        User, ComplianceAlert.user_id == User.user_id
    )
    
    # Apply status filter
    if status and status.lower() != "all":
        if status.lower() == "pending":
            query = query.filter(ComplianceAlert.status.in_(['active', 'investigating']))
        else:
            query = query.filter(ComplianceAlert.status == status.lower())
    else:
        # Default to pending alerts (active + investigating)
        query = query.filter(ComplianceAlert.status.in_(['active', 'investigating']))
    
    # Order by severity (descending) then by created_at (most recent first)
    alerts = query.order_by(
        severity_order.desc(),
        desc(ComplianceAlert.created_at)
    ).limit(k).all()
    
    # Build response
    result = []
    for alert in alerts:
        result.append({
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "user_id": alert.user_id,
            "user_name": alert.user.username if alert.user else None,
            "transaction_id": alert.transaction_id,
            "entity_id": alert.entity_id,
            "rps360": alert.rps360,
            "status": alert.status,
            "priority": alert.priority,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "is_acknowledged": alert.is_acknowledged
        })
    
    return {
        "total_returned": len(result),
        "k": k,
        "status_filter": status,
        "alerts": result
    }


@router.get("/alerts/{alert_id}", response_model=ComplianceAlertRead)
def get_compliance_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific compliance alert by ID"""
    alert = db.query(ComplianceAlert).outerjoin(
        User, ComplianceAlert.user_id == User.user_id
    ).filter(ComplianceAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return ComplianceAlertRead(
        id=alert.id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        user_id=alert.user_id,
        user_name=alert.user.username if alert.user else None,
        transaction_id=alert.transaction_id,
        entity_id=alert.entity_id,
        entity_type=alert.entity_type,
        rps360=alert.rps360,
        priority=alert.priority,
        source=alert.source,
        triggered_by=alert.triggered_by,
        alert_metadata=alert.alert_metadata,
        triggered_at=alert.triggered_at,
        status=alert.status,
        is_acknowledged=alert.is_acknowledged,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        dismissal_reason=alert.dismissal_reason,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.post("/alerts", response_model=ComplianceAlertRead, status_code=201)
def create_compliance_alert(
    alert_data: ComplianceAlertCreate,
    db: Session = Depends(get_db)
):
    """Create a new compliance alert"""
    alert = ComplianceAlert(
        alert_type=alert_data.alert_type,
        severity=alert_data.severity,
        title=alert_data.title,
        description=alert_data.description,
        user_id=alert_data.user_id,
        transaction_id=alert_data.transaction_id,
        entity_id=alert_data.entity_id,
        entity_type=alert_data.entity_type,
        rps360=alert_data.rps360,
        priority=alert_data.priority,
        source=alert_data.source,
        triggered_by=alert_data.triggered_by,
        alert_metadata=alert_data.alert_metadata,
        triggered_at=alert_data.triggered_at or datetime.now(timezone.utc)
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return ComplianceAlertRead(
        id=alert.id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        user_id=alert.user_id,
        user_name=None,
        transaction_id=alert.transaction_id,
        entity_id=alert.entity_id,
        entity_type=alert.entity_type,
        rps360=alert.rps360,
        priority=alert.priority,
        source=alert.source,
        triggered_by=alert.triggered_by,
        alert_metadata=alert.alert_metadata,
        triggered_at=alert.triggered_at,
        status=alert.status,
        is_acknowledged=alert.is_acknowledged,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        dismissal_reason=alert.dismissal_reason,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.patch("/alerts/{alert_id}", response_model=ComplianceAlertRead)
def update_compliance_alert(
    alert_id: int,
    update_data: ComplianceAlertUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Update a compliance alert.
    Use status='resolved' for true positives, status='dismissed' for false positives.
    """
    alert = db.query(ComplianceAlert).filter(ComplianceAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update fields
    if update_data.status is not None:
        alert.status = update_data.status
    if update_data.priority is not None:
        alert.priority = update_data.priority
    if update_data.is_acknowledged is not None:
        alert.is_acknowledged = update_data.is_acknowledged
        if update_data.is_acknowledged:
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = current_admin.username
    if update_data.acknowledged_by is not None:
        alert.acknowledged_by = update_data.acknowledged_by
    if update_data.dismissal_reason is not None:
        alert.dismissal_reason = update_data.dismissal_reason
    
    db.commit()
    db.refresh(alert)
    
    # Create audit log
    action_type = "dismiss_alert" if update_data.status == "dismissed" else "escalate_alert" if update_data.status == "escalated" else "classify_alert"
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type=action_type,
        action_description=f"Admin {current_admin.username} updated alert {alert_id} - status: {alert.status}",
        target_type="alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        metadata={
            "new_status": alert.status,
            "dismissal_reason": alert.dismissal_reason
        },
        ip_address=get_client_ip(request)
    )
    
    # Get user info for response
    user = db.query(User).filter(User.user_id == alert.user_id).first() if alert.user_id else None
    
    return ComplianceAlertRead(
        id=alert.id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        user_id=alert.user_id,
        user_name=user.username if user else None,
        transaction_id=alert.transaction_id,
        entity_id=alert.entity_id,
        entity_type=alert.entity_type,
        rps360=alert.rps360,
        priority=alert.priority,
        source=alert.source,
        triggered_by=alert.triggered_by,
        alert_metadata=alert.alert_metadata,
        triggered_at=alert.triggered_at,
        status=alert.status,
        is_acknowledged=alert.is_acknowledged,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        dismissal_reason=alert.dismissal_reason,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Acknowledge an alert without changing its status"""
    alert = db.query(ComplianceAlert).filter(ComplianceAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_admin.username
    
    db.commit()
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="classify_alert",
        action_description=f"Admin {current_admin.username} acknowledged alert {alert_id}",
        target_type="alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        ip_address=get_client_ip(request)
    )
    
    return {
        "success": True,
        "alert_id": alert_id,
        "acknowledged_at": alert.acknowledged_at.isoformat(),
        "acknowledged_by": alert.acknowledged_by
    }


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    notes: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Mark alert as resolved (equivalent to true positive classification)"""
    alert = db.query(ComplianceAlert).filter(ComplianceAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_admin.username
    if notes:
        alert.dismissal_reason = notes
    
    db.commit()
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="classify_alert",
        action_description=f"Admin {current_admin.username} resolved alert {alert_id} as true positive",
        target_type="alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        metadata={"classification": "true_positive", "notes": notes},
        ip_address=get_client_ip(request) if request else None
    )
    
    return {
        "success": True,
        "message": "Alert resolved as true positive",
        "alert_id": alert_id,
        "status": "resolved",
        "resolved_at": alert.acknowledged_at.isoformat(),
        "resolved_by": current_admin.username
    }


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_compliance_alert(
    alert_id: int,
    reason: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Mark alert as dismissed (equivalent to false positive classification)"""
    alert = db.query(ComplianceAlert).filter(ComplianceAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "dismissed"
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_admin.username
    alert.dismissal_reason = reason
    
    db.commit()
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="dismiss_alert",
        action_description=f"Admin {current_admin.username} dismissed alert {alert_id} as false positive",
        target_type="alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        metadata={"classification": "false_positive", "reason": reason},
        ip_address=get_client_ip(request) if request else None
    )
    
    return {
        "success": True,
        "message": "Alert dismissed as false positive",
        "alert_id": alert_id,
        "status": "dismissed",
        "dismissed_at": alert.acknowledged_at.isoformat(),
        "dismissed_by": current_admin.username,
        "reason": reason
    }


@router.get("/alerts/stats/summary")
def get_alerts_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for compliance alerts"""
    from sqlalchemy import func
    
    total = db.query(ComplianceAlert).count()
    active = db.query(ComplianceAlert).filter(ComplianceAlert.status == "active").count()
    investigating = db.query(ComplianceAlert).filter(ComplianceAlert.status == "investigating").count()
    resolved = db.query(ComplianceAlert).filter(ComplianceAlert.status == "resolved").count()
    dismissed = db.query(ComplianceAlert).filter(ComplianceAlert.status == "dismissed").count()
    escalated = db.query(ComplianceAlert).filter(ComplianceAlert.status == "escalated").count()
    
    # Severity breakdown
    by_severity = {}
    for severity in ["low", "medium", "high", "critical"]:
        by_severity[severity] = db.query(ComplianceAlert).filter(
            ComplianceAlert.severity == severity,
            ComplianceAlert.status == "active"
        ).count()
    
    return {
        "total": total,
        "pending_review": active + investigating,
        "active": active,
        "investigating": investigating,
        "resolved": resolved,
        "dismissed": dismissed,
        "escalated": escalated,
        "by_severity": by_severity
    }

