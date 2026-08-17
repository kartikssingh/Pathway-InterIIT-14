from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================== Audit Log Schemas ====================

class AuditLogBase(BaseModel):
    action_type: str
    action_description: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_identifier: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    admin_id: int
    action_metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: int
    admin_id: int
    action_metadata: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    admin_username: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    admin_id: Optional[int] = None
    action_type: Optional[str] = None
    target_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


# ==================== System Metrics Schemas ====================

class SystemMetricsBase(BaseModel):
    metric_type: str
    metric_category: str
    metric_value: float
    metric_unit: Optional[str] = None


class SystemMetricsCreate(SystemMetricsBase):
    time_window: Optional[str] = None
    aggregation_period_start: Optional[datetime] = None
    aggregation_period_end: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    total_count: Optional[int] = None
    positive_count: Optional[int] = None
    negative_count: Optional[int] = None
    is_anomaly: bool = False
    anomaly_threshold: Optional[float] = None


class SystemMetricsResponse(SystemMetricsBase):
    id: int
    time_window: Optional[str] = None
    aggregation_period_start: Optional[datetime] = None
    aggregation_period_end: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    total_count: Optional[int] = None
    positive_count: Optional[int] = None
    negative_count: Optional[int] = None
    recorded_at: datetime
    is_anomaly: bool
    anomaly_threshold: Optional[float] = None

    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    """Summary statistics for metrics dashboard"""
    resolution_rate: float  # Percentage of alerts that have been resolved
    avg_response_time_ms: float
    api_error_rate: float
    total_alerts: int
    resolved: int  # Alerts that have been acknowledged/resolved
    unresolved: int  # Alerts pending review (not yet acknowledged)
    period_start: datetime
    period_end: datetime


# ==================== System Health Schemas ====================

class SystemHealthBase(BaseModel):
    check_type: str
    component_name: str
    status: str
    severity: str


class SystemHealthCreate(SystemHealthBase):
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_stacktrace: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None
    response_context: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    retry_count: int = 0
    affected_operations: Optional[List[str]] = None
    user_impact: Optional[str] = None


class SystemHealthResponse(SystemHealthBase):
    id: int
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None
    response_context: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    retry_count: Optional[int] = None
    affected_operations: Optional[List[str]] = None
    user_impact: Optional[str] = None
    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    auto_recovered: Optional[bool] = None
    detected_at: datetime
    last_occurrence: Optional[datetime] = None
    alert_sent: Optional[bool] = None

    class Config:
        from_attributes = True


class SystemHealthUpdate(BaseModel):
    status: Optional[str] = None
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None


# ==================== System Alert Schemas ====================

class SystemAlertBase(BaseModel):
    alert_type: str
    title: str
    description: str
    severity: str


class SystemAlertCreate(SystemAlertBase):
    component: Optional[str] = None
    metric_type: Optional[str] = None
    threshold_value: Optional[str] = None
    actual_value: Optional[str] = None
    alert_data: Optional[Dict[str, Any]] = None


class SystemAlertResponse(SystemAlertBase):
    id: int
    component: Optional[str] = None
    metric_type: Optional[str] = None
    threshold_value: Optional[str] = None
    actual_value: Optional[str] = None
    alert_data: Optional[Dict[str, Any]] = None
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    triggered_at: datetime
    last_updated: datetime
    notifications_sent: int

    class Config:
        from_attributes = True


class SystemAlertUpdate(BaseModel):
    status: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolution_notes: Optional[str] = None


# ==================== Dashboard Aggregations ====================

class ComplianceAlertSummary(BaseModel):
    """Summary of a compliance alert for dashboard display"""
    id: int
    alert_type: str
    severity: str
    title: str
    description: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    status: str
    priority: Optional[str] = None
    is_acknowledged: bool
    created_at: datetime
    triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SuperadminDashboard(BaseModel):
    """Complete superadmin dashboard data"""
    metrics_summary: MetricsSummary
    unresolved_compliance_alerts: List[ComplianceAlertSummary]  # Top unresolved compliance alerts
    active_system_alerts: List[SystemAlertResponse]  # System-level alerts (separate)
    recent_health_issues: List[SystemHealthResponse]
    recent_audit_logs: List[AuditLogResponse]
    system_status: str  # 'healthy', 'degraded', 'critical'


class AlertResolutionStats(BaseModel):
    """Statistics about how alerts were resolved"""
    total_alerts: int
    resolved: int  # Alerts that have been acknowledged/resolved
    unresolved: int  # Alerts pending review (not yet acknowledged)
    escalated: int  # Alerts that were escalated for further review
    avg_resolution_time_hours: float


class AdminActivityStats(BaseModel):
    """Statistics about admin activity"""
    admin_id: int
    admin_username: str
    total_actions: int
    alerts_reviewed: int
    users_flagged: int
    decisions_made: int
    last_active: datetime
