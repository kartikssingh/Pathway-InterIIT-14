-- =============================================================================
-- 005 — Reporting views and maintenance functions
--
-- `calculate_alert_hit_rate` referenced `compliance_alerts.is_true_positive`,
-- which was only added by a later ad-hoc migration; running the original setup
-- script end to end therefore failed to create this function. The column now
-- exists from migration 003, so the ordering is correct.
-- =============================================================================

-- Audit log joined with the acting admin.
CREATE OR REPLACE VIEW v_audit_logs_with_admin AS
SELECT
    al.*,
    a.username AS admin_username,
    a.email    AS admin_email,
    a.role     AS admin_role
FROM audit_logs al
JOIN admins a ON al.admin_id = a.id;

-- Everything currently wrong with the system, from either source.
CREATE OR REPLACE VIEW v_active_system_issues AS
SELECT
    'health_check'  AS issue_type,
    id,
    component_name  AS component,
    severity,
    error_message   AS description,
    detected_at     AS created_at,
    is_resolved
FROM system_health
WHERE is_resolved = FALSE AND severity IN ('error', 'critical')
UNION ALL
SELECT
    'system_alert'  AS issue_type,
    id,
    component,
    severity,
    description,
    triggered_at    AS created_at,
    (status IN ('resolved', 'false_alarm')) AS is_resolved
FROM system_alerts
WHERE status IN ('active', 'acknowledged');

-- Rolling 24-hour metric summary.
CREATE OR REPLACE VIEW v_metrics_last_24h AS
SELECT
    metric_type,
    metric_category,
    AVG(metric_value) AS avg_value,
    MIN(metric_value) AS min_value,
    MAX(metric_value) AS max_value,
    COUNT(*)          AS data_points,
    SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count
FROM system_metrics
WHERE recorded_at >= NOW() - INTERVAL '24 hours'
GROUP BY metric_type, metric_category;

-- Per-user risk snapshot for the console's user list.
CREATE OR REPLACE VIEW v_user_risk_overview AS
SELECT
    u.user_id,
    u.username,
    u.kyc_status,
    u.risk_category,
    u.current_rps_not,
    u.current_rps_360,
    u.blacklisted,
    u.last_rps_calculation,
    COALESCE(alert_counts.open_alerts, 0)   AS open_alerts,
    COALESCE(txn_counts.txn_count_30d, 0)   AS txn_count_30d,
    COALESCE(txn_counts.volume_30d, 0)      AS volume_30d,
    sanctions.matched_entity_name           AS latest_sanction_match
FROM Users u
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS open_alerts
    FROM compliance_alerts ca
    WHERE ca.user_id = u.user_id AND ca.status IN ('active', 'investigating')
) alert_counts ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS txn_count_30d, COALESCE(SUM(t.amount), 0) AS volume_30d
    FROM Transactions t
    WHERE t.user_id = u.user_id AND t.txn_timestamp >= NOW() - INTERVAL '30 days'
) txn_counts ON TRUE
LEFT JOIN LATERAL (
    SELECT m.matched_entity_name
    FROM UserSanctionMatches m
    WHERE m.user_id = u.user_id AND m.match_found
    ORDER BY m.checked_at DESC
    LIMIT 1
) sanctions ON TRUE;


-- -----------------------------------------------------------------------------
-- Maintenance functions
-- -----------------------------------------------------------------------------

-- Share of reviewed alerts that turned out to be genuine, as a percentage.
CREATE OR REPLACE FUNCTION calculate_alert_hit_rate(
    start_date TIMESTAMP WITH TIME ZONE,
    end_date   TIMESTAMP WITH TIME ZONE
)
RETURNS FLOAT AS $$
DECLARE
    reviewed       INTEGER;
    true_positives INTEGER;
BEGIN
    SELECT
        COUNT(*) FILTER (WHERE is_true_positive IS NOT NULL),
        COUNT(*) FILTER (WHERE is_true_positive)
    INTO reviewed, true_positives
    FROM compliance_alerts
    WHERE created_at BETWEEN start_date AND end_date;

    IF reviewed = 0 THEN
        RETURN 0;
    END IF;
    RETURN (true_positives::FLOAT / reviewed::FLOAT) * 100;
END;
$$ LANGUAGE plpgsql STABLE;


CREATE OR REPLACE FUNCTION get_system_health_status()
RETURNS VARCHAR AS $$
DECLARE
    critical_count    INTEGER;
    unresolved_errors INTEGER;
BEGIN
    SELECT COUNT(*) INTO critical_count
    FROM system_alerts WHERE status = 'active' AND severity = 'critical';

    SELECT COUNT(*) INTO unresolved_errors
    FROM system_health WHERE is_resolved = FALSE AND severity IN ('error', 'critical');

    IF critical_count > 0 THEN
        RETURN 'critical';
    ELSIF unresolved_errors > 0 THEN
        RETURN 'degraded';
    END IF;
    RETURN 'healthy';
END;
$$ LANGUAGE plpgsql STABLE;


-- Retention: audit logs are kept for a year, resolved health checks for a month.
CREATE OR REPLACE FUNCTION archive_old_audit_logs(retain_days INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM audit_logs
        WHERE created_at < NOW() - (retain_days || ' days')::INTERVAL
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION cleanup_old_health_checks(retain_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM system_health
        WHERE is_resolved = TRUE
          AND resolved_at < NOW() - (retain_days || ' days')::INTERVAL
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- Staging_Buffer is a landing table; nothing reads it after the trigger fires.
CREATE OR REPLACE FUNCTION cleanup_staging_buffer(retain_hours INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM Staging_Buffer
        WHERE created_at < NOW() - (retain_hours || ' hours')::INTERVAL
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
