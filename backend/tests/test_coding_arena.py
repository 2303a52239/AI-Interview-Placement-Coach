import json
import time

import pytest

from app.coding import complexity
from app.coding.executor import run_submission, build_docker_command
from app.config import settings
from app.database import SessionLocal
from app.models.coding import CodingQuestion

PY_SUM = "a, b = map(int, input().split())\nprint(a + b)\n"
JAVA_SUM = "import java.util.*;\npublic class Main { public static void main(String[] a){ Scanner s=new Scanner(System.in); System.out.println(s.nextInt()+s.nextInt()); } }\n"
CPP_SUM = "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<std::endl;}\n"


@pytest.fixture(scope="module")
def hidden_question_id():
    with SessionLocal() as db:
        q = CodingQuestion(
            title="Sum with hidden tests", problem_statement="Print a+b.", sample_input="3 5", sample_output="8",
            difficulty="easy", topic_tag="basics", company_tags=json.dumps(["acmecorp"]),
            test_cases=json.dumps([
                {"input": "3 5", "expected_output": "8"},
                {"input": "100 200", "expected_output": "300", "hidden": True},
                {"input": "-5 -6", "expected_output": "-11", "hidden": True}]))
        db.add(q)
        db.commit()
        return q.id


@pytest.mark.parametrize("lang,src", [("python", PY_SUM), ("java", JAVA_SUM), ("cpp", CPP_SUM)])
def test_all_three_languages_run_and_pass(lang, src):
    r = run_submission(lang, src, [{"input": "3 5", "expected_output": "8"}], time_limit=5)
    assert r.status == "passed" and r.passed_count == 1


def test_compile_error_and_timeout_and_wrong_answer_statuses():
    assert run_submission("cpp", "int main(){ return 1 }", [{"input": "", "expected_output": ""}]).status == "compiled_error"
    assert run_submission("python", "while True: pass", [{"input": "", "expected_output": "x"}], time_limit=1).status == "timeout"
    assert run_submission("python", "print(1)", [{"input": "", "expected_output": "2"}]).status == "failed"
    assert run_submission("python", "raise SystemExit(3)", [{"input": "", "expected_output": ""}]).cases[0].status == "runtime_error"


def test_unsupported_language_rejected_by_api(client, auth_headers, hidden_question_id):
    r = client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": "x", "language": "ruby"})
    assert r.status_code == 422


def test_hidden_tests_count_but_are_not_revealed(client, auth_headers, hidden_question_id):
    r = client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": PY_SUM, "language": "python"}).json()
    assert r["status"] == "passed" and r["total_test_cases"] == 3 and r["hidden_total"] == 2 and r["hidden_passed"] == 2
    hidden = [c for c in r["test_case_results"] if c["hidden"]]
    assert len(hidden) == 2 and all(c["input"] == "" and c["expected_output"] == "" and c["actual_output"] == "" for c in hidden)
    q = client.get(f"/coding/questions/{hidden_question_id}", headers=auth_headers).json()
    assert q["hidden_tests"] == 2 and "300" not in json.dumps(q)


def test_hard_coded_sample_fails_hidden_tests(client, auth_headers, hidden_question_id):
    r = client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": "print(8)", "language": "python"}).json()
    assert r["passed_test_cases"] == 1 and r["hidden_passed"] == 0 and r["score"] < 40


def test_run_does_not_create_a_submission(client, auth_headers, hidden_question_id):
    before = client.get("/coding/submissions", headers=auth_headers).json()["total"]
    r = client.post("/coding/run", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": PY_SUM, "language": "python"}).json()
    assert r["passed"] is True
    assert client.get("/coding/submissions", headers=auth_headers).json()["total"] == before


def test_submission_history_is_paginated_and_private(client, auth_headers, hidden_question_id):
    for _ in range(3):
        client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": PY_SUM, "language": "python"})
    page = client.get("/coding/submissions?page_size=2", headers=auth_headers).json()
    assert len(page["items"]) == 2 and page["total"] >= 3 and page["pages"] >= 2
    sid = page["items"][0]["id"]
    detail = client.get(f"/coding/submissions/{sid}", headers=auth_headers).json()
    assert detail["source_code"] == PY_SUM
    other = client.post("/auth/register", json={"name": "O", "email": f"o{time.time_ns()}@example.com", "password": "StrongPass1"}).json()
    assert client.get(f"/coding/submissions/{sid}", headers={"Authorization": f"Bearer {other['access_token']}"}).status_code == 404


def test_complexity_estimates():
    assert "n^2" in complexity.analyze("python", "for i in a:\n    for j in a:\n        pass\n")["time"]
    assert "2^n" in complexity.analyze("java", "static int f(int n){ if(n<2) return n; return f(n-1)+f(n-2); }")["time"]
    assert "n log n" in complexity.analyze("cpp", "sort(v.begin(), v.end());")["time"]
    assert complexity.analyze("python", "print(1)")["time"].startswith("O(1)")


def test_timed_assessment_flow_and_server_side_deadline(client, auth_headers, hidden_question_id):
    a = client.post("/coding/assessments", headers=auth_headers, json={"num_questions": 1, "duration_minutes": 5, "company": "acmecorp"}).json()
    assert a["status"] == "in_progress" and 0 < a["remaining_seconds"] <= 300 and a["questions"][0]["id"] == hidden_question_id
    ok = client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": PY_SUM, "language": "python", "assessment_id": a["id"]})
    assert ok.status_code == 200
    done = client.post(f"/coding/assessments/{a['id']}/finish", headers=auth_headers).json()
    assert done["status"] == "completed" and done["score"] == 100.0
    late = client.post("/coding/submit", headers=auth_headers, json={"question_id": hidden_question_id, "source_code": PY_SUM, "language": "python", "assessment_id": a["id"]})
    assert late.status_code == 400


def test_assessment_expires_after_deadline(client, auth_headers, hidden_question_id):
    import datetime as dt
    from app.models.coding import CodingAssessment
    a = client.post("/coding/assessments", headers=auth_headers, json={"num_questions": 1, "duration_minutes": 5}).json()
    with SessionLocal() as db:
        row = db.query(CodingAssessment).get(a["id"])
        row.deadline = dt.datetime.utcnow() - dt.timedelta(seconds=1)
        db.commit()
    r = client.post("/coding/submit", headers=auth_headers, json={"question_id": a["questions"][0]["id"], "source_code": PY_SUM, "language": "python", "assessment_id": a["id"]})
    assert r.status_code == 400
    assert client.get(f"/coding/assessments/{a['id']}", headers=auth_headers).json()["status"] == "expired"


def test_docker_command_applies_isolation_flags():
    cmd = " ".join(build_docker_command("/tmp/w", "n"))
    for flag in ["--network none", "--read-only", "--cap-drop ALL", "no-new-privileges", "--pids-limit", "--memory ", "--cpus", "--user 65534:65534"]:
        assert flag in cmd


@pytest.mark.skipif(not __import__("shutil").which("docker") or __import__("subprocess").run(["docker", "image", "inspect", "placement-sandbox:latest"], capture_output=True).returncode != 0,
                    reason="Docker daemon or sandbox image not available")
def test_docker_backend_isolation(monkeypatch):
    monkeypatch.setattr(settings, "EXECUTION_BACKEND", "docker")
    ok = run_submission("python", PY_SUM, [{"input": "3 5", "expected_output": "8"}], time_limit=5)
    assert ok.status == "passed" and ok.sandbox == "docker"
    net = run_submission("python", "import socket\ns=socket.socket();s.settimeout(2)\ntry:\n s.connect(('1.1.1.1',80));print('NET')\nexcept Exception:\n print('blocked')\n",
                         [{"input": "", "expected_output": "blocked"}], time_limit=5)
    assert net.status == "passed"            # network is unreachable inside the sandbox
    ro = run_submission("python", "open('/etc/x','w')", [{"input": "", "expected_output": ""}], time_limit=5)
    assert ro.cases[0].status == "runtime_error"  # read-only root filesystem
    assert run_submission("python", "while True: pass", [{"input": "", "expected_output": ""}], time_limit=2).status == "timeout"
