# Superadmin Monitoring & Audit System

## Overview

This system provides comprehensive monitoring, auditing, and alerting capabilities for superadmin users. It tracks system health, records metrics, maintains audit logs, and provides alerting for anomalous behavior.

## Features

### 1. Audit Logging
- **Records all admin actions** including who was flagged, by which admin, and how decisions were resolved
- **Tracks alert classifications** with before/after states
- **Captures context** including IP address, user agent, and detailed metadata
- **Provides searchable history** with filters by admin, action type, target, and date range

### 2. Metrics Tracking
- **Alert Hit Rate**: Percentage of alerts that are true positives
- **False Positive Rate**: Percentage of alerts that are false positives
- **Response Times**: Average time from alert creation to review
- **API Error Rates**: Tracking of API failures and errors
- **Resolution Statistics**: How alerts are resolved (true positive, false positive, dismissed, escalated)
- **Admin Activity**: Performance metrics for each admin

### 3. System Health Monitoring
- **Upstream API Monitoring**: Detects and tracks API downtime
- **Parser Error Detection**: Captures and logs parsing failures
- **Database Health**: Monitors database connectivity and performance
- **Service Health**: Tracks individual service status

### 4. System Alerts
- **Automatic Alert Generation**: Creates alerts when system behaves unexpectedly
- **Severity Levels**: Warning, error, and critical alerts
- **Threshold Breach Detection**: Monitors metrics against configured thresholds
- **Alert Management**: Acknowledge, resolve, and track alert lifecycle

## Database Schema

### New Tables

#### `system_metrics`
Stores system-wide metrics for analysis and monitoring.

#### `system_health`
Records health checks, failures, and system issues.

#### `system_alerts`
Stores system-level alerts for superadmin attention.

## API Endpoints

### Dashboard
- `GET /api/superadmin/dashboard?days=7`
  - Complete dashboard with metrics, alerts, and recent activity
  - Requires: Superadmin role

### Audit Logs
- `GET /api/superadmin/audit-logs`
  - Get filtered audit logs
  - Query params: admin_id, action_type, target_type, start_date, end_date, limit, offset
  
- `GET /api/superadmin/audit-logs/{audit_id}`
  - Get specific audit log details

### Metrics
- `GET /api/superadmin/metrics/summary?days=7`
  - Get metrics summary (hit rates, false positives, response times, errors)
  
- `GET /api/superadmin/metrics/history`
  - Get historical metrics data
  - Query params: metric_type, metric_category, start_date, end_date, limit
  
- `GET /api/superadmin/metrics/alert-resolutions?days=30`
  - Get statistics about alert resolutions
  
- `GET /api/superadmin/metrics/admin-activity?days=30`
  - Get admin activity and performance statistics

### System Health
- `GET /api/superadmin/health/checks`
  - Get system health checks
  - Query params: check_type, component_name, status, severity, is_resolved, start_date, end_date, limit
  
- `PATCH /api/superadmin/health/checks/{health_id}`
  - Update health check (mark as resolved)
  - Body: `{"status": "resolved", "is_resolved": true, "resolution_notes": "Fixed by..."}"`

### System Alerts
- `GET /api/superadmin/alerts`
  - Get system alerts
  - Query params: alert_type, status, severity, component, start_date, end_date, limit
  
- `PATCH /api/superadmin/alerts/{alert_id}`
  - Update system alert (acknowledge, resolve)
  - Body: `{"status": "acknowledged", "resolution_notes": "Investigating..."}`
  
- `GET /api/superadmin/system-status`
  - Get overall system status (healthy, degraded, critical)

## Integration Guide

### 1. Database Migration

Run the migration script to create new tables:

```bash
cd backend
python scripts/migrations/migrate_add_superadmin_monitoring.py
```

### 2. Adding Audit Logging to Existing Flows

When classifying an alert, include audit logging:

```python
from app.services.alert_service import mark_alert_classification
from fastapi import Request

# In your route handler
result = mark_alert_classification(
    db=db,
    alert_id=alert_id,
    is_true_positive=classification.is_true_positive,
    reviewed_by=current_admin.username,
    admin_id=current_admin.id,  # For audit logging
    notes=classification.notes,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

### 3. Recording System Metrics

Periodically calculate and record metrics:

```python
from app.services.superadmin_service import MetricsService
from datetime import datetime, timedelta

# Calculate and record metrics
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=1)

metrics = MetricsService.calculate_alert_metrics(db, start_date, end_date)

# Record the metrics
MetricsService.record_metric(
    db=db,
    metric_type="alert_hit_rate",
    metric_category="alert",
    metric_value=metrics.alert_hit_rate,
    metric_unit="percentage",
    time_window="daily",
    aggregation_period_start=start_date,
    aggregation_period_end=end_date
)
```

### 4. Recording Health Checks

When making API calls or critical operations:

```python
from app.services.superadmin_service import HealthService
import time

start_time = time.time()
try:
    # Make API call
    response = await upstream_api.call()
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Record successful health check
    HealthService.record_health_check(
        db=db,
        check_type="api_health",
        component_name="sanctions_api",
        status="healthy",
        severity="info",
        response_time_ms=response_time_ms
    )
except Exception as e:
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Record failed health check
    HealthService.record_health_check(
        db=db,
        check_type="api_health",
        component_name="sanctions_api",
        status="failed",
        severity="error",
        error_type="connection_timeout",
        error_message=str(e),
        response_time_ms=response_time_ms,
        user_impact="high"
    )
```

### 5. Creating Manual Audit Logs

For any admin action that should be audited:

```python
from app.services.superadmin_service import AuditService

AuditService.create_audit_log(
    db=db,
    admin_id=current_admin.id,
    action_type="blacklist_user",
    action_description=f"Blacklisted user {user_id} for suspicious activity",
    target_type="user",
    target_id=user_id,
    target_identifier=str(user_id),
    action_metadata={
        "reason": "Multiple high-risk transactions",
        "previous_status": "active",
        "new_status": "blacklisted"
    },
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

### 6. Creating System Alerts

When detecting anomalies:

```python
from app.services.superadmin_service import HealthService

# Example: High API error rate detected
if error_rate > 5.0:  # 5% threshold
    HealthService.create_system_alert(
        db=db,
        alert_type="high_error_rate",
        title="High API Error Rate Detected",
        description=f"API error rate is {error_rate}%, exceeding threshold of 5%",
        severity="warning" if error_rate < 10 else "error",
        component="sanctions_api",
        metric_type="api_error_rate",
        threshold_value="5%",
        actual_value=f"{error_rate}%",
        alert_data={
            "error_count": error_count,
            "total_requests": total_requests,
            "time_window": "1hour"
        }
    )
```

## Action Types for Audit Logs

Common action types to use:
- `classify_alert` - Alert classification (true/false positive)
- `dismiss_alert` - Alert dismissed
- `escalate_alert` - Alert escalated
- `blacklist_user` - User blacklisted
- `whitelist_user` - User whitelisted
- `flag_user` - User flagged for review
- `unflag_user` - User unflagged
- `update_user_status` - User status changed
- `update_system_alert` - System alert updated
- `resolve_health_issue` - Health issue resolved

## Metric Types

Available metric types:
- `alert_hit_rate` - Percentage of true positive alerts
- `false_positive_rate` - Percentage of false positive alerts
- `api_response_time` - API response time in milliseconds
- `api_error_rate` - API error percentage
- `alert_response_time` - Time to review alerts
- `transaction_volume` - Transaction count
- `user_flagging_rate` - Rate of user flagging

## Health Check Types

Available check types:
- `api_health` - External API health
- `parser_health` - Parser operation health
- `db_health` - Database health
- `service_health` - Internal service health

## Alert Severity Levels

- `info` - Informational, no action required
- `warning` - Potential issue, should be monitored
- `error` - Issue detected, action recommended
- `critical` - Severe issue, immediate action required

## Best Practices

1. **Always log admin actions** that affect users or alerts
2. **Record health checks** for all external API calls
3. **Calculate metrics regularly** (daily or hourly)
4. **Set appropriate thresholds** for system alerts
5. **Review and acknowledge alerts** promptly
6. **Include context** in action_metadata for better traceability
7. **Use consistent action types** for easier filtering and analysis

## Monitoring Recommendations

### Daily Tasks
- Review system status and active alerts
- Check false positive rates
- Monitor API error rates
- Review unresolved health issues

### Weekly Tasks
- Analyze admin activity statistics
- Review alert resolution patterns
- Check metric trends
- Verify system health history

### Monthly Tasks
- Generate comprehensive reports
- Analyze long-term trends
- Review and adjust thresholds
- Audit admin performance

## Example Dashboard Query

```python
# Get complete dashboard data
response = requests.get(
    "http://localhost:8000/api/superadmin/dashboard?days=7",
    headers={"Authorization": f"Bearer {token}"}
)

dashboard = response.json()
print(f"System Status: {dashboard['system_status']}")
print(f"Alert Hit Rate: {dashboard['metrics_summary']['alert_hit_rate']}%")
print(f"False Positive Rate: {dashboard['metrics_summary']['false_positive_rate']}%")
print(f"Active Alerts: {len(dashboard['active_system_alerts'])}")
```

## Troubleshooting

### Issue: Audit logs not appearing
- Ensure `admin_id` is passed to audit-logging functions
- Verify database migration was successful
- Check that imports are correct

### Issue: Metrics showing 0%
- Ensure alerts are being classified (`is_true_positive` not NULL)
- Check that the date range includes classified alerts
- Verify calculation logic in MetricsService

### Issue: Health checks not creating alerts
- Check severity levels (only 'error' and 'critical' create alerts)
- Verify status is 'failed'
- Check database for SystemAlert records

## Security Considerations

- All endpoints require `superadmin` role
- Audit logs capture IP addresses for security tracking
- System alerts should be reviewed promptly
- Regular backups of audit logs recommended
- Consider log retention policies
