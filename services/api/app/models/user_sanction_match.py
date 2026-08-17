from sqlalchemy import Column, BigInteger, Integer, Boolean, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class UserSanctionMatch(Base):
    __tablename__ = "usersanctionmatches"

    # Primary Key
    match_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Key
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Match Details
    match_found = Column(Boolean)
    match_confidence = Column(Float)
    matched_entity_name = Column(String(500))
    
    # Metadata
    checked_at = Column(DateTime, server_default=func.now())
    
    # Pathway Fields
    time = Column(BigInteger)  # Pathway timestamp
    diff = Column(Integer)     # Pathway diff field
    
    # Relationships
    user = relationship("User", back_populates="sanction_matches")
