"""Bulk import of coding problems.

Used by the admin UI (POST /admin/coding-questions/import), the CLI (scripts/import_coding_questions.py) and the
built-in problem pack that is loaded at startup. Importing is idempotent by title: a problem whose title already
exists is skipped, never overwritten.

Item format (JSON list):
  {"title", "problem_statement", "difficulty": easy|medium|hard, "topic_tag",
   "input_format"?, "output_format"?, "constraints"?, "sample_input"?, "sample_output"?,
   "company_tags"?: [..], "starter_codes"?: {"python","java","cpp"}, "time_limit_seconds"?,
   "tests": [{"input", "expected_output", "hidden"?: bool}, ...]}
"""
import json
import os
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.coding import CodingQuestion

DIFFICULTIES = {"easy", "medium", "hard"}
MAX_ITEMS = 2000
PACK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "problem_pack.json")


def _validate(item: Any) -> str:
    """Returns an error message, or '' when the item is valid."""
    if not isinstance(item, dict):
        return "not an object"
    for f in ("title", "problem_statement"):
        if not isinstance(item.get(f), str) or not item[f].strip():
            return f"missing {f}"
    if len(item["title"]) > 255:
        return "title longer than 255 characters"
    if item.get("difficulty", "easy") not in DIFFICULTIES:
        return "difficulty must be easy, medium or hard"
    tests = item.get("tests", item.get("test_cases"))
    if not isinstance(tests, list) or not tests:
        return "needs at least one test case"
    for i, t in enumerate(tests, 1):
        if not isinstance(t, dict) or not isinstance(t.get("input", ""), str) or not isinstance(t.get("expected_output"), str):
            return f"test {i} needs string 'input' and 'expected_output'"
    return ""


def import_questions(db: Session, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(items) > MAX_ITEMS:
        raise ValueError(f"At most {MAX_ITEMS} problems per import.")
    existing = {t.lower() for (t,) in db.query(CodingQuestion.title).all()}
    added, skipped, errors = 0, 0, []
    for idx, item in enumerate(items, 1):
        err = _validate(item)
        label = item.get("title", f"#{idx}") if isinstance(item, dict) else f"#{idx}"
        if err:
            errors.append({"item": label, "error": err})
            continue
        if item["title"].strip().lower() in existing:
            skipped += 1
            continue
        tests = [{"input": t.get("input", ""), "expected_output": t["expected_output"], "hidden": bool(t.get("hidden", False))}
                 for t in item.get("tests", item.get("test_cases"))]
        db.add(CodingQuestion(
            title=item["title"].strip(), problem_statement=item["problem_statement"],
            input_format=item.get("input_format", ""), output_format=item.get("output_format", ""),
            constraints=item.get("constraints", ""), sample_input=item.get("sample_input", tests[0]["input"]),
            sample_output=item.get("sample_output", tests[0]["expected_output"]),
            difficulty=item.get("difficulty", "easy"), topic_tag=item.get("topic_tag", "general"),
            starter_code=item.get("starter_code", ""), starter_codes=json.dumps(item.get("starter_codes", {})),
            time_limit_seconds=int(item.get("time_limit_seconds", 0) or 0),
            company_tags=json.dumps([str(c).lower() for c in item.get("company_tags", [])]),
            test_cases=json.dumps(tests)))
        existing.add(item["title"].strip().lower())
        added += 1
    db.commit()
    return {"added": added, "skipped_existing": skipped, "errors": errors}


def load_problem_pack(db: Session) -> Dict[str, Any]:
    """Loads the built-in pack (app/data/problem_pack.json). Safe to call on every start."""
    path = os.path.normpath(PACK_PATH)
    if not os.path.exists(path):
        return {"added": 0, "skipped_existing": 0, "errors": []}
    with open(path, encoding="utf-8") as f:
        return import_questions(db, json.load(f))
