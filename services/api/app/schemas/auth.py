from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AdminRole(str, Enum):
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


# Login Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: AdminRole
    username: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# Admin Schemas
class AdminBase(BaseModel):
    username: str
    email: EmailStr
    role: AdminRole


class AdminCreate(AdminBase):
    password: str


class AdminResponse(AdminBase):
    id: int
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


# Audit Log Schemas
class AuditLogBase(BaseModel):
    action_type: str
    action_description: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_identifier: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    admin_id: int
    ip_address: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: int
    admin_id: int
    admin_username: Optional[str] = None
    admin_email: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    admin_id: Optional[int] = None
    action_type: Optional[str] = None
    target_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
