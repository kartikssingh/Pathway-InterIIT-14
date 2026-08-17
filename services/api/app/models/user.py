from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, BigInteger, CHAR, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"

    # Primary Key
    user_id = Column(BigInteger, primary_key=True)
    
    # Core Identity
    uin = Column(CHAR(20))
    uin_hash = Column(CHAR(64))
    username = Column(String(100))
    profile_pic = Column(Text)  # Profile picture URL/path
    email = Column(String(255))
    phone = Column(String(15))
    date_of_birth = Column(DateTime)
    address = Column(Text)
    occupation = Column(String(200))
    annual_income = Column(Float)
    
    # KYC Status
    kyc_status = Column(String(100))
    kyc_verified_at = Column(DateTime)
    signature_hash = Column(String(64))
    
    # Credit & Risk Scoring
    credit_score = Column(Integer)
    current_rps_not = Column(Float)
    current_rps_360 = Column(Float)
    last_rps_calculation = Column(DateTime)
    risk_category = Column(String(100))
    
    # Account Status
    blacklisted = Column(Boolean, default=False)
    blacklisted_at = Column(DateTime)
    
    # Version Control & Pathway Fields
    version = Column(Integer, default=1)
    time = Column(BigInteger)  # Pathway timestamp
    diff = Column(Integer)     # Pathway diff field
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    toxicity_history = relationship("ToxicityHistory", back_populates="user", cascade="all, delete-orphan")
    sanction_matches = relationship("UserSanctionMatch", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("ComplianceAlert", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
