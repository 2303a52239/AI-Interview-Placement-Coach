import io

from app.rag.chunker import chunk_text
from app.rag.embeddings import HashingEmbedder, SentenceTransformerEmbedder, embedder_info
from app.rag import search as rsearch

DOC = """Kubernetes is a container orchestration platform. It schedules containers across a cluster of machines and restarts failed ones.

PostgreSQL supports the pgvector extension, which stores embeddings and answers nearest neighbour queries using cosine distance.

A B-tree index keeps keys sorted so range queries and ordering are fast. Hash indexes only help equality lookups.

The TCP three-way handshake uses SYN, SYN-ACK and ACK packets to establish a reliable connection between client and server.
"""


def _upload(client, headers, name="notes.txt", content=DOC, doc_type="notes"):
    return client.post("/rag/documents", headers=headers, data={"doc_type": doc_type},
                       files={"file": (name, io.BytesIO(content.encode()), "text/plain")})


def test_chunker_respects_size_and_overlap():
    text = " ".join(f"Sentence number {i} talks about topic {i % 5}." for i in range(120))
    chunks = chunk_text(text, chunk_words=60, overlap_words=10)
    assert len(chunks) > 3 and all(len(c.split()) <= 75 for c in chunks)
    assert set(chunks[0].split()[-4:]) & set(chunks[1].split()[:20])  # overlap carries context


def test_hashing_embedding_is_deterministic_normalised_and_reports_non_semantic():
    e = HashingEmbedder(384)
    a, b = e.embed(["tcp handshake syn ack"])[0], e.embed(["tcp handshake syn ack"])[0]
    assert a == b and abs(sum(x * x for x in a) - 1) < 1e-6 and len(a) == 384
    assert embedder_info()["semantic"] is False and "not meaning" in embedder_info()["note"]


def test_sentence_transformer_adapter_with_stub_model():
    class Stub:
        def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
            return [[1.0] + [0.0] * 383 for _ in texts]
    emb = SentenceTransformerEmbedder("stub", 384, model=Stub())
    assert len(emb.embed(["x"])[0]) == 384 and emb.semantic is True


def test_upload_search_and_citations(client, auth_headers):
    r = _upload(client, auth_headers)
    assert r.status_code == 201 and r.json()["chunk_count"] >= 1
    s = client.post("/rag/search", headers=auth_headers, json={"query": "pgvector cosine nearest neighbour", "mode": "hybrid", "top_k": 2}).json()
    assert s["results"] and "pgvector" in s["results"][0]["content"] and s["reranker"] == "lexical"
    assert set(s["results"][0]["methods"]) & {"bm25", "vector(python)", "vector(pgvector)"}
    chat = client.post("/rag/chat", headers=auth_headers, json={"question": "What does the TCP three-way handshake use?"}).json()
    assert "SYN" in chat["answer"] and "[1]" in chat["answer"]
    assert chat["citations"][0]["filename"] == "notes.txt" and chat["simulated"] is True
    assert chat["retrieval"]["semantic"] is False


def test_modes_lexical_semantic_and_isolation_between_users(client, auth_headers):
    _upload(client, auth_headers, "mine.txt", "Zebra crossing facts: zebras have stripes.")
    for mode in ("lexical", "semantic", "hybrid"):
        r = client.post("/rag/search", headers=auth_headers, json={"query": "zebra stripes", "mode": mode}).json()
        assert r["mode"] == mode and r["results"], mode
    other = client.post("/auth/register", json={"name": "O", "email": "rag.other@example.com", "password": "StrongPass1"}).json()
    h2 = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/rag/search", headers=h2, json={"query": "zebra stripes"}).json()["results"] == []


def test_answer_when_nothing_relevant_is_honest(client, auth_headers):
    other = client.post("/auth/register", json={"name": "E", "email": "rag.empty@example.com", "password": "StrongPass1"}).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}   # a user with no documents at all
    out = client.post("/rag/chat", headers=h, json={"question": "what is a bucket in hashmap"}).json()
    assert out["citations"] == [] and "could not find" in out["answer"].lower()


def test_rejects_bad_files(client, auth_headers):
    assert client.post("/rag/documents", headers=auth_headers, files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")}).status_code == 400
    assert client.post("/rag/documents", headers=auth_headers, files={"file": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}).status_code == 400
    assert client.post("/rag/documents", headers=auth_headers, files={"file": ("e.txt", io.BytesIO(b"   "), "text/plain")}).status_code == 400


def test_delete_document_removes_chunks(client, auth_headers):
    d = _upload(client, auth_headers, "tmp.txt", "Unique phrase flibbertigibbet appears here.").json()
    assert client.delete(f"/rag/documents/{d['id']}", headers=auth_headers).status_code == 204
    assert client.post("/rag/search", headers=auth_headers, json={"query": "flibbertigibbet"}).json()["results"] == []


def test_rrf_prefers_items_ranked_by_both_methods():
    a = [{"chunk_id": 1, "score": 1, "method": "vector"}, {"chunk_id": 2, "score": .5, "method": "vector"}]
    b = [{"chunk_id": 2, "score": 9, "method": "bm25"}, {"chunk_id": 3, "score": 1, "method": "bm25"}]
    assert rsearch.rrf([a, b], 3)[0]["chunk_id"] == 2


def test_uses_pgvector_when_running_on_postgres(client, auth_headers):
    import os
    _upload(client, auth_headers, "pg.txt", "pgvector stores embeddings for similarity search.")
    s = client.post("/rag/search", headers=auth_headers, json={"query": "similarity search embeddings", "mode": "semantic"}).json()
    on_pg = os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql")
    assert s["vector_store"] == ("pgvector" if on_pg else "in-process (JSON vectors)")
    if on_pg:
        assert any("vector(pgvector)" in r["methods"] for r in s["results"])
