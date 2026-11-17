import json
import os

from tests.test_admin_and_seed import staff  # noqa: F401  (fixture)
from app.services.coding_import import PACK_PATH, import_questions, load_problem_pack
from app.database import SessionLocal
from app.models.coding import CodingQuestion


def _pack():
    with open(os.path.normpath(PACK_PATH), encoding="utf-8") as f:
        return json.load(f)


def test_pack_is_large_and_well_formed():
    pack = _pack()
    assert len(pack) >= 45
    titles = [p["title"].lower() for p in pack]
    assert len(titles) == len(set(titles))
    for p in pack:
        assert p["difficulty"] in {"easy", "medium", "hard"}
        assert any(t["hidden"] for t in p["tests"]) and any(not t["hidden"] for t in p["tests"]), p["title"]
        assert p["sample_input"] == p["tests"][0]["input"] and p["sample_output"] == p["tests"][0]["expected_output"]
        assert all(t["expected_output"] != "" for t in p["tests"]), p["title"]


def test_pack_loads_once_and_is_idempotent():
    with SessionLocal() as db:
        first = load_problem_pack(db)
        second = load_problem_pack(db)
        assert second["added"] == 0 and second["skipped_existing"] >= len(_pack())
        assert db.query(CodingQuestion).count() >= len(_pack())
    assert first["errors"] == []


def test_import_validates_and_skips_duplicates():
    with SessionLocal() as db:
        good = {"title": "Import Test Problem", "problem_statement": "Print 1.", "difficulty": "easy", "tests": [{"input": "", "expected_output": "1"}]}
        res = import_questions(db, [good, good, {"title": "x"}, {"title": "Bad diff", "problem_statement": "p", "difficulty": "legendary", "tests": [{"expected_output": "1"}]}, "nope"])
        assert res["added"] == 1 and res["skipped_existing"] == 1 and len(res["errors"]) == 3
        row = db.query(CodingQuestion).filter(CodingQuestion.title == "Import Test Problem").one()
        assert json.loads(row.test_cases)[0]["hidden"] is False


def test_import_endpoint_requires_admin(client, auth_headers, staff):
    admin_headers = staff["admin"]
    body = [{"title": "Endpoint Import", "problem_statement": "Print 2.", "tests": [{"input": "", "expected_output": "2", "hidden": True}]}]
    assert client.post("/admin/coding-questions/import", headers=auth_headers, json=body).status_code in (401, 403)
    r = client.post("/admin/coding-questions/import", headers=admin_headers, json=body)
    assert r.status_code == 200 and r.json()["added"] == 1
    assert client.post("/admin/coding-questions/import", headers=admin_headers, json=body).json()["skipped_existing"] == 1


def test_pack_problem_is_solvable_end_to_end(client, auth_headers):
    with SessionLocal() as db:
        load_problem_pack(db)
        q = db.query(CodingQuestion).filter(CodingQuestion.title == "Two Sum Indices").one()
        qid = q.id
    code = "n=int(input());a=list(map(int,input().split()));t=int(input())\nseen={}\nfor j,x in enumerate(a):\n    if t-x in seen:\n        print(seen[t-x],j);break\n    seen.setdefault(x,j)\n"
    r = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": code, "language": "python"})
    assert r.status_code == 200 and r.json()["status"] == "passed", r.text


def test_interview_question_count_is_user_selectable(client, auth_headers):
    for n in (1, 15, 30):
        r = client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": n})
        assert r.status_code == 200, r.text
        assert r.json()["target_questions"] == n
        assert len(r.json()["questions"]) == n
    assert client.post("/interviews/start", headers=auth_headers, json={"interview_type": "hr", "num_questions": 31}).status_code == 400
    assert client.post("/interviews/start", headers=auth_headers, json={"interview_type": "technical", "num_questions": 0}).status_code == 400
