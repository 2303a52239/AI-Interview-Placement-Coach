"""Sentence-aware text chunking with overlap (sizes in words, from settings)."""
import re
from typing import List

from app.config import settings


def chunk_text(text: str, chunk_words: int = 0, overlap_words: int = 0) -> List[str]:
    chunk_words = chunk_words or settings.RAG_CHUNK_WORDS
    overlap_words = overlap_words if overlap_words else settings.RAG_CHUNK_OVERLAP
    text = re.sub(r"[ \t]+", " ", text or "").strip()
    if not text:
        return []
    # split into sentences / lines first so chunks end on natural boundaries
    pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n{1,}", text) if p.strip()]
    chunks: List[str] = []
    cur: List[str] = []
    count = 0
    for piece in pieces:
        w = len(piece.split())
        if w > chunk_words:  # a single huge sentence: hard split
            words = piece.split()
            for i in range(0, len(words), chunk_words - overlap_words):
                chunks.append(" ".join(words[i:i + chunk_words]))
            continue
        if count + w > chunk_words and cur:
            chunks.append(" ".join(cur))
            tail: List[str] = []
            t = 0
            for s in reversed(cur):  # carry the last ~overlap words into the next chunk
                tw = len(s.split())
                if t + tw > overlap_words:
                    break
                tail.insert(0, s)
                t += tw
            cur, count = tail, t
        cur.append(piece)
        count += w
    if cur:
        chunks.append(" ".join(cur))
    # drop exact duplicates created by overlap handling on tiny inputs
    out: List[str] = []
    for c in chunks:
        if not out or c != out[-1]:
            out.append(c)
    return out
