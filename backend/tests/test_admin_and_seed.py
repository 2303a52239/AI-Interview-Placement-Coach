import json
import subprocess
import sys
import time

import pytest

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password
from scripts.seed_extra import PROBLEMS, seed_extra


def _login(client, email, password):
    return {"Authorization": "Bearer " + client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]}


@pytest.fixture()
def staff(client):
    with SessionLocal() as db:
        for email, role, admin in [("adm@t.com", "admin", 1), ("off@t.com", "placement_officer", 0)]:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(name=role, email=email, hashed_password=hash_password("Passw0rd!1"), role=role, is_admin=admin))
        db.commit()
        seed_extra(db)
    return {"admin": _login(client, "adm@t.com", "Passw0rd!1"), "officer": _login(client, "off@t.com", "Passw0rd!1")}


@pytest.mark.parametrize("problem", PROBLEMS, ids=[p["title"] for p in PROBLEMS])
def test_every_seeded_problem_passes_its_own_reference_solution(problem):
    """Guards against wrong expected outputs in the bank (including hidden tests)."""
    for t in problem["tests"]:
        r = subprocess.run([sys.executable, "-c", problem["ref"]], input=t["input"], capture_output=True, text=True, timeout=10)
        assert r.stdout.strip() == t["expected_output"], (problem["title"], t)


def test_rbac_matrix(client, staff, auth_headers):
    assert client.get("/admin/students", headers=auth_headers).status_code == 403                      # student
    assert client.get("/admin/students", headers=staff["officer"]).status_code == 200                  # officer reads
    assert client.get("/admin/analytics", headers=staff["officer"]).status_code == 200
    assert client.post("/admin/interview-bank", headers=staff["officer"], json={}).status_code == 403   # officer cannot write
    assert client.delete("/admin/coding-questions/1", headers=staff["officer"]).status_code == 403
    assert client.get("/admin/students").status_code == 401


def test_students_list_filters_and_pagination(client, staff, auth_headers):
    client.put("/users/me/profile", headers=auth_headers, json={"branch": "Computer Science", "graduation_year": 2026, "cgpa": 8.1})
    page = client.get("/admin/students?page_size=1", headers=staff["officer"]).json()
    assert page["page_size"] == 1 and len(page["items"]) == 1 and page["total"] >= 1
    f = client.get("/admin/students?branch=computer science&graduation_year=2026", headers=staff["admin"]).json()
    assert f["total"] >= 1 and all(r["branch"].lower() == "computer science" for r in f["items"])
    uid = f["items"][0]["user_id"]
    d = client.get(f"/admin/students/{uid}", headers=staff["admin"]).json()
    assert "readiness" in d and "profile" in d


def test_interview_bank_crud_and_validation(client, staff):
    body = {"interview_type": "technical", "topic": "python", "difficulty": "easy", "question": "What does the yield keyword do in Python?",
            "ideal_answer": "yield turns a function into a generator.", "key_points": [{"label": "generator", "terms": ["generator"]}]}
    assert client.post("/admin/interview-bank", headers=staff["admin"], json={**body, "topic": "cobol"}).status_code == 400
    created = client.post("/admin/interview-bank", headers=staff["admin"], json=body)
    assert created.status_code == 201 and created.json()["source"] == "admin"
    iid = created.json()["id"]
    upd = client.put(f"/admin/interview-bank/{iid}", headers=staff["admin"], json={**body, "difficulty": "hard"}).json()
    assert upd["difficulty"] == "hard"
    lst = client.get("/admin/interview-bank?topic=python&page_size=100", headers=staff["officer"]).json()
    assert any(i["id"] == iid for i in lst["items"])
    assert client.delete(f"/admin/interview-bank/{iid}", headers=staff["admin"]).status_code == 204


def test_coding_question_admin_roundtrip_with_hidden_tests(client, staff, auth_headers):
    body = {"title": f"Admin Q {time.time_ns()}", "problem_statement": "Print the input.", "sample_input": "x", "sample_output": "x",
            "test_cases": [{"input": "a", "expected_output": "a"}, {"input": "b", "expected_output": "b", "hidden": True}],
            "time_limit_seconds": 3, "company_tags": ["tcs"]}
    r = client.post("/admin/coding-questions", headers=staff["admin"], json=body)
    assert r.status_code == 201
    q = client.get(f"/coding/questions/{r.json()['id']}", headers=auth_headers).json()
    assert q["hidden_tests"] == 1 and q["visible_tests"] == 1 and q["time_limit_seconds"] == 3 and q["company_tags"] == ["tcs"]


def test_job_description_crud_autoextracts_skills_and_student_can_match(client, staff, auth_headers):
    jd = client.post("/admin/job-descriptions", headers=staff["admin"], json={
        "title": "Data Engineer", "company": "Acme", "description": "Looking for strong SQL, Python and Docker skills plus Kubernetes."}).json()
    assert {"SQL", "Python", "Docker", "Kubernetes"} <= set(jd["required_skills"])
    assert any(j["id"] == jd["id"] for j in client.get("/resume/job-descriptions", headers=auth_headers).json())
    assert client.delete(f"/admin/job-descriptions/{jd['id']}", headers=staff["admin"]).status_code == 204


def test_user_role_management(client, staff):
    with SessionLocal() as db:
        target = User(name="T", email=f"t{time.time_ns()}@x.com", hashed_password=hash_password("Passw0rd!1"), role="student")
        db.add(target)
        db.commit()
        tid = target.id
    assert client.patch(f"/admin/users/{tid}", headers=staff["admin"], json={"role": "placement_officer"}).json()["role"] == "placement_officer"
    assert client.patch(f"/admin/users/{tid}", headers=staff["admin"], json={"is_active": False}).json()["is_active"] is False
    assert client.patch(f"/admin/users/{tid}", headers=staff["officer"], json={"role": "admin"}).status_code == 403
    me = client.get("/users/me", headers=staff["admin"]).json()["id"]
    assert client.patch(f"/admin/users/{me}", headers=staff["admin"], json={"is_active": False}).status_code == 400


def test_deactivated_user_cannot_login(client):
    with SessionLocal() as db:
        u = User(name="D", email="deact@x.com", hashed_password=hash_password("Passw0rd!1"), role="student", is_active=False)
        db.add(u)
        db.commit()
    assert client.post("/auth/login", json={"email": "deact@x.com", "password": "Passw0rd!1"}).status_code == 401


def test_institution_analytics_and_csv(client, staff, auth_headers):
    a = client.get("/admin/analytics", headers=staff["officer"]).json()
    assert a["totals"]["students"] >= 1 and "ai" in a and a["ai"]["mode"] in ("mock", "openai")
    csv_resp = client.get("/admin/reports/institution?format=csv", headers=staff["officer"])
    assert csv_resp.headers["content-type"].startswith("text/csv") and csv_resp.text.splitlines()[0].startswith("name,email")
    assert "readiness_score" in csv_resp.text.splitlines()[0]


def test_assessments_overview(client, staff):
    assert "items" in client.get("/admin/assessments?kind=interview", headers=staff["officer"]).json()
    assert "items" in client.get("/admin/assessments?kind=coding", headers=staff["officer"]).json()
