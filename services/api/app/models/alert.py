from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class ComplianceAlert(Base):
    """
    Compliance Alert model.
    Tracks alerts related to users and transactions.
    """
    __tablename__ = "compliance_alerts"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys (updated to match new Transaction schema)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=True, index=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.transaction_id"), nullable=True, index=True)
    
    # Alert Classification
    alert_type = Column(String(50), nullable=False, index=True)  # kyc_alert, transaction_alert, fraud_alert, etc.
    severity = Column(String(20), nullable=False, default='medium', index=True)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Alert Details
    entity_id = Column(String(100), nullable=True)
    entity_type = Column(String(50), nullable=True)
    rps360 = Column(Float, default=0.0)
    
    # Alert Status
    status = Column(String(20), default='active', index=True)  # active, investigating, resolved, dismissed, escalated
    priority = Column(String(20), default='medium')  # low, medium, high, critical
    
    # Dismissal & Acknowledgment
    is_acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    dismissal_reason = Column(Text, nullable=True)
    
    # Source & Context
    source = Column(String(100), nullable=True)
    triggered_by = Column(String(100), nullable=True)
    alert_metadata = Column(Text, nullable=True)  # JSON field for additional context
    
    # Timestamps
    # Note: Database does not have 'triggered_at'. Use 'created_at' and expose
    # a property 'triggered_at' for code that references it.
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    transaction = relationship("Transaction", back_populates="alerts")

    @property
    def triggered_at(self):
        return self.created_at

    @triggered_at.setter
    def triggered_at(self, value):
        # Map any assignments to triggered_at onto created_at to avoid DB column usage
        self.created_at = value
