from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class DashboardSummary(BaseModel):
    total_users: int
    total_transactions: int
    blacklisted_users: int
    high_risk_users: int
    average_i360_score: float
    total_volume: float
    average_i_not_score: float


class RiskDistribution(BaseModel):
    low_risk: int
    medium_risk: int
    high_risk: int
    critical_risk: int


class FlaggedTransaction(BaseModel):
    transaction_id: int
    user_id: int
    user_name: str
    amount: float
    currency: str
    suspicious_score: float
    transaction_type: str
    created_at: str

    class Config:
        from_attributes = True


# Critical Alerts
class CriticalAlert(BaseModel):
    id: str
    alert_type: str
    severity: str
    description: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    transaction_id: Optional[int] = None
    amount: Optional[float] = None
    triggered_at: str
    time_ago_seconds: int
    is_acknowledged: bool
    assigned_to: Optional[str] = None

    class Config:
        from_attributes = True


# Live Alerts
class LiveAlert(BaseModel):
    id: str
    severity: str
    triggered_at: str
    time_display: str

    class Config:
        from_attributes = True


# Alert Trend
class AlertTrendDataPoint(BaseModel):
    timestamp: str
    count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


class AlertTrendResponse(BaseModel):
    period: str
    interval: str
    data_points: List[AlertTrendDataPoint]
    total_alerts: int
    avg_per_interval: float


# Alert Dismissal
class AlertDismissRequest(BaseModel):
    reason: Optional[str] = None
    notes: Optional[str] = None


class AlertDismissResponse(BaseModel):
    success: bool
    alert_id: str
    dismissed_at: str
    dismissed_by: str


# Investigation Case
class CaseCreateRequest(BaseModel):
    title: str
    description: str
    user_id: int
    transaction_ids: Optional[List[int]] = []
    alert_ids: Optional[List[str]] = []
    priority: Optional[str] = "MEDIUM"
    assigned_to: Optional[str] = None


class CaseCreateResponse(BaseModel):
    success: bool
    case_id: str
    created_at: str
    status: str
    assigned_to: Optional[str] = None


# Account Hold
class AccountHoldRequest(BaseModel):
    reason: str
    duration_hours: Optional[int] = None
    hold_type: Optional[str] = "TRANSACTION_ONLY"
    notes: Optional[str] = None


class AccountHoldResponse(BaseModel):
    success: bool
    user_id: int
    hold_id: str
    hold_placed_at: str
    hold_expires_at: Optional[str] = None
    hold_type: str
    status: str
