import os
import uuid
from fastapi import HTTPException, UploadFile, status

from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def validate_and_save_upload(file: UploadFile, subdir: str = "resumes", allowed=None) -> str:
    """Validates file type/size and saves it to disk. Returns the saved path."""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    allowed = allowed or ALLOWED_EXTENSIONS
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}.",
        )

    contents = file.file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max allowed size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    if ext == ".pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file is not a valid PDF.")
    if ext == ".docx" and not contents.startswith(b"PK"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file is not a valid DOCX.")
    if ext in (".txt", ".md") and b"\x00" in contents[:2048]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file is not plain text.")

    target_dir = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(target_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(target_dir, safe_name)

    with open(full_path, "wb") as f:
        f.write(contents)

    return full_path
