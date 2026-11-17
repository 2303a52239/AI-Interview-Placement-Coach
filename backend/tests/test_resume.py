import io
from docx import Document


def _make_docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def test_resume_upload_extracts_skills(client, auth_headers):
    resume_text = (
        "John Doe\nEDUCATION\nB.Tech Computer Science\n\n"
        "SKILLS\nPython, Java, React, SQL\n\n"
        "PROJECTS\nBuilt a Library Management System using Java and MySQL.\n"
        "Built a portfolio website using React and CSS.\n\n"
        "EXPERIENCE\nInterned as a backend developer using Python and FastAPI.\n"
    )
    docx_bytes = _make_docx_bytes(resume_text)

    resp = client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 201
    data = resp.json()
    all_skills = [s.lower() for s in data["extracted_skills"] + data["extracted_technologies"]]
    assert "python" in all_skills
    assert "java" in all_skills


def test_resume_upload_rejects_invalid_file_type(client, auth_headers):
    resp = client.post(
        "/resume/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code == 400


def test_get_resume_without_upload_returns_404(client):
    reg = client.post("/auth/register", json={"name": "NoResume", "email": "noresume@example.com", "password": "Password1"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    resp = client.get("/resume", headers=headers)
    assert resp.status_code == 404

