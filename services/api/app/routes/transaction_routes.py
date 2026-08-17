from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import get_db
from app import services, schemas
from app.models.transaction import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=schemas.transaction.TransactionListResponse)
@router.get("/all", response_model=schemas.transaction.TransactionListResponse)
def read_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all transactions with pagination. Returns { total, items }."""
    items = services.transaction_service.get_transactions(db, skip=skip, limit=limit)
    total = db.query(Transaction).count()
    return {"total": total, "items": items}


@router.get("/{transaction_id}", response_model=schemas.transaction.TransactionRead)
def read_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Get a single transaction by transaction_id."""
    tx = services.transaction_service.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.get("/user/{user_id}", response_model=schemas.transaction.TransactionListResponse)
def read_transactions_by_user(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all transactions for a specific user. Returns { total, items }."""
    # Verify user exists
    user = services.user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    items = services.transaction_service.get_transactions_by_user(db, user_id, skip=skip, limit=limit)
    total = db.query(Transaction).filter(Transaction.user_id == user_id).count()
    return {"total": total, "items": items}


@router.get("/type/{txn_type}", response_model=schemas.transaction.TransactionListResponse)
def read_transactions_by_type(
    txn_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get transactions filtered by type (e.g., 'TRANSFER', 'DEPOSIT', 'WITHDRAWAL'). Returns { total, items }."""
    items = services.transaction_service.get_transactions_by_type(db, txn_type, skip=skip, limit=limit)
    total = db.query(Transaction).filter(Transaction.txn_type == txn_type).count()
    return {"total": total, "items": items}


@router.get("/fraud/all", response_model=schemas.transaction.TransactionListResponse)
def read_fraud_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all transactions flagged as fraud. Returns { total, items }."""
    items = services.transaction_service.get_fraud_transactions(db, skip=skip, limit=limit)
    total = db.query(Transaction).filter(Transaction.is_fraud == 1).count()
    return {"total": total, "items": items}


@router.get("/filter/amount", response_model=schemas.transaction.TransactionListResponse)
def filter_transactions_by_amount(
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Filter transactions by amount range. Returns { total, items }."""
    items = services.transaction_service.get_transactions_by_amount_range(
        db, min_amount=min_amount, max_amount=max_amount, skip=skip, limit=limit
    )
    # Build count query with same filters
    query = db.query(Transaction)
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    total = query.count()
    return {"total": total, "items": items}


@router.get("/filter/date", response_model=schemas.transaction.TransactionListResponse)
def filter_transactions_by_date(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Filter transactions by date range. Returns { total, items }."""
    items = services.transaction_service.get_transactions_by_date_range(
        db, start_date=start_date, end_date=end_date, skip=skip, limit=limit
    )
    # Build count query with same filters
    query = db.query(Transaction)
    if start_date is not None:
        query = query.filter(Transaction.txn_timestamp >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.txn_timestamp <= end_date)
    total = query.count()
    return {"total": total, "items": items}


@router.post("/add", response_model=schemas.transaction.TransactionRead)
def create_transaction(tx: schemas.transaction.TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction."""
    # Check if transaction_id already exists
    existing = services.transaction_service.get_transaction(db, tx.transaction_id)
    if existing:
        raise HTTPException(status_code=400, detail="Transaction ID already exists")
    
    # Ensure user exists
    user = services.user_service.get_user(db, tx.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return services.transaction_service.create_transaction(db, tx)


@router.patch("/{transaction_id}", response_model=schemas.transaction.TransactionRead)
def update_transaction(
    transaction_id: int,
    tx: schemas.transaction.TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction."""
    updated = services.transaction_service.update_transaction(db, transaction_id, tx)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Delete a transaction."""
    ok = services.transaction_service.delete_transaction(db, transaction_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"ok": True}


@router.get("/stats/user/{user_id}")
def get_user_transaction_stats(user_id: int, db: Session = Depends(get_db)):
    """Get transaction statistics for a user."""
    # Verify user exists
    user = services.user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    count = services.transaction_service.get_transaction_count_by_user(db, user_id)
    total = services.transaction_service.get_total_amount_by_user(db, user_id)
    
    return {
        "user_id": user_id,
        "transaction_count": count,
        "total_amount": total
    }
