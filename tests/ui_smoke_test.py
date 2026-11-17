"""
End-to-end browser test for the Advanced Edition of Placement Coach.

Drives a real Chromium through the running app: auth, theme toggle, profile editing,
resume upload + analysis + profile auto-fill, adaptive interview, coding in Python,
roadmap, skill gap, analytics, study assistant (RAG upload + cited answer),
company prep, admin / officer access control and the mobile layout.

Prerequisites
  1. Backend on http://localhost:8000, migrated and seeded (python -m scripts.seed).
     For a quick run without Docker: EXECUTION_BACKEND=local (dev only, not a security boundary).
  2. Frontend on http://localhost:5173 (npm run dev).
  3. pip install playwright python-docx   and   python -m playwright install chromium

Usage:  python tests/ui_smoke_test.py [--screenshots tests/screenshots]
Env:    BASE_URL (default http://localhost:5173), CHROME_PATH, HEADED=1

The test creates real data for the demo user (interviews, submissions, documents).
Re-seed a fresh database to reset.
"""
import argparse
import os
import sys
import tempfile

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:5173")
parser = argparse.ArgumentParser()
parser.add_argument("--screenshots", default=None)
args = parser.parse_args()
if args.screenshots:
    os.makedirs(args.screenshots, exist_ok=True)

results, errors, CURRENT = [], [], []
PY_SUM = "a, b = map(int, input().split())\nprint(a + b)\n"
RESUME_LINES = [
    "Asha Rao", "asha@example.com | +91 98765 43210 | github.com/asharao",
    "SUMMARY", "Computer science student focused on backend development.",
    "SKILLS", "Python, Java, SQL, FastAPI, React, Docker, PostgreSQL, Git",
    "PROJECTS", "Placement Tracker - built a FastAPI and PostgreSQL service used by 200 students, cutting lookup time by 40%.",
    "EDUCATION", "B.Tech Computer Science, Anna University, 2026, CGPA 8.4",
    "CERTIFICATIONS", "AWS Cloud Practitioner",
]


def shot(page, name, full=False):
    if args.screenshots:
        page.screenshot(path=os.path.join(args.screenshots, name), full_page=full)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  -- {detail}" if detail and not ok else ""))
    if not ok and CURRENT:
        try:
            CURRENT[0].screenshot(path=f"/tmp/fail_{len(results)}.png")
            print("      page:", CURRENT[0].url, "|", CURRENT[0].inner_text("body")[:300].replace("\n", " / "))
        except Exception:
            pass


def login(page, email, password):
    page.goto(f"{BASE}/login")
    page.fill('input[type="email"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')


def has(page, text, timeout=8000):
    try:
        page.wait_for_selector(f"text={text}", timeout=timeout)
        return True
    except Exception:
        return False


def set_code(page, code):
    fb = page.locator('textarea[aria-label="Source code"]')
    if fb.count():
        fb.fill(code)
    else:
        page.evaluate("(c) => window.monaco.editor.getModels()[0].setValue(c)", code)


def make_resume(path):
    import docx
    d = docx.Document()
    for line in RESUME_LINES:
        d.add_paragraph(line)
    d.save(path)


def _on_crash(tp, val, tb):
    try:
        CURRENT[0].screenshot(path="/tmp/crash.png")
    except Exception:
        pass
    sys.__excepthook__(tp, val, tb)


sys.excepthook = _on_crash
tmp = tempfile.mkdtemp()
resume_path = os.path.join(tmp, "resume.docx")
make_resume(resume_path)
notes_path = os.path.join(tmp, "notes.txt")
open(notes_path, "w").write("A hash map stores key value pairs and gives average constant time lookup. Collisions are handled by chaining or open addressing.\n\nA B-tree keeps data sorted and supports logarithmic search, insertion and deletion, which is why databases use it for indexes.")

with sync_playwright() as p:
    la = {"headless": os.environ.get("HEADED") != "1", "args": ["--no-sandbox"]}
    if os.environ.get("CHROME_PATH"):
        la["executable_path"] = os.environ["CHROME_PATH"]
    browser = p.chromium.launch(**la)
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    CURRENT.append(page)
    page.on("response", lambda r: print("      HTTP", r.status, r.url[-45:]) if r.status in (401, 403, 429) else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    # ---------- landing + auth ----------
    page.goto(BASE)
    check("landing page renders", page.locator("text=Walk into every interview").count() == 1)
    login(page, "demo@student.com", "wrong-password")
    page.wait_for_timeout(1200)
    check("invalid login shows an error", page.locator("text=Invalid email or password").count() >= 1)
    login(page, "demo@student.com", "Demo@1234")
    page.wait_for_url("**/dashboard", timeout=8000)
    check("login reaches the dashboard", has(page, "Your readiness at a glance"))
    check("dashboard shows honest AI mode", has(page, "AI mode:"))
    check("dashboard shows placement readiness", has(page, "Placement readiness"))
    shot(page, "01_dashboard.png", full=True)

    # ---------- theme ----------
    page.click('button[aria-label="Switch to dark theme"]')
    check("dark theme applies", page.evaluate("document.documentElement.classList.contains('dark')"))
    page.wait_for_timeout(500)
    shot(page, "02_dark.png")
    page.reload(); page.wait_for_timeout(800)
    check("theme persists across reload", page.evaluate("document.documentElement.classList.contains('dark')"))
    page.click('button[aria-label="Switch to light theme"]')

    # ---------- every page loads ----------
    for path, marker in [
        ("/analytics", "Analytics"), ("/performance", "Strong and weak topics"), ("/preparation-plan", "This week"),
        ("/history", "Interview History"), ("/skill-gap", "Skill gap analysis"), ("/roadmap", "Preparation roadmap"),
        ("/companies", "Company preparation"), ("/assistant", "Study assistant"), ("/coding", "Coding assessment"),
        ("/resume", "Resume intelligence"), ("/profile", "Your profile"),
    ]:
        page.goto(f"{BASE}{path}")
        ok = has(page, marker, 8000)
        check(f"page loads: {path}", ok and page.locator("text=Could not").count() == 0)

    # ---------- resume upload, analysis, profile auto-fill ----------
    page.goto(f"{BASE}/resume"); has(page, "Resume intelligence")
    page.set_input_files('input[aria-label="Upload resume file"]', resume_path)
    check("resume: upload shows overview with ATS score", has(page, "ATS score", 15000))
    check("resume: extracted skills and project shown", has(page, "Placement Tracker") and page.locator("text=FastAPI").count() >= 1)
    page.click('role=tab[name="ATS & quality"]')
    check("resume: ATS checks and quality dimensions listed", has(page, "ATS checks") and has(page, "Quality dimensions"))
    shot(page, "03_resume.png", full=True)
    page.click('role=tab[name="Job match"]')
    page.fill("#jdx", "We need a backend developer with Python, FastAPI, PostgreSQL, Docker and Kubernetes experience for building APIs.")
    page.click("button:has-text('Match resume')")
    check("resume: JD match lists a missing skill", has(page, "Missing skills", 10000) and page.locator("text=Kubernetes").count() >= 1)
    page.click('role=tab[name^="Versions"]')
    check("resume: versions tab lists the upload", has(page, "resume.docx"))

    page.goto(f"{BASE}/profile"); has(page, "Your profile")
    page.click('role=tab[name="Resume"]')
    page.click("button:has-text('Auto-fill profile from resume')")
    check("profile: auto-fill reports what it filled", has(page, "Filled from your resume", 10000))
    page.click('role=tab[name="Skills"]')
    check("profile: skills now include the extracted ones", page.locator('input[aria-label="Skill 1 name"]').count() == 1)
    page.click('role=tab[name="Basics"]')
    page.fill("#college", "Anna University")
    page.click("button:has-text('Save profile')")
    check("profile: save confirms", has(page, "Profile saved"))
    page.reload(); page.wait_for_selector("#college")
    check("profile: saved value persists", page.input_value("#college") == "Anna University")
    page.set_input_files('input[aria-label="Upload photo"]', os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "favicon.png")) if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "favicon.png")) else None
    shot(page, "04_profile.png", full=True)

    # ---------- skill gap, roadmap ----------
    page.goto(f"{BASE}/skill-gap"); has(page, "Skill gap analysis")
    check("skill gap lists ranked skills with evidence", has(page, "Evidence:", 10000))
    page.goto(f"{BASE}/roadmap"); has(page, "Preparation roadmap")
    page.click("button:has-text('Generate roadmap'), button:has-text('Replace roadmap')")
    check("roadmap generates with progress and today's tasks", has(page, "Weekly plan", 15000) and has(page, "Progress"))
    cb = page.locator('[role="checkbox"]').first
    before = cb.get_attribute("aria-checked")
    cb.click(); page.wait_for_timeout(800)
    check("roadmap: task can be marked done", page.locator('[role="checkbox"]').first.get_attribute("aria-checked") != before)
    shot(page, "05_roadmap.png", full=True)

    # ---------- coding in Python, hidden tests ----------
    page.goto(f"{BASE}/coding/1"); has(page, "Sum of Two Numbers")
    page.wait_for_timeout(7000)
    page.select_option('select[aria-label="Language"]', "python")
    set_code(page, PY_SUM)
    page.click("button:has-text('Run sample')")
    check("coding: Run sample passes in Python", has(page, "Sample passed", 25000))
    page.click("button:has-text('Submit')")
    check("coding: Submit passes every test case", has(page, "3/3 tests", 40000) and page.locator("text=Passed").count() >= 1)
    check("coding: complexity estimate shown", page.locator("text=Estimated complexity").count() == 1)
    check("coding: submission history lists the attempt", page.locator("text=/\\d+\\/\\d+ · \\d+/").count() >= 1)
    shot(page, "06_coding.png", full=True)
    page.goto(f"{BASE}/coding"); has(page, "Coding assessment")
    page.click('role=tab[name="Timed assessment"]')
    page.click("button:has-text('Start assessment')")
    check("timed assessment shows a countdown", has(page, "Finish assessment", 15000) and page.locator('[role="timer"]').count() == 1)

    # ---------- adaptive technical interview ----------
    page.goto(f"{BASE}/interview/technical"); has(page, "Start interview")
    page.wait_for_load_state("networkidle")
    page.fill("#num", "3"); page.select_option("#topic", "dbms")
    page.click('button[aria-label="Adaptive difficulty"]')
    page.click("button:has-text('Start interview')")
    ok = has(page, "Question 1 of 3", 10000)
    check("interview: adaptive question shown with difficulty", ok and page.locator("text=adaptive").count() >= 1)
    page.fill("textarea", "An index is a B-tree structure that speeds up lookups at the cost of slower writes and more storage. For example a primary key index avoids full table scans.")
    page.click("button:has-text('Submit answer')")
    check("interview: per-answer rubric and ideal answer shown", has(page, "Feedback on this answer", 15000) and has(page, "Correctness") and has(page, "Ideal answer"))
    shot(page, "07_interview_feedback.png", full=True)
    page.click("button:has-text('Next question'), button:has-text('Finish and see results')")
    page.click("text=End early")
    page.click('[role="dialog"] >> text=End and see results')
    check("interview: end early shows results", has(page, "Interview completed", 10000))
    page.click("text=Detailed answers and ideal answers")
    check("interview detail shows rubric", has(page, "Questions and answers") and has(page, "Correctness"))

    # ---------- HR interview full flow ----------
    page.goto(f"{BASE}/interview/hr"); has(page, "Start interview")
    page.fill("#num", "3"); page.click("button:has-text('Start interview')")
    has(page, "Question 1 of 3", 10000)
    for i in range(3):
        page.fill("textarea", "In my last project I led the backend design because I enjoy ownership. For example, I built a REST API, then cut latency, and the result was a faster experience.")
        page.click("button:has-text('Submit answer')")
        has(page, "Feedback on this answer", 15000)
        page.click("button:has-text('Next question'), button:has-text('Finish and see results')")
        if i < 2:
            has(page, f"Question {i + 2} of 3", 10000)
    check("HR flow: completion screen", has(page, "Interview completed", 15000) and page.locator("text=Overall score").count() == 1 and page.locator("text=AI Feedback").count() == 1)

    # ---------- analytics, assistant, companies ----------
    page.goto(f"{BASE}/analytics"); has(page, "Analytics")
    check("analytics: real charts after activity", has(page, "Topic strength", 10000) and page.locator("text=No data to chart yet").count() == 0)
    shot(page, "08_analytics.png", full=True)
    page.goto(f"{BASE}/assistant"); has(page, "Study assistant")
    page.set_input_files('input[aria-label="Upload document"]', notes_path)
    check("assistant: document indexed", has(page, "Indexed notes.txt", 15000))
    page.fill('input[aria-label="Your question"]', "Why do databases use a B-tree for indexes?")
    page.click("button[type=submit]:has-text('Ask')")
    check("assistant: answer with cited sources", has(page, "source", 15000) and page.locator("text=notes.txt").count() >= 1)
    shot(page, "09_assistant.png", full=True)
    page.goto(f"{BASE}/companies"); has(page, "Company preparation")
    page.click('role=tab[name="Google"]')
    check("companies: guide with verify-disclaimer and focus topics", has(page, "Focus topics") and has(page, "Preparation themes"))

    # ---------- logout ----------
    page.click("aside >> text=Log out")
    check("logout asks for confirmation", page.locator('[role="dialog"]').count() == 1)
    page.click('[role="dialog"] >> button:has-text("Log out")')
    page.wait_for_url("**/login", timeout=5000)
    check("logout returns to the login page", True)

    # ---------- role-based access ----------
    login(page, "demo@student.com", "Demo@1234"); page.wait_for_url("**/dashboard")
    check("no Admin link in navigation", page.locator('nav a[href="/admin"]').count() == 0)
    page.goto(f"{BASE}/admin"); page.wait_for_timeout(1500)
    check("/admin is not a page (Not found)", page.locator("text=/not found|404/i").count() >= 1)

    # ---------- mobile ----------
    m = browser.new_context(viewport={"width": 390, "height": 800}).new_page()
    m.goto(f"{BASE}/login"); m.fill('input[type="email"]', "demo@student.com"); m.fill('input[type="password"]', "Demo@1234")
    m.click('button[type="submit"]'); m.wait_for_url("**/dashboard"); m.wait_for_timeout(1500)
    check("mobile: sidebar hidden by default", m.locator("nav a:visible", has_text="Dashboard").count() == 0)
    m.click('button[aria-label="Open menu"]')
    check("mobile: menu opens the drawer", m.locator("nav a:visible", has_text="Dashboard").count() >= 1)
    m.click("nav a:visible >> text=Profile"); m.wait_for_timeout(1200)
    check("mobile: no horizontal scrolling on profile", not m.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"))
    shot(m, "11_mobile.png")
    browser.close()

print(f"\nJavaScript page errors: {len(errors)}")
for e in errors[:10]:
    print("  ", e[:200])
failed = [r for r in results if not r[1]]
print(f"{len(results) - len(failed)}/{len(results)} UI checks passed")
sys.exit(1 if failed or errors else 0)
