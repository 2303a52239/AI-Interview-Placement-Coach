import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    doc_type = Column(String(30), default="notes")  # notes | resume | job_description | other
    char_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    embedding_provider = Column(String(60), default="")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Text chunk with its embedding. On PostgreSQL with pgvector an extra `embedding_vec vector(N)`
    column (created by the Alembic migration, not mapped here) is used for indexed similarity search;
    the JSON copy in `embedding` is the portable fallback (SQLite, or Postgres without pgvector)."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(Text, default="")  # JSON list[float]

    document = relationship("Document", back_populates="chunks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    citations = Column(Text, default="[]")  # JSON
    simulated = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    feature = Column(String(60), default="")
    provider = Column(String(30), default="")
    model = Column(String(80), default="")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
