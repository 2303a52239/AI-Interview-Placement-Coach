"""Vector, lexical (BM25) and hybrid retrieval with reciprocal rank fusion and reranking."""
import json
import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.rag import DocumentChunk, Document
from app.rag.embeddings import get_embedder

logger = logging.getLogger("rag.search")
_TOK = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
STOP = set("a an the and or of to in on for with is are was were be it this that as at by from what how why do does can you i".split())


def tokenize(t: str) -> List[str]:
    return [w for w in _TOK.findall((t or "").lower()) if w not in STOP]


def has_pgvector(db: Session) -> bool:
    """True when running on PostgreSQL and the indexed `embedding_vec` column exists."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    key = id(bind)
    if key not in _PG_CACHE:
        row = db.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='document_chunks' "
                              "AND column_name='embedding_vec'")).first()
        _PG_CACHE[key] = bool(row)
    return _PG_CACHE[key]


_PG_CACHE: Dict[int, bool] = {}


def _vec_literal(v: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def store_embeddings(db: Session, chunks: List[DocumentChunk], vectors: List[List[float]]) -> None:
    pg = has_pgvector(db)
    for ch, vec in zip(chunks, vectors):
        ch.embedding = json.dumps([round(x, 6) for x in vec])
    db.flush()
    if pg:
        for ch, vec in zip(chunks, vectors):
            db.execute(text("UPDATE document_chunks SET embedding_vec = CAST(:v AS vector) WHERE id = :i"),
                       {"v": _vec_literal(vec), "i": ch.id})


def _cos(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # vectors are L2-normalised


def _scope(db: Session, user_id: int, doc_ids: Optional[List[int]]):
    q = db.query(DocumentChunk).filter(DocumentChunk.user_id == user_id)
    if doc_ids:
        q = q.filter(DocumentChunk.document_id.in_(doc_ids))
    return q


def vector_search(db: Session, user_id: int, query: str, k: int, doc_ids: Optional[List[int]] = None) -> List[Dict]:
    qv = get_embedder().embed([query])[0]
    if has_pgvector(db):
        sql = ("SELECT id, 1 - (embedding_vec <=> CAST(:q AS vector)) AS sim FROM document_chunks "
               "WHERE user_id = :u AND embedding_vec IS NOT NULL" + (" AND document_id = ANY(:d)" if doc_ids else "") +
               " ORDER BY embedding_vec <=> CAST(:q AS vector) LIMIT :k")
        params = {"q": _vec_literal(qv), "u": user_id, "k": k}
        if doc_ids:
            params["d"] = doc_ids
        rows = db.execute(text(sql), params).all()
        return [{"chunk_id": r[0], "score": float(r[1]), "method": "vector(pgvector)"} for r in rows]
    scored = []
    for ch in _scope(db, user_id, doc_ids).all():
        if ch.embedding:
            scored.append({"chunk_id": ch.id, "score": _cos(qv, json.loads(ch.embedding)), "method": "vector(python)"})
    scored.sort(key=lambda x: -x["score"])
    return scored[:k]


def bm25_search(db: Session, user_id: int, query: str, k: int, doc_ids: Optional[List[int]] = None) -> List[Dict]:
    chunks = _scope(db, user_id, doc_ids).all()
    if not chunks:
        return []
    docs = [(c.id, tokenize(c.content)) for c in chunks]
    n = len(docs)
    avgdl = sum(len(t) for _, t in docs) / n or 1.0
    df: Counter = Counter()
    for _, toks in docs:
        df.update(set(toks))
    q_terms = tokenize(query)
    k1, b = 1.5, 0.75
    scored = []
    for cid, toks in docs:
        tf = Counter(toks)
        s = 0.0
        for t in q_terms:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(toks) / avgdl))
        if s > 0:
            scored.append({"chunk_id": cid, "score": s, "method": "bm25"})
    scored.sort(key=lambda x: -x["score"])
    return scored[:k]


def rrf(lists: List[List[Dict]], k: int, c: int = 60) -> List[Dict]:
    fused: Dict[int, Dict] = {}
    for lst in lists:
        for rank, item in enumerate(lst, start=1):
            e = fused.setdefault(item["chunk_id"], {"chunk_id": item["chunk_id"], "score": 0.0, "methods": [], "parts": {}})
            e["score"] += 1.0 / (c + rank)
            e["methods"].append(item["method"])
            e["parts"][item["method"]] = round(item["score"], 4)
    return sorted(fused.values(), key=lambda x: -x["score"])[:k]


def lexical_rerank(query: str, candidates: List[Dict], contents: Dict[int, str]) -> List[Dict]:
    """Cheap reranker: query-term coverage + exact phrase / bigram hits + the fused retrieval score."""
    q = tokenize(query)
    qset = set(q)
    bigrams = {f"{a} {b}" for a, b in zip(q, q[1:])}
    out = []
    for c in candidates:
        text_l = contents[c["chunk_id"]].lower()
        toks = set(tokenize(text_l))
        coverage = len(qset & toks) / len(qset) if qset else 0
        phrase = sum(1 for bg in bigrams if bg in text_l) / len(bigrams) if bigrams else 0
        out.append({**c, "rerank_score": round(0.6 * coverage + 0.3 * phrase + 0.1 * min(1.0, c["score"] * 30), 4)})
    return sorted(out, key=lambda x: -x["rerank_score"])


_CE = {}


def cross_encoder_rerank(query: str, candidates: List[Dict], contents: Dict[int, str]) -> List[Dict]:
    from sentence_transformers import CrossEncoder  # lazy / optional
    if "m" not in _CE:
        _CE["m"] = CrossEncoder(settings.RERANK_MODEL)
    scores = _CE["m"].predict([(query, contents[c["chunk_id"]]) for c in candidates])
    out = [{**c, "rerank_score": round(float(s), 4)} for c, s in zip(candidates, scores)]
    return sorted(out, key=lambda x: -x["rerank_score"])


def search(db: Session, user_id: int, query: str, mode: str = "hybrid", top_k: int = 5, rerank: bool = True,
           doc_ids: Optional[List[int]] = None) -> Dict:
    pool = max(top_k * 4, 20)
    if mode == "semantic":
        cands = rrf([vector_search(db, user_id, query, pool, doc_ids)], pool)
    elif mode == "lexical":
        cands = rrf([bm25_search(db, user_id, query, pool, doc_ids)], pool)
    else:
        cands = rrf([vector_search(db, user_id, query, pool, doc_ids), bm25_search(db, user_id, query, pool, doc_ids)], pool)
    reranker = "none"
    if cands:
        rows = db.query(DocumentChunk, Document.filename).join(Document, Document.id == DocumentChunk.document_id) \
            .filter(DocumentChunk.id.in_([c["chunk_id"] for c in cands])).all()
        info = {ch.id: (ch, fn) for ch, fn in rows}
        contents = {i: v[0].content for i, v in info.items()}
        if rerank:
            if settings.RERANK_PROVIDER.lower() == "cross-encoder":
                try:
                    cands, reranker = cross_encoder_rerank(query, cands, contents), "cross-encoder"
                except Exception as exc:  # noqa: BLE001
                    logger.error("cross-encoder unavailable (%s); using lexical reranker.", exc)
                    cands, reranker = lexical_rerank(query, cands, contents), "lexical"
            else:
                cands, reranker = lexical_rerank(query, cands, contents), "lexical"
        results = []
        for c in cands[:top_k]:
            ch, fn = info[c["chunk_id"]]
            results.append({"chunk_id": ch.id, "document_id": ch.document_id, "filename": fn, "chunk_index": ch.chunk_index,
                            "content": ch.content, "score": round(c["score"], 5), "rerank_score": c.get("rerank_score"),
                            "methods": sorted(set(c["methods"])), "parts": c["parts"]})
    else:
        results = []
    emb = get_embedder()
    return {"results": results, "mode": mode, "reranker": reranker, "embedding": emb.name, "semantic": emb.semantic,
            "vector_store": "pgvector" if has_pgvector(db) else "in-process (JSON vectors)"}
