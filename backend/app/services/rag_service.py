import os
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai import usage
from app.ai.factory import get_ai_provider
from app.models.rag import Document, DocumentChunk, ChatMessage
from app.rag import search as rsearch
from app.rag.chunker import chunk_text
from app.rag.embeddings import get_embedder
from app.services import resume_service as rs
import json

MAX_DOCS_PER_USER = 25


def read_any(path: str) -> str:
    low = path.lower()
    if low.endswith((".txt", ".md")):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return rs.extract_text(path)


def index_document(db: Session, user_id: int, filename: str, text: str, doc_type: str = "notes") -> Document:
    chunks_text = chunk_text(text)
    if not chunks_text:
        raise ValueError("No readable text found in the document.")
    emb = get_embedder()
    doc = Document(user_id=user_id, filename=filename, doc_type=doc_type, char_count=len(text),
                   chunk_count=len(chunks_text), embedding_provider=emb.name)
    db.add(doc)
    db.flush()
    rows = [DocumentChunk(document_id=doc.id, user_id=user_id, chunk_index=i, content=c) for i, c in enumerate(chunks_text)]
    db.add_all(rows)
    db.flush()
    rsearch.store_embeddings(db, rows, emb.embed(chunks_text))
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, doc: Document) -> None:
    db.delete(doc)
    db.commit()


def answer(db: Session, user_id: int, question: str, top_k: int, doc_ids: Optional[List[int]]) -> dict:
    res = rsearch.search(db, user_id, question, "hybrid", top_k, True, doc_ids)
    provider = get_ai_provider()
    passages = res["results"]
    if not passages:
        out = {"answer": "I could not find anything relevant in your uploaded documents. Upload notes, a resume or a job "
                         "description first.", "simulated": provider.simulated}
    else:
        out = provider.rag_answer(question, passages)
    citations = [{"n": i, "document_id": p["document_id"], "filename": p["filename"], "chunk_index": p["chunk_index"],
                  "snippet": p["content"][:280], "score": p["score"], "rerank_score": p["rerank_score"], "methods": p["methods"]}
                 for i, p in enumerate(passages, start=1)]
    db.add(ChatMessage(user_id=user_id, role="user", content=question))
    db.add(ChatMessage(user_id=user_id, role="assistant", content=out["answer"], citations=json.dumps(citations),
                       simulated=bool(out.get("simulated", True))))
    usage.persist(db, user_id)
    db.commit()
    return {"answer": out["answer"], "citations": citations, "simulated": bool(out.get("simulated", True)),
            "retrieval": {k: res[k] for k in ("mode", "reranker", "embedding", "semantic", "vector_store")}}
