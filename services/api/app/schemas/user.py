from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base schema matching core_schema.sql Users table."""
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    user_id: int  # Required for creation
    uin: Optional[str] = None
    uin_hash: Optional[str] = None
    profile_pic: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    kyc_status: Optional[str] = None
    signature_hash: Optional[str] = None
    credit_score: Optional[int] = Field(None, ge=300, le=900, description="Credit score between 300-900")
    risk_category: Optional[str] = None
    current_rps_not: Optional[float] = Field(None, ge=0, le=1, description="RPS NOT score between 0-1")
    current_rps_360: Optional[float] = Field(None, ge=0, le=1, description="RPS 360 score between 0-1")
    
    @field_validator('current_rps_not', 'current_rps_360', mode='before')
    @classmethod
    def validate_rps_score(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('RPS score must be between 0 and 1')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    username: Optional[str] = None
    profile_pic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    kyc_status: Optional[str] = None
    kyc_verified_at: Optional[datetime] = None
    signature_hash: Optional[str] = None
    credit_score: Optional[int] = Field(None, ge=300, le=900, description="Credit score between 300-900")
    current_rps_not: Optional[float] = Field(None, ge=0, le=1, description="RPS NOT score between 0-1")
    current_rps_360: Optional[float] = Field(None, ge=0, le=1, description="RPS 360 score between 0-1")
    risk_category: Optional[str] = None
    blacklisted: Optional[bool] = None
    blacklisted_at: Optional[datetime] = None
    
    @field_validator('current_rps_not', 'current_rps_360', mode='before')
    @classmethod
    def validate_rps_score(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('RPS score must be between 0 and 1')
        return v


class UserRead(UserBase):
    """Schema for reading user information - matches core_schema.sql."""
    user_id: int
    uin: Optional[str] = None
    uin_hash: Optional[str] = None
    profile_pic: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    
    # KYC Status
    kyc_status: Optional[str] = None
    kyc_verified_at: Optional[datetime] = None
    signature_hash: Optional[str] = None
    
    # Credit & Risk Scoring
    credit_score: Optional[int] = None
    current_rps_not: Optional[float] = None
    current_rps_360: Optional[float] = None
    last_rps_calculation: Optional[datetime] = None
    risk_category: Optional[str] = None
    
    # Account Status
    blacklisted: bool = False
    blacklisted_at: Optional[datetime] = None
    
    # Version Control & Pathway Fields
    version: Optional[int] = 1
    time: Optional[int] = None
    diff: Optional[int] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    """Compact user summary for lists and references."""
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    risk_category: Optional[str] = None
    blacklisted: bool = False

    class Config:
        from_attributes = True

class UploadFormResponse(BaseModel):
    """Response schema for uploading a form."""
    ok: bool
    key: str
    url: Optional[str] = None
    filename: str
    file_size: int