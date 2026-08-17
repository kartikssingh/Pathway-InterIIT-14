from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.services.auth_dependencies import require_superadmin
from app.services.superadmin_service import (
    AuditService, MetricsService, HealthService, SuperadminService
)
from app.schemas.auth import TokenData
from app.schemas.superadmin import (
    AuditLogFilter, AuditLogResponse,
    SystemMetricsResponse, MetricsSummary,
    SystemHealthResponse, SystemHealthUpdate,
    SystemAlertResponse, SystemAlertUpdate,
    SuperadminDashboard, AlertResolutionStats, AdminActivityStats
)

router = APIRouter(prefix="/api/superadmin", tags=["Superadmin"])


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=SuperadminDashboard)
async def get_superadmin_dashboard(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive superadmin dashboard with metrics, alerts, and audit logs.
    Requires superadmin role.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    dashboard = SuperadminService.get_dashboard(db, start_date, end_date)
    return dashboard


# ==================== Audit Logs ====================

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    admin_id: Optional[int] = Query(None, description="Filter by admin ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs with filters.
    Returns logs of admin actions including who was flagged, by which admin, and resolutions.
    """
    filters = AuditLogFilter(
        admin_id=admin_id,
        action_type=action_type,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    audit_logs = AuditService.get_audit_logs_with_admin_info(db, filters)
    return [AuditLogResponse(**log) for log in audit_logs]


@router.get("/audit-logs/{audit_id}", response_model=AuditLogResponse)
async def get_audit_log_detail(
    audit_id: int,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific audit log entry."""
    audit_log = AuditService.get_audit_log_by_id(db, audit_id)
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return audit_log


# ==================== Metrics ====================

@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get summary of key metrics including hit rates, false positive rates, 
    response times, and API error rates.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    metrics = MetricsService.calculate_alert_metrics(db, start_date, end_date)
    return metrics


@router.get("/metrics/history", response_model=List[SystemMetricsResponse])
async def get_metrics_history(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    metric_category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get historical metrics data for trend analysis."""
    metrics = MetricsService.get_metrics(
        db,
        metric_type=metric_type,
        metric_category=metric_category,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return metrics


@router.get("/metrics/alert-resolutions", response_model=AlertResolutionStats)
async def get_alert_resolution_stats(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get statistics about how alerts were resolved."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    stats = MetricsService.get_alert_resolution_stats(db, start_date, end_date)
    return stats


@router.get("/metrics/admin-activity", response_model=List[AdminActivityStats])
async def get_admin_activity_stats(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get statistics about admin activity and performance."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    stats = MetricsService.get_admin_activity_stats(db, start_date, end_date)
    return stats


# ==================== System Health ====================

@router.get("/health/checks", response_model=List[SystemHealthResponse])
async def get_health_checks(
    check_type: Optional[str] = Query(None, description="Filter by check type"),
    component_name: Optional[str] = Query(None, description="Filter by component"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get system health checks.
    Shows upstream API downtime, parser errors, and other system failures.
    """
    health_checks = HealthService.get_health_checks(
        db,
        check_type=check_type,
        component_name=component_name,
        status=status,
        severity=severity,
        is_resolved=is_resolved,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return health_checks


@router.patch("/health/checks/{health_id}", response_model=SystemHealthResponse)
async def update_health_check(
    health_id: int,
    update_data: SystemHealthUpdate,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Update a health check record (e.g., mark as resolved)."""
    health_check = HealthService.update_health_check(db, health_id, update_data)
    if not health_check:
        raise HTTPException(status_code=404, detail="Health check not found")
    
    # Create audit log for resolve action
    if update_data.is_resolved:
        action_description = f"Resolved health check {health_id} ({health_check.component_name} - {health_check.check_type})"
        AuditService.create_audit_log(
            db=db,
            admin_id=current_admin.id,
            action_type="resolve_health_check",
            action_description=action_description,
            target_type="system_health",
            target_id=health_id,
            target_identifier=f"health_{health_id}",
            action_metadata={
                "component_name": health_check.component_name,
                "check_type": health_check.check_type,
                "severity": health_check.severity,
                "status": health_check.status,
                "resolution_notes": update_data.resolution_notes
            }
        )
    
    return health_check


# ==================== System Alerts ====================

@router.get("/alerts/unresolved")
async def get_unresolved_system_alerts(
    include_acknowledged: bool = Query(True, description="Include acknowledged alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, error, warning, info)"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get all unresolved system alerts (not yet resolved).
    
    Returns all alerts that are either 'active' or 'acknowledged' (pending resolution).
    Alerts are sorted by:
    1. Severity (critical > error > warning > info)
    2. Recency (most recent first)
    
    - **include_acknowledged**: Include acknowledged alerts (default: true, shows all pending)
    - **severity**: Optional filter by severity level
    """
    from sqlalchemy import case, desc
    from app.models.system_health import SystemAlert
    
    # Define severity ordering (higher = more critical)
    severity_order = case(
        (SystemAlert.severity == 'critical', 4),
        (SystemAlert.severity == 'error', 3),
        (SystemAlert.severity == 'warning', 2),
        (SystemAlert.severity == 'info', 1),
        else_=0
    )
    
    query = db.query(SystemAlert)
    
    # Filter by status - exclude resolved alerts
    if include_acknowledged:
        query = query.filter(SystemAlert.status.in_(['active', 'acknowledged']))
    else:
        query = query.filter(SystemAlert.status == 'active')
    
    # Optional severity filter
    if severity:
        query = query.filter(SystemAlert.severity == severity.lower())
    
    # Order by severity (descending) then by triggered_at (most recent first)
    alerts = query.order_by(
        severity_order.desc(),
        desc(SystemAlert.triggered_at)
    ).all()
    
    # Build response
    result = []
    for alert in alerts:
        result.append({
            "id": alert.id,
            "alert_type": alert.alert_type,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "status": alert.status,
            "component": alert.component,
            "metric_type": alert.metric_type,
            "threshold_value": alert.threshold_value,
            "actual_value": alert.actual_value,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        })
    
    # Count by severity for summary
    severity_counts = {
        "critical": sum(1 for a in result if a["severity"] == "critical"),
        "error": sum(1 for a in result if a["severity"] == "error"),
        "warning": sum(1 for a in result if a["severity"] == "warning"),
        "info": sum(1 for a in result if a["severity"] == "info")
    }
    
    return {
        "total": len(result),
        "severity_counts": severity_counts,
        "include_acknowledged": include_acknowledged,
        "alerts": result
    }


@router.get("/alerts", response_model=List[SystemAlertResponse])
async def get_system_alerts(
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    component: Optional[str] = Query(None, description="Filter by component"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get system alerts.
    Shows alerts triggered when system behaves unexpectedly.
    """
    alerts = HealthService.get_system_alerts(
        db,
        alert_type=alert_type,
        status=status,
        severity=severity,
        component=component,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return alerts


@router.patch("/alerts/{alert_id}", response_model=SystemAlertResponse)
async def update_system_alert(
    alert_id: int,
    update_data: SystemAlertUpdate,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Update a system alert (e.g., acknowledge or resolve)."""
    # Add current admin username to update if acknowledging
    if update_data.acknowledged_by is None and update_data.status == 'acknowledged':
        update_data.acknowledged_by = current_admin.username
    
    alert = HealthService.update_system_alert(db, alert_id, update_data)
    if not alert:
        raise HTTPException(status_code=404, detail="System alert not found")
    
    # Create audit log for this action (using 'update_system_alert' for all system alert updates per DB constraint)
    action_type = "update_system_alert"
    action_description = f"{'Resolved' if update_data.status == 'resolved' else 'Acknowledged' if update_data.status == 'acknowledged' else 'Updated'} system alert {alert_id} ({alert.alert_type} - {alert.title})"
    
    AuditService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type=action_type,
        action_description=action_description,
        target_type="system_alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        action_metadata={
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "component": alert.component,
            "new_status": update_data.status,
            "resolution_notes": update_data.resolution_notes,
            "acknowledged_by": update_data.acknowledged_by
        }
    )
    
    return alert


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_system_alert(
    alert_id: int,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Acknowledge a system alert.
    Marks the alert as seen/acknowledged without resolving it.
    """
    from app.models.system_health import SystemAlert
    
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="System alert not found")
    
    if alert.status == 'resolved':
        raise HTTPException(status_code=400, detail="Cannot acknowledge a resolved alert")
    
    alert.status = 'acknowledged'
    alert.acknowledged_by = current_admin.username
    alert.acknowledged_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(alert)
    
    # Create audit log
    AuditService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="update_system_alert",
        action_description=f"Acknowledged system alert {alert_id} ({alert.alert_type} - {alert.title})",
        target_type="system_alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        action_metadata={
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "action": "acknowledge"
        }
    )
    
    return {
        "success": True,
        "message": "Alert acknowledged",
        "alert_id": alert_id,
        "status": "acknowledged",
        "acknowledged_at": alert.acknowledged_at.isoformat(),
        "acknowledged_by": current_admin.username
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_system_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Resolve a system alert.
    Marks the alert as resolved/handled (confirmed issue that was addressed).
    
    - **resolution_notes**: Optional notes about how the issue was resolved
    """
    from app.models.system_health import SystemAlert
    
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="System alert not found")
    
    if alert.status == 'resolved':
        raise HTTPException(status_code=400, detail="Alert is already resolved")
    
    alert.status = 'resolved'
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = resolution_notes
    
    # Also set acknowledged if not already
    if not alert.acknowledged_by:
        alert.acknowledged_by = current_admin.username
        alert.acknowledged_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(alert)
    
    # Create audit log
    AuditService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="update_system_alert",
        action_description=f"Resolved system alert {alert_id} ({alert.alert_type} - {alert.title})",
        target_type="system_alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        action_metadata={
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "action": "resolve",
            "resolution_notes": resolution_notes
        }
    )
    
    return {
        "success": True,
        "message": "Alert resolved",
        "alert_id": alert_id,
        "status": "resolved",
        "resolved_at": alert.resolved_at.isoformat(),
        "resolved_by": current_admin.username,
        "resolution_notes": resolution_notes
    }


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_system_alert(
    alert_id: int,
    reason: Optional[str] = None,
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Dismiss a system alert as false positive or not actionable.
    Use this when the alert was triggered incorrectly or doesn't require action.
    
    - **reason**: Optional reason for dismissal (e.g., "false positive", "expected behavior")
    """
    from app.models.system_health import SystemAlert
    
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="System alert not found")
    
    if alert.status == 'resolved':
        raise HTTPException(status_code=400, detail="Cannot dismiss a resolved alert")
    
    # Mark as resolved but with dismissal notes
    alert.status = 'resolved'
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = f"DISMISSED: {reason}" if reason else "DISMISSED: No reason provided"
    
    # Set acknowledged if not already
    if not alert.acknowledged_by:
        alert.acknowledged_by = current_admin.username
        alert.acknowledged_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(alert)
    
    # Create audit log
    AuditService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="update_system_alert",
        action_description=f"Dismissed system alert {alert_id} ({alert.alert_type} - {alert.title}) - Reason: {reason or 'Not specified'}",
        target_type="system_alert",
        target_id=alert_id,
        target_identifier=str(alert_id),
        action_metadata={
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "action": "dismiss",
            "dismissal_reason": reason
        }
    )
    
    return {
        "success": True,
        "message": "Alert dismissed",
        "alert_id": alert_id,
        "status": "resolved",
        "dismissed_at": alert.resolved_at.isoformat(),
        "dismissed_by": current_admin.username,
        "reason": reason
    }


@router.get("/system-status")
async def get_system_status(
    current_admin: TokenData = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """Get overall system status (healthy, degraded, or critical)."""
    status = HealthService.get_system_status(db)
    
    # Get counts
    critical_alerts = len(HealthService.get_system_alerts(
        db, status='active', severity='critical', limit=1000
    ))
    unresolved_errors = len(HealthService.get_health_checks(
        db, is_resolved=False, severity='error', limit=1000
    ))
    
    return {
        "status": status,
        "critical_alerts": critical_alerts,
        "unresolved_errors": unresolved_errors,
        "checked_at": datetime.now(timezone.utc)
    }
