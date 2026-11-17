def test_start_hr_interview_generates_questions(client, auth_headers):
    resp = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["interview_type"] == "hr"
    assert len(data["questions"]) == 3


def test_start_interview_invalid_type_rejected(client, auth_headers):
    resp = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "bogus", "num_questions": 3})
    assert resp.status_code == 400


def test_submit_answer_and_complete_interview_flow(client, auth_headers):
    start_resp = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 2})
    interview_id = start_resp.json()["interview_id"]
    questions = start_resp.json()["questions"]

    for q in questions:
        answer_resp = client.post(
            f"/interviews/{interview_id}/answer",
            headers=auth_headers,
            json={"question_id": q["id"], "answer_text": "This is a detailed technical answer explaining the concept with an example.", "input_mode": "text"},
        )
        assert answer_resp.status_code == 200
        assert "score" in answer_resp.json()["evaluation"]

    complete_resp = client.post(f"/interviews/{interview_id}/complete", headers=auth_headers)
    assert complete_resp.status_code == 200
    body = complete_resp.json()
    assert body["overall_score"] >= 0
    assert isinstance(body["recommended_topics"], list)


def test_cannot_answer_same_question_twice(client, auth_headers):
    start_resp = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 1})
    interview_id = start_resp.json()["interview_id"]
    q_id = start_resp.json()["questions"][0]["id"]

    r1 = client.post(f"/interviews/{interview_id}/answer", headers=auth_headers,
                      json={"question_id": q_id, "answer_text": "First answer.", "input_mode": "text"})
    assert r1.status_code == 200

    r2 = client.post(f"/interviews/{interview_id}/answer", headers=auth_headers,
                      json={"question_id": q_id, "answer_text": "Second answer.", "input_mode": "text"})
    assert r2.status_code == 400


def test_interview_history_lists_past_interviews(client, auth_headers):
    client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 1})
    resp = client.get("/interviews/history", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_empty_answer_is_handled_gracefully(client, auth_headers):
    start_resp = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 1})
    interview_id = start_resp.json()["interview_id"]
    q_id = start_resp.json()["questions"][0]["id"]

    resp = client.post(f"/interviews/{interview_id}/answer", headers=auth_headers,
                        json={"question_id": q_id, "answer_text": "", "input_mode": "text"})
    assert resp.status_code == 200
    assert resp.json()["evaluation"]["score"] == 0.0


def test_ending_with_no_answers_does_not_pollute_analytics(client, auth_headers):
    """An abandoned round must not record a 0 score that drags down averages."""
    s = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 2}).json()
    done = client.post(f"/interviews/{s['interview_id']}/complete", headers=auth_headers)
    assert done.status_code == 200
    assert "not scored" in done.json()["ai_feedback"]
    perf = client.get("/performance", headers=auth_headers).json()
    assert perf["score_trend"] == [] and perf["technical_score"] == 0.0
