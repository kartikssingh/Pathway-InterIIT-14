from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class Transaction(Base):
    """
    Transaction model matching core_schema.sql.
    Each row represents an individual transaction.
    """
    __tablename__ = "transactions"

    # Primary Key
    transaction_id = Column(BigInteger, primary_key=True)
    
    # Foreign Key to User
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction Details
    txn_timestamp = Column(DateTime)  # When the transaction occurred
    amount = Column(Float)  # Transaction amount (DOUBLE PRECISION in schema)
    currency = Column(String(10))  # e.g., 'USD', 'INR'
    txn_type = Column(String(50))  # e.g., 'TRANSFER', 'DEPOSIT', 'WITHDRAWAL'
    counterparty_id = Column(BigInteger)  # ID of the other party in the transaction
    is_fraud = Column(Integer)  # 0 or 1 indicating fraud status
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    alerts = relationship("ComplianceAlert", back_populates="transaction")
