import datetime as dt
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, Profile
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, UserOut, RefreshRequest, LogoutRequest,
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    rotate_refresh_token, revoke_refresh_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("app.auth")


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email,
                   is_admin=user.is_admin_role, role=user.role or "student")


def _tokens(db: Session, user: User) -> TokenResponse:
    access = create_access_token(subject=str(user.id))
    refresh = create_refresh_token(db, user.id)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_out(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
    user = User(name=payload.name.strip(), email=email, hashed_password=hash_password(payload.password), role="student")
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.commit()
    db.refresh(user)
    logger.info("user registered id=%s", user.id)
    return _tokens(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    user.last_login_at = dt.datetime.utcnow()
    db.commit()
    return _tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    user, new_refresh = rotate_refresh_token(db, payload.refresh_token)
    return TokenResponse(access_token=create_access_token(str(user.id)), refresh_token=new_refresh,
                         user=_user_out(user))


@router.post("/logout")
def logout(payload: LogoutRequest = LogoutRequest(), db: Session = Depends(get_db),
           current_user: User = Depends(get_current_user)):
    if payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out. Refresh token revoked; discard the access token on the client."}
