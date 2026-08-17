-- =============================================================================
-- 004 — Administration and superadmin monitoring
--
-- admins, audit_logs, system_metrics, system_health, system_alerts.
-- =============================================================================

CREATE TABLE IF NOT EXISTS admins (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'admin',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at   TIMESTAMP WITH TIME ZONE,

    CHECK (role IN ('admin', 'superadmin'))
);

CREATE INDEX IF NOT EXISTS idx_admins_username ON admins (username);
CREATE INDEX IF NOT EXISTS idx_admins_email    ON admins (email);
CREATE INDEX IF NOT EXISTS idx_admins_role     ON admins (role);


CREATE TABLE IF NOT EXISTS audit_logs (
    id                SERIAL PRIMARY KEY,
    admin_id          INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    action_type       VARCHAR(50) NOT NULL,
    action_description TEXT NOT NULL,
    target_type       VARCHAR(50),
    target_id         INTEGER,
    target_identifier VARCHAR(255),
    action_metadata   JSONB,
    ip_address        VARCHAR(50),
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CHECK (action_type IN (
        'classify_alert', 'dismiss_alert', 'escalate_alert',
        'blacklist_user', 'whitelist_user', 'flag_user', 'unflag_user',
        'block_transaction', 'approve_transaction', 'update_system_alert',
        'resolve_health_check', 'login', 'logout', 'other'
    ))
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id        ON audit_logs (admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type     ON audit_logs (action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_type     ON audit_logs (target_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target_id       ON audit_logs (target_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at      ON audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_metadata ON audit_logs USING GIN (action_metadata);

COMMENT ON TABLE audit_logs IS 'Every admin action, for compliance tracking';
COMMENT ON COLUMN audit_logs.action_metadata IS
    'Before/after states, classification details and other per-action context';


CREATE TABLE IF NOT EXISTS system_metrics (
    id                       SERIAL PRIMARY KEY,
    metric_type              VARCHAR(50) NOT NULL,
    metric_category          VARCHAR(50) NOT NULL,
    metric_value             FLOAT NOT NULL,
    metric_unit              VARCHAR(20),
    time_window              VARCHAR(20),
    aggregation_period_start TIMESTAMP WITH TIME ZONE,
    aggregation_period_end   TIMESTAMP WITH TIME ZONE,
    details                  JSONB,
    total_count              INTEGER,
    positive_count           INTEGER,
    negative_count           INTEGER,
    recorded_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_anomaly               BOOLEAN DEFAULT FALSE,
    anomaly_threshold        FLOAT,

    CHECK (metric_type IN (
        'alert_hit_rate', 'false_positive_rate', 'api_response_time',
        'api_error_rate', 'alert_response_time', 'user_flag_rate',
        'transaction_block_rate', 'other'
    )),
    CHECK (metric_category IN ('alert', 'api', 'transaction', 'user', 'system')),
    CHECK (metric_unit IN ('percentage', 'milliseconds', 'seconds', 'count', 'rate', 'ratio')),
    CHECK (time_window IN ('hourly', 'daily', 'weekly', 'monthly', 'realtime'))
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_type         ON system_metrics (metric_type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_category     ON system_metrics (metric_category);
CREATE INDEX IF NOT EXISTS idx_system_metrics_recorded_at  ON system_metrics (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_time_window  ON system_metrics (time_window);
CREATE INDEX IF NOT EXISTS idx_system_metrics_is_anomaly   ON system_metrics (is_anomaly) WHERE is_anomaly;
CREATE INDEX IF NOT EXISTS idx_system_metrics_period_start ON system_metrics (aggregation_period_start);
CREATE INDEX IF NOT EXISTS idx_system_metrics_details      ON system_metrics USING GIN (details);


CREATE TABLE IF NOT EXISTS system_health (
    id                   SERIAL PRIMARY KEY,
    check_type           VARCHAR(50) NOT NULL,
    component_name       VARCHAR(100) NOT NULL,
    status               VARCHAR(20) NOT NULL,
    severity             VARCHAR(20) NOT NULL,
    error_type           VARCHAR(100),
    error_message        TEXT,
    error_stacktrace     TEXT,
    request_context      JSONB,
    response_context     JSONB,
    response_time_ms     INTEGER,
    retry_count          INTEGER DEFAULT 0,
    affected_operations  JSONB,
    user_impact          VARCHAR(20),
    is_resolved          BOOLEAN DEFAULT FALSE,
    resolved_at          TIMESTAMP WITH TIME ZONE,
    resolution_notes     TEXT,
    auto_recovered       BOOLEAN DEFAULT FALSE,
    detected_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_occurrence      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    alert_sent           BOOLEAN DEFAULT FALSE,
    alert_sent_at        TIMESTAMP WITH TIME ZONE,
    alert_recipients     JSONB,

    CHECK (check_type IN ('api_health', 'parser_health', 'db_health', 'service_health', 'network_health')),
    CHECK (status IN ('healthy', 'degraded', 'failed', 'recovering')),
    CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    CHECK (user_impact IN ('none', 'low', 'medium', 'high', 'critical'))
);

CREATE INDEX IF NOT EXISTS idx_system_health_check_type       ON system_health (check_type);
CREATE INDEX IF NOT EXISTS idx_system_health_component_name   ON system_health (component_name);
CREATE INDEX IF NOT EXISTS idx_system_health_status           ON system_health (status);
CREATE INDEX IF NOT EXISTS idx_system_health_severity         ON system_health (severity);
CREATE INDEX IF NOT EXISTS idx_system_health_is_resolved      ON system_health (is_resolved);
CREATE INDEX IF NOT EXISTS idx_system_health_detected_at      ON system_health (detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_user_impact      ON system_health (user_impact);
CREATE INDEX IF NOT EXISTS idx_system_health_request_context  ON system_health USING GIN (request_context);
CREATE INDEX IF NOT EXISTS idx_system_health_response_context ON system_health USING GIN (response_context);


CREATE TABLE IF NOT EXISTS system_alerts (
    id                    SERIAL PRIMARY KEY,
    alert_type            VARCHAR(50) NOT NULL,
    title                 VARCHAR(255) NOT NULL,
    description           TEXT NOT NULL,
    severity              VARCHAR(20) NOT NULL,
    component             VARCHAR(100),
    metric_type           VARCHAR(50),
    threshold_value       VARCHAR(50),
    actual_value          VARCHAR(50),
    alert_data            JSONB,
    status                VARCHAR(20) NOT NULL DEFAULT 'active',
    acknowledged_by       VARCHAR(100),
    acknowledged_at       TIMESTAMP WITH TIME ZONE,
    resolved_at           TIMESTAMP WITH TIME ZONE,
    resolution_notes      TEXT,
    triggered_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notifications_sent    INTEGER DEFAULT 0,
    last_notification_at  TIMESTAMP WITH TIME ZONE,

    CHECK (alert_type IN (
        'high_error_rate', 'api_downtime', 'anomaly_detected',
        'threshold_breach', 'health_check_failed', 'performance_degradation',
        'security_incident', 'other'
    )),
    CHECK (severity IN ('warning', 'error', 'critical')),
    CHECK (status IN ('active', 'acknowledged', 'resolved', 'false_alarm'))
);

CREATE INDEX IF NOT EXISTS idx_system_alerts_alert_type   ON system_alerts (alert_type);
CREATE INDEX IF NOT EXISTS idx_system_alerts_severity     ON system_alerts (severity);
CREATE INDEX IF NOT EXISTS idx_system_alerts_status       ON system_alerts (status);
CREATE INDEX IF NOT EXISTS idx_system_alerts_triggered_at ON system_alerts (triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_alerts_component    ON system_alerts (component);
CREATE INDEX IF NOT EXISTS idx_system_alerts_metric_type  ON system_alerts (metric_type);
CREATE INDEX IF NOT EXISTS idx_system_alerts_alert_data   ON system_alerts USING GIN (alert_data);

COMMENT ON TABLE system_metrics IS 'System-wide performance metrics and KPIs';
COMMENT ON TABLE system_health  IS 'Health checks, failures and recoveries';
COMMENT ON TABLE system_alerts  IS 'System-level alerts surfaced to superadmins';
