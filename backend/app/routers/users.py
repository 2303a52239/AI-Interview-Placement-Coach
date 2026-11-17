import io
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.user import MeResponse, ProfileUpdateRequest, ProfileOut, AutofillRequest
from app.services import profile_service as ps
from app.utils.security import get_current_user

router = APIRouter(tags=["User Profile"])


@router.get("/users/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeResponse(id=current_user.id, name=current_user.name, email=current_user.email,
                      is_admin=current_user.is_admin_role, role=current_user.role or "student",
                      profile=ps.build_profile_out(db, current_user))


@router.put("/users/me/profile", response_model=ProfileOut)
def update_profile(payload: ProfileUpdateRequest, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    ps.apply_profile_update(db, current_user, payload)
    return ps.build_profile_out(db, current_user)


@router.get("/users/me/readiness")
def get_readiness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ps.readiness(db, current_user)


@router.post("/users/me/profile/autofill")
def autofill(payload: AutofillRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Resume).filter(Resume.user_id == current_user.id)
    resume = q.filter(Resume.id == payload.resume_id).first() if payload.resume_id else \
        q.filter(Resume.is_active == True).first()  # noqa: E712
    if not resume:
        raise HTTPException(status_code=404, detail="Upload a resume first.")
    result = ps.autofill_from_resume(db, current_user, resume, payload.overwrite)
    result["profile"] = ps.build_profile_out(db, current_user).model_dump()
    return result


@router.post("/users/me/photo")
def upload_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    data = file.file.read()
    if len(data) > settings.MAX_PHOTO_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Photo too large (max {settings.MAX_PHOTO_SIZE_MB}MB).")
    try:  # validate it really is an image, then re-encode (strips metadata / embedded payloads)
        img = Image.open(io.BytesIO(data))
        if img.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError("format")
        img = img.convert("RGB")
        img.thumbnail((512, 512))
    except (UnidentifiedImageError, ValueError, OSError):
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WEBP image.")
    folder = os.path.join(settings.UPLOAD_DIR, "photos")
    os.makedirs(folder, exist_ok=True)
    profile = ps.get_or_create_profile(db, current_user)
    if profile.photo_path and os.path.exists(profile.photo_path):
        os.remove(profile.photo_path)
    path = os.path.join(folder, f"{uuid.uuid4().hex}.jpg")
    img.save(path, "JPEG", quality=88)
    profile.photo_path = path
    db.commit()
    return {"has_photo": True}


@router.get("/users/me/photo")
def get_photo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = ps.get_or_create_profile(db, current_user)
    if not profile.photo_path or not os.path.exists(profile.photo_path):
        raise HTTPException(status_code=404, detail="No photo.")
    return FileResponse(profile.photo_path, media_type="image/jpeg")


@router.delete("/users/me/photo", status_code=204)
def delete_photo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = ps.get_or_create_profile(db, current_user)
    if profile.photo_path and os.path.exists(profile.photo_path):
        os.remove(profile.photo_path)
    profile.photo_path = ""
    db.commit()
