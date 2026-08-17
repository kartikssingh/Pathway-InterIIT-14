-- =============================================================================
-- USEFUL QUERIES FOR COMPLIANCE & FRAUD DETECTION SYSTEM
-- =============================================================================

-- =============================================================================
-- USER QUERIES
-- =============================================================================

-- Get all high-risk users
SELECT entity_id, applicant_name, risk_level, suspicious_score, account_status
FROM users
WHERE risk_level IN ('high', 'critical')
ORDER BY suspicious_score DESC;

-- Get users pending KYC verification
SELECT entity_id, applicant_name, email, kyc_status, created_at
FROM users
WHERE kyc_status = 'pending' OR kyc_status = 'under_review'
ORDER BY created_at DESC;

-- Get blacklisted users
SELECT entity_id, applicant_name, email, blacklist_reason, blacklisted_at
FROM users
WHERE is_blacklisted = TRUE
ORDER BY blacklisted_at DESC;

-- =============================================================================
-- TRANSACTION QUERIES
-- =============================================================================

-- Get all flagged transactions
SELECT t.transaction_id, u.applicant_name, t.amount, t.transaction_type,
    t.suspicious_score, t.flag_reason, t.transaction_date
FROM transactions t
    JOIN users u ON t.user_id = u.id
WHERE t.is_flagged = TRUE
ORDER BY t.transaction_date DESC;

-- Get high-value transactions (> 100,000)
SELECT t.transaction_id, u.applicant_name, t.amount, t.transaction_type,
    t.risk_level, t.status, t.transaction_date
FROM transactions t
    JOIN users u ON t.user_id = u.id
WHERE t.amount > 100000
ORDER BY t.amount DESC;

-- Get recent transactions for a specific user
SELECT transaction_id, transaction_type, amount, status,
    suspicious_score, transaction_date
FROM transactions
WHERE user_id = 1
-- Change to desired user_id
ORDER BY transaction_date DESC
LIMIT 10;

-- =============================================================================
-- COMPLIANCE ALERT QUERIES
-- =============================================================================

-- Get all active critical alerts
SELECT ca.title, ca.severity, u.applicant_name, ca.alert_type, 
       ca.status
, ca.triggered_at
FROM compliance_alerts ca
LEFT JOIN users u ON ca.user_id = u.id
WHERE ca.severity = 'critical' AND ca.status = 'active'
ORDER BY ca.triggered_at DESC;

-- Get unacknowledged alerts
SELECT ca.id, ca.title, ca.severity, ca.alert_type, u.applicant_name, ca.triggered_at
FROM compliance_alerts ca
    LEFT JOIN users u ON ca.user_id = u.id
WHERE ca.is_acknowledged = FALSE
ORDER BY ca.severity DESC, ca.triggered_at DESC;

-- Count alerts by type and severity
SELECT alert_type, severity, COUNT(*) as alert_count
FROM compliance_alerts
GROUP BY alert_type, severity
ORDER BY alert_type, severity;

-- Get alerts for specific user
SELECT title, alert_type, severity, status, description, triggered_at
FROM compliance_alerts
WHERE user_id = 3
-- Change to desired user_id
ORDER BY triggered_at DESC;

-- =============================================================================
-- INVESTIGATION CASE QUERIES
-- =============================================================================

-- Get all open/investigating cases
SELECT ic.id, ic.case_title, u.applicant_name, ic.severity,
    ic.status, ic.assigned_to, ic.created_at, ic.due_date
FROM investigation_cases ic
    JOIN users u ON ic.user_id = u.id
WHERE ic.status IN ('open', 'investigating')
ORDER BY ic.severity DESC, ic.due_date ASC;

-- Get overdue cases
SELECT ic.id, ic.case_title, u.applicant_name, ic.due_date, ic.assigned_to
FROM investigation_cases ic
    JOIN users u ON ic.user_id = u.id
WHERE ic.status NOT IN ('closed') AND ic.due_date < CURRENT_TIMESTAMP
ORDER BY ic.due_date ASC;

-- Get cases by investigator
SELECT id, case_title, case_type, severity, status, created_at, due_date
FROM investigation_cases
WHERE assigned_to = 'investigator@example.com'
-- Change to desired investigator
ORDER BY severity DESC, due_date ASC;

-- =============================================================================
-- ACCOUNT HOLD QUERIES
-- =============================================================================

-- Get all active holds
SELECT ah.id, u.applicant_name, ah.hold_type, ah.severity,
    ah.hold_reason, ah.hold_placed_at, ah.hold_expires_at
FROM account_holds ah
    JOIN users u ON ah.user_id = u.id
WHERE ah.status = 'active'
ORDER BY ah.severity DESC, ah.hold_placed_at DESC;

-- Get holds expiring soon (within 7 days)
SELECT ah.id, u.applicant_name, ah.hold_type, ah.hold_expires_at, ah.placed_by
FROM account_holds ah
    JOIN users u ON ah.user_id = u.id
WHERE ah.status = 'active'
    AND ah.hold_expires_at IS NOT NULL
    AND ah.hold_expires_at BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL
'7 days'
ORDER BY ah.hold_expires_at ASC;

-- =============================================================================
-- DASHBOARD & ANALYTICS QUERIES
-- =============================================================================

-- Risk distribution of users
SELECT risk_level, COUNT(*) as user_count,
    ROUND(AVG(suspicious_score), 2) as avg_score
FROM users
GROUP BY risk_level
ORDER BY 
    CASE risk_level 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END;

-- Transaction volume by type (last 30 days)
SELECT transaction_type,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MAX(amount) as max_amount
FROM transactions
WHERE transaction_date >= CURRENT_TIMESTAMP - INTERVAL
'30 days'
GROUP BY transaction_type
ORDER BY total_amount DESC;

-- Alert statistics by severity
SELECT severity,
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_alerts,
    SUM(CASE WHEN is_acknowledged = FALSE THEN 1 ELSE 0 END) as unacknowledged_alerts
FROM compliance_alerts
GROUP BY severity
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END;

-- Top 5 users by suspicious activity
SELECT u.entity_id, u.applicant_name, u.risk_level, u.suspicious_score,
    COUNT(DISTINCT t.id) as flagged_transactions,
    COUNT(DISTINCT ca.id) as alerts_count
FROM users u
    LEFT JOIN transactions t ON u.id = t.user_id AND t.is_flagged = TRUE
    LEFT JOIN compliance_alerts ca ON u.id = ca.user_id
GROUP BY u.id, u.entity_id, u.applicant_name, u.risk_level, u.suspicious_score
ORDER BY u.suspicious_score DESC, alerts_count DESC
LIMIT 5;

-- Recent activity summary
SELECT 
    (SELECT COUNT
(*) FROM users WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days') as new_users,
(SELECT COUNT(*)
FROM transactions
WHERE transaction_date >= CURRENT_TIMESTAMP - INTERVAL
'7 days') as new_transactions,
(SELECT COUNT(*)
FROM compliance_alerts
WHERE triggered_at >= CURRENT_TIMESTAMP - INTERVAL
'7 days') as new_alerts,
(SELECT COUNT(*)
FROM investigation_cases
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL
'7 days') as new_cases;

-- =============================================================================
-- COMPLEX JOIN QUERIES
-- =============================================================================

-- Users with their transaction and alert summaries
SELECT u.entity_id, u.applicant_name, u.risk_level,
    COUNT(DISTINCT t.id) as total_transactions,
    SUM(CASE WHEN t.is_flagged THEN 1 ELSE 0 END) as flagged_transactions,
    COUNT(DISTINCT ca.id) as total_alerts,
    SUM(CASE WHEN ca.severity = 'critical' THEN 1 ELSE 0 END) as critical_alerts
FROM users u
    LEFT JOIN transactions t ON u.id = t.user_id
    LEFT JOIN compliance_alerts ca ON u.id = ca.user_id
GROUP BY u.id, u.entity_id, u.applicant_name, u.risk_level
ORDER BY critical_alerts DESC, u.risk_level DESC;

-- Investigation cases with related transactions and alerts
SELECT ic.id as case_id, ic.case_title, u.applicant_name,
    ic.severity, ic.status,
    COUNT(DISTINCT t.id) as related_transactions,
    COUNT(DISTINCT ca.id) as related_alerts
FROM investigation_cases ic
    JOIN users u ON ic.user_id = u.id
    LEFT JOIN transactions t ON t.user_id = u.id
    LEFT JOIN compliance_alerts ca ON ca.user_id = u.id
GROUP BY ic.id, ic.case_title, u.applicant_name, ic.severity, ic.status
ORDER BY ic.severity DESC;

-- =============================================================================
-- PERFORMANCE & MONITORING QUERIES
-- =============================================================================

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Record counts for all tables
    SELECT 'users' as table_name, COUNT(*) as record_count
    FROM users
UNION ALL
    SELECT 'transactions', COUNT(*)
    FROM transactions
UNION ALL
    SELECT 'compliance_alerts', COUNT(*)
    FROM compliance_alerts
UNION ALL
    SELECT 'investigation_cases', COUNT(*)
    FROM investigation_cases
UNION ALL
    SELECT 'account_holds', COUNT(*)
    FROM account_holds
UNION ALL
    SELECT 'notification_settings', COUNT(*)
    FROM notification_settings
UNION ALL
    SELECT 'organization_settings', COUNT(*)
    FROM organization_settings;
