"""
Centralized application configuration. Every value comes from environment
variables (see .env.example). Never hard-code secrets here.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "insecure-dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Environment ----
    ENVIRONMENT: str = "development"  # development | production
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # ---- Database ----
    DATABASE_URL: str = "sqlite:///./dev.db"

    # ---- Auth ----
    JWT_SECRET: str = INSECURE_DEFAULT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- AI provider ----
    AI_PROVIDER: str = "mock"  # mock | openai
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_SECONDS: float = 30.0
    OPENAI_MAX_RETRIES: int = 3

    # ---- RAG / embeddings ----
    # hashing -> offline fixed-size hashed TF-IDF vectors (default, no downloads)
    # sentence-transformers -> real semantic embeddings (needs `pip install sentence-transformers`
    #                          and a one-time model download from HuggingFace)
    EMBEDDING_PROVIDER: str = "hashing"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    # lexical -> BM25-style lexical reranker (default) | cross-encoder -> sentence-transformers CrossEncoder
    RERANK_PROVIDER: str = "lexical"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RAG_CHUNK_WORDS: int = 180
    RAG_CHUNK_OVERLAP: int = 30

    # ---- Uploads ----
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    MAX_PHOTO_SIZE_MB: int = 2

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- Rate limiting (in-memory, per client IP) ----
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 600
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20
    RATE_LIMIT_AI_PER_MINUTE: int = 60

    # ---- Code execution ----
    # docker -> every submission runs in a throw-away, network-less container (recommended)
    # local  -> subprocess on the API host. DEVELOPMENT ONLY; refused when ENVIRONMENT=production
    EXECUTION_BACKEND: str = "docker"
    SANDBOX_IMAGE: str = "placement-sandbox:latest"
    SANDBOX_MEMORY_MB: int = 256
    SANDBOX_CPUS: float = 1.0
    SANDBOX_PIDS_LIMIT: int = 128
    EXEC_TIMEOUT_SECONDS: int = 8
    EXEC_COMPILE_TIMEOUT_SECONDS: int = 20
    CODE_EXEC_DIR: str = "./code_runs"
    MAX_OUTPUT_CHARS: int = 20000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    # Backward-compatible alias used by the original code runner
    @property
    def JAVA_EXEC_TIMEOUT_SECONDS(self) -> int:  # noqa: N802
        return self.EXEC_TIMEOUT_SECONDS


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

if settings.is_production and settings.JWT_SECRET == INSECURE_DEFAULT_SECRET:
    raise RuntimeError("JWT_SECRET must be set to a long random value when ENVIRONMENT=production.")

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CODE_EXEC_DIR, exist_ok=True)
