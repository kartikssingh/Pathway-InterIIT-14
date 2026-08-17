from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.db import get_db
from app.services import dashboard_service
from app.schemas import dashboard
from app.models.admin import Admin
from app.services.auth_dependencies import require_admin, get_client_ip, get_user_agent
from app.services.auth_service import AuthService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=dashboard.DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get overall dashboard summary statistics"""
    return dashboard_service.get_summary(db)


@router.get("/risk-distribution", response_model=dashboard.RiskDistribution)
def get_risk_distribution(db: Session = Depends(get_db)):
    """Get risk distribution across all users"""
    return dashboard_service.get_risk_distribution(db)


@router.get("/flagged-transactions")
def get_flagged_transactions(limit: int = 10, db: Session = Depends(get_db)):
    """Get most suspicious/flagged transactions"""
    return dashboard_service.get_flagged_transactions(db, limit)


@router.get("/critical-alerts", response_model=List[dashboard.CriticalAlert])
def get_critical_alerts(
    limit: int = Query(10, ge=1, le=100),
    severity: Optional[str] = Query(None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW|all)$"),
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Get critical alerts with filtering options.
    
    - **limit**: Maximum number of alerts to return (1-100)
    - **severity**: Filter by severity level (CRITICAL, HIGH, MEDIUM, LOW, or all)
    - **hours**: Return alerts from last N hours (1-168)
    """
    try:
        return dashboard_service.get_critical_alerts(db, limit, severity, hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-alerts", response_model=List[dashboard.LiveAlert])
def get_live_alerts(
    limit: int = Query(20, ge=1, le=100),
    since: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get live alert feed for real-time display.
    
    - **limit**: Maximum number of alerts to return (1-100)
    - **since**: Return alerts after this timestamp (ISO 8601 format)
    """
    try:
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO 8601.")
        
        return dashboard_service.get_live_alerts(db, limit, since_dt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alert-trend", response_model=dashboard.AlertTrendResponse)
def get_alert_trend(
    period: str = Query("1h", pattern="^(1h|6h|24h|7d|30d)$"),
    interval: str = Query("5m", pattern="^(1m|5m|15m|1h)$"),
    severity: Optional[str] = Query("all", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|all)$"),
    db: Session = Depends(get_db)
):
    """
    Get alert trend data for visualization.
    
    - **period**: Time period to analyze (1h, 6h, 24h, 7d, 30d)
    - **interval**: Data point interval (1m, 5m, 15m, 1h)
    - **severity**: Filter by severity or "all"
    """
    try:
        return dashboard_service.get_alert_trend(db, period, interval, severity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/unclassified")
def get_unclassified_alerts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query("all", description="Filter by severity"),
    db: Session = Depends(get_db)
):
    """
    Get alerts that are pending review (status='active' or 'investigating').
    This replaces the old 'unclassified' concept - now based on status.
    
    - **limit**: Maximum number of alerts to return
    - **offset**: Offset for pagination  
    - **severity**: Filter by severity (low, medium, high, critical, all)
    """
    from sqlalchemy import desc
    from app.models.alert import ComplianceAlert
    from app.models.user import User
    
    # Query for active/investigating alerts (pending review)
    query = db.query(ComplianceAlert).outerjoin(
        User, ComplianceAlert.user_id == User.user_id
    ).filter(ComplianceAlert.status.in_(['active', 'investigating']))
    
    # Apply severity filter
    if severity and severity.lower() != "all":
        query = query.filter(ComplianceAlert.severity == severity.lower())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    alerts = query.order_by(desc(ComplianceAlert.created_at)).offset(offset).limit(limit).all()
    
    # Build response
    result_alerts = []
    for alert in alerts:
        result_alerts.append({
            "id": alert.id,
            "user_id": alert.user_id,
            "user_name": alert.user.username if alert.user else None,
            "transaction_id": alert.transaction_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "entity_id": alert.entity_id,
            "rps360": alert.rps360,
            "status": alert.status,
            "priority": alert.priority,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        })
    
    return {
        "total": total,
        "alerts": result_alerts,
        "limit": limit,
        "offset": offset
    }


@router.post("/alerts/{alert_id}/dismiss", response_model=dashboard.AlertDismissResponse)
def dismiss_alert(
    alert_id: str,
    dismiss_data: dashboard.AlertDismissRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Dismiss/acknowledge an alert. Requires admin authentication.
    
    - **alert_id**: Alert identifier
    - **reason**: Optional dismissal reason
    - **notes**: Optional additional notes
    """
    try:
        result = dashboard_service.dismiss_alert(
            db, 
            alert_id, 
            dismiss_data.reason, 
            dismiss_data.notes
        )
        
        # Create audit log
        AuthService.create_audit_log(
            db=db,
            admin_id=current_admin.id,
            action_type="dismiss_alert",
            action_description=f"Admin {current_admin.username} dismissed alert {alert_id}",
            target_type="alert",
            target_id=int(alert_id) if alert_id.isdigit() else None,
            target_identifier=alert_id,
            metadata={"reason": dismiss_data.reason, "notes": dismiss_data.notes},
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/cases/create", response_model=dashboard.CaseCreateResponse, status_code=201)
# def create_investigation_case(
#     case_data: dashboard.CaseCreateRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Create a new investigation case for suspicious activity.
#     
#     - **title**: Case title
#     - **description**: Detailed case description
#     - **user_id**: User under investigation
#     - **transaction_ids**: Related transaction IDs
#     - **alert_ids**: Related alert IDs
#     - **priority**: Case priority (LOW, MEDIUM, HIGH, CRITICAL)
#     - **assigned_to**: Investigator username
#     """
#     try:
#         return dashboard_service.create_investigation_case(db, case_data)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/users/{user_id}/hold", response_model=dashboard.AccountHoldResponse, status_code=201)
# def place_account_hold(
#     user_id: int,
#     hold_data: dashboard.AccountHoldRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Place a hold on a user account, restricting transactions.
#     
#     - **user_id**: User identifier
#     - **reason**: Reason for placing hold
#     - **duration_hours**: Hold duration in hours (null = indefinite)
#     - **hold_type**: FULL or TRANSACTION_ONLY
#     - **notes**: Additional notes
#     """
#     try:
#         return dashboard_service.place_account_hold(db, user_id, hold_data)
#     except ValueError as e:
#         if "not found" in str(e):
#             raise HTTPException(status_code=404, detail=str(e))
#         else:
#             raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
