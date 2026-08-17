# Frontend API Reference

Complete API reference with dummy data, request/response examples, and endpoint documentation.

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Users API](#users-api)
3. [Transactions API](#transactions-api)
4. [Compliance Alerts API](#compliance-alerts-api)
5. [Dashboard API](#dashboard-api)
6. [Superadmin API](#superadmin-api)
7. [Dummy Data Reference](#dummy-data-reference)

---

## 🔐 Authentication

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "superadmin",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "superadmin",
  "username": "superadmin"
}
```

### Test Credentials

| Username | Password | Role |
|----------|----------|------|
| `superadmin` | `password123` | superadmin |
| `admin1` | `password123` | admin |
| `admin2` | `password123` | admin |

### Using the Token

Include in all authenticated requests:
```http
Authorization: Bearer <access_token>
```

---

## 👤 Users API

### Get All Users

```http
GET /users?skip=0&limit=100
```

**Response:**
```json
[
  {
    "user_id": 1001,
    "username": "john_doe",
    "email": "john.doe@example.com",
    "phone": "9876543210",
    "uin": "AAAA1234567890BBBB12",
    "uin_hash": null,
    "profile_pic": null,
    "date_of_birth": "1992-05-15T00:00:00",
    "address": "123 Main Street, City 25",
    "occupation": "Software Engineer",
    "annual_income": 1200000.0,
    "kyc_status": "verified",
    "kyc_verified_at": "2024-06-15T10:30:00",
    "signature_hash": null,
    "credit_score": 750,
    "current_rps_not": 0.15,
    "current_rps_360": 0.22,
    "last_rps_calculation": "2024-12-06T14:00:00",
    "risk_category": "low",
    "blacklisted": false,
    "blacklisted_at": null,
    "version": 1,
    "time": null,
    "diff": null,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-12-06T14:00:00"
  }
]
```

### Get Single User

```http
GET /users/{user_id}
```

**Example:** `GET /users/1001`

**Response:** Same as single user object above

### User Field Reference

| Field | Type | Range/Format | Description |
|-------|------|--------------|-------------|
| `user_id` | integer | BIGINT | Primary key |
| `username` | string | max 100 chars | Display name |
| `email` | string | email format | User email |
| `phone` | string | max 15 chars | Phone number |
| `credit_score` | integer | 300-900 | Credit score |
| `current_rps_not` | float | 0.0-1.0 | RPS NOT score |
| `current_rps_360` | float | 0.0-1.0 | RPS 360 score |
| `risk_category` | string | low/medium/high/critical | Risk level |
| `kyc_status` | string | pending/verified/rejected/under_review | KYC state |
| `blacklisted` | boolean | true/false | Blacklist status |

---

## 💳 Transactions API

### Get All Transactions

```http
GET /transactions?skip=0&limit=100
```

**Response:**
```json
[
  {
    "transaction_id": 5001,
    "user_id": 1001,
    "timestamp": "2024-11-15T14:30:00",
    "amount": 25000.50,
    "currency": "INR",
    "txn_type": "TRANSFER",
    "counterparty_id": 1002,
    "is_fraud": 0
  }
]
```

### Get User Transactions

```http
GET /transactions/user/{user_id}?skip=0&limit=100
```

### Get Fraud Transactions

```http
GET /transactions/fraud/all?skip=0&limit=100
```

### Filter by Amount

```http
GET /transactions/filter/amount?min_amount=1000&max_amount=100000
```

### Filter by Date

```http
GET /transactions/filter/date?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59
```

### Transaction Field Reference

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `transaction_id` | integer | BIGINT | Primary key |
| `user_id` | integer | BIGINT | User foreign key |
| `amount` | float | > 0 | Transaction amount |
| `currency` | string | INR/USD/EUR/GBP | Currency code |
| `txn_type` | string | TRANSFER/DEPOSIT/WITHDRAWAL/PAYMENT/REFUND | Type |
| `is_fraud` | integer | 0 or 1 | Fraud flag |

---

## 🚨 Compliance Alerts API

### Get Alerts (with filters)

```http
GET /compliance/alerts?limit=50&offset=0&severity=all&status=active
```

**Query Parameters:**
| Parameter | Type | Values | Default |
|-----------|------|--------|---------|
| `limit` | int | 1-500 | 50 |
| `offset` | int | ≥0 | 0 |
| `severity` | string | low/medium/high/critical/all | - |
| `status` | string | active/investigating/resolved/dismissed/escalated/all | - |
| `alert_type` | string | kyc_alert/transaction_alert/fraud_alert/aml_alert/sanction_alert/behavioral_alert | - |
| `user_id` | int | valid user_id | - |

**Response:**
```json
{
  "total": 25,
  "items": [
    {
      "id": 1,
      "alert_type": "fraud_alert",
      "severity": "critical",
      "title": "Fraud Detected: Transaction 5045",
      "description": "Suspicious transaction of INR 450000.00 detected. Transaction flagged as potential fraud.",
      "user_id": 1003,
      "user_name": "robert_johnson",
      "transaction_id": 5045,
      "entity_id": "5045",
      "entity_type": "transaction",
      "rps360": 0.85,
      "priority": "critical",
      "source": "fraud_detection",
      "triggered_by": "ml_model",
      "alert_metadata": null,
      "triggered_at": "2024-12-05T15:45:00",
      "status": "active",
      "is_acknowledged": false,
      "acknowledged_at": null,
      "acknowledged_by": null,
      "dismissal_reason": null,
      "created_at": "2024-12-05T15:45:00",
      "updated_at": "2024-12-05T15:45:00"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

### Get Pending/Unclassified Alerts

```http
GET /dashboard/alerts/unclassified?limit=50&severity=all
```

**Response:**
```json
{
  "total": 15,
  "alerts": [
    {
      "id": 5,
      "user_id": 1003,
      "user_name": "robert_johnson",
      "transaction_id": null,
      "alert_type": "aml_alert",
      "severity": "high",
      "title": "Risk Alert: robert_johnson",
      "description": "User robert_johnson flagged due to elevated risk profile. RPS 360 Score: 0.78",
      "entity_id": "1003",
      "rps360": 0.78,
      "status": "active",
      "priority": "high",
      "triggered_at": "2024-12-01T10:00:00",
      "created_at": "2024-12-01T10:00:00"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

### Resolve Alert (True Positive)

```http
POST /compliance/alerts/{alert_id}/resolve
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": "Confirmed as valid fraud - action taken"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Alert resolved as true positive",
  "alert_id": 5,
  "status": "resolved",
  "resolved_at": "2024-12-07T10:30:00",
  "resolved_by": "admin1"
}
```

### Dismiss Alert (False Positive)

```http
POST /compliance/alerts/{alert_id}/dismiss
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "False positive - legitimate transaction verified"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Alert dismissed as false positive",
  "alert_id": 5,
  "status": "dismissed",
  "dismissed_at": "2024-12-07T10:30:00",
  "dismissed_by": "admin1",
  "reason": "False positive - legitimate transaction verified"
}
```

### Get Alert Statistics

```http
GET /compliance/alerts/stats/summary
```

**Response:**
```json
{
  "total": 45,
  "pending_review": 15,
  "active": 12,
  "investigating": 3,
  "resolved": 20,
  "dismissed": 8,
  "escalated": 2,
  "by_severity": {
    "low": 2,
    "medium": 5,
    "high": 6,
    "critical": 2
  }
}
```

---

## 📊 Dashboard API

### Get Summary

```http
GET /dashboard/summary
```

**Response:**
```json
{
  "total_users": 10,
  "total_transactions": 125,
  "blacklisted_users": 1,
  "high_risk_users": 2,
  "average_i360_score": 45.2,
  "total_volume": 12500000.50,
  "average_i_not_score": 38.5
}
```

### Get Risk Distribution

```http
GET /dashboard/risk-distribution
```

**Response:**
```json
{
  "low_risk": 5,
  "medium_risk": 2,
  "high_risk": 2,
  "critical_risk": 1
}
```

### Get Critical Alerts

```http
GET /dashboard/critical-alerts?limit=10&severity=all&hours=24
```

**Response:**
```json
[
  {
    "id": "alert_1",
    "alert_type": "fraud_alert",
    "severity": "critical",
    "description": "Suspicious transaction detected",
    "user_id": 1003,
    "user_name": "robert_johnson",
    "transaction_id": 5045,
    "amount": 450000.00,
    "triggered_at": "2024-12-06T15:45:00",
    "time_ago_seconds": 3600,
    "is_acknowledged": false,
    "assigned_to": null
  }
]
```

### Get Live Alerts

```http
GET /dashboard/live-alerts?limit=20
```

**Response:**
```json
[
  {
    "id": "alert_1",
    "severity": "critical",
    "triggered_at": "2024-12-06T15:45:00",
    "time_display": "15:45:00"
  }
]
```

### Get Alert Trend

```http
GET /dashboard/alert-trend?period=24h&interval=1h&severity=all
```

**Response:**
```json
{
  "period": "24h",
  "interval": "1h",
  "data_points": [
    {
      "timestamp": "2024-12-05T16:00:00",
      "count": 3,
      "critical_count": 1,
      "high_count": 1,
      "medium_count": 1,
      "low_count": 0
    }
  ],
  "total_alerts": 25,
  "avg_per_interval": 1.04
}
```

### Get Flagged Transactions

```http
GET /dashboard/flagged-transactions?limit=10
```

**Response:**
```json
[
  {
    "transaction_id": 5045,
    "user_id": 1003,
    "user_name": "robert_johnson",
    "amount": 450000.00,
    "currency": "INR",
    "suspicious_score": 100,
    "transaction_type": "TRANSFER",
    "is_fraud": 1,
    "created_at": "2024-12-05T14:30:00"
  }
]
```

---

## 🛡️ Superadmin API

All endpoints require `superadmin` role.

### Get Dashboard

```http
GET /api/superadmin/dashboard?days=7
Authorization: Bearer <superadmin_token>
```

**Response:**
```json
{
  "metrics_summary": {
    "alert_hit_rate": 78.5,
    "false_positive_rate": 21.5,
    "avg_response_time_ms": 250.0,
    "api_error_rate": 0.5,
    "total_alerts": 45,
    "true_positives": 35,
    "false_positives": 10,
    "unreviewed": 15,
    "period_start": "2024-11-30T00:00:00",
    "period_end": "2024-12-07T00:00:00"
  },
  "active_system_alerts": [],
  "recent_health_issues": [],
  "recent_audit_logs": [
    {
      "id": 1,
      "admin_id": 1,
      "admin_username": "superadmin",
      "action_type": "blacklist_user",
      "action_description": "Admin superadmin performed blacklist_user on user",
      "target_type": "user",
      "target_id": 1007,
      "created_at": "2024-12-05T10:00:00"
    }
  ],
  "system_status": "healthy"
}
```

### Get Audit Logs

```http
GET /api/superadmin/audit-logs?limit=100&offset=0
Authorization: Bearer <superadmin_token>
```

### Get Metrics Summary

```http
GET /api/superadmin/metrics/summary?days=7
Authorization: Bearer <superadmin_token>
```

### Get Alert Resolution Stats

```http
GET /api/superadmin/metrics/alert-resolutions?days=30
Authorization: Bearer <superadmin_token>
```

**Response:**
```json
{
  "total_alerts": 100,
  "resolved_true_positive": 65,
  "resolved_false_positive": 20,
  "dismissed": 20,
  "escalated": 5,
  "pending_review": 10,
  "avg_resolution_time_hours": 4.5
}
```

### Get Admin Activity Stats

```http
GET /api/superadmin/metrics/admin-activity?days=30
Authorization: Bearer <superadmin_token>
```

**Response:**
```json
[
  {
    "admin_id": 1,
    "admin_username": "superadmin",
    "total_actions": 150,
    "alerts_reviewed": 45,
    "users_flagged": 10,
    "decisions_made": 55,
    "last_active": "2024-12-07T10:00:00"
  }
]
```

### Get System Status

```http
GET /api/superadmin/system-status
Authorization: Bearer <superadmin_token>
```

**Response:**
```json
{
  "status": "healthy",
  "critical_alerts": 0,
  "unresolved_errors": 0,
  "checked_at": "2024-12-07T10:30:00"
}
```

---

## 📦 Dummy Data Reference

### Users

| user_id | username | email | risk_category | rps_360 | blacklisted |
|---------|----------|-------|---------------|---------|-------------|
| 1001 | john_doe | john.doe@example.com | low | 0.22 | false |
| 1002 | jane_smith | jane.smith@example.com | medium | 0.52 | false |
| 1003 | robert_johnson | robert.johnson@example.com | high | 0.78 | false |
| 1004 | emily_brown | emily.brown@example.com | low | 0.12 | false |
| 1005 | michael_wilson | michael.wilson@example.com | medium | 0.61 | false |
| 1006 | sarah_davis | sarah.davis@example.com | low | 0.30 | false |
| 1007 | david_martinez | david.martinez@example.com | critical | 0.92 | **true** |
| 1008 | lisa_anderson | lisa.anderson@example.com | low | 0.15 | false |
| 1009 | james_taylor | james.taylor@example.com | high | 0.75 | false |
| 1010 | amanda_thomas | amanda.thomas@example.com | low | 0.24 | false |

### Sample Transactions

| transaction_id | user_id | amount | currency | txn_type | is_fraud |
|----------------|---------|--------|----------|----------|----------|
| 5001 | 1001 | 25000.50 | INR | TRANSFER | 0 |
| 5002 | 1001 | 15000.00 | INR | PAYMENT | 0 |
| 5045 | 1003 | 450000.00 | INR | TRANSFER | 1 |
| 5078 | 1007 | 980000.00 | USD | TRANSFER | 1 |

### Alert Types

| Type | Description |
|------|-------------|
| `kyc_alert` | KYC verification issues |
| `transaction_alert` | Unusual transaction patterns |
| `fraud_alert` | Potential fraud detected |
| `aml_alert` | Anti-money laundering triggers |
| `sanction_alert` | Sanction list matches |
| `behavioral_alert` | Behavioral anomalies |

### Alert Severities

| Severity | Description | Color |
|----------|-------------|-------|
| `low` | Minor concern | 🟢 Green |
| `medium` | Moderate risk | 🟡 Yellow |
| `high` | Significant risk | 🟠 Orange |
| `critical` | Urgent action needed | 🔴 Red |

### Alert Statuses

| Status | Description |
|--------|-------------|
| `active` | New, pending review |
| `investigating` | Under investigation |
| `resolved` | Confirmed as true positive |
| `dismissed` | Confirmed as false positive |
| `escalated` | Escalated to higher authority |

---

## 🔧 Running the Seed Script

To populate the database with dummy data:

```bash
cd backend
python scripts/seed_database.py
```

This will create:
- **3 admin accounts** (superadmin, admin1, admin2)
- **10 user accounts** (user_id: 1001-1010)
- **123 transactions** (transaction_id: 5001+)
- **21 compliance alerts** (mixed statuses and severities)
- **50 audit logs** (admin actions)
- **15 system health records**
- **21 system metrics** (7 days of metrics data)

---

## 📝 Notes

1. **RPS Scores**: All RPS scores (`current_rps_not`, `current_rps_360`, `rps360`) are floats between 0.0 and 1.0
2. **Credit Scores**: Valid range is 300-900
3. **Timestamps**: All timestamps are in ISO 8601 format
4. **Authentication**: Most write operations require admin authentication
5. **Pagination**: Use `skip`/`offset` and `limit` for paginated endpoints

---

**Last Updated**: December 7, 2024
**API Version**: 2.0

