from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ComplianceAlertBase(BaseModel):
    alert_type: str
    severity: str
    title: str
    description: Optional[str] = None
    user_id: Optional[int] = None
    transaction_id: Optional[int] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    rps360: Optional[float] = Field(default=0.0, ge=0, le=1, description="RPS 360 score between 0-1")
    priority: Optional[str] = 'medium'
    source: Optional[str] = None
    triggered_by: Optional[str] = None
    alert_metadata: Optional[str] = None
    triggered_at: Optional[datetime] = None
    
    @field_validator('rps360', mode='before')
    @classmethod
    def validate_rps360(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('RPS 360 score must be between 0 and 1')
        return v


class ComplianceAlertCreate(ComplianceAlertBase):
    pass


class ComplianceAlertUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    is_acknowledged: Optional[bool] = None
    acknowledged_by: Optional[str] = None
    dismissal_reason: Optional[str] = None


class ComplianceAlertRead(ComplianceAlertBase):
    id: int
    user_name: Optional[str] = None
    status: str
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    dismissal_reason: Optional[str] = None
    triggered_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
    @property
    def alert_id(self):
        return self.id


class ComplianceAlertListResponse(BaseModel):
    total: int
    items: list[ComplianceAlertRead]


class UploadFormResponse(BaseModel):
    success: bool
    user_id: int
    extracted_data: dict
    message: str
