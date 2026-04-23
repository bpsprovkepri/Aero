"""
auth.py — Authentication endpoints (login, refresh, logout, me).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut, ChangePasswordRequest
from app.services.auth_service import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    blacklist_token,
    is_token_blacklisted,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate user, return access token + set refresh token cookie."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id, remember_me=req.remember_me)

    # Set refresh token as httpOnly cookie
    max_age = (
        settings.REFRESH_TOKEN_EXPIRE_DAYS_LONG * 86400
        if req.remember_me
        else settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,           # required for HTTPS
        samesite="none",       # required for cross-origin (different subdomain)
        domain=".gurind.am",   # leading dot = shared across all subdomains
        max_age=max_age,
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Validate refresh token cookie, return new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token tidak ditemukan")

    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token tidak valid")

    # Check blacklist
    jti = payload.get("jti")
    if jti and is_token_blacklisted(db, jti):
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token sudah di-revoke")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")

    new_access_token = create_access_token(user.id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Logout: blacklist both access and refresh tokens, clear cookie."""
    # Blacklist access token (from Authorization header)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
        payload = decode_token(access_token)
        if payload and payload.get("jti"):
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            blacklist_token(db, payload["jti"], exp)

    # Blacklist refresh token
    refresh = request.cookies.get("refresh_token")
    if refresh:
        payload = decode_token(refresh)
        if payload and payload.get("jti"):
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            blacklist_token(db, payload["jti"], exp)

    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Berhasil logout"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user."""
    return current_user


@router.patch("/password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change current user's password."""
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama salah",
        )

    if len(req.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 6 karakter",
        )

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()

    return {"message": "Password berhasil diubah"}
