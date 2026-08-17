from sqlalchemy.orm import Session
from sqlalchemy import desc
from app import models, schemas
from typing import Optional, List
from datetime import datetime


def get_transactions(db: Session, skip: int = 0, limit: int = 100) -> List:
    """Get all transactions with pagination."""
    return db.query(models.transaction.Transaction).offset(skip).limit(limit).all()


def get_transaction(db: Session, transaction_id: int):
    """Get a single transaction by transaction_id."""
    return db.query(models.transaction.Transaction).filter(
        models.transaction.Transaction.transaction_id == transaction_id
    ).first()


def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get all transactions for a specific user."""
    return db.query(models.transaction.Transaction).filter(
        models.transaction.Transaction.user_id == user_id
    ).order_by(desc(models.transaction.Transaction.txn_timestamp)).offset(skip).limit(limit).all()


def get_transactions_by_type(db: Session, txn_type: str, skip: int = 0, limit: int = 100):
    """Get transactions filtered by type."""
    return db.query(models.transaction.Transaction).filter(
        models.transaction.Transaction.txn_type == txn_type
    ).offset(skip).limit(limit).all()


def get_transactions_by_amount_range(
    db: Session,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    skip: int = 0,
    limit: int = 100
):
    """Filter transactions by amount range."""
    query = db.query(models.transaction.Transaction)
    
    if min_amount is not None:
        query = query.filter(models.transaction.Transaction.amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(models.transaction.Transaction.amount <= max_amount)
    
    return query.offset(skip).limit(limit).all()


def get_fraud_transactions(db: Session, skip: int = 0, limit: int = 100):
    """Get all transactions flagged as fraud."""
    return db.query(models.transaction.Transaction).filter(
        models.transaction.Transaction.is_fraud == 1
    ).offset(skip).limit(limit).all()


def get_transactions_by_date_range(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get transactions within a date range."""
    query = db.query(models.transaction.Transaction)
    
    if start_date:
        query = query.filter(models.transaction.Transaction.txn_timestamp >= start_date)
    
    if end_date:
        query = query.filter(models.transaction.Transaction.txn_timestamp <= end_date)
    
    return query.order_by(desc(models.transaction.Transaction.txn_timestamp)).offset(skip).limit(limit).all()


def create_transaction(db: Session, tx: schemas.transaction.TransactionCreate):
    """Create a new transaction."""
    db_tx = models.transaction.Transaction(
        transaction_id=tx.transaction_id,
        user_id=tx.user_id,
        txn_timestamp=tx.txn_timestamp,
        amount=tx.amount,
        currency=tx.currency,
        txn_type=tx.txn_type,
        counterparty_id=tx.counterparty_id,
        is_fraud=tx.is_fraud
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


def update_transaction(db: Session, transaction_id: int, tx: schemas.transaction.TransactionUpdate):
    """Update an existing transaction."""
    db_tx = get_transaction(db, transaction_id)
    if not db_tx:
        return None
    
    for field, value in tx.model_dump(exclude_unset=True).items():
        setattr(db_tx, field, value)
    
    db.commit()
    db.refresh(db_tx)
    return db_tx


def delete_transaction(db: Session, transaction_id: int):
    """Delete a transaction by transaction_id."""
    db_tx = get_transaction(db, transaction_id)
    if not db_tx:
        return False
    db.delete(db_tx)
    db.commit()
    return True


def get_transaction_count_by_user(db: Session, user_id: int) -> int:
    """Get the count of transactions for a user."""
    return db.query(models.transaction.Transaction).filter(
        models.transaction.Transaction.user_id == user_id
    ).count()


def get_total_amount_by_user(db: Session, user_id: int) -> float:
    """Get the total transaction amount for a user."""
    from sqlalchemy import func
    result = db.query(func.sum(models.transaction.Transaction.amount)).filter(
        models.transaction.Transaction.user_id == user_id
    ).scalar()
    return float(result) if result else 0.0
