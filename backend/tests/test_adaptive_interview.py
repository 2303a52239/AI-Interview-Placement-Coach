def _start(client, h, **body):
    r = client.post("/interviews/start", headers=h, json=body)
    assert r.status_code == 200, r.text
    return r.json()


STRONG = ("It relies on hashing and buckets; collisions are handled by chaining, for example linked lists or trees, "
          "because that keeps lookups fast. The load factor triggers resize and rehash. Equals and hashCode are used. "
          "Mutable versus immutable, abstract class versus interface, indexes, B-tree, ACID, isolation, atomic, normalization.")


def test_bank_is_seeded_for_all_topics(client, auth_headers):
    for topic in ["python", "java", "sql", "dsa", "dbms", "os", "cn", "ml", "dl", "nlp", "genai", "llm", "rag", "system_design"]:
        s = _start(client, auth_headers, interview_type="technical", num_questions=1, topic=topic)
        assert s["questions"][0]["skill_tag"] == topic


def test_unknown_topic_rejected(client, auth_headers):
    r = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 1, "topic": "cobol"})
    assert r.status_code == 400


def test_adaptive_starts_with_one_question_and_serves_the_rest_after_answers(client, auth_headers):
    s = _start(client, auth_headers, interview_type="technical", num_questions=3, topic="sql", adaptive=True)
    assert s["adaptive"] is True and len(s["questions"]) == 1
    qid, main, follow = s["questions"][0]["id"], 0, 0
    while qid and main + follow < 8:
        r = client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers,
                        json={"question_id": qid, "answer_text": STRONG}).json()
        assert "rubric" in r["evaluation"] and r["evaluation"]["simulated"] is True
        nxt = r["next_question"]
        # the question just answered counts as a follow-up only if the previous step produced one
        main += 1
        qid = nxt["id"] if nxt else None
        if nxt and nxt["is_followup"]:
            follow += 1
            main -= 0
    total_answered = main
    detail = client.get(f"/interviews/{s['interview_id']}", headers=auth_headers).json()
    mains = [q for q in detail["questions"] if not q["is_followup"] and q["answer_text"]]
    assert len(mains) == 3                      # the target number of main questions was reached
    assert total_answered - len(mains) <= 2     # follow-ups are capped at two


def test_difficulty_ladder_rises_after_strong_answers_and_falls_after_weak():
    from app.services.adaptive_engine import next_difficulty
    assert next_difficulty("easy", 90) == "medium"
    assert next_difficulty("medium", 90) == "hard"
    assert next_difficulty("hard", 95) == "hard"
    assert next_difficulty("medium", 30) == "easy"
    assert next_difficulty("easy", 10) == "easy"
    assert next_difficulty("medium", 60) == "medium"


def test_api_reports_current_difficulty_and_scores_weak_answer_low(client, auth_headers):
    s = _start(client, auth_headers, interview_type="technical", num_questions=3, topic="python", adaptive=True)
    r = client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers,
                    json={"question_id": s["questions"][0]["id"], "answer_text": "idk"}).json()
    assert r["evaluation"]["score"] < 40 and r["current_difficulty"] == "easy"


def test_weak_answer_triggers_followup_on_missing_point(client, auth_headers):
    s = _start(client, auth_headers, interview_type="technical", num_questions=3, topic="os", adaptive=True)
    r = client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers,
                    json={"question_id": s["questions"][0]["id"], "answer_text": "It is a thing in computers."}).json()
    assert r["next_question"]["is_followup"] is True
    assert "did not mention" in r["next_question"]["question_text"]


def test_voice_answer_returns_speech_metrics(client, auth_headers):
    s = _start(client, auth_headers, interview_type="hr", num_questions=1, voice_mode=True)
    text = "Um I basically led the backend and, you know, I built an API because I like ownership for example."
    r = client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers,
                    json={"question_id": s["questions"][0]["id"], "answer_text": text, "input_mode": "voice",
                          "duration_seconds": 8, "pauses": [0.4, 2.1, 1.8, 2.5]}).json()
    sp = r["evaluation"]["speech"]
    assert sp["wpm"] and sp["filler_total"] >= 3 and sp["long_pauses"] == 3 and sp["feedback"]


def test_detail_includes_rubric_and_ideal_answer(client, auth_headers):
    s = _start(client, auth_headers, interview_type="technical", num_questions=1, topic="java")
    client.post(f"/interviews/{s['interview_id']}/answer", headers=auth_headers,
                json={"question_id": s["questions"][0]["id"], "answer_text": STRONG})
    client.post(f"/interviews/{s['interview_id']}/complete", headers=auth_headers)
    d = client.get(f"/interviews/{s['interview_id']}", headers=auth_headers).json()
    q = d["questions"][0]
    assert q["ideal_answer"] and len(q["rubric"]) == 6 and d["simulated"] is True


def test_history_personalises_start_difficulty(client, auth_headers):
    # a weak history on a topic keeps the next interview on that topic easy; a strong one raises it
    from app.services.adaptive_engine import start_difficulty
    assert start_difficulty({}, "sql") == "easy"
    assert start_difficulty({"sql": {"avg": 90, "attempts": 3}}, "sql") == "hard"
    assert start_difficulty({"sql": {"avg": 30, "attempts": 3}}, "sql") == "easy"


def test_speech_analyze_endpoint_and_capabilities(client, auth_headers):
    r = client.post("/speech/analyze", headers=auth_headers, json={
        "transcript": "so um I think like it works by hashing keys", "duration_seconds": 6, "pauses": [0.3, 2.0]}).json()
    assert r["words"] == 10 and r["wpm"] == 100.0 and r["filler_total"] == 2 and r["long_pauses"] == 1
    assert any("slower" in f for f in r["feedback"])
    no_time = client.post("/speech/analyze", headers=auth_headers, json={"transcript": "hello there"}).json()
    assert no_time["wpm"] is None
    assert client.get("/speech/capabilities", headers=auth_headers).json()["server_side_audio"] is False
