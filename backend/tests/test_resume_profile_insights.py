import io
import json
import time

import pytest
from docx import Document

RESUME = """Asha Verma
asha.verma@example.com | +91 98765 43210 | github.com/ashav | linkedin.com/in/asha-verma

SUMMARY
Final-year CSE student aiming for backend roles.

EDUCATION
B.Tech in Computer Science, Sample Institute of Technology, 2026, CGPA: 8.4/10

SKILLS
Languages: Python, Java, C++, SQL
Frameworks: FastAPI, React, Spring Boot
Tools: Docker, Git, PostgreSQL, AWS

PROJECTS
Placement Portal
- Built a REST API with FastAPI and PostgreSQL serving 2,000 users
- Reduced query latency by 35% using indexes
Chatbot using RAG
- Developed a retrieval augmented generation chatbot with LLMs and pgvector

EXPERIENCE
Software Intern, Acme Corp
- Implemented unit tests with pytest, increasing coverage to 80%

CERTIFICATIONS
AWS Certified Cloud Practitioner
"""
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx(text):
    d = Document()
    for line in text.split("\n"):
        d.add_paragraph(line)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def _upload(client, h, text=RESUME, name="resume.docx", label=""):
    r = client.post(f"/resume/upload?label={label}", headers=h, files={"file": (name, _docx(text), DOCX_MIME)})
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- resume intelligence
def test_resume_analysis_extracts_sections_contacts_and_scores(client, auth_headers):
    r = _upload(client, auth_headers)
    a = r["analysis"]
    assert {"education", "skills", "projects", "experience", "certifications", "summary"} <= set(a["sections_found"])
    assert a["contacts"]["email"] == "asha.verma@example.com" and "github" in a["contacts"] and "linkedin" in a["contacts"]
    assert a["education_details"]["cgpa"] == 8.4 and a["education_details"]["graduation_year"] == 2026
    assert {"Python", "FastAPI", "PostgreSQL", "Docker", "RAG", "LLMs"} <= set(r["keywords"])
    assert 0 < r["ats_score"] <= 100 and 0 < r["quality_score"] <= 100
    assert all({"check", "weight", "passed", "detail"} <= set(c) for c in a["ats"]["checks"])
    assert sum(c["weight"] for c in a["ats"]["checks"]) == 100


def test_poor_resume_scores_lower_and_gets_suggestions(client, auth_headers):
    good = _upload(client, auth_headers)
    poor = _upload(client, auth_headers, "John\nI like computers and I am hardworking and I want a job.\nSkills: Python")
    assert poor["ats_score"] < good["ats_score"] and poor["quality_score"] < good["quality_score"]
    assert len(poor["analysis"]["suggestions"]) >= 4


def test_scores_are_deterministic(client, auth_headers):
    a, b = _upload(client, auth_headers), _upload(client, auth_headers)
    assert (a["ats_score"], a["quality_score"]) == (b["ats_score"], b["quality_score"])


def test_versions_activate_and_delete(client, auth_headers):
    v1 = _upload(client, auth_headers, label="first")
    v2 = _upload(client, auth_headers, label="second")
    assert v2["version"] == v1["version"] + 1 and v2["is_active"]
    versions = client.get("/resume/versions", headers=auth_headers).json()
    assert [v["is_active"] for v in versions].count(True) == 1
    assert client.post(f"/resume/{v1['id']}/activate", headers=auth_headers).json()["is_active"] is True
    assert client.get("/resume", headers=auth_headers).json()["id"] == v1["id"]
    assert client.delete(f"/resume/{v1['id']}", headers=auth_headers).status_code == 204
    assert client.get("/resume", headers=auth_headers).json()["id"] == v2["id"]   # falls back to newest


def test_resume_of_another_user_is_not_accessible(client, auth_headers):
    r = _upload(client, auth_headers)
    other = client.post("/auth/register", json={"name": "O", "email": f"o{time.time_ns()}@x.com", "password": "StrongPass1"}).json()
    h2 = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/resume/{r['id']}", headers=h2).status_code == 404
    assert client.delete(f"/resume/{r['id']}", headers=h2).status_code == 404


def test_pdf_resume_is_parsed():
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas
    from app.services import resume_service as rs
    import tempfile, os
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in RESUME.splitlines():
        c.drawString(40, y, line[:100])
        y -= 14
    c.save()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(buf.getvalue())
    try:
        out = rs.analyze_resume(rs.extract_text(f.name))
        assert "Python" in json.loads(out["keywords"]) and out["ats_score"] > 0
    finally:
        os.remove(f.name)


def test_unreadable_resume_is_rejected(client, auth_headers):
    r = client.post("/resume/upload", headers=auth_headers, files={"file": ("empty.docx", _docx(""), DOCX_MIME)})
    assert r.status_code == 400 and "readable text" in r.json()["detail"]
    bad = client.post("/resume/upload", headers=auth_headers, files={"file": ("x.pdf", b"nope", "application/pdf")})
    assert bad.status_code == 400


# --------------------------------------------------------------------------- JD matching
def test_jd_match_scores_matched_and_missing_skills(client, auth_headers):
    _upload(client, auth_headers)
    jd = "Backend engineer: Python, FastAPI, PostgreSQL, Docker, Kafka and Kubernetes experience required."
    m = client.post("/resume/match", headers=auth_headers, json={"jd_text": jd, "jd_title": "Backend"}).json()
    assert {"Python", "FastAPI", "PostgreSQL", "Docker"} <= set(m["matched_skills"])
    assert "Kubernetes" in m["missing_skills"] and 40 < m["match_score"] < 95
    assert any("Kubernetes" in s for s in m["suggestions"])
    worse = client.post("/resume/match", headers=auth_headers, json={"jd_text": "Needs Rust, Go, Kafka, Terraform, Swift and Scala."}).json()
    assert worse["match_score"] < m["match_score"]
    assert len(client.get("/resume/matches", headers=auth_headers).json()) >= 2
    assert client.post("/resume/match", headers=auth_headers, json={"jd_text": "short"}).status_code == 400


# --------------------------------------------------------------------------- profile
def test_full_profile_roundtrip_with_proficiency_and_lists(client, auth_headers):
    body = {"college": "Sample University", "degree": "B.Tech", "branch": "CSE", "graduation_year": 2026, "cgpa": 8.4,
            "github_url": "https://github.com/x", "linkedin_url": "https://linkedin.com/in/x", "leetcode_url": "https://leetcode.com/x",
            "career_objective": "Backend engineer", "preferred_companies": ["Amazon", "TCS"], "target_roles": ["Backend Developer"],
            "skills": [{"name": "python", "proficiency": "advanced"}, "java"],
            "projects": [{"title": "Portal", "description": "d", "technologies": "FastAPI", "github_url": "https://github.com/x/p"}],
            "certifications": [{"name": "AWS CCP", "issuer": "AWS", "year": 2025}],
            "internships": [{"company": "Acme", "role": "Intern", "start_date": "2025-05", "end_date": "2025-07", "description": "APIs"}]}
    assert client.put("/users/me/profile", headers=auth_headers, json=body).status_code == 200
    p = client.get("/users/me", headers=auth_headers).json()["profile"]
    assert p["cgpa"] == 8.4 and p["preferred_companies"] == ["Amazon", "TCS"]
    assert {"name": "Python", "proficiency": "advanced"} in p["skills"] and {"name": "Java", "proficiency": "intermediate"} in p["skills"]
    assert p["projects"][0]["github_url"].endswith("/x/p") and p["certifications"][0]["year"] == 2025 and p["internships"][0]["company"] == "Acme"


def test_profile_validation(client, auth_headers):
    assert client.put("/users/me/profile", headers=auth_headers, json={"cgpa": 14}).status_code == 422
    assert client.put("/users/me/profile", headers=auth_headers, json={"skills": [{"name": "x", "proficiency": "god"}]}).status_code == 422


def test_autofill_from_resume_fills_empty_fields_but_keeps_user_values(client, auth_headers):
    client.put("/users/me/profile", headers=auth_headers, json={"college": "My Own College"})
    _upload(client, auth_headers)
    r = client.post("/users/me/profile/autofill", headers=auth_headers, json={}).json()
    p = r["profile"]
    assert p["college"] == "My Own College"                         # user value kept
    assert p["cgpa"] == 8.4 and p["graduation_year"] == 2026 and p["github_url"].endswith("github.com/ashav")
    assert "Python" in {s["name"] for s in p["skills"]} and any(x["title"] == "Placement Portal" for x in p["projects"])
    again = client.post("/users/me/profile/autofill", headers=auth_headers, json={}).json()
    assert again["added_skills"] == [] and again["added_projects"] == []   # idempotent


def test_photo_upload_validates_and_serves_image(client, auth_headers):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 30, 30)).save(buf, "PNG")
    assert client.post("/users/me/photo", headers=auth_headers, files={"file": ("me.png", buf.getvalue(), "image/png")}).status_code == 200
    got = client.get("/users/me/photo", headers=auth_headers)
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    assert max(Image.open(io.BytesIO(got.content)).size) <= 512
    assert client.post("/users/me/photo", headers=auth_headers, files={"file": ("x.png", b"not an image", "image/png")}).status_code == 400
    assert client.delete("/users/me/photo", headers=auth_headers).status_code == 204
    assert client.get("/users/me/photo", headers=auth_headers).status_code == 404


def test_readiness_uses_only_available_data(client, auth_headers):
    empty = client.get("/users/me/readiness", headers=auth_headers).json()
    assert set(empty["not_yet_measured"]) == {"resume", "interviews", "coding"} and empty["score"] == 0
    _upload(client, auth_headers)
    client.post("/users/me/profile/autofill", headers=auth_headers, json={})
    r = client.get("/users/me/readiness", headers=auth_headers).json()
    assert "resume" in r["components"] and r["score"] > 0 and "resume" not in r["not_yet_measured"]


# --------------------------------------------------------------------------- skill gap / roadmap / analytics / companies
def test_skill_gap_reflects_resume_and_measured_performance(client, auth_headers):
    base = client.get("/skill-gap?role=Backend Developer", headers=auth_headers).json()
    assert base["role"] == "Backend Developer" and base["summary"]["missing"] > 5 and base["has_resume"] is False
    _upload(client, auth_headers)
    g = {i["skill"]: i for i in client.get("/skill-gap?role=Backend Developer", headers=auth_headers).json()["gaps"]}
    assert g["Python"]["state"] == "unverified" and g["Python"]["current"] > 0
    assert g["Kubernetes"]["state"] if "Kubernetes" in g else True
    # a strong measured SQL interview answer turns SQL from unverified/missing into measured evidence
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 1, "topic": "sql"}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers, json={"question_id": s["questions"][0]["id"], "answer_text": "idk"})
    after = {i["skill"]: i for i in client.get("/skill-gap?role=Backend Developer", headers=auth_headers).json()["gaps"]}
    assert after["SQL"]["state"] == "weak" and any("Interview 'sql'" in e for e in after["SQL"]["evidence"])


def test_unknown_role_falls_back_and_roles_listed(client, auth_headers):
    assert "GenAI Engineer" in client.get("/skill-gap/roles", headers=auth_headers).json()["roles"]
    assert client.get("/skill-gap?role=Astronaut", headers=auth_headers).json()["role"] == "Software Developer"


def test_roadmap_generation_progress_and_refresh(client, auth_headers):
    assert client.get("/roadmap", headers=auth_headers).status_code == 404
    rm = client.post("/roadmap", headers=auth_headers, json={"weeks": 2, "hours_per_day": 2, "role": "Backend Developer"}).json()
    assert rm["weeks"] == 2 and len(rm["weekly_targets"]) == 2 and rm["progress"]["total"] > 10
    kinds = {t["task_type"] for t in rm["tasks"]}
    assert {"study", "practice", "revision", "mock"} <= kinds
    assert all(0 < t["est_minutes"] <= 120 for t in rm["tasks"])
    first_study = next(t for t in rm["tasks"] if t["task_type"] == "study")
    revs = [t for t in rm["tasks"] if t["task_type"] == "revision" and t["topic"] == first_study["topic"]]
    assert revs and all(t["due_date"] > first_study["due_date"] for t in revs)           # revision always follows study
    done = client.patch(f"/roadmap/tasks/{first_study['id']}", headers=auth_headers, json={"status": "done"}).json()
    assert done["progress"]["done"] == 1 and done["progress"]["percent"] > 0
    ref = client.post("/roadmap/refresh", headers=auth_headers).json()
    assert ref["changes"]["added"] >= 0 and ref["roadmap"]["progress"]["done"] == 1      # completed work is preserved
    assert client.patch(f"/roadmap/tasks/{first_study['id']}", headers=auth_headers, json={"status": "bogus"}).status_code == 422


def test_new_roadmap_archives_the_old_one_and_tasks_are_private(client, auth_headers):
    a = client.post("/roadmap", headers=auth_headers, json={"weeks": 1}).json()
    b = client.post("/roadmap", headers=auth_headers, json={"weeks": 1}).json()
    assert client.get("/roadmap", headers=auth_headers).json()["id"] == b["id"] != a["id"]
    other = client.post("/auth/register", json={"name": "O", "email": f"o{time.time_ns()}@x.com", "password": "StrongPass1"}).json()
    h2 = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.patch(f"/roadmap/tasks/{b['tasks'][0]['id']}", headers=h2, json={"status": "done"}).status_code == 404


def test_analytics_empty_state_then_real_numbers(client):
    r = client.post("/auth/register", json={"name": "N", "email": f"n{time.time_ns()}@x.com", "password": "StrongPass1"}).json()
    h = {"Authorization": f"Bearer {r['access_token']}"}
    empty = client.get("/analytics/me", headers=h).json()
    assert empty["has_data"] is False and empty["trend"] == [] and empty["topics"] == [] and empty["overview"]["streak"]["current"] == 0
    s = client.post("/interviews/start", headers=h, json={"interview_type": "technical", "num_questions": 1, "topic": "java"}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=h, json={"question_id": s["questions"][0]["id"], "answer_text": "idk"})
    client.post(f"/interviews/{s['interview_id']}/complete", headers=h)
    a = client.get("/analytics/me", headers=h).json()
    assert a["has_data"] and a["overview"]["interviews_completed"] == 1 and a["topics"][0]["topic"] == "java"
    assert a["overview"]["streak"]["current"] == 1 and len(a["rubric"]) == 6 and a["activity"][0]["count"] >= 1
    assert a["interview_by_type"]["technical"] == a["overview"]["avg_interview_score"]


def test_company_guides_are_general_and_carry_verification_note(client, auth_headers):
    lst = client.get("/companies", headers=auth_headers).json()
    assert {c["slug"] for c in lst} == {"microsoft", "google", "amazon", "accenture", "infosys", "tcs", "deloitte"}
    g = client.get("/companies/amazon", headers=auth_headers).json()
    assert "verify" in g and "official" in g["verify"].lower() and g["readiness"] is None and g["not_attempted"]
    blob = json.dumps({k: v for k, v in g.items() if k != "verify"}).lower()
    for banned in ("cut-off", "cutoff", "exactly", "guaranteed", "asked in"):
        assert banned not in blob
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 1, "topic": "dsa"}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers, json={"question_id": s["questions"][0]["id"], "answer_text": "idk"})
    g2 = client.get("/companies/amazon", headers=auth_headers).json()
    assert g2["readiness"] is not None and "dsa" in g2["weakest"]
    assert client.get("/companies/nowhere", headers=auth_headers).status_code == 404
