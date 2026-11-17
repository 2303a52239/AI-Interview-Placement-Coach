# Advanced Edition guide

## 1. What is new

| Area | What you get |
|---|---|
| Profile | Photo, university/degree/branch/year/CGPA, skills with proficiency, projects (GitHub), internships, certifications, LinkedIn/LeetCode/portfolio, preferred companies, target roles, objective, resume management, readiness score, auto-fill from resume |
| Resume | PDF/DOCX parsing, skill/project/education extraction (dictionary + rules, not ML), ATS score with 8 weighted checks, 6 quality dimensions, JD matching, missing skills, suggestions, versions |
| Interviews | HR/Technical, topics Python, Java, SQL, DSA, DBMS, OS, CN, ML, DL, NLP, GenAI, LLMs, RAG, System Design; optional adaptive difficulty ladder, follow-ups, personalisation from history and resume |
| Evaluation | Rubric: correctness, understanding, relevance, completeness, communication, problem-solving; weighted score, strengths, weaknesses, missed points, ideal answer |
| Coding | Monaco editor, Python/Java/C++, visible and hidden tests, submission history, complexity estimate, timed assessments with server-side deadline, Docker isolation |
| Skill gap / roadmap | Evidence-weighted gaps per target role; daily/weekly roadmap with spaced revisions, task tracking, refresh from latest results |
| Study assistant | Upload PDF/DOCX/TXT/MD, chunking, embeddings, pgvector (PostgreSQL) or in-process cosine, semantic/keyword/hybrid search, reranking, cited answers |
| Voice | Browser speech-to-text and text-to-speech; words/min, filler words, long pauses with feedback |
| Analytics | Real aggregates from your attempts only; empty states instead of invented data |
| Companies | Microsoft, Google, Amazon, Accenture, Infosys, TCS, Deloitte: general preparation themes (no claimed real question patterns) compared with *your* scores |
| Admin | Students, assessments, interview bank, coding questions with hidden tests, job descriptions, cohort analytics, RBAC (student / placement_officer / admin), institutional CSV report |
| Platform | JWT access + refresh with rotation and reuse detection, rate limiting, pagination, upload validation (extension, size, magic bytes), structured logging, token-usage tracking |
| Frontend | Redesigned UI, dark/light theme, TypeScript for the new layer (`allowJs`), Tailwind with shadcn-style components, toasts and confirmation dialogs |

## 2. Install (Windows PowerShell)

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt        # or requirements.txt without the test tools
copy .env.example .env                      # then edit JWT_SECRET
# create the database once:  psql -U postgres -c "CREATE DATABASE interview_coach"
python -m alembic upgrade head
python -m scripts.seed                      # demo users and sample data
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

Demo account: `demo@student.com / Demo@1234`. The app is student-only: there is no admin panel and no staff accounts are seeded. Remove the demo account for a public deployment.

Question banks (interview and coding) are seeded automatically on startup and by `python -m scripts.seed`;
`python -m scripts.seed_extra` adds extra coding problems with hidden tests.

## 3. Configuration

All settings are in `backend/.env` (template: `backend/.env.example`; production template:
`backend/.env.production.example`). The frontend reads `VITE_API_URL` (`frontend/.env.example`).
Nothing in the repository contains a real secret. Keep `.env` out of version control.

Key switches:

* `AI_PROVIDER=mock|openai`. Mock is the default. The dashboard, interview feedback and `/ai/status` all say which mode is active.
* `EMBEDDING_PROVIDER=hashing|sentence-transformers` (the second needs `pip install -r requirements-ml.txt` and a one-time model download).
* `EXECUTION_BACKEND=docker|local`. `local` is for development on your own machine and is refused when `ENVIRONMENT=production`.
* `ENVIRONMENT=production` refuses the placeholder JWT secret.

### Running code in Docker (recommended)

```bash
docker build -t placement-sandbox:latest ./sandbox
# then in backend/.env:  EXECUTION_BACKEND=docker
```

Each submission runs in its own container with `--network none`, read-only root, `--cap-drop ALL`,
`no-new-privileges`, user 65534, and memory/CPU/PID limits, with a time limit enforced by the API.

## 4. Run everything with Docker Compose

```bash
docker build -t placement-sandbox:latest ./sandbox
mkdir -p /tmp/placement_code_runs
docker compose up --build
```

Frontend http://localhost:5173, API http://localhost:8000/docs. The compose file uses the `pgvector/pgvector:pg16`
image so indexed vector search is available. The backend container mounts the host Docker socket so it can start
sandbox containers; that grants it control of the host Docker, so treat the API host as trusted infrastructure.
The compose file has not been run end to end in the environment where this edition was built (no Docker Hub access).

## 5. Migrations and upgrading

The Advanced Edition adds one Alembic revision on top of the original schema (`b7c8d9e0f1a2_advanced_edition`,
after `a1b2c3d4e5f6`). Existing databases upgrade in place:

```bash
cd backend
python -m alembic upgrade head
```

Existing users, profiles, interviews and submissions are kept; new columns are nullable or have defaults.
Back up the database first (`pg_dump interview_coach > backup.sql`). The pgvector column and HNSW index are created only
if the `vector` extension is available on the server; otherwise search runs in-process and everything else is identical.
Downgrade: `python -m alembic downgrade a1b2c3d4e5f6`.

## 6. Tests

```bash
cd backend && python -m pytest -q                         # SQLite (default)
TEST_DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/placement_test python -m pytest -q   # PostgreSQL + pgvector
cd frontend && npm test                                    # vitest: components, forms, API client, auth
cd frontend && npm run typecheck && npm run build
# Browser E2E (backend seeded + running with EXECUTION_BACKEND=local, frontend running):
pip install playwright python-docx && python -m playwright install chromium
python tests/ui_smoke_test.py --screenshots tests/screenshots
```

The E2E test creates data for the demo user, so re-seed a fresh database for a clean repeat run.


## 6b. Coding problem bank and interview length

* **Problem pack.** `backend/app/data/problem_pack.json` holds 49 original-wording problems (258 test cases, first two visible, rest hidden). Expected outputs are produced by running reference solutions (`backend/scripts/build_problem_pack.py`), so they are verified by construction. The pack is loaded idempotently at startup and by `scripts/seed.py`; existing titles are skipped.
* **Adding more problems at scale.** Run `python -m scripts.import_coding_questions problems.json` on the server (there is no admin UI). Item format: `title`, `problem_statement`, `difficulty` (easy/medium/hard), `topic_tag`, optional `company_tags`, `starter_codes`, and `tests`: `[{"input","expected_output","hidden"}]`. Up to 2000 per call; duplicates (by title) are skipped and invalid items are reported, not silently dropped.
* **LeetCode.** The full LeetCode catalogue is not included: its statements are copyrighted, and its problems use function-signature judging rather than stdin/stdout. Import only problem sets you wrote or are licensed to use.
* **Interview length.** Students choose 1-30 questions for HR and technical interviews. The built-in bank has 10 HR and 70 technical questions; beyond that, mock mode produces generic questions and a live OpenAI key produces fresh, tailored ones. Add bank questions in the admin panel to widen coverage.

## 7. Known limitations

* **Mock AI is not an LLM.** In mock mode, questions come from the bank and answers are scored by keyword coverage, structure and length against the question's key points; a fluent but wrong answer can score well. Every mock result is marked simulated.
* **The OpenAI path has not been exercised against the live API** (no network access during development). It is tested with a stubbed HTTP transport (success, retry, malformed JSON, fallback, token accounting).
* **Default embeddings are lexical hashing vectors**, not semantic. Search finds shared words and phrases. Real semantic search needs `sentence-transformers`, which was not downloaded or tested here, nor was the cross-encoder reranker.
* **The `local` executor is not a security boundary.** Use `EXECUTION_BACKEND=docker` for untrusted code. Docker isolation was verified with a locally imported image; building `sandbox/Dockerfile` from Docker Hub was not possible in the build environment.
* **Resume parsing** is a skills dictionary plus regex rules; it misses unusual skills and cannot read scanned PDFs (no OCR). ATS and quality scores are transparent heuristics, not what any specific ATS does.
* **Complexity analysis** is a static heuristic and may be wrong.
* **Voice**: speech-to-text uses the browser's Web Speech API (Chrome/Edge); text-to-speech uses the browser. No audio is stored or analysed on the server, so pace and pauses are estimated from browser timing.
* **Rate limiting** is in-process memory (per worker). Add proxy-level limiting for multi-instance deployments.
* **Monaco and Google Fonts load from CDNs**; offline, the editor becomes a textarea and fonts fall back to system fonts.
* Company guides are general preparation themes, not leaked or verified interview patterns. Each carries a "verify with current sources" notice.
* The component library is shadcn-style, hand-written (the shadcn registry was unreachable); it is not generated by the shadcn CLI.
* Some original pages (landing, login, register, history, performance, preparation plan) remain JavaScript and were restyled rather than rewritten.
