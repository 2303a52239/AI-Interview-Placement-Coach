"""Embedding providers.

* "hashing" (default): signed feature-hashing of word unigrams+bigrams into EMBEDDING_DIM dimensions, L2-normalised.
  Needs no download and works offline, but it is LEXICAL: it matches shared words/phrases, not meaning.
* "sentence-transformers": real semantic embeddings (default model all-MiniLM-L6-v2, 384-d). Requires
  `pip install sentence-transformers` and a one-time model download; selected with EMBEDDING_PROVIDER.

`embedder_info()` reports which one is active so the UI never overstates what the search does."""
import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import List

from app.config import settings

logger = logging.getLogger("rag.embeddings")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")
_STOP = set("a an the and or of to in on for with is are was were be it this that as at by from".split())


class HashingEmbedder:
    name = "hashing"
    semantic = False

    def __init__(self, dim: int):
        self.dim = dim

    def _feats(self, text: str) -> List[str]:
        toks = [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]
        return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for text in texts:
            v = [0.0] * self.dim
            for f in self._feats(text):
                h = int(hashlib.md5(f.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
            v = [math.copysign(math.log1p(abs(x)), x) for x in v]
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class SentenceTransformerEmbedder:
    name = "sentence-transformers"
    semantic = True

    def __init__(self, model_name: str, dim: int, model=None):
        if model is None:
            from sentence_transformers import SentenceTransformer  # lazy: heavy optional dependency
            model = SentenceTransformer(model_name)
        self.model = model
        self.dim = dim
        self.model_name = model_name

    def embed(self, texts: List[str]) -> List[List[float]]:
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        out = [list(map(float, v)) for v in vecs]
        if out and len(out[0]) != self.dim:
            raise RuntimeError(f"Embedding model returned {len(out[0])} dims but EMBEDDING_DIM={self.dim}; fix the setting or the model.")
        return out


@lru_cache
def get_embedder():
    if settings.EMBEDDING_PROVIDER.lower() == "sentence-transformers":
        try:
            return SentenceTransformerEmbedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)
        except Exception as exc:  # noqa: BLE001
            logger.error("sentence-transformers unavailable (%s); falling back to hashing embeddings.", exc)
    return HashingEmbedder(settings.EMBEDDING_DIM)


def embedder_info() -> dict:
    e = get_embedder()
    return {"provider": e.name, "semantic": e.semantic, "dim": settings.EMBEDDING_DIM,
            "model": getattr(e, "model_name", None),
            "note": None if e.semantic else "Hashing embeddings match shared words and phrases, not meaning. "
                                            "Set EMBEDDING_PROVIDER=sentence-transformers for semantic search."}
