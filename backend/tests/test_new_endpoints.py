SUM_OK = """import java.util.Scanner;
public class Solution { public static void main(String[] a) { Scanner s = new Scanner(System.in);
  System.out.println(s.nextInt() + s.nextInt()); } }"""


def test_evaluate_scores_a_good_answer_higher_than_empty(client, auth_headers):
    good = client.post("/evaluate", headers=auth_headers, json={
        "interview_type": "technical", "question": "Explain how HashMap works internally in Java.",
        "answer": "A HashMap hashes the key to pick a bucket, for example using hashCode, and handles collisions "
                  "with linked lists or trees because buckets can hold several entries."})
    empty = client.post("/evaluate", headers=auth_headers, json={
        "interview_type": "technical", "question": "Explain how HashMap works internally in Java.", "answer": ""})
    assert good.status_code == 200 and empty.status_code == 200
    assert good.json()["score"] > empty.json()["score"] == 0.0
    assert set(good.json()) == {"score", "strengths", "weaknesses", "feedback", "suggested_improvement"}


def test_evaluate_rejects_bad_interview_type(client, auth_headers):
    r = client.post("/evaluate", headers=auth_headers, json={"interview_type": "x", "question": "q", "answer": "a"})
    assert r.status_code == 422


def test_evaluate_requires_auth(client):
    assert client.post("/evaluate", json={"interview_type": "hr", "question": "q", "answer": "a"}).status_code == 401


def test_transcribe_without_api_key_returns_clear_503(client, auth_headers):
    r = client.post("/speech/transcribe", headers=auth_headers, files={"file": ("a.webm", b"1234", "audio/webm")})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


def test_transcribe_rejects_non_audio(client, auth_headers):
    r = client.post("/speech/transcribe", headers=auth_headers, files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def _qid(client, headers):
    return next(q["id"] for q in client.get("/coding/questions", headers=headers).json() if q["title"] == "Sum of Two Numbers")


def test_run_uses_sample_only_and_saves_nothing(client, auth_headers):
    qid = _qid(client, auth_headers)
    r = client.post("/coding/run", headers=auth_headers, json={"question_id": qid, "source_code": SUM_OK})
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is True and body["actual_output"].strip() == "8"
    perf = client.get("/performance", headers=auth_headers).json()
    assert perf["total_coding_attempts"] == 0


def test_run_reports_compile_error(client, auth_headers):
    qid = _qid(client, auth_headers)
    r = client.post("/coding/run", headers=auth_headers, json={"question_id": qid, "source_code": "public class Solution { int x = ; }"})
    assert r.json()["status"] == "compiled_error"


def test_history_includes_difficulty_and_strengths(client, auth_headers):
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 1}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers, json={
        "question_id": s["questions"][0]["id"], "answer_text": "Detailed answer, for example with because reasoning and structure."})
    client.post(f"/interviews/{s['interview_id']}/complete", headers=auth_headers)
    item = client.get("/interviews/history", headers=auth_headers).json()[0]
    assert item["difficulty"] in {"easy", "medium", "hard", "mixed"}
    assert isinstance(item["strengths"], list) and isinstance(item["weaknesses"], list)


def test_performance_has_topics_and_progress(client, auth_headers):
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 1}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers, json={
        "question_id": s["questions"][0]["id"], "answer_text": "ok"})
    client.post(f"/interviews/{s['interview_id']}/complete", headers=auth_headers)
    perf = client.get("/performance", headers=auth_headers).json()
    assert perf["topic_scores"] and "recommended_topics" in perf
    assert 0 <= perf["preparation_progress"] <= 100


def test_plan_has_seven_day_schedule(client, auth_headers):
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 1}).json()
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers, json={
        "question_id": s["questions"][0]["id"], "answer_text": "short"})
    client.post(f"/interviews/{s['interview_id']}/complete", headers=auth_headers)
    plan = client.post("/preparation-plan/regenerate", headers=auth_headers).json()
    assert [d["day"] for d in plan["weekly_schedule"]][0] == "Monday"
    assert len(plan["weekly_schedule"]) == 7


def test_admin_endpoints_forbidden_for_students(client, auth_headers):
    assert client.get("/admin/candidates", headers=auth_headers).status_code == 403
