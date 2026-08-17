"""
Helper utilities for superadmin monitoring and audit logging.
Provides convenient wrappers for common monitoring tasks.
"""

from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session
from fastapi import Request
import time
import functools
from datetime import datetime, timedelta

from app.services.superadmin_service import (
    AuditService, MetricsService, HealthService
)


class AuditLogger:
    """Helper class for audit logging"""
    
    @staticmethod
    def log_action(
        db: Session,
        admin_id: int,
        action_type: str,
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """
        Convenient method to create audit log.
        
        Example:
            AuditLogger.log_action(
                db=db,
                admin_id=current_admin.id,
                action_type="blacklist_user",
                description=f"Blacklisted user {user_id}",
                target_type="user",
                target_id=user_id,
                metadata={"reason": "Suspicious activity"},
                request=request
            )
        """
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        return AuditService.create_audit_log(
            db=db,
            admin_id=admin_id,
            action_type=action_type,
            action_description=description,
            target_type=target_type,
            target_id=target_id,
            target_identifier=str(target_id) if target_id else None,
            action_metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )


class HealthMonitor:
    """Helper class for health monitoring"""
    
    @staticmethod
    def check_and_record(
        db: Session,
        component_name: str,
        check_function: Callable,
        check_type: str = "api_health",
        severity_on_fail: str = "error",
        user_impact: str = "medium"
    ) -> tuple[bool, Any]:
        """
        Execute a health check and automatically record results.
        
        Returns: (success: bool, result: Any)
        
        Example:
            success, data = HealthMonitor.check_and_record(
                db=db,
                component_name="sanctions_api",
                check_function=lambda: sanctions_api.get_data(),
                check_type="api_health",
                severity_on_fail="error"
            )
        """
        start_time = time.time()
        try:
            result = check_function()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            HealthService.record_health_check(
                db=db,
                check_type=check_type,
                component_name=component_name,
                status="healthy",
                severity="info",
                response_time_ms=response_time_ms
            )
            
            return True, result
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            HealthService.record_health_check(
                db=db,
                check_type=check_type,
                component_name=component_name,
                status="failed",
                severity=severity_on_fail,
                error_type=type(e).__name__,
                error_message=str(e),
                error_stacktrace=None,  # Could add traceback here
                response_time_ms=response_time_ms,
                user_impact=user_impact
            )
            
            return False, None


def monitor_api_call(component_name: str, check_type: str = "api_health"):
    """
    Decorator to automatically monitor API calls.
    
    Example:
        @monitor_api_call("sanctions_api")
        async def get_sanctions(db: Session, user_id: int):
            # Your API call here
            return api_client.get_sanctions(user_id)
    
    Usage in route:
        result = await get_sanctions(db, user_id)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to find db session in args or kwargs
            db = None
            for arg in args:
                if isinstance(arg, Session):
                    db = arg
                    break
            if not db and 'db' in kwargs:
                db = kwargs['db']
            
            if not db:
                # If no db found, just execute function without monitoring
                return await func(*args, **kwargs)
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                response_time_ms = int((time.time() - start_time) * 1000)
                
                HealthService.record_health_check(
                    db=db,
                    check_type=check_type,
                    component_name=component_name,
                    status="healthy",
                    severity="info",
                    response_time_ms=response_time_ms
                )
                
                return result
                
            except Exception as e:
                response_time_ms = int((time.time() - start_time) * 1000)
                
                HealthService.record_health_check(
                    db=db,
                    check_type=check_type,
                    component_name=component_name,
                    status="failed",
                    severity="error",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    response_time_ms=response_time_ms,
                    user_impact="medium"
                )
                
                raise  # Re-raise the exception
        
        return wrapper
    return decorator


class MetricsCalculator:
    """Helper class for calculating and recording metrics"""
    
    @staticmethod
    def calculate_and_record_daily_metrics(db: Session):
        """
        Calculate and record all daily metrics.
        Should be run as a scheduled task.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        # Calculate alert metrics
        metrics = MetricsService.calculate_alert_metrics(db, start_date, end_date)
        
        # Record each metric
        MetricsService.record_metric(
            db=db,
            metric_type="resolution_rate",
            metric_category="alert",
            metric_value=metrics.resolution_rate,
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=start_date,
            aggregation_period_end=end_date,
            total_count=metrics.total_alerts,
            positive_count=metrics.resolved,
            negative_count=metrics.unresolved
        )
        
        MetricsService.record_metric(
            db=db,
            metric_type="avg_response_time",
            metric_category="alert",
            metric_value=metrics.avg_response_time_ms,
            metric_unit="milliseconds",
            time_window="daily",
            aggregation_period_start=start_date,
            aggregation_period_end=end_date
        )
        
        MetricsService.record_metric(
            db=db,
            metric_type="api_error_rate",
            metric_category="api",
            metric_value=metrics.api_error_rate,
            metric_unit="percentage",
            time_window="daily",
            aggregation_period_start=start_date,
            aggregation_period_end=end_date
        )
        
        return metrics
    
    @staticmethod
    def check_and_alert_on_thresholds(db: Session, metrics):
        """
        Check metrics against thresholds and create alerts if needed.
        """
        alerts_created = []
        
        # Check low resolution rate (if less than 50% resolved, create alert)
        if metrics.resolution_rate < 50 and metrics.total_alerts > 0:  # 50% threshold
            alert = HealthService.create_system_alert(
                db=db,
                alert_type="threshold_breach",
                title="Low Alert Resolution Rate",
                description=f"Alert resolution rate is {metrics.resolution_rate}%, below 50% threshold",
                severity="warning" if metrics.resolution_rate > 25 else "error",
                metric_type="resolution_rate",
                threshold_value="50%",
                actual_value=f"{metrics.resolution_rate}%",
                alert_data={
                    "total_alerts": metrics.total_alerts,
                    "resolved": metrics.resolved,
                    "unresolved": metrics.unresolved,
                    "period_start": metrics.period_start.isoformat(),
                    "period_end": metrics.period_end.isoformat()
                }
            )
            alerts_created.append(alert)
        
        # Check API error rate
        if metrics.api_error_rate > 5:  # 5% threshold
            alert = HealthService.create_system_alert(
                db=db,
                alert_type="high_error_rate",
                title="High API Error Rate",
                description=f"API error rate is {metrics.api_error_rate}%, exceeding 5% threshold",
                severity="error" if metrics.api_error_rate > 10 else "warning",
                component="api",
                metric_type="api_error_rate",
                threshold_value="5%",
                actual_value=f"{metrics.api_error_rate}%"
            )
            alerts_created.append(alert)
        
        # Check response time
        if metrics.avg_response_time_ms > 5000:  # 5 seconds threshold
            alert = HealthService.create_system_alert(
                db=db,
                alert_type="slow_response",
                title="Slow Alert Response Time",
                description=f"Average response time is {metrics.avg_response_time_ms}ms, exceeding 5000ms threshold",
                severity="warning",
                metric_type="avg_response_time",
                threshold_value="5000ms",
                actual_value=f"{metrics.avg_response_time_ms}ms"
            )
            alerts_created.append(alert)
        
        return alerts_created


def audit_user_flag(
    db: Session,
    admin_id: int,
    user_id: int,
    action: str,  # 'blacklist', 'whitelist', 'flag', 'unflag'
    reason: str,
    request: Optional[Request] = None
):
    """Audit log for user flagging/blacklisting"""
    action_types = {
        'blacklist': 'blacklist_user',
        'whitelist': 'whitelist_user',
        'flag': 'flag_user',
        'unflag': 'unflag_user'
    }
    
    return AuditLogger.log_action(
        db=db,
        admin_id=admin_id,
        action_type=action_types.get(action, 'other'),
        description=f"{action.title()}ed user {user_id}: {reason}",
        target_type="user",
        target_id=user_id,
        metadata={
            "action": action,
            "reason": reason
        },
        request=request
    )
