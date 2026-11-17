from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.ai.factory import get_ai_provider
from app.models.user import User
from app.speech.stt import transcribe_audio_bytes
from app.utils.security import get_current_user

router = APIRouter(tags=["Evaluation & Speech"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg"}


class EvaluateRequest(BaseModel):
    interview_type: str = Field(pattern="^(hr|technical)$")
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(max_length=10000)
    context: str = ""


class EvaluateResponse(BaseModel):
    score: float
    strengths: List[str]
    weaknesses: List[str]
    feedback: str
    suggested_improvement: str


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest, current_user: User = Depends(get_current_user)):
    """Stateless answer evaluation: scores any question/answer pair without
    creating an interview. Useful for quick practice and for API demos."""
    result = get_ai_provider().evaluate_answer(
        payload.interview_type, payload.question, payload.answer, payload.context
    )
    return EvaluateResponse(
        score=float(result["score"]),
        strengths=list(result.get("strengths", [])),
        weaknesses=list(result.get("weaknesses", [])),
        feedback=result.get("feedback", ""),
        suggested_improvement=result.get("suggested_improvement", ""),
    )


@router.post("/speech/transcribe")
def transcribe(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Server-side speech-to-text fallback (used when the browser has no Web
    Speech API). Requires OPENAI_API_KEY; otherwise returns a clear 503."""
    if file.content_type and file.content_type.split(";")[0] not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported audio format.")
    audio = file.file.read()
    if not audio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is too large (max 10MB).")
    try:
        text = transcribe_audio_bytes(audio, file.filename or "audio.webm")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"text": text}
