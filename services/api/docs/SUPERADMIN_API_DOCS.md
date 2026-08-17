# Superadmin Monitoring API Documentation

## Overview
This API provides comprehensive monitoring, auditing, and alerting capabilities for superadmin users. All endpoints require superadmin authentication via JWT token.

**Base URL**: `http://localhost:8000/api/superadmin`

**Authentication**: All endpoints require `Authorization: Bearer <token>` header with a valid superadmin JWT token.

**Database Schema**: Complete database schema is available in `superadmin_monitoring_schema.sql` at the project root.

---

## Table of Contents
1. [Dashboard](#dashboard)
2. [Audit Logs](#audit-logs)
3. [Metrics](#metrics)
4. [System Health](#system-health)
5. [System Alerts](#system-alerts)
6. [Response Models](#response-models)
7. [Error Handling](#error-handling)

---

## Dashboard

### Get Complete Dashboard
Get comprehensive superadmin dashboard with metrics, alerts, health issues, and recent audit logs.

**Endpoint**: `GET /api/superadmin/dashboard`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 7 | Number of days to analyze (1-90) |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/dashboard?days=7" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
{
  "metrics_summary": {
    "alert_hit_rate": 78.5,
    "false_positive_rate": 15.2,
    "avg_response_time_ms": 8234.56,
    "api_error_rate": 0.8,
    "total_alerts": 150,
    "true_positives": 118,
    "false_positives": 23,
    "unreviewed": 9,
    "period_start": "2025-11-29T00:00:00Z",
    "period_end": "2025-12-06T00:00:00Z"
  },
  "active_system_alerts": [
    {
      "id": 1,
      "alert_type": "threshold_breach",
      "title": "High False Positive Rate",
      "description": "False positive rate is 32.5%, exceeding 30% threshold",
      "severity": "warning",
      "component": "alert_system",
      "metric_type": "false_positive_rate",
      "threshold_value": "30%",
      "actual_value": "32.5%",
      "alert_data": {
        "total_alerts": 150,
        "false_positives": 49
      },
      "status": "active",
      "acknowledged_by": null,
      "acknowledged_at": null,
      "resolved_at": null,
      "resolution_notes": null,
      "triggered_at": "2025-12-06T10:30:00Z",
      "last_updated": "2025-12-06T10:30:00Z",
      "notifications_sent": 1
    }
  ],
  "recent_health_issues": [
    {
      "id": 15,
      "check_type": "api_health",
      "component_name": "sanctions_api",
      "status": "failed",
      "severity": "error",
      "error_type": "ConnectionTimeout",
      "error_message": "Connection timeout after 5000ms",
      "request_context": {
        "endpoint": "/api/sanctions/check",
        "user_id": 12345
      },
      "response_context": null,
      "response_time_ms": 5001,
      "retry_count": 3,
      "affected_operations": ["sanctions_check"],
      "user_impact": "high",
      "is_resolved": false,
      "resolved_at": null,
      "resolution_notes": null,
      "auto_recovered": false,
      "detected_at": "2025-12-06T09:15:00Z",
      "last_occurrence": "2025-12-06T09:15:00Z",
      "alert_sent": true
    }
  ],
  "recent_audit_logs": [
    {
      "id": 234,
      "admin_id": 5,
      "admin_username": "john.admin",
      "action_type": "classify_alert",
      "action_description": "Classified alert 567 as true_positive",
      "target_type": "alert",
      "target_id": 567,
      "target_identifier": "alert_567",
      "action_metadata": {
        "previous_state": {
          "is_true_positive": null,
          "status": "active"
        },
        "new_classification": "true_positive",
        "is_true_positive": true,
        "alert_type": "transaction_alert",
        "severity": "high"
      },
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2025-12-06T11:45:23Z"
    }
  ],
  "system_status": "healthy"
}
```

**Response Status Codes**:
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - User is not a superadmin
- `500 Internal Server Error` - Server error

---

## Audit Logs

### Get Audit Logs
Retrieve audit logs with optional filtering. Returns logs of admin actions including who was flagged, by which admin, and how decisions were resolved.

**Endpoint**: `GET /api/superadmin/audit-logs`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `admin_id` | integer | No | null | Filter by specific admin ID |
| `action_type` | string | No | null | Filter by action type (e.g., "classify_alert", "blacklist_user") |
| `target_type` | string | No | null | Filter by target type (e.g., "user", "alert", "transaction") |
| `start_date` | datetime | No | null | Start date (ISO 8601 format) |
| `end_date` | datetime | No | null | End date (ISO 8601 format) |
| `limit` | integer | No | 100 | Number of results (1-1000) |
| `offset` | integer | No | 0 | Pagination offset (≥0) |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/audit-logs?action_type=classify_alert&limit=50" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
[
  {
    "id": 234,
    "admin_id": 5,
    "admin_username": "john.admin",
    "action_type": "classify_alert",
    "action_description": "Classified alert 567 as true_positive",
    "target_type": "alert",
    "target_id": 567,
    "target_identifier": "alert_567",
    "action_metadata": {
      "previous_state": {
        "is_true_positive": null,
        "reviewed_at": null,
        "reviewed_by": null,
        "status": "active"
      },
      "new_classification": "true_positive",
      "is_true_positive": true,
      "notes": "Confirmed fraudulent transaction",
      "alert_type": "transaction_alert",
      "severity": "high",
      "user_id": 12345,
      "entity_id": "txn_98765"
    },
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "created_at": "2025-12-06T11:45:23Z"
  }
]
```

**Common Action Types**:
- `classify_alert` - Alert classified as true/false positive
- `dismiss_alert` - Alert dismissed
- `escalate_alert` - Alert escalated
- `blacklist_user` - User blacklisted
- `whitelist_user` - User whitelisted
- `flag_user` - User flagged for review
- `unflag_user` - User unflagged
- `update_system_alert` - System alert updated

---

### Get Specific Audit Log
Retrieve detailed information about a specific audit log entry.

**Endpoint**: `GET /api/superadmin/audit-logs/{audit_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `audit_id` | integer | Yes | Audit log ID |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/audit-logs/234" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK` - Same structure as audit log item above

**Response Status Codes**:
- `200 OK` - Success
- `404 Not Found` - Audit log not found

---

## Metrics

### Get Metrics Summary
Get summary of key performance metrics including hit rates, false positive rates, response times, and API error rates.

**Endpoint**: `GET /api/superadmin/metrics/summary`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 7 | Number of days to analyze (1-90) |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/metrics/summary?days=30" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
{
  "alert_hit_rate": 78.5,
  "false_positive_rate": 15.2,
  "avg_response_time_ms": 8234.56,
  "api_error_rate": 0.8,
  "total_alerts": 150,
  "true_positives": 118,
  "false_positives": 23,
  "unreviewed": 9,
  "period_start": "2025-11-06T00:00:00Z",
  "period_end": "2025-12-06T00:00:00Z"
}
```

**Field Descriptions**:
- `alert_hit_rate`: Percentage of alerts that were true positives (0-100)
- `false_positive_rate`: Percentage of alerts that were false positives (0-100)
- `avg_response_time_ms`: Average time from alert creation to review in milliseconds
- `api_error_rate`: Percentage of API calls that failed (0-100)
- `total_alerts`: Total number of alerts in the period
- `true_positives`: Number of alerts classified as true positives
- `false_positives`: Number of alerts classified as false positives
- `unreviewed`: Number of alerts not yet reviewed

---

### Get Metrics History
Retrieve historical metrics data for trend analysis.

**Endpoint**: `GET /api/superadmin/metrics/history`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `metric_type` | string | No | null | Filter by metric type (see below) |
| `metric_category` | string | No | null | Filter by category ("alert", "api", "transaction", "user") |
| `start_date` | datetime | No | null | Start date (ISO 8601 format) |
| `end_date` | datetime | No | null | End date (ISO 8601 format) |
| `limit` | integer | No | 100 | Number of results (1-1000) |

**Metric Types**:
- `alert_hit_rate` - % of true positive alerts
- `false_positive_rate` - % of false positive alerts
- `api_response_time` - API response time in milliseconds
- `api_error_rate` - API error percentage
- `alert_response_time` - Time to review alerts

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/metrics/history?metric_type=alert_hit_rate&limit=30" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
[
  {
    "id": 45,
    "metric_type": "alert_hit_rate",
    "metric_category": "alert",
    "metric_value": 78.5,
    "metric_unit": "percentage",
    "time_window": "daily",
    "aggregation_period_start": "2025-12-05T00:00:00Z",
    "aggregation_period_end": "2025-12-06T00:00:00Z",
    "details": {
      "by_severity": {
        "high": 85.2,
        "medium": 72.3,
        "low": 65.1
      }
    },
    "total_count": 150,
    "positive_count": 118,
    "negative_count": 23,
    "recorded_at": "2025-12-06T00:05:00Z",
    "is_anomaly": false,
    "anomaly_threshold": null
  }
]
```

---

### Get Alert Resolution Statistics
Get statistics about how alerts were resolved (true positive, false positive, dismissed, etc.).

**Endpoint**: `GET /api/superadmin/metrics/alert-resolutions`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 30 | Number of days to analyze (1-365) |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/metrics/alert-resolutions?days=90" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
{
  "total_alerts": 450,
  "resolved_true_positive": 340,
  "resolved_false_positive": 78,
  "dismissed": 12,
  "escalated": 8,
  "pending_review": 12,
  "avg_resolution_time_hours": 4.35
}
```

**Field Descriptions**:
- `total_alerts`: Total alerts in the period
- `resolved_true_positive`: Alerts confirmed as true positives
- `resolved_false_positive`: Alerts marked as false positives
- `dismissed`: Alerts dismissed without action
- `escalated`: Alerts escalated to higher authority
- `pending_review`: Alerts awaiting classification
- `avg_resolution_time_hours`: Average time from creation to review (in hours)

---

### Get Admin Activity Statistics
Get performance and activity statistics for each admin user.

**Endpoint**: `GET /api/superadmin/metrics/admin-activity`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `days` | integer | No | 30 | Number of days to analyze (1-365) |

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/metrics/admin-activity?days=30" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
[
  {
    "admin_id": 5,
    "admin_username": "john.admin",
    "total_actions": 234,
    "alerts_reviewed": 156,
    "users_flagged": 12,
    "decisions_made": 168,
    "last_active": "2025-12-06T11:45:23Z"
  },
  {
    "admin_id": 7,
    "admin_username": "sarah.admin",
    "total_actions": 198,
    "alerts_reviewed": 132,
    "users_flagged": 8,
    "decisions_made": 140,
    "last_active": "2025-12-06T09:30:15Z"
  }
]
```

---

## System Health

### Get Health Checks
Retrieve system health checks showing API downtime, parser errors, and other system failures.

**Endpoint**: `GET /api/superadmin/health/checks`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `check_type` | string | No | null | Filter by check type (see below) |
| `component_name` | string | No | null | Filter by component (e.g., "sanctions_api") |
| `status` | string | No | null | Filter by status ("healthy", "degraded", "failed", "recovering") |
| `severity` | string | No | null | Filter by severity ("info", "warning", "error", "critical") |
| `is_resolved` | boolean | No | null | Filter by resolution status |
| `start_date` | datetime | No | null | Start date (ISO 8601 format) |
| `end_date` | datetime | No | null | End date (ISO 8601 format) |
| `limit` | integer | No | 100 | Number of results (1-1000) |

**Check Types**:
- `api_health` - External API health checks
- `parser_health` - Data parser operations
- `db_health` - Database health
- `service_health` - Internal service health

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/health/checks?is_resolved=false&severity=error" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
[
  {
    "id": 15,
    "check_type": "api_health",
    "component_name": "sanctions_api",
    "status": "failed",
    "severity": "error",
    "error_type": "ConnectionTimeout",
    "error_message": "Connection timeout after 5000ms",
    "request_context": {
      "endpoint": "/api/sanctions/check",
      "user_id": 12345,
      "method": "POST"
    },
    "response_context": null,
    "response_time_ms": 5001,
    "retry_count": 3,
    "affected_operations": ["sanctions_check", "user_verification"],
    "user_impact": "high",
    "is_resolved": false,
    "resolved_at": null,
    "resolution_notes": null,
    "auto_recovered": false,
    "detected_at": "2025-12-06T09:15:00Z",
    "last_occurrence": "2025-12-06T09:15:00Z",
    "alert_sent": true
  }
]
```

---

### Update Health Check
Update a health check record (e.g., mark as resolved).

**Endpoint**: `PATCH /api/superadmin/health/checks/{health_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `health_id` | integer | Yes | Health check ID |

**Request Body**:
```json
{
  "status": "resolved",
  "is_resolved": true,
  "resolution_notes": "API endpoint fixed and deployed. Monitoring for 24h."
}
```

**Body Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | New status ("healthy", "degraded", "failed", "recovering") |
| `is_resolved` | boolean | No | Whether issue is resolved |
| `resolution_notes` | string | No | Notes about resolution |

**Request Example**:
```bash
curl -X PATCH "http://localhost:8000/api/superadmin/health/checks/15" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "is_resolved": true,
    "resolution_notes": "API endpoint fixed"
  }'
```

**Response**: `200 OK` - Returns updated health check (same structure as GET response)

**Response Status Codes**:
- `200 OK` - Successfully updated
- `404 Not Found` - Health check not found

---

## System Alerts

### Get System Alerts
Retrieve system-level alerts that are triggered when the system behaves unexpectedly.

**Endpoint**: `GET /api/superadmin/alerts`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `alert_type` | string | No | null | Filter by alert type (see below) |
| `status` | string | No | null | Filter by status ("active", "acknowledged", "resolved", "false_alarm") |
| `severity` | string | No | null | Filter by severity ("warning", "error", "critical") |
| `component` | string | No | null | Filter by component name |
| `start_date` | datetime | No | null | Start date (ISO 8601 format) |
| `end_date` | datetime | No | null | End date (ISO 8601 format) |
| `limit` | integer | No | 100 | Number of results (1-1000) |

**Alert Types**:
- `high_error_rate` - High API error rate detected
- `api_downtime` - API downtime detected
- `anomaly_detected` - System anomaly detected
- `threshold_breach` - Metric threshold breached
- `health_check_failed` - Critical health check failed

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/alerts?status=active&severity=critical" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
[
  {
    "id": 8,
    "alert_type": "threshold_breach",
    "title": "High False Positive Rate",
    "description": "False positive rate is 32.5%, exceeding 30% threshold",
    "severity": "warning",
    "component": "alert_system",
    "metric_type": "false_positive_rate",
    "threshold_value": "30%",
    "actual_value": "32.5%",
    "alert_data": {
      "total_alerts": 150,
      "false_positives": 49,
      "time_window": "24h"
    },
    "status": "active",
    "acknowledged_by": null,
    "acknowledged_at": null,
    "resolved_at": null,
    "resolution_notes": null,
    "triggered_at": "2025-12-06T10:30:00Z",
    "last_updated": "2025-12-06T10:30:00Z",
    "notifications_sent": 1
  }
]
```

---

### Update System Alert
Update a system alert (acknowledge or resolve).

**Endpoint**: `PATCH /api/superadmin/alerts/{alert_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_id` | integer | Yes | Alert ID |

**Request Body**:
```json
{
  "status": "acknowledged",
  "resolution_notes": "Investigating the cause. Will provide update in 2 hours."
}
```

**Body Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | New status ("active", "acknowledged", "resolved", "false_alarm") |
| `acknowledged_by` | string | No | Username acknowledging (auto-set if null) |
| `resolution_notes` | string | No | Notes about resolution or acknowledgment |

**Request Example**:
```bash
curl -X PATCH "http://localhost:8000/api/superadmin/alerts/8" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_notes": "Adjusted alert classification rules to reduce false positives"
  }'
```

**Response**: `200 OK` - Returns updated alert (same structure as GET response)

**Response Status Codes**:
- `200 OK` - Successfully updated
- `404 Not Found` - Alert not found

---

### Get System Status
Get overall system status summary.

**Endpoint**: `GET /api/superadmin/system-status`

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/superadmin/system-status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "critical_alerts": 0,
  "unresolved_errors": 2,
  "checked_at": "2025-12-06T12:00:00Z"
}
```

**Status Values**:
- `healthy` - All systems operational
- `degraded` - Some issues detected but not critical
- `critical` - Critical issues requiring immediate attention

---

## Response Models

### Common Response Fields

#### Timestamps
All timestamps are in ISO 8601 format with timezone (UTC):
```
"2025-12-06T12:34:56Z"
```

#### Pagination
For paginated endpoints, use `limit` and `offset`:
```
?limit=50&offset=100
```

#### Date Filtering
Date parameters accept ISO 8601 format:
```
?start_date=2025-12-01T00:00:00Z&end_date=2025-12-06T23:59:59Z
```

---

## Error Handling

### Error Response Format
All errors follow this structure:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid parameters or request body |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | User is not a superadmin |
| `404` | Not Found | Requested resource doesn't exist |
| `500` | Internal Server Error | Server-side error |

### Common Error Scenarios

#### Authentication Error
```json
{
  "detail": "Not authenticated"
}
```
**Solution**: Include valid JWT token in Authorization header

#### Insufficient Permissions
```json
{
  "detail": "Superadmin privileges required"
}
```
**Solution**: Use a superadmin account token

#### Resource Not Found
```json
{
  "detail": "Audit log not found"
}
```
**Solution**: Verify the resource ID exists

#### Invalid Parameters
```json
{
  "detail": "Invalid date format. Use ISO 8601."
}
```
**Solution**: Check parameter format and valid values

---

## Integration Examples

### JavaScript/TypeScript (React)

```typescript
// API client setup
const API_BASE_URL = 'http://localhost:8000/api/superadmin';

interface DashboardData {
  metrics_summary: MetricsSummary;
  active_system_alerts: SystemAlert[];
  recent_health_issues: HealthCheck[];
  recent_audit_logs: AuditLog[];
  system_status: 'healthy' | 'degraded' | 'critical';
}

// Fetch dashboard
async function fetchDashboard(token: string, days: number = 7): Promise<DashboardData> {
  const response = await fetch(`${API_BASE_URL}/dashboard?days=${days}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Get audit logs
async function fetchAuditLogs(
  token: string,
  filters: {
    admin_id?: number;
    action_type?: string;
    limit?: number;
  } = {}
): Promise<AuditLog[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) params.append(key, String(value));
  });
  
  const response = await fetch(`${API_BASE_URL}/audit-logs?${params}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  return await response.json();
}

// Acknowledge alert
async function acknowledgeAlert(
  token: string,
  alertId: number,
  notes: string
): Promise<SystemAlert> {
  const response = await fetch(`${API_BASE_URL}/alerts/${alertId}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      status: 'acknowledged',
      resolution_notes: notes
    })
  });
  
  return await response.json();
}
```

### Python (Requests)

```python
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000/api/superadmin"

class SuperadminClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_dashboard(self, days: int = 7) -> Dict:
        """Get complete dashboard data"""
        response = requests.get(
            f"{API_BASE_URL}/dashboard",
            headers=self.headers,
            params={"days": days}
        )
        response.raise_for_status()
        return response.json()
    
    def get_audit_logs(
        self,
        admin_id: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get filtered audit logs"""
        params = {"limit": limit}
        if admin_id:
            params["admin_id"] = admin_id
        if action_type:
            params["action_type"] = action_type
        
        response = requests.get(
            f"{API_BASE_URL}/audit-logs",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_metrics_summary(self, days: int = 7) -> Dict:
        """Get metrics summary"""
        response = requests.get(
            f"{API_BASE_URL}/metrics/summary",
            headers=self.headers,
            params={"days": days}
        )
        response.raise_for_status()
        return response.json()
    
    def resolve_health_check(
        self,
        health_id: int,
        resolution_notes: str
    ) -> Dict:
        """Mark health check as resolved"""
        response = requests.patch(
            f"{API_BASE_URL}/health/checks/{health_id}",
            headers=self.headers,
            json={
                "status": "resolved",
                "is_resolved": True,
                "resolution_notes": resolution_notes
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = SuperadminClient(token="your_token_here")
dashboard = client.get_dashboard(days=30)
print(f"System Status: {dashboard['system_status']}")
print(f"Hit Rate: {dashboard['metrics_summary']['alert_hit_rate']}%")
```

---

## Best Practices

### 1. Authentication
- Store JWT tokens securely (use httpOnly cookies or secure storage)
- Implement token refresh mechanism
- Handle 401/403 errors gracefully

### 2. Error Handling
- Always check response status codes
- Display user-friendly error messages
- Log errors for debugging

### 3. Performance
- Use pagination for large result sets
- Cache dashboard data (refresh every 5-10 minutes)
- Implement loading states

### 4. User Experience
- Show loading indicators during API calls
- Implement real-time updates for critical alerts
- Provide filters and search functionality
- Use charts/graphs for metrics visualization

### 5. Data Refresh
- Dashboard: Refresh every 5-10 minutes
- Active alerts: Refresh every 1-2 minutes
- Audit logs: Refresh on user action
- Metrics: Can be cached for longer periods

---

## TypeScript Type Definitions

```typescript
// Core types for TypeScript projects
interface MetricsSummary {
  alert_hit_rate: number;
  false_positive_rate: number;
  avg_response_time_ms: number;
  api_error_rate: number;
  total_alerts: number;
  true_positives: number;
  false_positives: number;
  unreviewed: number;
  period_start: string;
  period_end: string;
}

interface SystemAlert {
  id: number;
  alert_type: string;
  title: string;
  description: string;
  severity: 'warning' | 'error' | 'critical';
  component: string | null;
  metric_type: string | null;
  threshold_value: string | null;
  actual_value: string | null;
  alert_data: Record<string, any> | null;
  status: 'active' | 'acknowledged' | 'resolved' | 'false_alarm';
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  triggered_at: string;
  last_updated: string;
  notifications_sent: number;
}

interface HealthCheck {
  id: number;
  check_type: string;
  component_name: string;
  status: 'healthy' | 'degraded' | 'failed' | 'recovering';
  severity: 'info' | 'warning' | 'error' | 'critical';
  error_type: string | null;
  error_message: string | null;
  request_context: Record<string, any> | null;
  response_context: Record<string, any> | null;
  response_time_ms: number | null;
  retry_count: number;
  affected_operations: string[] | null;
  user_impact: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  resolution_notes: string | null;
  auto_recovered: boolean;
  detected_at: string;
  last_occurrence: string;
  alert_sent: boolean;
}

interface AuditLog {
  id: number;
  admin_id: number;
  admin_username: string | null;
  action_type: string;
  action_description: string;
  target_type: string | null;
  target_id: number | null;
  target_identifier: string | null;
  action_metadata: Record<string, any> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

interface Dashboard {
  metrics_summary: MetricsSummary;
  active_system_alerts: SystemAlert[];
  recent_health_issues: HealthCheck[];
  recent_audit_logs: AuditLog[];
  system_status: 'healthy' | 'degraded' | 'critical';
}
```

---

## FAQ

**Q: How often should I refresh the dashboard?**
A: Recommended refresh interval is 5-10 minutes for the dashboard. Active alerts can be refreshed more frequently (every 1-2 minutes).

**Q: What's the difference between system alerts and compliance alerts?**
A: System alerts are for infrastructure/system-level issues (API downtime, high error rates). Compliance alerts are for user/transaction-related compliance issues.

**Q: Can I filter audit logs by date range?**
A: Yes, use `start_date` and `end_date` parameters in ISO 8601 format.

**Q: How do I know if I have superadmin access?**
A: If you receive a 403 Forbidden error, your account doesn't have superadmin privileges.

**Q: What happens when an alert is acknowledged?**
A: The status changes to "acknowledged", the acknowledger's username is recorded, and the timestamp is saved. The alert remains visible but marked as acknowledged.

**Q: Can I get metrics for a specific admin?**
A: Yes, use the `/api/superadmin/metrics/admin-activity` endpoint and filter the results by admin_id.

**Q: Are there webhooks for real-time alerts?**
A: Not in the current version. Consider polling the alerts endpoint or implementing WebSocket support.

---

## Support

For additional support or questions:
- Review the full documentation in `docs/SUPERADMIN_MONITORING.md`
- Check the quick start guide in `SUPERADMIN_QUICKSTART.md`
- Run the verification tests: `python tests/test_superadmin_monitoring.py`

**API Version**: 1.0  
**Last Updated**: December 6, 2025
