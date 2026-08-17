from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionBase(BaseModel):
    """Base schema matching core_schema.sql Transactions table."""
    user_id: int
    txn_timestamp: Optional[datetime] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    txn_type: Optional[str] = None
    counterparty_id: Optional[int] = None
    is_fraud: Optional[int] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    transaction_id: int  # Required for creation


class TransactionUpdate(BaseModel):
    """Schema for updating transaction information."""
    txn_timestamp: Optional[datetime] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    txn_type: Optional[str] = None
    counterparty_id: Optional[int] = None
    is_fraud: Optional[int] = None


class TransactionRead(TransactionBase):
    """Schema for reading transaction information - matches core_schema.sql."""
    transaction_id: int

    class Config:
        from_attributes = True


class TransactionSummary(BaseModel):
    """Compact transaction summary for lists."""
    transaction_id: int
    user_id: int
    amount: Optional[float] = None
    currency: Optional[str] = None
    txn_type: Optional[str] = None
    txn_timestamp: Optional[datetime] = None
    is_fraud: Optional[int] = None

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    """Schema for filtering transactions."""
    user_id: Optional[int] = None
    txn_type: Optional[str] = None
    currency: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_fraud: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 100


class TransactionListResponse(BaseModel):
    """Response model for paginated transaction list."""
    total: int
    items: list[TransactionRead]

    class Config:
        from_attributes = True
