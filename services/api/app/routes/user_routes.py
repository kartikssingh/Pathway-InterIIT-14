from datetime import datetime, timezone
from typing import List

import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app import schemas, services
from app.core.config import get_settings
from app.db import get_db
from app.models.admin import Admin
from app.services.auth_dependencies import get_client_ip, get_user_agent, require_admin
from app.services.auth_service import AuthService
from app.services.s3_service import s3_service

router = APIRouter(prefix="/user", tags=["Users"])
users_router = APIRouter(prefix="/users", tags=["Users"])  # plural alias used by the frontend

#: KYC forms are a few pages of PDF; anything larger is a mistake or an attack.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.get("/all", response_model=List[schemas.user.UserRead])
@users_router.get("", response_model=List[schemas.user.UserRead])  # /users endpoint
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users with pagination."""
    return services.user_service.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=schemas.user.UserRead)
@users_router.get("/{user_id}", response_model=schemas.user.UserRead)  # /users/{user_id} endpoint
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get a single user by user_id."""
    db_user = services.user_service.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/add", response_model=schemas.user.UserRead)
def create_user(user: schemas.user.UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    # Check if user_id already exists
    existing_user = services.user_service.get_user(db, user.user_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User ID already exists")
    
    # Check if email already exists (if provided)
    if user.email:
        existing_email = services.user_service.get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    return services.user_service.create_user(db, user)


@router.patch("/{user_id}", response_model=schemas.user.UserRead)
def patch_user(
    user_id: int,
    patch: schemas.user.UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Update user information. Requires admin authentication."""
    db_user = services.user_service.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated = services.user_service.update_user(db, user_id, patch)
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="other",
        action_description=f"Admin {current_admin.username} updated user information",
        target_type="user",
        target_id=user_id,
        target_identifier=str(user_id),
        metadata={"updated_fields": patch.model_dump(exclude_unset=True)},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return updated


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Delete a user. Requires admin authentication."""
    user = services.user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ok = services.user_service.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="other",
        action_description=f"Admin {current_admin.username} deleted user {user_id}",
        target_type="user",
        target_id=user_id,
        target_identifier=str(user_id),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"ok": True}


@router.post("/{user_id}/blacklist", response_model=schemas.user.UserRead)
def blacklist_user(
    user_id: int,
    reason: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Blacklist a user. Requires admin authentication.
    This action is logged for superadmin audit trail.
    """
    user = services.user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.blacklisted:
        raise HTTPException(status_code=400, detail="User is already blacklisted")
    
    # Blacklist the user
    from datetime import datetime
    user.blacklisted = True
    user.blacklisted_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="blacklist_user",
        action_description=f"Admin {current_admin.username} blacklisted user {user_id} - Reason: {reason}",
        target_type="user",
        target_id=user_id,
        target_identifier=str(user_id),
        metadata={"reason": reason, "previous_status": "active"},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return user


@router.post("/{user_id}/whitelist", response_model=schemas.user.UserRead)
def whitelist_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Remove a user from blacklist (whitelist). Requires admin authentication.
    This action is logged for superadmin audit trail.
    """
    user = services.user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.blacklisted:
        raise HTTPException(status_code=400, detail="User is not blacklisted")
    
    # Whitelist the user
    user.blacklisted = False
    user.blacklisted_at = None
    db.commit()
    db.refresh(user)
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="whitelist_user",
        action_description=f"Admin {current_admin.username} removed user {user_id} from blacklist",
        target_type="user",
        target_id=user_id,
        target_identifier=str(user_id),
        metadata={"new_status": "active"},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return user


@router.get("/risk/{risk_category}", response_model=List[schemas.user.UserRead])
def get_users_by_risk(
    risk_category: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get users by risk category."""
    return services.user_service.get_users_by_risk_category(db, risk_category, skip, limit)


@router.get("/blacklisted/all", response_model=List[schemas.user.UserRead])
def get_blacklisted_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all blacklisted users."""
    return services.user_service.get_blacklisted_users(db, skip, limit)

@router.post("/upload-form", response_model=schemas.user.UploadFormResponse)
async def upload_form(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Upload a form in S3 bucket after converting it to binary."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )

    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    original_filename = file.filename or "form.pdf"
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', original_filename)
    # Strip the extension: the object is stored as opaque binary so the S3
    # console offers a download rather than an inline PDF preview.
    base_name = sanitized.rsplit('.', 1)[0] if '.' in sanitized else sanitized
    s3_key = f"{settings.s3.forms_prefix}{timestamp}_{unique_id}_{base_name}.bin"

    # UpstreamError from the service is rendered as a 502 by the global handler.
    result = s3_service.upload_bytes(key=s3_key, data=file_bytes, force_binary=True)
    url = result.url

    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="other",
        action_description=f"Admin {current_admin.username} uploaded form: {original_filename}",
        target_type="form",
        target_id=None,
        target_identifier=s3_key,
        metadata={
            "s3_key": s3_key,
            "filename": original_filename,
            "file_size": file_size,
            "url": url
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {
        "ok": True,
        "key": s3_key,
        "url": url,
        "filename": original_filename,
        "file_size": file_size
    }