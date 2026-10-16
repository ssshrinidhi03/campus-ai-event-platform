from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
import secrets
import logging

from app.db.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_organizer,
    require_roles,
)
from app.core.config import settings
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    Token,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.email import send_verification_email, send_password_reset_email, send_welcome_email
from app.services.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])

VERIFICATION_TOKEN_EXPIRY_HOURS = 24
RESET_TOKEN_EXPIRY_HOURS = 1


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def _get_client_ip(request: Request) -> str:
    """Extract client IP for rate limiting."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_auth_rate_limit(request: Request, endpoint: str, max_attempts: int, window_minutes: int) -> None:
    """Check rate limit for auth endpoints."""
    if not settings.RATE_LIMIT_ENABLED:
        return
    client_ip = _get_client_ip(request)
    allowed, remaining = check_rate_limit(client_ip, endpoint, max_attempts, window_minutes)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again later.",
            headers={"Retry-After": str(window_minutes * 60)},
        )


@router.post("/auth/register", response_model=Token)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for registration
    _check_auth_rate_limit(
        request, "register",
        settings.RATE_LIMIT_REGISTER_ATTEMPTS,
        settings.RATE_LIMIT_REGISTER_WINDOW_MINUTES
    )

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if roll number already exists (if provided)
    if req.roll_number:
        existing_roll = db.query(User).filter(User.roll_number == req.roll_number).first()
        if existing_roll:
            raise HTTPException(status_code=400, detail="Roll number already registered")

    # Create user with verification token (stored as hash)
    verification_token = generate_verification_token()

    user = User(
        name=req.name,
        email=req.email,
        password_hash=get_password_hash(req.password),
        role=req.account_type,
        roll_number=req.roll_number,
        is_verified=False,
        is_identity_verified=False,
    )
    user.set_verification_token(verification_token, VERIFICATION_TOKEN_EXPIRY_HOURS)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send welcome email (registration must not fail if email delivery fails)
    welcome_sent = send_welcome_email(user.email)
    if not welcome_sent and settings.ENVIRONMENT == "production":
        logger.warning(f"Failed to send welcome email to {user.email}")

    # Send verification email (never expose token in response)
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    email_sent = send_verification_email(user.email, verification_link)

    if not email_sent and settings.ENVIRONMENT == "production":
        logger.warning(f"Failed to send verification email to {user.email}")

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/auth/login", response_model=Token)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for login
    _check_auth_rate_limit(
        request, "login",
        settings.RATE_LIMIT_LOGIN_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_MINUTES
    )

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if account is verified (for students)
    if user.role == UserRole.STUDENT and not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Account not verified. Please check your email for verification link."
        )

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/auth/verify-email", response_model=dict)
def verify_email(req: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for verification
    _check_auth_rate_limit(
        request, "verify",
        settings.RATE_LIMIT_VERIFY_ATTEMPTS,
        settings.RATE_LIMIT_VERIFY_WINDOW_MINUTES
    )

    # Find user by verification token hash (need to check all unverified users)
    # This is inefficient but necessary since we store hashes
    # In production, consider adding a token lookup table or index
    users = db.query(User).filter(User.is_verified == False).all()
    user = None
    for u in users:
        if u.verify_verification_token(req.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    user.is_verified = True
    user.clear_verification_token()
    db.add(user)
    db.commit()

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/auth/resend-verification", response_model=dict)
def resend_verification(req: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for resend
    _check_auth_rate_limit(
        request, "resend",
        settings.RATE_LIMIT_RESEND_ATTEMPTS,
        settings.RATE_LIMIT_RESEND_WINDOW_MINUTES
    )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a verification link has been sent."}

    if user.is_verified:
        return {"message": "Account is already verified. You can log in."}

    # Generate new verification token (invalidates old one)
    verification_token = generate_verification_token()
    user.set_verification_token(verification_token, VERIFICATION_TOKEN_EXPIRY_HOURS)
    db.add(user)
    db.commit()

    # Send verification email (never expose token in response)
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    send_verification_email(user.email, verification_link)

    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/auth/forgot-password", response_model=dict)
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for password reset requests
    _check_auth_rate_limit(
        request, "forgot_password",
        settings.RATE_LIMIT_RESEND_ATTEMPTS,
        settings.RATE_LIMIT_RESEND_WINDOW_MINUTES
    )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a password reset link has been sent."}

    # Generate reset token
    reset_token = generate_verification_token()
    user.set_reset_token(reset_token, RESET_TOKEN_EXPIRY_HOURS)
    db.add(user)
    db.commit()

    # Send reset email
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    send_password_reset_email(user.email, reset_link)

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/auth/reset-password", response_model=dict)
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limiting for password reset
    _check_auth_rate_limit(
        request, "reset_password",
        settings.RATE_LIMIT_VERIFY_ATTEMPTS,
        settings.RATE_LIMIT_VERIFY_WINDOW_MINUTES
    )

    # Find user by reset token hash
    users = db.query(User).all()
    user = None
    for u in users:
        if u.verify_reset_token(req.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = get_password_hash(req.password)
    user.clear_reset_token()
    db.add(user)
    db.commit()

    return {"message": "Password reset successfully. You can now log in."}


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user