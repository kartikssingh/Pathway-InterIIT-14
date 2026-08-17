-- =============================================================================
-- SUPERADMIN MONITORING - DATA POPULATION SCRIPT (Schema-Aligned)
-- =============================================================================
-- This script populates superadmin monitoring tables with realistic data
-- aligned with the actual database schema.
--
-- Data Coverage: 90 days of historical data with realistic patterns
-- Volume: 1000+ alerts, 2700+ metrics, 50+ health events, 30+ system alerts
--
-- Usage: psql -U dhruv -d compliance_db -f populate_superadmin_monitoring_data_fixed.sql
-- =============================================================================

BEGIN;

-- Clean existing monitoring data
DELETE FROM audit_logs;
DELETE FROM system_alerts;
DELETE FROM system_health;
DELETE FROM system_metrics;

-- =============================================================================
-- STEP 1: Ensure Admin Users Exist
-- =============================================================================

-- Insert admins only if they don't exist
INSERT INTO admins (username, email, hashed_password, role, is_active, created_at, last_login_at)
VALUES 
    ('superadmin', 'superadmin@compliance.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaB3h5rW1C2', 'SUPERADMIN', TRUE, NOW() - INTERVAL '180 days', NOW() - INTERVAL '2 hours'),
    ('admin_john', 'john@compliance.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaB3h5rW1C2', 'ADMIN', TRUE, NOW() - INTERVAL '150 days', NOW() - INTERVAL '1 day'),
    ('admin_sarah', 'sarah@compliance.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaB3h5rW1C2', 'ADMIN', TRUE, NOW() - INTERVAL '120 days', NOW() - INTERVAL '3 hours'),
    ('admin_mike', 'mike@compliance.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaB3h5rW1C2', 'ADMIN', TRUE, NOW() - INTERVAL '90 days', NOW() - INTERVAL '5 days'),
    ('admin_emily', 'emily@compliance.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aqaB3h5rW1C2', 'ADMIN', TRUE, NOW() - INTERVAL '60 days', NOW() - INTERVAL '12 hours')
ON CONFLICT (username) DO NOTHING;

-- =============================================================================
-- STEP 2: Update Existing Compliance Alerts with Classification
-- =============================================================================

-- IMPORTANT: Only classify HISTORICAL alerts (older than 30 days) to avoid
-- polluting current user activity with fake data.
-- This keeps demo data separate from real user work.

UPDATE compliance_alerts
SET is_true_positive = CASE 
        WHEN random() < 0.70 THEN TRUE  -- 70% true positives
        ELSE FALSE
    END,
    reviewed_at = created_at + ((random() * 48)::TEXT || ' hours')::INTERVAL,
    reviewed_by = (ARRAY['admin_john', 'admin_sarah', 'admin_mike', 'admin_emily'])[1 + floor(random() * 4)::INT]
WHERE created_at >= NOW() - INTERVAL '90 days'
  AND created_at < NOW() - INTERVAL '30 days'  -- ONLY historical data
  AND random() < 0.70;  -- Only classify 70% of alerts, leaving 30% as unreviewed

-- =============================================================================
-- STEP 3: Create Audit Logs for Classified Alerts
-- =============================================================================

INSERT INTO audit_logs (
    admin_id, action_type, action_description, target_type, target_id, target_identifier,
    action_metadata, ip_address, user_agent, created_at
)
SELECT 
    a.id,
    'classify_alert',
    'Classified alert ' || ca.id || ' as ' || CASE WHEN ca.is_true_positive THEN 'true positive' ELSE 'false positive' END,
    'compliance_alert',
    ca.id,
    'alert_' || ca.id,
    jsonb_build_object(
        'alert_id', ca.id,
        'user_id', ca.user_id,
        'alert_type', ca.alert_type,
        'severity', ca.severity,
        'classification', ca.is_true_positive,
        'previous_status', 'unclassified'
    ),
    '192.168.1.' || (100 + (random() * 50)::INT),
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    ca.reviewed_at
FROM compliance_alerts ca
JOIN admins a ON a.username = ca.reviewed_by
WHERE ca.is_true_positive IS NOT NULL 
  AND ca.reviewed_at IS NOT NULL
  AND ca.reviewed_at >= NOW() - INTERVAL '90 days'
  AND ca.reviewed_at < NOW() - INTERVAL '30 days';  -- ONLY historical audit logs

-- =============================================================================
-- STEP 4: Create System Metrics (2700+ entries across 90 days)
-- =============================================================================

-- Hourly alert hit rate metrics for the past 90 days (2160 entries)
INSERT INTO system_metrics (
    metric_type, metric_category, metric_value, metric_unit, time_window,
    aggregation_period_start, aggregation_period_end, 
    total_count, positive_count, negative_count, details, is_anomaly, recorded_at
)
SELECT 
    'alert_hit_rate',
    'alert',
    CASE 
        WHEN day_offset < 7 THEN 60.0 + (random() * 20)
        WHEN day_offset < 30 THEN 70.0 + (random() * 15)
        WHEN day_offset < 60 THEN 78.0 + (random() * 12)
        ELSE 82.0 + (random() * 10)
    END,
    'percentage',
    'hourly',
    NOW() - (day_offset || ' days')::INTERVAL - (hour_offset || ' hours')::INTERVAL,
    NOW() - (day_offset || ' days')::INTERVAL - (hour_offset || ' hours')::INTERVAL + INTERVAL '1 hour',
    50 + (random() * 50)::INT,
    35 + (random() * 30)::INT,
    10 + (random() * 15)::INT,
    jsonb_build_object(
        'by_severity', jsonb_build_object('critical', 2 + (random() * 3)::INT, 'high', 8 + (random() * 7)::INT, 'medium', 15 + (random() * 10)::INT),
        'by_type', jsonb_build_object('sanctions', 10 + (random() * 10)::INT, 'aml', 15 + (random() * 15)::INT, 'kyc', 8 + (random() * 8)::INT)
    ),
    FALSE,
    NOW() - (day_offset || ' days')::INTERVAL - (hour_offset || ' hours')::INTERVAL
FROM generate_series(0, 89) day_offset
CROSS JOIN generate_series(0, 23) hour_offset;

-- Daily false positive rate metrics (90 entries)
INSERT INTO system_metrics (
    metric_type, metric_category, metric_value, metric_unit, time_window,
    aggregation_period_start, aggregation_period_end,
    total_count, positive_count, negative_count, details, is_anomaly, recorded_at
)
SELECT 
    'false_positive_rate',
    'alert',
    CASE 
        WHEN n < 7 THEN 15.0 + (random() * 10)
        WHEN n < 30 THEN 20.0 + (random() * 8)
        WHEN n < 60 THEN 22.0 + (random() * 6)
        ELSE 18.0 + (random() * 7)
    END + CASE WHEN n IN (15, 45, 75) THEN 15.0 ELSE 0 END,
    'percentage',
    'daily',
    NOW() - (n || ' days')::INTERVAL,
    NOW() - (n || ' days')::INTERVAL + INTERVAL '1 day',
    100 + (n * 5),
    70 + (random() * 30)::INT,
    30 + (random() * 20)::INT,
    jsonb_build_object('review_count', 100 + (n * 5), 'false_positives', 20 + (random() * 15)::INT, 'true_positives', 80 + (random() * 20)::INT),
    n IN (15, 45, 75),
    NOW() - (n || ' days')::INTERVAL + INTERVAL '23 hours'
FROM generate_series(0, 89) n;

-- API response time (every 4 hours for 90 days = 540 entries)
INSERT INTO system_metrics (
    metric_type, metric_category, metric_value, metric_unit, time_window,
    aggregation_period_start, aggregation_period_end,
    details, is_anomaly, recorded_at
)
SELECT 
    'api_response_time',
    'api',
    CASE 
        WHEN n IN (10, 25, 60) THEN 3000.0 + (random() * 2000)
        ELSE 800.0 + (random() * 700)
    END,
    'milliseconds',
    'realtime',
    time_point,
    time_point + INTERVAL '4 hours',
    jsonb_build_object(
        'endpoint', '/api/sanctions/check',
        'method', 'POST',
        'p50_ms', 500 + (random() * 300)::INT,
        'p95_ms', 1200 + (random() * 500)::INT,
        'p99_ms', 2000 + (random() * 1000)::INT
    ),
    n IN (10, 25, 60),
    time_point
FROM generate_series(0, 539) n
CROSS JOIN LATERAL (
    SELECT NOW() - ((n * 0.167)::TEXT || ' days')::INTERVAL AS time_point
) times;

-- API error rate (daily for 90 days)
INSERT INTO system_metrics (
    metric_type, metric_category, metric_value, metric_unit, time_window,
    aggregation_period_start, aggregation_period_end,
    total_count, positive_count, negative_count, details, is_anomaly, recorded_at
)
SELECT 
    'api_error_rate',
    'api',
    CASE 
        WHEN n IN (3, 40, 70) THEN 8.0 + (random() * 4)
        WHEN n IN (12, 55) THEN 3.0 + (random() * 2)
        ELSE 0.5 + (random() * 1.5)
    END,
    'percentage',
    'daily',
    NOW() - (n || ' days')::INTERVAL,
    NOW() - (n || ' days')::INTERVAL + INTERVAL '1 day',
    1000 + (n * 10),
    CASE WHEN n IN (3, 40, 70) THEN 80 + (random() * 40)::INT ELSE 5 + (random() * 10)::INT END,
    NULL,
    jsonb_build_object(
        'error_types', jsonb_build_object('503', 3, '500', 2, 'timeout', 1),
        'endpoints', jsonb_build_array('/api/sanctions', '/api/transactions', '/api/users')
    ),
    n IN (3, 40, 70),
    NOW() - (n || ' days')::INTERVAL + INTERVAL '23 hours'
FROM generate_series(0, 89) n;

-- Alert response time (daily for 90 days)
INSERT INTO system_metrics (
    metric_type, metric_category, metric_value, metric_unit, time_window,
    aggregation_period_start, aggregation_period_end,
    details, is_anomaly, recorded_at
)
SELECT 
    'alert_response_time',
    'alert',
    CASE 
        WHEN n < 15 THEN 1.5 + (random() * 2.5)
        WHEN n < 45 THEN 3.0 + (random() * 2.0)
        ELSE 4.5 + (random() * 3.5)
    END,
    'seconds',
    'daily',
    NOW() - (n || ' days')::INTERVAL,
    NOW() - (n || ' days')::INTERVAL + INTERVAL '1 day',
    jsonb_build_object(
        'avg_hours', 2.5 + (random() * 3)::NUMERIC(10,2),
        'min_hours', 0.5,
        'max_hours', 12.0,
        'median_hours', 2.0 + (random() * 2)::NUMERIC(10,2)
    ),
    FALSE,
    NOW() - (n || ' days')::INTERVAL + INTERVAL '23 hours'
FROM generate_series(0, 89) n;

-- =============================================================================
-- STEP 5: Create System Health Events (41 entries)
-- =============================================================================

-- Resolved health issues (35 entries distributed over 90 days)
INSERT INTO system_health (
    check_type, component_name, status, severity, error_type, error_message,
    request_context, response_context, response_time_ms, user_impact,
    is_resolved, resolved_at, resolution_notes, auto_recovered, detected_at, alert_sent
)
SELECT 
    (ARRAY['api_health', 'database_health', 'service_health', 'dependency_health'])[1 + (n % 4)],
    (ARRAY['sanctions_api', 'postgres_primary', 'transaction_parser', 'redis_cache', 'ml_model_service'])[1 + (n % 5)],
    'healthy',
    CASE WHEN n % 5 = 0 THEN 'critical' WHEN n % 3 = 0 THEN 'high' ELSE 'medium' END,
    (ARRAY['timeout', 'connection_refused', 'service_unavailable', 'parsing_error', 'rate_limit_exceeded'])[1 + (n % 5)],
    (ARRAY[
        'API endpoint timed out after 30 seconds',
        'Database connection pool exhausted',
        'Service returned 503 status code',
        'Failed to parse transaction data',
        'Rate limit exceeded on external service'
    ])[1 + (n % 5)],
    jsonb_build_object(
        'method', 'POST',
        'endpoint', '/api/check',
        'user_id', 1000 + n,
        'request_id', 'req_' || n
    ),
    jsonb_build_object(
        'status_code', (ARRAY[503, 500, 504, 429])[1 + (n % 4)],
        'error_code', 'ERR_' || n
    ),
    5000 + (random() * 25000)::INT,
    CASE WHEN n % 4 = 0 THEN 'high' WHEN n % 2 = 0 THEN 'medium' ELSE 'low' END,
    TRUE,
    NOW() - ((n * 2.5)::TEXT || ' days')::INTERVAL + INTERVAL '2 hours',
    (ARRAY[
        'Service restarted successfully',
        'Database connection pool increased',
        'Rate limiting adjusted',
        'Parser updated to handle edge case',
        'Automatic recovery after upstream fix'
    ])[1 + (n % 5)],
    n % 3 = 0,
    NOW() - ((n * 2.5)::TEXT || ' days')::INTERVAL,
    TRUE
FROM generate_series(1, 35) n;

-- Active health issues (6 entries from last 2-3 days)
INSERT INTO system_health (
    check_type, component_name, status, severity, error_type, error_message,
    request_context, response_context, response_time_ms, retry_count, user_impact,
    is_resolved, auto_recovered, detected_at, alert_sent, alert_sent_at
)
VALUES 
    (
        'api_health', 'sanctions_api', 'unhealthy', 'medium', 'slow_response',
        'Sanctions API response time exceeds threshold (2.5s avg)',
        '{"endpoint": "/api/sanctions/check", "method": "POST"}'::jsonb,
        '{"status_code": 200, "response_time_ms": 2500}'::jsonb,
        2500, 2, 'medium', FALSE, FALSE, NOW() - INTERVAL '6 hours', TRUE, NOW() - INTERVAL '6 hours'
    ),
    (
        'database_health', 'postgres_primary', 'degraded', 'high', 'connection_pool_high',
        'Database connection pool at 85% capacity',
        '{"active_connections": 85, "max_connections": 100}'::jsonb,
        NULL, NULL, 0, 'high', FALSE, FALSE, NOW() - INTERVAL '3 hours', TRUE, NOW() - INTERVAL '3 hours'
    ),
    (
        'service_health', 'redis_cache', 'degraded', 'medium', 'memory_high',
        'Redis memory usage at 82% capacity',
        '{"used_memory_mb": 3280, "max_memory_mb": 4000}'::jsonb,
        NULL, NULL, 0, 'low', FALSE, FALSE, NOW() - INTERVAL '8 hours', TRUE, NOW() - INTERVAL '8 hours'
    ),
    (
        'api_health', 'payment_gateway', 'unhealthy', 'high', 'error_rate_high',
        'Payment gateway error rate at 8.5%',
        '{"total_requests": 250, "failed_requests": 21}'::jsonb,
        '{"primary_errors": ["500", "503"]}'::jsonb,
        NULL, 3, 'high', FALSE, FALSE, NOW() - INTERVAL '45 minutes', TRUE, NOW() - INTERVAL '45 minutes'
    ),
    (
        'dependency_health', 'ml_model_service', 'degraded', 'medium', 'latency_increase',
        'ML model inference latency increased by 40%',
        '{"model_name": "fraud_detection_v2", "avg_latency_ms": 350}'::jsonb,
        NULL, 350, 1, 'medium', FALSE, FALSE, NOW() - INTERVAL '2 hours', FALSE, NULL
    ),
    (
        'service_health', 'transaction_parser', 'unhealthy', 'critical', 'parsing_failures',
        'Transaction parser failing on 12% of transactions',
        '{"failure_rate": 0.12, "total_processed": 1000}'::jsonb,
        '{"error_types": ["invalid_json", "missing_field"]}'::jsonb,
        NULL, 5, 'high', FALSE, FALSE, NOW() - INTERVAL '1 hour', TRUE, NOW() - INTERVAL '1 hour'
    );

-- =============================================================================
-- STEP 6: Create System Alerts (30 entries)
-- =============================================================================

-- Resolved system alerts (25 historical)
INSERT INTO system_alerts (
    alert_type, title, description, severity, component, metric_type,
    threshold_value, actual_value, alert_data, status, acknowledged_by,
    acknowledged_at, resolved_at, resolution_notes, triggered_at, last_updated, notifications_sent
)
SELECT 
    (ARRAY['high_error_rate', 'api_downtime', 'threshold_breach', 'anomaly_detected', 'health_check_failed', 'performance_degradation'])[1 + (n % 6)],
    (ARRAY[
        'Critical API Error Rate Spike',
        'Service Downtime Detected',
        'Threshold Breach Alert',
        'Unusual System Behavior',
        'Health Check Failure',
        'Performance Degradation'
    ])[1 + (n % 6)],
    (ARRAY[
        'API error rate exceeded acceptable thresholds',
        'Service unavailable for extended period',
        'System metric exceeded configured threshold',
        'Anomalous pattern detected in system behavior',
        'Critical health check failed multiple times',
        'System performance degraded below SLA'
    ])[1 + (n % 6)],
    CASE WHEN n % 5 = 0 THEN 'critical' WHEN n % 3 = 0 THEN 'error' ELSE 'warning' END,
    (ARRAY['payment_gateway', 'sanctions_api', 'alert_system', 'transaction_parser', 'postgres_primary', 'redis_cache'])[1 + (n % 6)],
    (ARRAY['api_error_rate', 'api_response_time', 'false_positive_rate', 'alert_hit_rate', NULL])[1 + (n % 5)],
    (ARRAY['5%', '2000ms', '30%', '75%', 'N/A'])[1 + (n % 5)],
    (ARRAY['12.5%', '8500ms', '38%', '62%', '15 failures'])[1 + (n % 5)],
    jsonb_build_object(
        'total_requests', 1000 + (n * 50),
        'failed_count', 50 + (n * 2),
        'time_window', (ARRAY['1h', '2h', '6h', '12h'])[1 + (n % 4)],
        'trend', (ARRAY['increasing', 'stable', 'decreasing'])[1 + (n % 3)]
    ),
    'resolved',
    (ARRAY['superadmin', 'admin_john', 'admin_sarah', 'admin_mike'])[1 + (n % 4)],
    alert_time + ((n % 3 + 1)::TEXT || ' hours')::INTERVAL,
    alert_time + ((n % 3 + 4)::TEXT || ' hours')::INTERVAL,
    (ARRAY[
        'Issue resolved after service restart',
        'Provider fixed infrastructure problem',
        'Configuration updated to new thresholds',
        'False alarm - expected behavior during maintenance',
        'Patched with hotfix deployment',
        'Load balanced to handle traffic spike'
    ])[1 + (n % 6)],
    alert_time,
    alert_time + ((n % 3 + 4)::TEXT || ' hours')::INTERVAL,
    2 + (n % 4)
FROM generate_series(1, 25) n
CROSS JOIN LATERAL (
    SELECT NOW() - ((n * 3.6)::TEXT || ' days')::INTERVAL AS alert_time
) times;

-- Active system alerts (5 recent)
INSERT INTO system_alerts (
    alert_type, title, description, severity, component, metric_type,
    threshold_value, actual_value, alert_data, status, acknowledged_by,
    acknowledged_at, triggered_at, last_updated, notifications_sent
)
VALUES 
    (
        'threshold_breach', 'High False Positive Rate',
        'False positive rate is 32.5%, exceeding 30% threshold for the past 6 hours',
        'warning', 'alert_system', 'false_positive_rate',
        '30%', '32.5%',
        '{"total_alerts": 150, "false_positives": 49, "time_window": "6h", "trend": "increasing"}'::jsonb,
        'active', NULL, NULL,
        NOW() - INTERVAL '4 hours', NOW() - INTERVAL '3 hours', 3
    ),
    (
        'api_downtime', 'Sanctions API Degraded Performance',
        'Sanctions API response time consistently exceeding 2000ms',
        'warning', 'sanctions_api', 'api_response_time',
        '2000ms', '2450ms',
        '{"endpoint": "/api/sanctions/check", "avg_response_time_ms": 2450, "p95_ms": 3200, "failure_count": 5}'::jsonb,
        'acknowledged', 'superadmin', NOW() - INTERVAL '1 hour',
        NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour', 4
    ),
    (
        'threshold_breach', 'Database Connection Pool Near Capacity',
        'Database connection pool utilization at 85%, approaching maximum',
        'warning', 'postgres_primary', NULL,
        '80%', '85%',
        '{"active_connections": 85, "max_connections": 100, "idle_connections": 5}'::jsonb,
        'acknowledged', 'admin_john', NOW() - INTERVAL '30 minutes',
        NOW() - INTERVAL '1 hour', NOW() - INTERVAL '30 minutes', 2
    ),
    (
        'high_error_rate', 'Payment Gateway Error Spike',
        'Payment gateway experiencing elevated error rates',
        'error', 'payment_gateway', 'api_error_rate',
        '5%', '8.5%',
        '{"total_requests": 250, "failed_requests": 21, "primary_errors": ["500", "503"], "time_window": "1h"}'::jsonb,
        'active', NULL, NULL,
        NOW() - INTERVAL '45 minutes', NOW() - INTERVAL '30 minutes', 2
    ),
    (
        'performance_degradation', 'Redis Cache Memory High',
        'Redis cache memory usage approaching capacity limits',
        'warning', 'redis_cache', NULL,
        '80%', '82%',
        '{"used_memory_mb": 3280, "max_memory_mb": 4000, "eviction_count": 145, "hit_rate": "94.2%"}'::jsonb,
        'active', NULL, NULL,
        NOW() - INTERVAL '6 hours', NOW() - INTERVAL '5 hours', 1
    );

-- =============================================================================
-- STEP 7: Create Audit Logs for System Actions
-- =============================================================================

-- Audit logs for acknowledged system alerts
INSERT INTO audit_logs (
    admin_id, action_type, action_description, target_type, target_id, target_identifier,
    action_metadata, ip_address, user_agent, created_at
)
SELECT 
    CASE sa.acknowledged_by
        WHEN 'superadmin' THEN (SELECT id FROM admins WHERE username = 'superadmin')
        WHEN 'admin_john' THEN (SELECT id FROM admins WHERE username = 'admin_john')
        WHEN 'admin_sarah' THEN (SELECT id FROM admins WHERE username = 'admin_sarah')
        WHEN 'admin_mike' THEN (SELECT id FROM admins WHERE username = 'admin_mike')
        WHEN 'admin_emily' THEN (SELECT id FROM admins WHERE username = 'admin_emily')
    END,
    'acknowledge_alert',
    'Acknowledged system alert: ' || sa.title,
    'system_alert',
    sa.id,
    'alert_' || sa.id,
    jsonb_build_object(
        'alert_type', sa.alert_type,
        'severity', sa.severity,
        'component', sa.component,
        'threshold_value', sa.threshold_value,
        'actual_value', sa.actual_value
    ),
    '192.168.1.' || (100 + (sa.id % 50)),
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    sa.acknowledged_at
FROM system_alerts sa
WHERE sa.acknowledged_at IS NOT NULL;

-- Audit logs for resolved system alerts
INSERT INTO audit_logs (
    admin_id, action_type, action_description, target_type, target_id, target_identifier,
    action_metadata, ip_address, user_agent, created_at
)
SELECT 
    CASE sa.acknowledged_by
        WHEN 'superadmin' THEN (SELECT id FROM admins WHERE username = 'superadmin')
        WHEN 'admin_john' THEN (SELECT id FROM admins WHERE username = 'admin_john')
        WHEN 'admin_sarah' THEN (SELECT id FROM admins WHERE username = 'admin_sarah')
        WHEN 'admin_mike' THEN (SELECT id FROM admins WHERE username = 'admin_mike')
        WHEN 'admin_emily' THEN (SELECT id FROM admins WHERE username = 'admin_emily')
    END,
    'resolve_alert',
    'Resolved system alert: ' || sa.title || ' - ' || sa.resolution_notes,
    'system_alert',
    sa.id,
    'alert_' || sa.id,
    jsonb_build_object(
        'alert_type', sa.alert_type,
        'severity', sa.severity,
        'component', sa.component,
        'resolution_notes', sa.resolution_notes,
        'time_to_resolve_hours', EXTRACT(EPOCH FROM (sa.resolved_at - sa.triggered_at)) / 3600
    ),
    '192.168.1.' || (100 + (sa.id % 50)),
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    sa.resolved_at
FROM system_alerts sa
WHERE sa.resolved_at IS NOT NULL;

COMMIT;

-- =============================================================================
-- VERIFICATION SUMMARY
-- =============================================================================

SELECT 
    'admins' as table_name,
    COUNT(*) as record_count
FROM admins
WHERE email LIKE '%@compliance.com'
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs
UNION ALL
SELECT 'system_metrics', COUNT(*) FROM system_metrics
UNION ALL
SELECT 'system_health', COUNT(*) FROM system_health
UNION ALL
SELECT 'system_alerts', COUNT(*) FROM system_alerts
UNION ALL
SELECT 'classified_alerts', COUNT(*) 
FROM compliance_alerts 
WHERE is_true_positive IS NOT NULL
ORDER BY table_name;

-- Show alert classification distribution
SELECT 
    CASE 
        WHEN is_true_positive IS NULL THEN 'Unclassified'
        WHEN is_true_positive = TRUE THEN 'True Positive'
        ELSE 'False Positive'
    END as classification,
    COUNT(*) as count,
    ROUND(COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM compliance_alerts) * 100, 2) as percentage
FROM compliance_alerts
GROUP BY classification
ORDER BY count DESC;

-- =============================================================================
-- END OF POPULATION SCRIPT
-- =============================================================================
