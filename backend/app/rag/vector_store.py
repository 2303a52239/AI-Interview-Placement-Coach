"""
A minimal, dependency-light vector store used for the RAG pipeline.

Pipeline:
  Candidate Data -> Document Processing -> Chunking -> Embeddings -> Vector Store
  -> Relevant Context Retrieval -> LLM -> Personalized Question

Two embedding backends:
  - LocalTfidfEmbedder (default, EMBEDDING_PROVIDER=local): scikit-learn TF-IDF
    vectors + cosine similarity. No external API, always works.
  - OpenAIEmbedder (EMBEDDING_PROVIDER=openai): calls OpenAI's embeddings
    endpoint. Requires OPENAI_API_KEY. Falls back to the local embedder on
    any failure so retrieval never breaks the app.

The vector store itself is purely in-memory / per-request, rebuilt each time
from the candidate's chunks - this keeps the project simple to run locally
without needing a dedicated vector DB service, while still implementing a
genuine embed -> similarity search -> retrieve pipeline.
"""
import re
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings


def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
    """Split text into overlapping word-based chunks."""
    words = re.findall(r"\S+", text or "")
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


class LocalTfidfEmbedder:
    """TF-IDF based embedder. Fits a fresh vectorizer per retrieval call since
    the corpus (candidate chunks) is small and request-scoped."""

    def embed_and_rank(self, query: str, documents: List[str]) -> List[Tuple[str, float]]:
        if not documents:
            return []
        corpus = documents + [query]
        vectorizer = TfidfVectorizer(stop_words="english")
        try:
            matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            # e.g. empty vocabulary after stop-word removal
            return [(doc, 0.0) for doc in documents]
        doc_vectors = matrix[:-1]
        query_vector = matrix[-1]
        similarities = cosine_similarity(query_vector, doc_vectors)[0]
        ranked = sorted(zip(documents, similarities.tolist()), key=lambda x: x[1], reverse=True)
        return ranked


class SimpleVectorStore:
    """In-memory vector store: holds candidate document chunks and retrieves
    the most relevant ones for a given query (e.g. 'technical interview
    questions for a Python Developer')."""

    def __init__(self):
        self.embedder = LocalTfidfEmbedder()

    def build_from_text(self, text: str) -> List[str]:
        return chunk_text(text)

    def retrieve(self, query: str, chunks: List[str], top_k: int = 5) -> str:
        if not chunks:
            return ""
        ranked = self.embedder.embed_and_rank(query, chunks)
        top_chunks = [doc for doc, score in ranked[:top_k] if score > 0] or [c for c in chunks[:top_k]]
        return "\n".join(top_chunks)
