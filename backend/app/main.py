import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - ensures all models are registered on Base.metadata
from app.routers import auth, users, resume, interviews, coding, performance, admin, evaluate, insights, rag

from app.utils.logging_config import configure_logging
from app.utils.rate_limit import RateLimitMiddleware

configure_logging()
logger = logging.getLogger("app.main")

app = FastAPI(
    title="AI Interview Intelligence & Placement Coach API",
    description="Backend API powering personalized HR/technical mock interviews, "
                "coding assessments, AI evaluation, analytics and preparation planning.",
    version="2.0.0",
)

# Middleware added last is outermost. CORS must wrap the rate limiter so a 429 still carries CORS
# headers; otherwise the browser reports a network error instead of "too many requests".
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
        from app.database import SessionLocal
        from app.services.bank_service import seed_question_bank
        from app.services.coding_import import load_problem_pack
        with SessionLocal() as db:
            seed_question_bank(db)
            load_problem_pack(db)  # classic problem pack; idempotent by title
    except OperationalError as exc:
        logger.error(
            "Could not connect to the database at startup. Please verify DATABASE_URL "
            "in your .env file and that PostgreSQL is running. Error: %s", exc,
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request data.", "errors": exc.errors()},
    )


@app.exception_handler(OperationalError)
async def db_exception_handler(request: Request, exc: OperationalError):
    logger.error("Database error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is currently unavailable. Please check your PostgreSQL connection and try again."},
    )


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "AI Interview Intelligence & Placement Coach API is running.",
        "docs": "/docs",
        "ai_provider": settings.AI_PROVIDER,
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": app.version}


@app.get("/ai/status", tags=["Health"])
def ai_mode():
    """Tells the UI honestly whether a live LLM or the rule-based mock is answering."""
    from app.ai.factory import ai_status
    return ai_status()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(resume.router)
app.include_router(interviews.router)
app.include_router(coding.router)
app.include_router(performance.router)
app.include_router(admin.router)
app.include_router(evaluate.router)
app.include_router(insights.router)
app.include_router(rag.router)
