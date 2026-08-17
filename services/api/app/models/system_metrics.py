from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.db import Base


class SystemMetrics(Base):
    """
    Tracks system-wide metrics for monitoring and analysis.
    Records hit rates, false positive rates, response times, and API errors.
    """
    __tablename__ = "system_metrics"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Metric Type
    metric_type = Column(String(50), nullable=False, index=True)  # 'alert_hit_rate', 'false_positive_rate', 'api_response_time', 'api_error_rate'
    metric_category = Column(String(50), nullable=False, index=True)  # 'alert', 'api', 'transaction', 'user'
    
    # Metric Values
    metric_value = Column(Float, nullable=False)  # The actual metric value
    metric_unit = Column(String(20))  # 'percentage', 'milliseconds', 'count', 'rate'
    
    # Context
    time_window = Column(String(20))  # 'hourly', 'daily', 'weekly', 'monthly'
    aggregation_period_start = Column(DateTime(timezone=True))
    aggregation_period_end = Column(DateTime(timezone=True))
    
    # Additional Details
    details = Column(JSON)  # Store additional context like breakdown by severity, alert type, etc.
    
    # Metadata
    total_count = Column(Integer)  # Total items in this metric calculation
    positive_count = Column(Integer)  # Count of positive cases (e.g., true positives)
    negative_count = Column(Integer)  # Count of negative cases (e.g., false positives)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Status
    is_anomaly = Column(Boolean, default=False)  # Flag if this metric is outside normal ranges
    anomaly_threshold = Column(Float)  # The threshold that was breached
