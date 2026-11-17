"""Password hashing, JWT access/refresh tokens and role-based access control."""
import datetime as dt
import uuid
from typing import Optional, Tuple

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, RefreshToken, ROLE_ADMIN, ROLE_OFFICER, ROLE_STUDENT

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

TOKEN_ACCESS = "access"
TOKEN_REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=minutes)
    return _encode({"sub": subject, "exp": expire, "type": TOKEN_ACCESS})


def create_refresh_token(db: Session, user_id: int) -> str:
    """Issue a refresh token and persist its jti so it can be rotated / revoked."""
    jti = uuid.uuid4().hex
    expire = dt.datetime.utcnow() + dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user_id, jti=jti, expires_at=expire))
    db.flush()
    return _encode({"sub": str(user_id), "exp": expire, "type": TOKEN_REFRESH, "jti": jti})


def _decode(token: str, expected_type: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("type", TOKEN_ACCESS) != expected_type:
        return None
    return payload


def decode_access_token(token: str) -> Optional[str]:
    payload = _decode(token, TOKEN_ACCESS)
    return payload.get("sub") if payload else None


def rotate_refresh_token(db: Session, token: str) -> Tuple[User, str]:
    """Validate a refresh token, revoke it and issue a new one (rotation). Raises 401 on any problem."""
    err = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
    payload = _decode(token, TOKEN_REFRESH)
    if not payload or not payload.get("jti"):
        raise err
    row = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if row is None or row.revoked or row.expires_at < dt.datetime.utcnow():
        # a reused (already rotated) token suggests theft: revoke the user's whole family
        if row is not None and row.revoked:
            db.query(RefreshToken).filter(RefreshToken.user_id == row.user_id).update({"revoked": True})
            db.commit()
        raise err
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None or not user.is_active:
        raise err
    row.revoked = True
    new_token = create_refresh_token(db, user.id)
    db.commit()
    return user, new_token


def revoke_refresh_token(db: Session, token: str) -> None:
    payload = _decode(token, TOKEN_REFRESH)
    if payload and payload.get("jti"):
        db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).update({"revoked": True})
        db.commit()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only the given roles. Admin always passes."""
    allowed = set(roles) | {ROLE_ADMIN}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed and not (ROLE_ADMIN in allowed and user.is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to do this.")
        return user

    return dependency


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# admin or placement officer (read-only institutional reports)
get_staff_user = require_roles(ROLE_OFFICER)
