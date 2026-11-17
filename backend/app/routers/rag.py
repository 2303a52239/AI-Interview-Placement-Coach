import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rag import Document, ChatMessage
from app.models.resume import Resume
from app.models.user import User
from app.rag import search as rsearch
from app.rag.embeddings import embedder_info
from app.services import rag_service as svc
from app.utils.file_utils import validate_and_save_upload
from app.utils.security import get_current_user

router = APIRouter(prefix="/rag", tags=["RAG Assistant"])
RAG_EXT = {".pdf", ".docx", ".txt", ".md"}


def _doc(d: Document) -> dict:
    return {"id": d.id, "filename": d.filename, "doc_type": d.doc_type, "char_count": d.char_count,
            "chunk_count": d.chunk_count, "embedding_provider": d.embedding_provider, "created_at": d.created_at}


@router.get("/status")
def status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"embedding": embedder_info(), "vector_store": "pgvector" if rsearch.has_pgvector(db) else "in-process (JSON vectors)",
            "documents": db.query(Document).filter(Document.user_id == current_user.id).count(), "max_documents": svc.MAX_DOCS_PER_USER}


@router.post("/documents", status_code=201)
def upload(file: UploadFile = File(...), doc_type: str = Form("notes"), current_user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    if doc_type not in ("notes", "resume", "job_description", "other"):
        raise HTTPException(status_code=400, detail="doc_type must be notes, resume, job_description or other.")
    if db.query(Document).filter(Document.user_id == current_user.id).count() >= svc.MAX_DOCS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Document limit reached ({svc.MAX_DOCS_PER_USER}). Delete one first.")
    path = validate_and_save_upload(file, subdir="rag", allowed=RAG_EXT)
    try:
        text = svc.read_any(path)
        doc = svc.index_document(db, current_user.id, file.filename or "document", text, doc_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read the document: {exc}") from exc
    finally:
        if os.path.exists(path):
            os.remove(path)  # the raw file is not needed once its text is indexed
    return _doc(doc)


@router.post("/documents/from-resume", status_code=201)
def index_resume(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Resume).filter(Resume.user_id == current_user.id, Resume.is_active == True).first()  # noqa: E712
    if not r:
        raise HTTPException(status_code=404, detail="Upload a resume first.")
    return _doc(svc.index_document(db, current_user.id, f"{r.original_filename} (v{r.version})", r.raw_text, "resume"))


@router.get("/documents")
def documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_doc(d) for d in db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc())]


@router.delete("/documents/{doc_id}", status_code=204)
def delete(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Document not found.")
    svc.delete_document(db, d)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    mode: str = Field(default="hybrid", pattern="^(semantic|lexical|hybrid)$")
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    document_ids: Optional[List[int]] = None


@router.post("/search")
def search(payload: SearchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return rsearch.search(db, current_user.id, payload.query, payload.mode, payload.top_k, payload.rerank, payload.document_ids)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)
    document_ids: Optional[List[int]] = None


@router.post("/chat")
def chat(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.answer(db, current_user.id, payload.question, payload.top_k, payload.document_ids)


@router.get("/chat/history")
def history(limit: int = Query(40, ge=1, le=200), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).order_by(ChatMessage.id.desc()).limit(limit).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "citations": json.loads(m.citations or "[]"),
             "simulated": m.simulated, "created_at": m.created_at} for m in reversed(rows)]


@router.delete("/chat/history", status_code=204)
def clear_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
