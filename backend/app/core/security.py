from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.password import verify_password, get_password_hash
from app.db.database import get_db
from app.models.enums import UserRole
from app.schemas.auth import TokenData

security = HTTPBearer()


def _get_secret_key() -> str:
    """Get the secret key, raising an error if not configured in production."""
    secret_key = settings.SECRET_KEY
    if not secret_key:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("SECRET_KEY must be set in production environment")
        # Development fallback - but warn
        import logging
        logging.warning("Using default SECRET_KEY for development. Set SECRET_KEY in production!")
        secret_key = "dev-secret-key-change-in-production-32-chars-minimum"
    return secret_key


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current user from JWT token. Returns User model."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, _get_secret_key(), algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    # Import User here to avoid circular import
    from app.models.user import User
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user=Depends(get_current_user)):
    return current_user


def require_roles(*roles):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user
    return role_checker


def require_organizer(current_user=Depends(get_current_user)):
    if current_user.role not in [UserRole.ORGANIZER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer permissions required",
        )
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )
    return current_user