def _complete_one_interview(client, headers, interview_type="hr"):
    start_resp = client.post("/interviews/start", headers=headers, json={"interview_type": interview_type, "num_questions": 1})
    interview_id = start_resp.json()["interview_id"]
    q_id = start_resp.json()["questions"][0]["id"]
    client.post(f"/interviews/{interview_id}/answer", headers=headers,
                json={"question_id": q_id, "answer_text": "A solid, detailed, relevant answer with an example.", "input_mode": "text"})
    client.post(f"/interviews/{interview_id}/complete", headers=headers)


def test_performance_summary_before_any_activity(client):
    reg = client.post("/auth/register", json={"name": "Fresh", "email": "fresh@example.com", "password": "Password1"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    resp = client.get("/performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_interviews"] == 0
    assert data["overall_readiness"] == 0.0


def test_performance_summary_reflects_completed_interview(client, auth_headers):
    _complete_one_interview(client, auth_headers, "hr")
    resp = client.get("/performance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_interviews"] >= 1
    assert len(data["score_trend"]) >= 1


def test_preparation_plan_generates_items(client, auth_headers):
    _complete_one_interview(client, auth_headers, "technical")
    resp = client.get("/preparation-plan", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["priority"] in ("high", "medium", "low")


def test_preparation_plan_regenerate(client, auth_headers):
    resp = client.post("/preparation-plan/regenerate", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()
