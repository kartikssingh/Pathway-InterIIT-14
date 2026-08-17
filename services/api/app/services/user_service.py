from sqlalchemy.orm import Session
from app import models, schemas


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users with pagination."""
    return db.query(models.user.User).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    """Get a single user by user_id."""
    return db.query(models.user.User).filter(models.user.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Get a user by email address."""
    return db.query(models.user.User).filter(models.user.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    """Get a user by username."""
    return db.query(models.user.User).filter(models.user.User.username == username).first()


def create_user(db: Session, user: schemas.user.UserCreate):
    """Create a new user matching core_schema.sql structure."""
    db_user = models.user.User(
        user_id=user.user_id,
        uin=user.uin,
        uin_hash=user.uin_hash,
        username=user.username,
        profile_pic=user.profile_pic,
        email=user.email,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        address=user.address,
        occupation=user.occupation,
        annual_income=user.annual_income,
        kyc_status=user.kyc_status,
        signature_hash=user.signature_hash,
        credit_score=user.credit_score,
        risk_category=user.risk_category,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, patch: schemas.user.UserUpdate):
    """Update an existing user."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    """Delete a user by user_id."""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True


def get_users_by_risk_category(db: Session, risk_category: str, skip: int = 0, limit: int = 100):
    """Get users filtered by risk category."""
    return db.query(models.user.User).filter(
        models.user.User.risk_category == risk_category
    ).offset(skip).limit(limit).all()


def get_blacklisted_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all blacklisted users."""
    return db.query(models.user.User).filter(
        models.user.User.blacklisted == True
    ).offset(skip).limit(limit).all()


def blacklist_user(db: Session, user_id: int):
    """Blacklist a user."""
    from datetime import datetime
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db_user.blacklisted = True
    db_user.blacklisted_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user


def whitelist_user(db: Session, user_id: int):
    """Remove a user from blacklist."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db_user.blacklisted = False
    db_user.blacklisted_at = None
    db.commit()
    db.refresh(db_user)
    return db_user
