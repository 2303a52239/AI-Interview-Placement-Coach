# AI Interview Intelligence & Placement Coach – Advanced Edition

> **Advanced Edition.** This version adds a full student profile, resume intelligence (ATS, JD matching, versions),
> adaptive HR/technical interviews with a six-criterion rubric, a Python/Java/C++ coding arena with hidden tests and
> Docker-isolated execution, skill-gap analysis, personalised roadmaps, a RAG study assistant, voice interviews,
> database-driven analytics, company preparation guides and an admin/placement-officer dashboard.
> **Start with [`docs/ADVANCED_EDITION.md`](docs/ADVANCED_EDITION.md)** for features, configuration, deployment,
> migrations, tests and honest limitations. The sections below are the original setup guide and still apply
> (use `backend/requirements-dev.txt` if you want to run the tests).

A full-stack, AI-powered placement preparation platform. Students upload a resume, get
personalized HR and technical mock interviews, take Java coding assessments with real
compilation, and receive a preparation plan that updates automatically based on their
performance.

This is a genuinely working application: every button in the frontend is wired to a real
FastAPI endpoint, backed by a PostgreSQL database, with a working (if intentionally simple)
AI layer that runs with **zero external API keys** out of the box.

---

## 1. Project Description

Placement Coach conducts personalized HR interviews, technical interviews, and Java coding
assessments, using the candidate's resume, skills, projects, and target role to generate
relevant questions and score their answers. Every attempt feeds a performance dashboard and
a prioritized preparation plan.

## 2. Features Implemented

- **Landing page** describing the product, features, and tech stack
- **Authentication**: registration, login, logout, JWT, protected routes, bcrypt password hashing
- **Student dashboard**: readiness/technical/HR/coding/communication scores, trend chart, weak/strong topics, recommended topics, preparation progress, recent interviews
- **Resume upload & analysis**: PDF/DOCX text extraction + keyword-dictionary based skill/project/education/experience/certification extraction, stored in PostgreSQL
- **Target role selection** used to personalize question generation
- **HR mock interviews**: questions generated from resume + skills + target role + past performance (via a RAG-style retrieval step)
- **Technical mock interviews**: personalized to the candidate's listed skills (Java, Python, React, SQL, etc.), with easy/medium/hard difficulty
- **RAG pipeline**: TF-IDF-based local vector store retrieves relevant candidate context (resume chunks, skills, projects, past weaknesses) before generating each question — no external embeddings API required
- **AI answer evaluation**: returns a structured score, strengths, weaknesses, feedback, and suggested improvement for every answer
- **Coding assessment**: problem on the left, Java editor on the right. **Run** tests your code on the sample input only (nothing is saved); **Submit** grades it against every test case and records the score. Real `javac`/`java` execution, timeout protection, compilation-error reporting, and time/space complexity estimates
- **Speech-to-text**: Chrome/Edge transcribe live in the browser (Web Speech API). Other browsers record audio and send it to `POST /speech/transcribe`, which needs `OPENAI_API_KEY`; without a key they get a clear message and can type instead
- **Performance analytics**: score by category, score over time, separate HR / technical / coding trend charts, and a strong-vs-weak topic chart
- **Personalized preparation plan**: a recommendation engine that ranks your weakest topics and gives concrete practice suggestions, with a 7-day schedule (Mon-Fri focus topics, Saturday mock interview, Sunday review), regenerated on demand
- **Interview history**: every past interview with date, type, score, difficulty, duration, strengths and weaknesses, plus a full question/answer/feedback detail view
- **Profile page**: update name, college, degree, target role, experience, skills, projects, and upload or replace your resume
- **Admin page** (admin accounts only): candidate overview table, and add/delete coding questions with their test cases. Also available as `/admin/*` API endpoints
- **Stateless evaluation API**: `POST /evaluate` scores any question/answer pair without starting an interview
- **App shell**: sidebar + top bar, mobile drawer menu, toast notifications, confirmation dialogs (logout, end interview early, regenerate plan, delete question), loading / empty / error states
- **AI provider abstraction**: switch between a fully offline `mock` provider (default, always works) and a real `openai` provider via one environment variable
- **Seed data**: a demo student account with a sample resume, completed interviews, and a coding question bank, so the app is immediately demonstrable
- **Automated tests**: 38 backend pytest tests (auth, resume parsing, interviews, evaluation, speech endpoint, Java execution, performance, plan, access control) that pass on both SQLite and a real PostgreSQL database, plus a 36-check browser smoke test (`tests/ui_smoke_test.py`) that drives the real UI
- **Error handling**: invalid login, invalid/oversized/empty file uploads, missing resume, database connection failures, AI API failures (silently falls back to mock), coding compile errors and timeouts, empty answers, network errors

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Router, Recharts, Monaco Editor, Axios |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL (via SQLAlchemy ORM), Alembic migrations |
| AI layer | Mock provider (offline, deterministic) or OpenAI (Chat Completions + Whisper), pluggable |
| RAG | TF-IDF (scikit-learn) local vector store, no external embeddings API required |
| Coding evaluation | Java (OpenJDK) — real `javac`/`java` subprocess execution with timeouts |
| Speech-to-Text | Browser Web Speech API (primary), optional OpenAI Whisper fallback |
| Auth | JWT (python-jose) + bcrypt (passlib) |

## 4. System Architecture

```
+-------------+      HTTPS/JSON      +------------------+      SQL      +------------+
|   React     | -------------------> |     FastAPI      | ------------> | PostgreSQL |
|  (Vite)     | <------------------- |     Backend      | <------------ |            |
+-------------+                      +------------------+               +------------+
                                             |      |
                                   +---------+      +---------+
                                   v                          v
                          +----------------+         +----------------+
                          |  AI Provider   |         |  Java Runner   |
                          | (mock/openai)  |         | (javac + java) |
                          +----------------+         +----------------+
                                   ^
                                   |
                          +----------------+
                          |  RAG Retriever |
                          | (TF-IDF vector |
                          |     store)     |
                          +----------------+
```

RAG pipeline: Candidate Data (resume text, skills, projects, target role, past interview
results) -> Chunking -> TF-IDF embedding -> similarity ranking -> top-k relevant context ->
fed into the AI Provider's question-generation prompt/logic.

## 5. Folder Structure

```
AI-Interview-Intelligence-Placement-Coach/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── routers/       # FastAPI route handlers
│   │   ├── services/      # Business logic
│   │   ├── ai/            # AIProvider abstraction (mock + openai)
│   │   ├── rag/           # TF-IDF vector store + retriever
│   │   ├── speech/        # Speech-to-text strategy
│   │   ├── coding/        # Java compile/run engine
│   │   └── utils/         # Security, file handling
│   ├── alembic/           # Database migrations
│   ├── scripts/seed.py    # Demo data seeding
│   ├── tests/             # Pytest suite (38 tests)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/, components/, context/, services/
│   │   ├── App.jsx, main.jsx
│   ├── package.json
│   └── .env.example
├── docker-compose.yml      # optional containerized setup
├── .gitignore
└── README.md
```

## 6. Prerequisites (Windows 10/11)

Install these before starting:

1. **Python 3.11 or later** — https://www.python.org/downloads/ (check "Add Python to PATH" during install)
2. **Node.js 20 LTS or later** — https://nodejs.org/
3. **PostgreSQL 15 or later** — https://www.postgresql.org/download/windows/ (remember the password you set for the `postgres` user)
4. **Java JDK 17 or later** (not just a JRE — `javac` is required) — https://adoptium.net/ (Eclipse Temurin is a good free choice)
5. **Visual Studio Code** — https://code.visualstudio.com/
6. Verify installs by opening **PowerShell** and running:
   ```powershell
   python --version
   node --version
   npm --version
   psql --version
   javac --version
   ```
   Every command should print a version number. If `javac` is not found, re-check that the JDK's `bin` folder was added to your `PATH` during installation.

## 7. Installation (Windows PowerShell + VS Code)

### 7.1 Extract and open

1. Extract `AI-Interview-Intelligence-Placement-Coach.zip`
2. Open the extracted folder in VS Code (`File > Open Folder...`)
3. Open a PowerShell terminal in VS Code (`` Ctrl+` ``)

### 7.2 Set up PostgreSQL

In PowerShell:
```powershell
psql -U postgres
```
Enter your PostgreSQL password when prompted, then inside the `psql` prompt:
```sql
CREATE DATABASE interview_coach;
\q
```

### 7.3 Backend setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Now edit `backend\.env` in VS Code and set your real PostgreSQL password:
```
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/interview_coach
JWT_SECRET=any-long-random-string-you-like
AI_PROVIDER=mock
```

Run database migrations:
```powershell
python -m alembic upgrade head
```

Seed demo data (creates a demo user, admin user, coding question bank, and sample completed interviews):
```powershell
python -m scripts.seed
```

Run the backend tests (optional but recommended):
```powershell
python -m pytest tests/ -v
```

### 7.4 Frontend setup

Open a **second** PowerShell terminal in VS Code:
```powershell
cd frontend
npm install
copy .env.example .env
```
`frontend\.env` already points at `http://localhost:8000` by default, which matches the backend — no changes needed unless you changed the backend port.

## 8. Running the Application

**Terminal 1 — Backend** (from the `backend` folder, with the virtual environment active):
```powershell
venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```
Backend will be available at **http://localhost:8000** (API docs at `/docs`).

**Terminal 2 — Frontend** (from the `frontend` folder):
```powershell
npm run dev
```
Frontend will be available at **http://localhost:5173**.

Open **http://localhost:5173** in your browser (Chrome or Edge recommended, for voice-answer support).

## 9. Demo Login

| Role | Email | Password |
|---|---|---|
| Student (with sample data) | `demo@student.com` | `Demo@1234` |

The demo student account already has a profile, skills, projects, one completed HR
interview, and one completed technical interview, so the dashboard and history pages have
data immediately. You can also register a brand-new account to see the empty-state flow.

## 10. AI API Configuration (Optional)

By default, `AI_PROVIDER=mock` in `backend/.env`. This uses a fully offline, deterministic
question-generation and answer-evaluation engine — **no API key needed**, and the app is
fully functional this way.

To use a real LLM instead:
1. Get an API key from https://platform.openai.com/
2. In `backend/.env`, set:
   ```
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
3. Restart the backend.

If the OpenAI call fails for any reason (bad key, no internet, rate limit), the app
automatically falls back to the mock provider for that request rather than crashing.

## 11. API Documentation

With the backend running, open:
- **http://localhost:8000/docs** — interactive Swagger UI (try endpoints directly)
- **http://localhost:8000/redoc** — ReDoc reference documentation

## 12. Known Limitations

See **docs/ADVANCED_EDITION.md → Known limitations** for the complete, current list. In short:
mock AI is rule-based (not an LLM) and is labelled as such; the live OpenAI path is untested against the real API;
default RAG embeddings are lexical hashing vectors unless `sentence-transformers` is installed; the `local` code
executor is not a security boundary (use `EXECUTION_BACKEND=docker`); resume parsing is dictionary/regex based and
cannot read scanned PDFs; voice input uses the browser's Web Speech API (Chromium); Monaco loads from a CDN and falls
back to a textarea offline.

## 13. Troubleshooting

| Problem | Solution |
|---|---|
| `psql` not recognized | Add PostgreSQL's `bin` folder (e.g. `C:\Program Files\PostgreSQL\16\bin`) to your Windows PATH and reopen PowerShell. |
| Backend fails to start with a database connection error | Confirm PostgreSQL is running (check the "postgresql-x64-16" Windows service) and that `DATABASE_URL` in `backend\.env` has the correct password. |
| `javac: command not found` / coding submissions always show "compiled_error" | Install a full JDK (not just a JRE) and ensure its `bin` folder is on PATH. Restart your terminal after installing. |
| Frontend shows "Could not reach the server" | Make sure the backend is running on port 8000 and `frontend\.env`'s `VITE_API_URL` matches. |
| `pip install` fails on `psycopg2-binary` | Make sure you're using a 64-bit Python install; this package ships prebuilt wheels for standard Windows Python installs. |
| Port 8000 or 5173 already in use | Stop the other process, or run `uvicorn app.main:app --port 8001` / `npm run dev -- --port 5174` and update `VITE_API_URL` / CORS accordingly. |
| Resume upload says "No readable text found" | The PDF is likely a scanned image rather than text-based; export/print the resume as a text-based PDF, or upload a DOCX instead. |
| Voice recording says transcription is not configured | You're not in Chrome/Edge and no `OPENAI_API_KEY` is set. Use Chrome or Edge, or type your answer. |
| Code editor looks plain / shows "Basic editor" notice | The Monaco editor couldn't download (offline or blocked CDN). It is fully usable; connect to the internet for syntax highlighting. |
| `alembic upgrade head` fails with a password error | Check the password in `DATABASE_URL` in `backend/.env` matches the one you set for the `postgres` user. |

## 14. Suggested Demonstration Flow

1. Open **http://localhost:5173** — show the landing page.
2. Log in as `demo@student.com` / `Demo@1234` — show the dashboard with pre-populated scores and trend chart.
3. Go to **Resume** — upload a sample resume (or view the pre-loaded extracted info) to show NLP extraction.
4. Go to **Technical Interview** — start a 3-question round; show that questions reflect the demo profile's skills (Java/React/SQL); answer one, show live scoring.
5. Go to **Coding Assessment** — open "Sum of Two Numbers", press **Run** on the starter code (shows the sample result), then write a correct solution and press **Submit** (all test cases pass) to demonstrate real Java compilation.
6. Go to **Performance** — show category and trend charts updating with the new attempt.
7. Go to **Preparation Plan** — show the regenerated, prioritized plan.
8. Go to **Interview History** — open a past interview's detail view.
9. (Optional) Open **http://localhost:8000/docs** to show the auto-generated API documentation.
10. (Optional) Mention `backend/tests/` and run `python -m pytest tests/ -v` live to show the 38 passing automated tests. Log in as the admin to show the Admin page.
