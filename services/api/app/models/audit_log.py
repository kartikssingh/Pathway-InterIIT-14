from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class AuditLog(Base):
    """
    Audit log model matching core_schema.sql.
    Records all admin actions for compliance and accountability.
    Note: user_agent column is NOT in core_schema.sql.
    """
    __tablename__ = "audit_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Admin who performed the action
    admin_id = Column(Integer, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(50), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    
    # Target entity (what was affected)
    target_type = Column(String(50), index=True)  # 'user', 'alert', 'transaction', 'system'
    target_id = Column(Integer, index=True)  # ID of the affected entity
    target_identifier = Column(String(255))  # e.g., entity_id, alert_id for easy reference
    
    # Additional context (stored as JSONB per core_schema.sql)
    action_metadata = Column(JSONB)  # before/after values, classification, notes, etc.
    
    # Security tracking
    ip_address = Column(String(50))
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    admin = relationship("Admin", back_populates="audit_logs")
    
    # Table-level constraints (matching core_schema.sql)
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('classify_alert', 'dismiss_alert', 'escalate_alert', "
            "'blacklist_user', 'whitelist_user', 'flag_user', 'unflag_user', "
            "'block_transaction', 'approve_transaction', 'update_system_alert', "
            "'resolve_health_check', 'other')",
            name='check_action_type'
        ),
    )
