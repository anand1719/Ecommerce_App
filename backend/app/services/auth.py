from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import RefreshToken, User, utc_now
from app.schemas.auth import TokenResponse, UserCreate


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return utc_now() >= expires_at


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def register_user(db: Session, payload: UserCreate) -> User:
    user = User(
        email=_normalize_email(payload.email),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    return user


def issue_token_pair(db: Session, user: User) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id)
    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(user.id)

    db.add(RefreshToken(jti=refresh_jti, user_id=user.id, expires_at=refresh_expires_at))
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def login_user(db: Session, email: str, password: str) -> TokenResponse:
    user = authenticate_user(db, email, password)
    return issue_token_pair(db, user)


def refresh_token_pair(db: Session, refresh_token: str) -> TokenResponse:
    payload = _decode_expected_token(refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    refresh_jti = payload.get("jti")
    if not user_id or not refresh_jti:
        raise _invalid_token_error()

    stored_token = db.scalar(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    if not stored_token or stored_token.is_revoked or _is_expired(stored_token.expires_at):
        raise _invalid_token_error()

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise _invalid_token_error()

    stored_token.revoked_at = utc_now()
    db.add(stored_token)
    db.flush()

    return issue_token_pair(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    payload = _decode_expected_token(refresh_token, expected_type="refresh")
    refresh_jti = payload.get("jti")
    if not refresh_jti:
        raise _invalid_token_error()

    stored_token = db.scalar(select(RefreshToken).where(RefreshToken.jti == refresh_jti))
    if stored_token and not stored_token.is_revoked:
        stored_token.revoked_at = utc_now()
        db.add(stored_token)
        db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": utc_now()}, synchronize_session=False)
    db.commit()


def _decode_expected_token(token: str, expected_type: str) -> dict:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise _invalid_token_error() from exc

    if payload.get("type") != expected_type:
        raise _invalid_token_error()
    return payload


def _invalid_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

