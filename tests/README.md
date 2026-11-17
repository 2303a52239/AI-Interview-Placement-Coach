# Tests

| Suite | Location | Run from | Command |
|---|---|---|---|
| Backend API tests (38) | `backend/tests/` | `backend` | `python -m pytest tests/ -v` |
| Browser smoke test (36 checks) | `tests/ui_smoke_test.py` | project root | `python tests\ui_smoke_test.py` |

**Backend tests** use a throwaway SQLite file by default. To run them on PostgreSQL instead:

```powershell
createdb interview_coach_test    # or create it in pgAdmin
$env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/interview_coach_test"
python -m pytest tests/ -v
```

**Browser smoke test** needs the backend (seeded) and frontend both running, then:

```powershell
pip install playwright
python -m playwright install chromium
python tests\ui_smoke_test.py --screenshots tests\screenshots
```

It signs in as the demo and admin users, completes interviews and submits code, so re-run
`python -m scripts.seed` on a fresh database afterwards if you want a clean demo state.
