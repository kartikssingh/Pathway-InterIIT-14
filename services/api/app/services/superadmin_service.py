from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from app.models.audit_log import AuditLog
from app.models.system_metrics import SystemMetrics
from app.models.system_health import SystemHealth, SystemAlert
from app.models.alert import ComplianceAlert
from app.models.admin import Admin
from app.schemas.superadmin import (
    AuditLogCreate, AuditLogFilter, AuditLogResponse,
    SystemMetricsCreate, SystemMetricsResponse, MetricsSummary,
    SystemHealthCreate, SystemHealthResponse, SystemHealthUpdate,
    SystemAlertCreate, SystemAlertResponse, SystemAlertUpdate,
    SuperadminDashboard, AlertResolutionStats, AdminActivityStats
)


class AuditService:
    """Service for managing audit logs"""
    
    @staticmethod
    def create_audit_log(
        db: Session,
        admin_id: int,
        action_type: str,
        action_description: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_identifier: Optional[str] = None,
        action_metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create a new audit log entry"""
        audit_log = AuditLog(
            admin_id=admin_id,
            action_type=action_type,
            action_description=action_description,
            target_type=target_type,
            target_id=target_id,
            target_identifier=target_identifier,
            action_metadata=action_metadata,
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        filters: AuditLogFilter
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        query = db.query(AuditLog)
        
        if filters.admin_id:
            query = query.filter(AuditLog.admin_id == filters.admin_id)
        if filters.action_type:
            query = query.filter(AuditLog.action_type == filters.action_type)
        if filters.target_type:
            query = query.filter(AuditLog.target_type == filters.target_type)
        if filters.start_date:
            query = query.filter(AuditLog.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(AuditLog.created_at <= filters.end_date)
        
        query = query.order_by(desc(AuditLog.created_at))
        query = query.offset(filters.offset).limit(filters.limit)
        
        return query.all()
    
    @staticmethod
    def get_audit_log_by_id(db: Session, audit_id: int) -> Optional[AuditLog]:
        """Get a specific audit log by ID"""
        return db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    
    @staticmethod
    def get_audit_logs_with_admin_info(
        db: Session,
        filters: AuditLogFilter
    ) -> List[Dict[str, Any]]:
        """Get audit logs with admin username included"""
        query = db.query(AuditLog, Admin.username).join(
            Admin, AuditLog.admin_id == Admin.id
        )
        
        if filters.admin_id:
            query = query.filter(AuditLog.admin_id == filters.admin_id)
        if filters.action_type:
            query = query.filter(AuditLog.action_type == filters.action_type)
        if filters.target_type:
            query = query.filter(AuditLog.target_type == filters.target_type)
        if filters.start_date:
            query = query.filter(AuditLog.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(AuditLog.created_at <= filters.end_date)
        
        query = query.order_by(desc(AuditLog.created_at))
        query = query.offset(filters.offset).limit(filters.limit)
        
        results = []
        for audit_log, username in query.all():
            log_dict = {
                "id": audit_log.id,
                "admin_id": audit_log.admin_id,
                "admin_username": username,
                "action_type": audit_log.action_type,
                "action_description": audit_log.action_description,
                "target_type": audit_log.target_type,
                "target_id": audit_log.target_id,
                "target_identifier": audit_log.target_identifier,
                "action_metadata": audit_log.action_metadata,
                "ip_address": audit_log.ip_address,
                "created_at": audit_log.created_at
            }
            results.append(log_dict)
        
        return results


class MetricsService:
    """Service for tracking and calculating system metrics"""
    
    @staticmethod
    def record_metric(
        db: Session,
        metric_type: str,
        metric_category: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        time_window: Optional[str] = None,
        aggregation_period_start: Optional[datetime] = None,
        aggregation_period_end: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
        total_count: Optional[int] = None,
        positive_count: Optional[int] = None,
        negative_count: Optional[int] = None,
        is_anomaly: bool = False,
        anomaly_threshold: Optional[float] = None
    ) -> SystemMetrics:
        """Record a system metric"""
        metric = SystemMetrics(
            metric_type=metric_type,
            metric_category=metric_category,
            metric_value=metric_value,
            metric_unit=metric_unit,
            time_window=time_window,
            aggregation_period_start=aggregation_period_start,
            aggregation_period_end=aggregation_period_end,
            details=details,
            total_count=total_count,
            positive_count=positive_count,
            negative_count=negative_count,
            is_anomaly=is_anomaly,
            anomaly_threshold=anomaly_threshold
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
    
    @staticmethod
    def calculate_alert_metrics(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> MetricsSummary:
        """Calculate comprehensive alert metrics"""
        now = datetime.now(timezone.utc)
        if not start_date:
            start_date = now - timedelta(days=7)
        if not end_date:
            end_date = now
        # Ensure dates are timezone-aware for proper comparison with DB timestamps
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Query all alerts in the time period
        query = db.query(ComplianceAlert).filter(
            and_(
                ComplianceAlert.created_at >= start_date,
                ComplianceAlert.created_at <= end_date
            )
        )
        
        total_alerts = max(0, query.count())
        
        # Count resolved alerts (acknowledged alerts are considered resolved)
        # Resolved = status in ('resolved', 'dismissed') OR is_acknowledged = True
        resolved = max(0, query.filter(
            or_(
                ComplianceAlert.status.in_(['resolved', 'dismissed']),
                ComplianceAlert.is_acknowledged == True
            )
        ).count())
        
        # Unresolved = total - resolved
        unresolved = max(0, total_alerts - resolved)
        
        # Calculate resolution rate with clamping to valid percentage range [0, 100]
        if total_alerts > 0:
            resolution_rate = max(0.0, min(100.0, (resolved / total_alerts * 100)))
        else:
            resolution_rate = 0.0
        
        # Calculate average response time (time from creation to acknowledgment)
        # Only include positive time differences (filter out data anomalies)
        acknowledged_alerts = query.filter(ComplianceAlert.acknowledged_at.isnot(None)).all()
        response_times = []
        for alert in acknowledged_alerts:
            if alert.acknowledged_at and alert.created_at:
                response_time = (alert.acknowledged_at - alert.created_at).total_seconds()
                # Only include positive response times (filter out timestamp anomalies)
                if response_time >= 0:
                    response_times.append(response_time)
        
        avg_response_time_ms = max(0.0, (sum(response_times) / len(response_times) * 1000) if response_times else 0.0)
        
        # Get API error rate from recent health checks (clamped to [0, 100])
        api_error_rate = max(0.0, min(100.0, MetricsService._calculate_api_error_rate(db, start_date, end_date)))
        
        return MetricsSummary(
            resolution_rate=round(resolution_rate, 2),
            avg_response_time_ms=round(avg_response_time_ms, 2),
            api_error_rate=round(api_error_rate, 2),
            total_alerts=total_alerts,
            resolved=resolved,
            unresolved=unresolved,
            period_start=start_date,
            period_end=end_date
        )
    
    @staticmethod
    def _calculate_api_error_rate(
        db: Session,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate API error rate from health checks"""
        health_checks = db.query(SystemHealth).filter(
            and_(
                SystemHealth.detected_at >= start_date,
                SystemHealth.detected_at <= end_date,
                SystemHealth.check_type == 'api_health'
            )
        ).all()
        
        if not health_checks:
            return 0.0
        
        failed_checks = sum(1 for check in health_checks if check.status == 'failed')
        return (failed_checks / len(health_checks)) * 100
    
    @staticmethod
    def get_metrics(
        db: Session,
        metric_type: Optional[str] = None,
        metric_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SystemMetrics]:
        """Get system metrics with filters"""
        query = db.query(SystemMetrics)
        
        if metric_type:
            query = query.filter(SystemMetrics.metric_type == metric_type)
        if metric_category:
            query = query.filter(SystemMetrics.metric_category == metric_category)
        if start_date:
            query = query.filter(SystemMetrics.recorded_at >= start_date)
        if end_date:
            query = query.filter(SystemMetrics.recorded_at <= end_date)
        
        query = query.order_by(desc(SystemMetrics.recorded_at)).limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_alert_resolution_stats(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AlertResolutionStats:
        """Get statistics about alert resolutions"""
        now = datetime.now(timezone.utc)
        if not start_date:
            start_date = now - timedelta(days=30)
        if not end_date:
            end_date = now
        # Ensure dates are timezone-aware for proper comparison with DB timestamps
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        query = db.query(ComplianceAlert).filter(
            and_(
                ComplianceAlert.created_at >= start_date,
                ComplianceAlert.created_at <= end_date
            )
        )
        
        # Ensure all counts are >= 0
        total_alerts = max(0, query.count())
        
        # Resolved = acknowledged alerts (status in resolved/dismissed OR is_acknowledged = True)
        resolved = max(0, query.filter(
            or_(
                ComplianceAlert.status.in_(['resolved', 'dismissed']),
                ComplianceAlert.is_acknowledged == True
            )
        ).count())
        
        # Unresolved = not acknowledged (active, investigating)
        unresolved = max(0, query.filter(
            and_(
                ComplianceAlert.status.in_(['active', 'investigating']),
                or_(
                    ComplianceAlert.is_acknowledged == False,
                    ComplianceAlert.is_acknowledged.is_(None)
                )
            )
        ).count())
        
        # Escalated alerts
        escalated = max(0, query.filter(ComplianceAlert.status == 'escalated').count())
        
        # Calculate average resolution time (using acknowledged_at as proxy)
        # Only include positive time differences to filter out data anomalies
        resolved_alerts = query.filter(
            and_(
                ComplianceAlert.acknowledged_at.isnot(None),
                ComplianceAlert.created_at.isnot(None)
            )
        ).all()
        
        resolution_times = []
        for alert in resolved_alerts:
            time_diff = (alert.acknowledged_at - alert.created_at).total_seconds() / 3600  # Convert to hours
            # Only include positive resolution times (filter out timestamp anomalies)
            if time_diff >= 0:
                resolution_times.append(time_diff)
        
        avg_resolution_time = max(0.0, sum(resolution_times) / len(resolution_times) if resolution_times else 0.0)
        
        return AlertResolutionStats(
            total_alerts=total_alerts,
            resolved=resolved,
            unresolved=unresolved,
            escalated=escalated,
            avg_resolution_time_hours=round(avg_resolution_time, 2)
        )
    
    @staticmethod
    def get_admin_activity_stats(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AdminActivityStats]:
        """Get statistics about admin activity"""
        now = datetime.now(timezone.utc)
        if not start_date:
            start_date = now - timedelta(days=30)
        if not end_date:
            end_date = now
        # Ensure dates are timezone-aware for proper comparison with DB timestamps
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Get all admins
        admins = db.query(Admin).all()
        stats = []
        
        for admin in admins:
            # Total actions from audit logs within the time period
            total_actions = max(0, db.query(AuditLog).filter(
                and_(
                    AuditLog.admin_id == admin.id,
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).count())
            
            # Alerts reviewed - count from audit logs with alert-related actions
            # Also include direct acknowledgments from ComplianceAlert table
            alerts_reviewed_from_audit = db.query(AuditLog).filter(
                and_(
                    AuditLog.admin_id == admin.id,
                    AuditLog.action_type.in_(['classify_alert', 'dismiss_alert', 'escalate_alert']),
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).count()
            
            # Also count alerts acknowledged directly (by username match)
            alerts_acknowledged = db.query(ComplianceAlert).filter(
                and_(
                    ComplianceAlert.acknowledged_by == admin.username,
                    ComplianceAlert.acknowledged_at >= start_date,
                    ComplianceAlert.acknowledged_at <= end_date
                )
            ).count()
            
            # Take the maximum of the two to avoid undercounting
            alerts_reviewed = max(0, max(alerts_reviewed_from_audit, alerts_acknowledged))
            
            # Users flagged (from audit logs) - include all user-related actions
            users_flagged = max(0, db.query(AuditLog).filter(
                and_(
                    AuditLog.admin_id == admin.id,
                    AuditLog.action_type.in_(['blacklist_user', 'flag_user', 'whitelist_user', 'unflag_user']),
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).count())
            
            # Decisions made (alert classifications and transaction decisions)
            decisions_made = max(0, db.query(AuditLog).filter(
                and_(
                    AuditLog.admin_id == admin.id,
                    AuditLog.action_type.in_([
                        'classify_alert', 'dismiss_alert', 'escalate_alert',
                        'block_transaction', 'approve_transaction',
                        'update_system_alert', 'resolve_health_check'
                    ]),
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date
                )
            ).count())
            
            # Last activity - check both audit logs and acknowledged alerts
            last_audit = db.query(AuditLog).filter(
                AuditLog.admin_id == admin.id
            ).order_by(desc(AuditLog.created_at)).first()
            
            # Also check for recent alert acknowledgments
            last_alert_ack = db.query(ComplianceAlert).filter(
                ComplianceAlert.acknowledged_by == admin.username
            ).order_by(desc(ComplianceAlert.acknowledged_at)).first()
            
            # Determine last active timestamp from available data
            timestamps = []
            if last_audit and last_audit.created_at:
                timestamps.append(last_audit.created_at)
            if last_alert_ack and last_alert_ack.acknowledged_at:
                timestamps.append(last_alert_ack.acknowledged_at)
            
            if timestamps:
                last_active = max(timestamps)
            else:
                last_active = admin.created_at
            
            stats.append(AdminActivityStats(
                admin_id=admin.id,
                admin_username=admin.username,
                total_actions=total_actions,
                alerts_reviewed=alerts_reviewed,
                users_flagged=users_flagged,
                decisions_made=decisions_made,
                last_active=last_active
            ))
        
        # Sort by total_actions descending to show most active admins first
        stats.sort(key=lambda x: x.total_actions, reverse=True)
        
        return stats


class HealthService:
    """Service for tracking system health and failures"""
    
    @staticmethod
    def record_health_check(
        db: Session,
        check_type: str,
        component_name: str,
        status: str,
        severity: str,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_stacktrace: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
        response_context: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None,
        retry_count: int = 0,
        affected_operations: Optional[List[str]] = None,
        user_impact: Optional[str] = None
    ) -> SystemHealth:
        """Record a system health check"""
        health_check = SystemHealth(
            check_type=check_type,
            component_name=component_name,
            status=status,
            severity=severity,
            error_type=error_type,
            error_message=error_message,
            error_stacktrace=error_stacktrace,
            request_context=request_context,
            response_context=response_context,
            response_time_ms=response_time_ms,
            retry_count=retry_count,
            affected_operations=affected_operations,
            user_impact=user_impact
        )
        db.add(health_check)
        db.commit()
        db.refresh(health_check)
        
        # Check if we should create a system alert
        if severity in ['error', 'critical'] and status == 'failed':
            HealthService.create_system_alert_from_health_check(db, health_check)
        
        return health_check
    
    @staticmethod
    def update_health_check(
        db: Session,
        health_id: int,
        update_data: SystemHealthUpdate
    ) -> Optional[SystemHealth]:
        """Update a health check record"""
        health_check = db.query(SystemHealth).filter(SystemHealth.id == health_id).first()
        if not health_check:
            return None
        
        if update_data.status:
            health_check.status = update_data.status
        if update_data.is_resolved is not None:
            health_check.is_resolved = update_data.is_resolved
            if update_data.is_resolved:
                health_check.resolved_at = datetime.utcnow()
        if update_data.resolution_notes:
            health_check.resolution_notes = update_data.resolution_notes
        
        db.commit()
        db.refresh(health_check)
        return health_check
    
    @staticmethod
    def get_health_checks(
        db: Session,
        check_type: Optional[str] = None,
        component_name: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SystemHealth]:
        """Get health checks with filters (by default shows only unresolved)"""
        query = db.query(SystemHealth)
        
        if check_type:
            query = query.filter(SystemHealth.check_type == check_type)
        if component_name:
            query = query.filter(SystemHealth.component_name == component_name)
        if status:
            query = query.filter(SystemHealth.status == status)
        if severity:
            query = query.filter(SystemHealth.severity == severity)
        # Filter by resolved status - default to showing only unresolved
        if is_resolved is not None:
            query = query.filter(SystemHealth.is_resolved == is_resolved)
        else:
            query = query.filter(SystemHealth.is_resolved == False)  # Default: only unresolved
        if start_date:
            query = query.filter(SystemHealth.detected_at >= start_date)
        if end_date:
            query = query.filter(SystemHealth.detected_at <= end_date)
        
        query = query.order_by(desc(SystemHealth.detected_at)).limit(limit)
        
        return query.all()
    
    @staticmethod
    def create_system_alert_from_health_check(
        db: Session,
        health_check: SystemHealth
    ) -> SystemAlert:
        """Create a system alert from a health check"""
        alert = SystemAlert(
            alert_type='health_check_failed',
            title=f"{health_check.component_name} - {health_check.error_type or 'Error'}",
            description=health_check.error_message or f"{health_check.component_name} health check failed",
            severity=health_check.severity,
            component=health_check.component_name,
            alert_data={
                'health_check_id': health_check.id,
                'check_type': health_check.check_type,
                'error_type': health_check.error_type,
                'response_time_ms': health_check.response_time_ms,
                'retry_count': health_check.retry_count
            }
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def create_system_alert(
        db: Session,
        alert_type: str,
        title: str,
        description: str,
        severity: str,
        component: Optional[str] = None,
        metric_type: Optional[str] = None,
        threshold_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        alert_data: Optional[Dict[str, Any]] = None
    ) -> SystemAlert:
        """Create a system alert"""
        alert = SystemAlert(
            alert_type=alert_type,
            title=title,
            description=description,
            severity=severity,
            component=component,
            metric_type=metric_type,
            threshold_value=threshold_value,
            actual_value=actual_value,
            alert_data=alert_data
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def update_system_alert(
        db: Session,
        alert_id: int,
        update_data: SystemAlertUpdate
    ) -> Optional[SystemAlert]:
        """Update a system alert"""
        alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
        if not alert:
            return None
        
        if update_data.status:
            alert.status = update_data.status
            if update_data.status == 'resolved':
                alert.resolved_at = datetime.now(timezone.utc)
        if update_data.acknowledged_by:
            alert.acknowledged_by = update_data.acknowledged_by
            alert.acknowledged_at = datetime.now(timezone.utc)
        if update_data.resolution_notes:
            alert.resolution_notes = update_data.resolution_notes
        
        db.commit()
        db.refresh(alert)
        return alert
    
    @staticmethod
    def get_system_alerts(
        db: Session,
        alert_type: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        component: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SystemAlert]:
        """Get system alerts with filters (by default shows only active/acknowledged, not resolved)"""
        query = db.query(SystemAlert)
        
        if alert_type:
            query = query.filter(SystemAlert.alert_type == alert_type)
        # Filter by status - default to showing only active/acknowledged (not resolved)
        if status:
            query = query.filter(SystemAlert.status == status)
        else:
            query = query.filter(SystemAlert.status.in_(['active', 'acknowledged']))  # Default: exclude resolved
        if severity:
            query = query.filter(SystemAlert.severity == severity)
        if component:
            query = query.filter(SystemAlert.component == component)
        if start_date:
            query = query.filter(SystemAlert.triggered_at >= start_date)
        if end_date:
            query = query.filter(SystemAlert.triggered_at <= end_date)
        
        query = query.order_by(desc(SystemAlert.triggered_at)).limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_system_status(db: Session) -> str:
        """Get overall system status"""
        # Check for active critical alerts
        critical_alerts = db.query(SystemAlert).filter(
            and_(
                SystemAlert.severity == 'critical',
                SystemAlert.status == 'active'
            )
        ).count()
        
        if critical_alerts > 0:
            return 'critical'
        
        # Check for unresolved errors
        unresolved_errors = db.query(SystemHealth).filter(
            and_(
                SystemHealth.severity.in_(['error', 'critical']),
                SystemHealth.is_resolved == False
            )
        ).count()
        
        if unresolved_errors > 0:
            return 'degraded'
        
        return 'healthy'


class SuperadminService:
    """Service for superadmin dashboard and overview"""
    
    @staticmethod
    def get_dashboard(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> SuperadminDashboard:
        """Get complete superadmin dashboard data"""
        now = datetime.now(timezone.utc)
        if not start_date:
            start_date = now - timedelta(days=7)
        if not end_date:
            end_date = now
        # Ensure dates are timezone-aware for proper comparison with DB timestamps
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        # Get metrics summary
        metrics_summary = MetricsService.calculate_alert_metrics(db, start_date, end_date)
        
        # Get unresolved compliance alerts (not acknowledged, sorted by severity and recency)
        from sqlalchemy import case
        from app.models.user import User
        
        severity_order = case(
            (ComplianceAlert.severity == 'critical', 4),
            (ComplianceAlert.severity == 'high', 3),
            (ComplianceAlert.severity == 'medium', 2),
            (ComplianceAlert.severity == 'low', 1),
            else_=0
        )
        
        unresolved_alerts = db.query(ComplianceAlert).outerjoin(
            User, ComplianceAlert.user_id == User.user_id
        ).filter(
            and_(
                ComplianceAlert.status.in_(['active', 'investigating']),
                or_(
                    ComplianceAlert.is_acknowledged == False,
                    ComplianceAlert.is_acknowledged.is_(None)
                )
            )
        ).order_by(
            severity_order.desc(),
            desc(ComplianceAlert.created_at)
        ).limit(20).all()
        
        # Build compliance alert summaries
        from app.schemas.superadmin import ComplianceAlertSummary
        compliance_alert_summaries = []
        for alert in unresolved_alerts:
            compliance_alert_summaries.append(ComplianceAlertSummary(
                id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                user_id=alert.user_id,
                user_name=alert.user.username if alert.user else None,
                status=alert.status,
                priority=alert.priority,
                is_acknowledged=alert.is_acknowledged or False,
                created_at=alert.created_at,
                triggered_at=alert.triggered_at
            ))
        
        # Get active system alerts (separate from compliance alerts)
        active_system_alerts = HealthService.get_system_alerts(
            db,
            status='active',
            limit=10
        )
        
        # Get recent health issues
        recent_health_issues = HealthService.get_health_checks(
            db,
            is_resolved=False,
            limit=10
        )
        
        # Get recent audit logs
        audit_filter = AuditLogFilter(limit=20, offset=0)
        recent_audit_logs_data = AuditService.get_audit_logs_with_admin_info(db, audit_filter)
        
        # Get system status
        system_status = HealthService.get_system_status(db)
        
        return SuperadminDashboard(
            metrics_summary=metrics_summary,
            unresolved_compliance_alerts=compliance_alert_summaries,
            active_system_alerts=[SystemAlertResponse.model_validate(alert) for alert in active_system_alerts],
            recent_health_issues=[SystemHealthResponse.model_validate(health) for health in recent_health_issues],
            recent_audit_logs=[AuditLogResponse(**log) for log in recent_audit_logs_data],
            system_status=system_status
        )
