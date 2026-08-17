from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.admin import Admin
from app.schemas.auth import (
    LoginRequest,
    Token,
    AdminResponse,
    AdminCreate,
    AuditLogResponse,
    AuditLogFilter
)
from app.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.auth_dependencies import (
    require_admin,
    require_superadmin,
    get_current_active_admin,
    get_client_ip,
    get_user_agent
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint for admin and superadmin users.
    Returns a JWT access token upon successful authentication.
    """
    admin = AuthService.authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        # Log failed login attempt
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": admin.username, "role": admin.role},
        expires_delta=access_token_expires
    )
    
    # Update last login
    AuthService.update_last_login(db, admin.id)
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=admin.id,
        action_type="other",
        action_description=f"Admin {admin.username} logged in successfully",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=admin.role,
        username=admin.username
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Logout endpoint. Creates an audit log entry for the logout action.
    Note: Token invalidation is handled client-side by discarding the token.
    """
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="other",
        action_description=f"Admin {current_admin.username} logged out",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=AdminResponse)
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_active_admin)
):
    """
    Get current authenticated admin's information.
    """
    return current_admin


@router.get("/superadmin/logs")
async def get_superadmin_logs(
    admin_id: Optional[int] = None,
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_admin: Admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Superadmin-only endpoint to view all audit logs.
    Shows which admin blacklisted which user, alerts, and other details.
    
    Query parameters:
    - admin_id: Filter by specific admin
    - action_type: Filter by action type (e.g., "blacklist_user", "whitelist_user", "dismiss_alert")
    - target_type: Filter by target type (e.g., "user", "alert", "transaction")
    - limit: Number of logs to return (default: 100)
    - offset: Pagination offset (default: 0)
    """
    result = AuthService.get_audit_logs(
        db=db,
        admin_id=admin_id,
        action_type=action_type,
        target_type=target_type,
        limit=limit,
        offset=offset
    )
    
    return result


@router.post("/superadmin/create-admin", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    request: Request,
    current_admin: Admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Superadmin-only endpoint to create a new admin user.
    """
    # Check if username already exists
    existing_admin = db.query(Admin).filter(Admin.username == admin_data.username).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Admin).filter(Admin.email == admin_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create new admin
    new_admin = AuthService.create_admin(
        db=db,
        username=admin_data.username,
        email=admin_data.email,
        password=admin_data.password,
        role=admin_data.role.value
    )
    
    # Create audit log
    AuthService.create_audit_log(
        db=db,
        admin_id=current_admin.id,
        action_type="other",
        action_description=f"Superadmin {current_admin.username} created new {admin_data.role.value} account: {admin_data.username}",
        target_type="admin",
        target_id=new_admin.id,
        target_identifier=new_admin.username,
        metadata={"created_admin_role": admin_data.role.value},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return new_admin


@router.get("/superadmin/admins")
async def list_admins(
    current_admin: Admin = Depends(require_superadmin),
    db: Session = Depends(get_db)
):
    """
    Superadmin-only endpoint to list all admin users.
    """
    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    return {"admins": [AdminResponse.from_orm(admin) for admin in admins]}
