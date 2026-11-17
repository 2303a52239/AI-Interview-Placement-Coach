"""
Resume intelligence: text extraction (PDF/DOCX), section + entity extraction, ATS analysis, quality scoring,
job-description matching and improvement suggestions.

Everything here is deterministic, dictionary/regex based NLP - there is no ML model and no randomness. That keeps
it fast, offline and explainable: every score is a sum of named checks the user can see and act on.
"""
import json
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import docx
from pypdf import PdfReader

from app.data.skills import find_skills, category_of, canonical, SKILLS

SECTION_HEADINGS = {
    "summary": ["summary", "professional summary", "career objective", "objective", "profile", "about me", "about"],
    "education": ["education", "academic background", "academics", "educational qualifications", "qualifications"],
    "skills": ["skills", "technical skills", "key skills", "core competencies", "skills & tools", "tech stack", "technologies"],
    "experience": ["experience", "work experience", "professional experience", "internships", "internship experience",
                   "employment history", "internship"],
    "projects": ["projects", "personal projects", "academic projects", "key projects", "project work", "projects & research"],
    "certifications": ["certifications", "certificates", "licenses & certifications", "courses", "courses & certifications",
                       "training"],
    "achievements": ["achievements", "awards", "accomplishments", "honors", "honours", "extracurricular", "activities",
                     "positions of responsibility"],
}
_HEADING_LOOKUP = {h: sec for sec, hs in SECTION_HEADINGS.items() for h in hs}

EDUCATION_KEYWORDS = ["b.tech", "btech", "bachelor", "b.e.", "b.e ", "m.tech", "mtech", "master", "mba", "b.sc", "m.sc",
                      "bca", "mca", "diploma", "phd", "university", "college", "institute of technology"]
ACTION_VERBS = set("""built developed designed implemented created led managed improved optimized reduced increased
delivered launched automated analyzed architected engineered deployed integrated migrated maintained collaborated
trained evaluated researched wrote refactored tested debugged scaled streamlined spearheaded mentored organized
presented achieved established initiated resolved secured contributed coordinated modelled modeled constructed
configured published enhanced owned drove""".split())
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{3,5}\)?[\s\-]?)?\d{3,5}[\s\-]?\d{4,5}(?!\d)")
LINK_RE = {
    "linkedin": re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?", re.I),
    "github": re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+(?:/[A-Za-z0-9\-_.]+)?/?", re.I),
    "leetcode": re.compile(r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?[A-Za-z0-9\-_]+/?", re.I),
}


# --------------------------------------------------------------------------- text extraction
def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text_from_docx(path: str) -> str:
    document = docx.Document(path)
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:  # resumes often put skills / education in tables
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
    return "\n".join(parts)


def extract_text(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(path)
    if lower.endswith(".docx"):
        return extract_text_from_docx(path)
    raise ValueError("Unsupported resume file type")


# --------------------------------------------------------------------------- sections + entities
def split_sections(text: str) -> Dict[str, str]:
    """Split resume text into sections by heading lines. Unmatched leading text goes under 'header'."""
    sections: Dict[str, List[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        stripped = line.strip()
        key = re.sub(r"[:\-–—_•\s]+$", "", stripped.lower()).strip()
        key = re.sub(r"^[•\-–—\s]+", "", key)
        if key in _HEADING_LOOKUP and len(stripped) <= 45:
            current = _HEADING_LOOKUP[key]
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def extract_contacts(text: str) -> Dict[str, str]:
    contacts: Dict[str, str] = {}
    m = EMAIL_RE.search(text)
    if m:
        contacts["email"] = m.group(0)
    head = text[:700]
    for pm in PHONE_RE.finditer(head):
        digits = re.sub(r"\D", "", pm.group(0))
        if 10 <= len(digits) <= 13:
            contacts["phone"] = pm.group(0).strip()
            break
    for name, rx in LINK_RE.items():
        lm = rx.search(text)
        if lm:
            url = lm.group(0)
            contacts[name] = url if url.lower().startswith("http") else "https://" + url
    return contacts


def _bullets(block: str) -> List[str]:
    items = []
    for line in block.splitlines():
        line = re.sub(r"^[\s•\-–—*▪●◦·]+", "", line).strip()
        if len(line) > 3:
            items.append(line)
    return items


def _group_entries(block: str) -> List[Dict[str, Any]]:
    """Group a projects/experience block into entries: a non-bullet line starts a new entry, bullets describe it."""
    entries: List[Dict[str, Any]] = []
    for raw in block.splitlines():
        if not raw.strip():
            continue
        is_bullet = bool(re.match(r"^\s*[•\-–—*▪●◦·]\s*", raw))
        text = re.sub(r"^[\s•\-–—*▪●◦·]+", "", raw).strip()
        if not is_bullet and (not entries or len(text) < 90):
            entries.append({"title": text[:200], "details": []})
        elif entries:
            entries[-1]["details"].append(text)
        else:
            entries.append({"title": text[:200], "details": []})
    return entries


def _extract_education(sections: Dict[str, str], text: str) -> List[str]:
    block = sections.get("education", "")
    lines = _bullets(block) if block else []
    if not lines:
        lines = [l.strip() for l in text.splitlines() if any(k in l.lower() for k in EDUCATION_KEYWORDS)]
    return [l[:200] for l in lines][:8]


def extract_education_details(education_lines: List[str]) -> Dict[str, Any]:
    joined = " ".join(education_lines)
    details: Dict[str, Any] = {}
    cg = re.search(r"(?:cgpa|gpa)[^0-9]{0,12}(\d{1,2}(?:\.\d{1,2})?)", joined, re.I) or re.search(r"(\d\.\d{1,2})\s*/\s*10", joined)
    if cg:
        val = float(cg.group(1))
        if 0 < val <= 10:
            details["cgpa"] = val
    years = [int(y) for y in re.findall(r"\b(20[0-4]\d)\b", joined)]
    if years:
        details["graduation_year"] = max(years)
    deg = re.search(r"(b\.?\s?tech|b\.?\s?e\b|bachelor[^,\n]{0,40}|m\.?\s?tech|master[^,\n]{0,40}|bca|mca|b\.?\s?sc|m\.?\s?sc|mba)", joined, re.I)
    if deg:
        details["degree"] = deg.group(0).strip()
    uni = re.search(r"([A-Z][A-Za-z.&' ]{3,60}(?:University|Institute of Technology|Institute|College|Engineering College))", joined)
    if uni:
        details["college"] = uni.group(1).strip()
    branch = re.search(r"(computer science(?: and engineering)?|information technology|electronics(?: and communication)?|"
                       r"electrical|mechanical|civil|data science|artificial intelligence|cse|ece|eee)", joined, re.I)
    if branch:
        details["branch"] = branch.group(1).strip().title() if len(branch.group(1)) > 4 else branch.group(1).upper()
    return details


def _extract_certifications(sections: Dict[str, str], text: str) -> List[str]:
    block = sections.get("certifications", "")
    if block:
        return [b[:200] for b in _bullets(block)][:10]
    return [l.strip()[:200] for l in text.splitlines() if re.search(r"certif", l, re.I)][:10]


# --------------------------------------------------------------------------- analysis pieces
def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _all_bullets(sections: Dict[str, str]) -> List[str]:
    out: List[str] = []
    for key in ("experience", "projects", "achievements", "summary"):
        out.extend(_bullets(sections.get(key, "")))
    return out


def _quantified(line: str) -> bool:
    return bool(re.search(r"\d+\s?%|\b\d+[kKmM]?\+?\s*(users|requests|ms|seconds|hours|people|students|customers|records|apis?|endpoints|tests?|x)\b|\$\s?\d|\b\d{2,}\b", line))


def _starts_with_action_verb(line: str) -> bool:
    first = re.sub(r"[^a-z]", "", (line.split() or [""])[0].lower())
    return first in ACTION_VERBS


def ats_analysis(text: str, sections: Dict[str, str], contacts: Dict[str, str], skills: List[str]) -> Dict[str, Any]:
    """Applicant-tracking-system readability checks. Every check is listed with its weight, outcome and a fix."""
    words = _word_count(text)
    bullets = _all_bullets(sections)
    quant = [b for b in bullets if _quantified(b)]
    verbs = [b for b in bullets if _starts_with_action_verb(b)]
    checks = [
        ("Machine-readable text", 10, words >= 80, "Text was extracted successfully.",
         "Very little text could be read; export your resume as a text-based PDF or DOCX, not an image."),
        ("Contact details", 10, "email" in contacts and "phone" in contacts, "Email and phone found.",
         "Add both an email address and a phone number at the top."),
        ("Professional links", 5, "linkedin" in contacts or "github" in contacts, "LinkedIn/GitHub link found.",
         "Add your LinkedIn and GitHub profile URLs."),
        ("Education section", 10, "education" in sections, "Education section detected.",
         "Add a clearly titled 'Education' section."),
        ("Skills section", 10, "skills" in sections or len(skills) >= 6, "Skills are easy for a parser to find.",
         "Add a 'Skills' section listing technologies as plain text."),
        ("Experience or projects", 10, "experience" in sections or "projects" in sections, "Experience/projects section detected.",
         "Add a 'Projects' or 'Experience' section with headings ATS tools recognise."),
        ("Keyword coverage", 10, len(skills) >= 8, f"{len(skills)} recognised skills/technologies.",
         f"Only {len(skills)} recognised skills; list at least 8 relevant technologies."),
        ("Length", 10, 250 <= words <= 900, f"{words} words - a good length.",
         f"{words} words. Aim for 250-900 words (one page for freshers)."),
        ("Bullet-point formatting", 5, len(bullets) >= 5, "Achievements are written as bullets.",
         "Describe projects and experience as short bullet points."),
        ("Action verbs", 10, bool(bullets) and len(verbs) / len(bullets) >= 0.5, "Most bullets start with action verbs.",
         "Start bullets with verbs such as 'Built', 'Designed', 'Optimized'."),
        ("Quantified impact", 10, bool(bullets) and len(quant) / len(bullets) >= 0.25, "Results are quantified.",
         "Add numbers: 'reduced load time by 35%', 'served 2,000 users'."),
    ]
    items, score = [], 0
    for name, weight, ok, good, fix in checks:
        if ok:
            score += weight
        items.append({"check": name, "weight": weight, "passed": bool(ok), "detail": good if ok else fix})
    return {"score": float(score), "checks": items,
            "stats": {"words": words, "bullets": len(bullets), "quantified_bullets": len(quant),
                      "action_verb_bullets": len(verbs), "skills_found": len(skills)}}


def quality_analysis(text: str, sections: Dict[str, str], skills: List[str], projects: List[Dict[str, Any]],
                     experience: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Content quality (distinct from parser-readability). Each dimension is 0-100; the total is a weighted mean."""
    bullets = _all_bullets(sections)
    n = len(bullets)
    impact = 100 * (0.6 * (len([b for b in bullets if _quantified(b)]) / n if n else 0)
                    + 0.4 * (len([b for b in bullets if _starts_with_action_verb(b)]) / n if n else 0))
    breadth = min(100.0, len(skills) / 12 * 100)
    cats = len({category_of(s) for s in skills})
    breadth = 0.7 * breadth + 0.3 * min(100.0, cats / 5 * 100)
    proj_depth = 0.0
    if projects:
        with_detail = sum(1 for p in projects if len(p.get("details", [])) >= 2)
        proj_depth = min(100.0, 40 * min(len(projects), 3) / 3 + 60 * (with_detail / len(projects)))
    exp_score = 0.0
    if experience:
        exp_score = min(100.0, 50 + 25 * min(len(experience), 2) / 2 * 2) if any(e.get("details") for e in experience) else 40.0
    sents = [s for s in re.split(r"[.!?\n]+", text) if len(s.split()) > 2]
    avg_len = sum(len(s.split()) for s in sents) / len(sents) if sents else 0
    readability = 100.0 if 8 <= avg_len <= 22 else (70.0 if avg_len <= 30 else 45.0)
    completeness = 100 * sum(1 for k in ("education", "skills", "projects", "experience", "certifications", "summary") if k in sections) / 6
    dims = {
        "impact": (0.25, impact, "Quantified, action-led bullet points."),
        "skills_breadth": (0.20, breadth, "Range of relevant technologies across categories."),
        "project_depth": (0.20, proj_depth, "Projects with multiple descriptive bullets."),
        "experience": (0.10, exp_score, "Internships or work experience with detail."),
        "readability": (0.10, readability, "Sentence length and scannability."),
        "completeness": (0.15, completeness, "Presence of standard sections."),
    }
    total = sum(w * s for w, s, _ in dims.values())
    return {"score": round(total, 1),
            "dimensions": {k: {"score": round(s, 1), "weight": w, "meaning": m} for k, (w, s, m) in dims.items()}}


def build_suggestions(ats: Dict[str, Any], quality: Dict[str, Any], sections: Dict[str, str]) -> List[str]:
    tips = [c["detail"] for c in ats["checks"] if not c["passed"]]
    dims = quality["dimensions"]
    if dims["project_depth"]["score"] < 60:
        tips.append("Give each project 2-3 bullets covering what you built, the tech used and the outcome.")
    if "summary" not in sections:
        tips.append("Add a 2-line professional summary naming your target role and strongest skills.")
    if "certifications" not in sections:
        tips.append("List relevant certifications or courses to strengthen credibility.")
    if dims["readability"]["score"] < 70:
        tips.append("Shorten long sentences; keep each bullet to one line or two.")
    seen, out = set(), []
    for t in tips:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:10]


# --------------------------------------------------------------------------- main entry
def analyze_resume(raw_text: str) -> Dict[str, Any]:
    """Run the full pipeline. Returns kwargs ready for `Resume(...)` (JSON-encoded text columns + scores)."""
    sections = split_sections(raw_text)
    contacts = extract_contacts(raw_text)
    skills = find_skills(raw_text)
    projects = _group_entries(sections.get("projects", ""))[:8]
    experience = _group_entries(sections.get("experience", ""))[:8]
    education = _extract_education(sections, raw_text)
    certifications = _extract_certifications(sections, raw_text)
    edu_details = extract_education_details(education)

    tech_cats = {"framework", "web", "cloud", "devops", "ai_ml", "database", "backend", "tools"}
    technologies = [s for s in skills if category_of(s) in tech_cats]
    languages_and_core = [s for s in skills if s not in technologies]

    ats = ats_analysis(raw_text, sections, contacts, skills)
    quality = quality_analysis(raw_text, sections, skills, projects, experience)
    suggestions = build_suggestions(ats, quality, sections)

    analysis = {
        "sections_found": sorted(k for k in sections if k != "header"),
        "contacts": contacts, "education_details": edu_details,
        "skills_by_category": {},
        "ats": ats, "quality": quality, "suggestions": suggestions,
        "projects": projects, "experience": experience,
    }
    for s in skills:
        analysis["skills_by_category"].setdefault(category_of(s), []).append(s)

    return {
        "extracted_skills": json.dumps(languages_and_core or skills),
        "extracted_technologies": json.dumps(technologies),
        "extracted_projects": json.dumps([p["title"] for p in projects]),
        "extracted_education": json.dumps(education),
        "extracted_experience": json.dumps([e["title"] for e in experience]),
        "extracted_certifications": json.dumps(certifications),
        "keywords": json.dumps(skills),
        "ats_score": ats["score"],
        "quality_score": quality["score"],
        "analysis": json.dumps(analysis),
    }


def all_skills_of(resume) -> List[str]:
    return json.loads(resume.keywords or "[]") or sorted(
        set(json.loads(resume.extracted_skills or "[]") + json.loads(resume.extracted_technologies or "[]")))


# --------------------------------------------------------------------------- job description matching
def _tf_cosine(a: str, b: str) -> float:
    ta = Counter(re.findall(r"[a-z][a-z+#.]{2,}", a.lower()))
    tb = Counter(re.findall(r"[a-z][a-z+#.]{2,}", b.lower()))
    if not ta or not tb:
        return 0.0
    dot = sum(ta[k] * tb.get(k, 0) for k in ta)
    return dot / (math.sqrt(sum(v * v for v in ta.values())) * math.sqrt(sum(v * v for v in tb.values())))


def extract_jd_skills(jd_text: str) -> List[str]:
    return find_skills(jd_text)


def match_resume_to_jd(resume_text: str, resume_skills: List[str], jd_text: str,
                       jd_skills: Optional[List[str]] = None) -> Dict[str, Any]:
    jd_skills = jd_skills if jd_skills else extract_jd_skills(jd_text)
    have = {canonical(s) for s in resume_skills}
    required = [canonical(s) for s in jd_skills]
    matched = [s for s in required if s in have]
    missing = [s for s in required if s not in have]
    coverage = len(matched) / len(required) if required else 0.0
    similarity = _tf_cosine(resume_text, jd_text)
    # coverage of named skills dominates; text similarity captures wording beyond the dictionary
    score = round(100 * (0.8 * coverage + 0.2 * min(1.0, similarity * 1.6)), 1) if required else round(100 * similarity, 1)
    suggestions = []
    for m in missing[:8]:
        cat = category_of(m)
        suggestions.append(f"The job description asks for {m}. If you have used it, add it to your skills and show it in a "
                           f"project bullet; if not, it is a {cat.replace('_', ' ')} gap worth learning.")
    if required and coverage >= 0.8:
        suggestions.append("Strong skill match. Mirror the JD's wording in your summary and top project bullets.")
    if not required:
        suggestions.append("No recognisable skills were found in this job description; paste the full requirements section.")
    return {"match_score": score, "matched_skills": matched, "missing_skills": missing,
            "required_skills": required, "text_similarity": round(similarity, 3), "suggestions": suggestions}
