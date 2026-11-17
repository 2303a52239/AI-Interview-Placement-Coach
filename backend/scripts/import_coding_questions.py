"""Import coding problems from a JSON file into the database.

    python -m scripts.import_coding_questions problems.json

Format and rules: see app/services/coding_import.py. Existing titles are skipped. Only import problem sets you wrote
or are licensed to use; this tool does not fetch anything from the internet.
"""
import json
import sys

from app.database import SessionLocal
from app.services.coding_import import import_questions

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    with SessionLocal() as db:
        res = import_questions(db, data if isinstance(data, list) else [data])
    print(f"added {res['added']}, skipped {res['skipped_existing']}, errors {len(res['errors'])}")
    for e in res["errors"]:
        print("  ERROR", e["item"], "-", e["error"])
