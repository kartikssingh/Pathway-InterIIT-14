from sqlalchemy import Column, BigInteger, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class ToxicityHistory(Base):
    __tablename__ = "toxicityhistory"

    # Primary Key
    history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Key
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Risk Scores
    rps_not = Column(Float)
    rps_360 = Column(Float)
    sanction_score = Column(Float)
    news_score = Column(Float)
    transaction_score = Column(Float)
    portfolio_score = Column(Float)
    
    # Calculation Metadata
    calculated_at = Column(DateTime, server_default=func.now())
    calculation_trigger = Column(String(50))
    
    # Pathway Fields
    time = Column(BigInteger)  # Pathway timestamp
    diff = Column(Integer)     # Pathway diff field
    
    # Relationships
    user = relationship("User", back_populates="toxicity_history")
