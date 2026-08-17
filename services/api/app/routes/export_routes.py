from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.models.transaction import Transaction
from typing import Optional, List
import csv
import io
from datetime import datetime

router = APIRouter(prefix="/export", tags=["export"])


def generate_csv(headers: List[str], rows: List[List]):
    """Generate CSV content from headers and rows"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return output.getvalue()


@router.post("/transactions")
def export_transactions(
    format: str = "CSV",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_suspicious_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Export transactions to CSV/Excel
    
    - **format**: Export format (CSV or Excel)
    - **start_date**: Start date filter (ISO 8601)
    - **end_date**: End date filter (ISO 8601)
    - **min_suspicious_score**: Minimum suspicious score
    
    Returns:
    - export_id: Unique export identifier
    - download_url: URL to download the file
    - record_count: Number of records exported
    """
    if format.upper() not in ["CSV", "EXCEL"]:
        raise HTTPException(status_code=400, detail="Format must be CSV or EXCEL")
    
    # Build query
    query = db.query(Transaction)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Transaction.created_at >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Transaction.created_at <= end_dt)
        except:
            pass
    
    if min_suspicious_score is not None:
        query = query.filter(Transaction.suspicious_score >= min_suspicious_score)
    
    transactions = query.all()
    
    # Generate export ID
    export_id = f"EXP-TX-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # For CSV format, return streaming response
    if format.upper() == "CSV":
        headers = [
            "Transaction ID", "User ID", "Amount", "Currency", 
            "Transaction Type", "Description", "Suspicious Score", "Created At"
        ]
        rows = [
            [
                tx.id, tx.user_id, tx.amount, tx.currency,
                tx.transaction_type or "", tx.description or "",
                tx.suspicious_score, tx.created_at.isoformat()
            ]
            for tx in transactions
        ]
        
        csv_content = generate_csv(headers, rows)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=transactions_{export_id}.csv"
            }
        )
    
    # For non-streaming, return export info
    return {
        "export_id": export_id,
        "download_url": f"/api/export/{export_id}/download",
        "record_count": len(transactions),
        "format": format
    }


@router.post("/users")
def export_users(
    format: str = "CSV",
    risk_level: Optional[List[str]] = None,
    is_blacklisted: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Export users to CSV/Excel
    
    - **format**: Export format (CSV or Excel)
    - **risk_level**: Filter by risk levels (e.g., ["HIGH", "CRITICAL"])
    - **is_blacklisted**: Filter by blacklist status
    
    Returns:
    - export_id: Unique export identifier
    - download_url: URL to download the file
    - record_count: Number of records exported
    """
    if format.upper() not in ["CSV", "EXCEL"]:
        raise HTTPException(status_code=400, detail="Format must be CSV or EXCEL")
    
    # Build query
    query = db.query(User)
    
    if risk_level:
        # Filter by risk levels based on i_360_score
        conditions = []
        for level in risk_level:
            if level == "LOW":
                conditions.append(User.i_360_score < 30)
            elif level == "MEDIUM":
                conditions.append((User.i_360_score >= 30) & (User.i_360_score < 60))
            elif level == "HIGH":
                conditions.append((User.i_360_score >= 60) & (User.i_360_score < 80))
            elif level == "CRITICAL":
                conditions.append(User.i_360_score >= 80)
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
    
    if is_blacklisted is not None:
        query = query.filter(User.is_blacklisted == is_blacklisted)
    
    users = query.all()
    
    # Generate export ID
    export_id = f"EXP-USR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # For CSV format, return streaming response
    if format.upper() == "CSV":
        headers = [
            "User ID", "Entity ID", "Applicant Name", "Email", "Mobile",
            "i_not_score", "i_360_score", "Is Blacklisted", "Created At"
        ]
        rows = [
            [
                user.id, user.entity_id, user.applicant_name,
                user.applicant_email or "", user.applicant_mobile_number or "",
                user.i_not_score, user.i_360_score, user.is_blacklisted,
                user.created_at.isoformat()
            ]
            for user in users
        ]
        
        csv_content = generate_csv(headers, rows)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=users_{export_id}.csv"
            }
        )
    
    # For non-streaming, return export info
    return {
        "export_id": export_id,
        "download_url": f"/api/export/{export_id}/download",
        "record_count": len(users),
        "format": format
    }
