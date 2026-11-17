import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force an isolated SQLite test database BEFORE importing app modules,
# so tests never touch the developer's real (Postgres/dev) database.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test.db")
os.environ["AI_PROVIDER"] = "mock"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["UPLOAD_DIR"] = "./test_uploads"
os.environ["CODE_EXEC_DIR"] = "./test_code_runs"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["EXECUTION_BACKEND"] = os.environ.get("EXECUTION_BACKEND", "local")

import uuid
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app import models  # noqa: F401
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    if engine.dialect.name == "postgresql":
        # build the schema through Alembic so tests exercise the real migrations (and the pgvector column)
        from sqlalchemy import text
        from alembic import command
        from alembic.config import Config
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        command.upgrade(cfg, "head")
    else:
        Base.metadata.create_all(bind=engine)
    _seed_minimal_coding_questions()
    from app.database import SessionLocal
    from app.services.bank_service import seed_question_bank
    with SessionLocal() as _db:
        seed_question_bank(_db)
    yield
    if engine.dialect.name != "postgresql":
        Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")


def _seed_minimal_coding_questions():
    """Seed a couple of coding questions directly so coding tests don't
    depend on the demo seed script."""
    import json
    from app.database import SessionLocal
    from app.models.coding import CodingQuestion

    db = SessionLocal()
    try:
        if db.query(CodingQuestion).count() > 0:
            return
        db.add(CodingQuestion(
            title="Sum of Two Numbers",
            problem_statement="Read two integers and print their sum.",
            input_format="Two space-separated integers.",
            output_format="Their sum.",
            constraints="-10^9 <= a,b <= 10^9",
            sample_input="3 5", sample_output="8",
            difficulty="easy", topic_tag="basics",
            starter_code="",
            test_cases=json.dumps([
                {"input": "3 5", "expected_output": "8"},
                {"input": "-2 7", "expected_output": "5"},
            ]),
        ))
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def registered_user(client):
    unique_email = f"test.user.{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/auth/register", json={
        "name": "Test User", "email": unique_email, "password": "TestPass123",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def auth_headers(registered_user):
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
