from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.db import Base


class SystemHealth(Base):
    """
    Tracks system health events, failures, and anomalies.
    Monitors upstream API downtime, parser errors, and unexpected system behavior.
    """
    __tablename__ = "system_health"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Health Check Type
    check_type = Column(String(50), nullable=False, index=True)  # 'api_health', 'parser_health', 'db_health', 'service_health'
    component_name = Column(String(100), nullable=False, index=True)  # 'sanctions_api', 'transaction_parser', 'postgres_db', etc.
    
    # Status
    status = Column(String(20), nullable=False, index=True)  # 'healthy', 'degraded', 'failed', 'recovering'
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'error', 'critical'
    
    # Error Details
    error_type = Column(String(100))  # 'connection_timeout', 'parse_error', 'api_rate_limit', 'database_connection_failed'
    error_message = Column(Text)
    error_stacktrace = Column(Text)
    
    # Context
    request_context = Column(JSON)  # Store details about the request that failed (endpoint, params, etc.)
    response_context = Column(JSON)  # Store details about the response if available
    
    # Metrics
    response_time_ms = Column(Integer)  # Response time if applicable
    retry_count = Column(Integer, default=0)  # Number of retries attempted
    
    # Impact
    affected_operations = Column(JSON)  # List of operations affected by this health issue
    user_impact = Column(String(20))  # 'none', 'low', 'medium', 'high', 'critical'
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    auto_recovered = Column(Boolean, default=False)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_occurrence = Column(DateTime(timezone=True), server_default=func.now())
    
    # Alerting
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True))
    alert_recipients = Column(JSON)  # List of emails/channels notified


class SystemAlert(Base):
    """
    Stores system-level alerts for superadmin monitoring.
    Triggered when system behaves unexpectedly.
    """
    __tablename__ = "system_alerts"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert Details
    alert_type = Column(String(50), nullable=False, index=True)  # 'high_error_rate', 'api_downtime', 'anomaly_detected', 'threshold_breach'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # 'warning', 'error', 'critical'
    
    # Context
    component = Column(String(100))  # Component that triggered the alert
    metric_type = Column(String(50))  # Related metric if applicable
    threshold_value = Column(String(50))  # The threshold that was breached
    actual_value = Column(String(50))  # The actual value that breached the threshold
    
    # Additional Data
    alert_data = Column(JSON)  # Additional context and data
    
    # Status
    status = Column(String(20), nullable=False, default='active', index=True)  # 'active', 'acknowledged', 'resolved', 'false_alarm'
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    
    # Timestamps
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Notification
    notifications_sent = Column(Integer, default=0)
    last_notification_at = Column(DateTime(timezone=True))
