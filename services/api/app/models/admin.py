from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class Admin(Base):
    """
    Admin model matching core_schema.sql.
    Roles are stored as VARCHAR, not Enum.
    Note: is_active column is NOT in core_schema.sql.
    """
    __tablename__ = "admins"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Role (stored as VARCHAR per core_schema.sql)
    role = Column(String(20), nullable=False, default='admin', index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="admin")
    
    # Table-level constraints (matching core_schema.sql)
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'superadmin')", name='check_admin_role'),
    )
