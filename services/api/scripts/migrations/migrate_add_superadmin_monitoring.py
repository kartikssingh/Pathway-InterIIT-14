"""
Database migration script to add superadmin monitoring tables.
Adds tables for system metrics, system health, and system alerts.

Run this script to update your database schema.
"""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL)
metadata = MetaData()


def create_system_metrics_table():
    """Create system_metrics table"""
    system_metrics = Table(
        'system_metrics',
        metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('metric_type', String(50), nullable=False, index=True),
        Column('metric_category', String(50), nullable=False, index=True),
        Column('metric_value', Float, nullable=False),
        Column('metric_unit', String(20)),
        Column('time_window', String(20)),
        Column('aggregation_period_start', DateTime(timezone=True)),
        Column('aggregation_period_end', DateTime(timezone=True)),
        Column('details', JSON),
        Column('total_count', Integer),
        Column('positive_count', Integer),
        Column('negative_count', Integer),
        Column('recorded_at', DateTime(timezone=True), server_default=func.now(), index=True),
        Column('is_anomaly', Boolean, default=False),
        Column('anomaly_threshold', Float)
    )
    return system_metrics


def create_system_health_table():
    """Create system_health table"""
    system_health = Table(
        'system_health',
        metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('check_type', String(50), nullable=False, index=True),
        Column('component_name', String(100), nullable=False, index=True),
        Column('status', String(20), nullable=False, index=True),
        Column('severity', String(20), nullable=False),
        Column('error_type', String(100)),
        Column('error_message', Text),
        Column('error_stacktrace', Text),
        Column('request_context', JSON),
        Column('response_context', JSON),
        Column('response_time_ms', Integer),
        Column('retry_count', Integer, default=0),
        Column('affected_operations', JSON),
        Column('user_impact', String(20)),
        Column('is_resolved', Boolean, default=False),
        Column('resolved_at', DateTime(timezone=True)),
        Column('resolution_notes', Text),
        Column('auto_recovered', Boolean, default=False),
        Column('detected_at', DateTime(timezone=True), server_default=func.now(), index=True),
        Column('last_occurrence', DateTime(timezone=True), server_default=func.now()),
        Column('alert_sent', Boolean, default=False),
        Column('alert_sent_at', DateTime(timezone=True)),
        Column('alert_recipients', JSON)
    )
    return system_health


def create_system_alerts_table():
    """Create system_alerts table"""
    system_alerts = Table(
        'system_alerts',
        metadata,
        Column('id', Integer, primary_key=True, index=True),
        Column('alert_type', String(50), nullable=False, index=True),
        Column('title', String(255), nullable=False),
        Column('description', Text, nullable=False),
        Column('severity', String(20), nullable=False, index=True),
        Column('component', String(100)),
        Column('metric_type', String(50)),
        Column('threshold_value', String(50)),
        Column('actual_value', String(50)),
        Column('alert_data', JSON),
        Column('status', String(20), nullable=False, default='active', index=True),
        Column('acknowledged_by', String(100)),
        Column('acknowledged_at', DateTime(timezone=True)),
        Column('resolved_at', DateTime(timezone=True)),
        Column('resolution_notes', Text),
        Column('triggered_at', DateTime(timezone=True), server_default=func.now(), index=True),
        Column('last_updated', DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        Column('notifications_sent', Integer, default=0),
        Column('last_notification_at', DateTime(timezone=True))
    )
    return system_alerts


def run_migration():
    """Run the migration to create new tables"""
    print("Starting migration...")
    
    # Create tables
    print("Creating system_metrics table...")
    system_metrics = create_system_metrics_table()
    
    print("Creating system_health table...")
    system_health = create_system_health_table()
    
    print("Creating system_alerts table...")
    system_alerts = create_system_alerts_table()
    
    # Create all tables
    try:
        metadata.create_all(engine)
        print("✓ Migration completed successfully!")
        print("✓ Created tables: system_metrics, system_health, system_alerts")
    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_migration()
