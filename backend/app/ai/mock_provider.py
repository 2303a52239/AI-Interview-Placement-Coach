"""
MockAIProvider

A fully offline, deterministic "AI" implementation so the whole platform can
be demonstrated without any external API key. It uses:
  - Curated question banks (HR + per-technology technical banks)
  - Simple keyword / heuristic based answer scoring (length, relevance,
    keyword overlap with the question's skill tag, filler-word detection)

This is intentionally simple and clearly documented as a fallback - it is not
meant to be mistaken for a real LLM. See OpenAIProvider for the real
LLM-backed implementation.
"""
import random
import re
from typing import List, Dict, Any

from app.ai.base import AIProvider
from app.ai.rubric import score_rubric

HR_QUESTION_BANK = [
    {"q": "Tell me about yourself and what led you to pursue a career in {role}.", "tag": "communication"},
    {"q": "Why should we hire you for this {role} position over other candidates?", "tag": "communication"},
    {"q": "What would you say are your greatest strengths relevant to a {role} role?", "tag": "self_awareness"},
    {"q": "What is one weakness you are actively working to improve?", "tag": "self_awareness"},
    {"q": "Why do you want to join our company as a {role}?", "tag": "motivation"},
    {"q": "Tell me about the most challenging project you have worked on, such as {project}.", "tag": "project_experience"},
    {"q": "Where do you see yourself in five years as a {role}?", "tag": "motivation"},
    {"q": "Describe a time you disagreed with a teammate. How did you resolve it?", "tag": "teamwork"},
    {"q": "How do you handle tight deadlines and pressure?", "tag": "resilience"},
    {"q": "What motivated you to learn {skill}, and how have you applied it?", "tag": "self_awareness"},
    {"q": "Describe a situation where you had to learn a new technology quickly.", "tag": "adaptability"},
    {"q": "How do you prioritize tasks when working on multiple projects at once?", "tag": "time_management"},
]

# Per-technology technical question banks, keyed by lowercase skill name.
TECH_QUESTION_BANK: Dict[str, List[Dict[str, str]]] = {
    "java": [
        {"q": "What is the difference between an abstract class and an interface in Java?", "d": "medium"},
        {"q": "Explain how HashMap works internally in Java.", "d": "medium"},
        {"q": "What are Java Generics and why are they useful?", "d": "medium"},
        {"q": "Explain the difference between checked and unchecked exceptions in Java.", "d": "easy"},
        {"q": "What is the difference between ArrayList and LinkedList? When would you use each?", "d": "easy"},
        {"q": "Explain multithreading in Java and the purpose of the synchronized keyword.", "d": "hard"},
        {"q": "What is garbage collection in Java and how does it work?", "d": "hard"},
    ],
    "python": [
        {"q": "What is the difference between a list and a tuple in Python?", "d": "easy"},
        {"q": "Explain Python's GIL (Global Interpreter Lock) and its impact on multithreading.", "d": "hard"},
        {"q": "What are Python decorators and when would you use one?", "d": "medium"},
        {"q": "Explain the difference between deep copy and shallow copy in Python.", "d": "medium"},
        {"q": "What are list comprehensions and why are they preferred over loops in some cases?", "d": "easy"},
        {"q": "How does Python's garbage collection work?", "d": "hard"},
    ],
    "react": [
        {"q": "What is the Virtual DOM and how does React use it?", "d": "easy"},
        {"q": "Explain the difference between useState and useEffect hooks.", "d": "medium"},
        {"q": "What is prop drilling and how can you avoid it?", "d": "medium"},
        {"q": "Explain the React component lifecycle in functional components using hooks.", "d": "hard"},
        {"q": "What is the purpose of keys in React lists?", "d": "easy"},
    ],
    "javascript": [
        {"q": "Explain closures in JavaScript with an example use case.", "d": "medium"},
        {"q": "What is the difference between '==' and '===' in JavaScript?", "d": "easy"},
        {"q": "Explain how the JavaScript event loop works.", "d": "hard"},
        {"q": "What are Promises and how do they differ from async/await?", "d": "medium"},
    ],
    "sql": [
        {"q": "What is the difference between INNER JOIN and LEFT JOIN?", "d": "easy"},
        {"q": "Explain database normalization and why it matters.", "d": "medium"},
        {"q": "What is an index and how does it improve query performance?", "d": "medium"},
        {"q": "What is the difference between a primary key and a unique key?", "d": "easy"},
        {"q": "Explain ACID properties in the context of relational databases.", "d": "hard"},
    ],
    "django": [
        {"q": "Explain Django's MVT architecture.", "d": "medium"},
        {"q": "What is the Django ORM and what problem does it solve?", "d": "easy"},
        {"q": "How does Django handle database migrations?", "d": "medium"},
    ],
    "fastapi": [
        {"q": "How does FastAPI use Python type hints for request validation?", "d": "medium"},
        {"q": "What is dependency injection in FastAPI and why is it useful?", "d": "medium"},
    ],
    "machine learning": [
        {"q": "Explain the bias-variance tradeoff in machine learning.", "d": "hard"},
        {"q": "What is the difference between supervised and unsupervised learning?", "d": "easy"},
        {"q": "How would you handle an imbalanced dataset in a classification problem?", "d": "medium"},
        {"q": "What is overfitting and how can you prevent it?", "d": "medium"},
    ],
    "data analysis": [
        {"q": "What steps would you take to clean a messy dataset before analysis?", "d": "easy"},
        {"q": "Explain the difference between correlation and causation.", "d": "medium"},
        {"q": "How would you detect and handle outliers in a dataset?", "d": "medium"},
    ],
    "node.js": [
        {"q": "Explain the event-driven, non-blocking I/O model in Node.js.", "d": "medium"},
        {"q": "What is middleware in Express.js and how is it used?", "d": "medium"},
    ],
    "spring boot": [
        {"q": "What is dependency injection in Spring, and how does Spring Boot simplify configuration?", "d": "medium"},
        {"q": "Explain the purpose of Spring Boot's @RestController annotation.", "d": "easy"},
    ],
    "html": [
        {"q": "What is semantic HTML and why does it matter?", "d": "easy"},
    ],
    "css": [
        {"q": "Explain the CSS box model.", "d": "easy"},
        {"q": "What is the difference between Flexbox and CSS Grid?", "d": "medium"},
    ],
    "algorithms": [
        {"q": "Explain the time complexity difference between quicksort and mergesort.", "d": "hard"},
        {"q": "What is dynamic programming and when would you use it?", "d": "hard"},
        {"q": "Explain the difference between BFS and DFS graph traversal.", "d": "medium"},
    ],
    "data structures": [
        {"q": "What is the difference between a stack and a queue?", "d": "easy"},
        {"q": "Explain how a hash table resolves collisions.", "d": "medium"},
        {"q": "What is a balanced binary search tree and why is balance important?", "d": "hard"},
    ],
}

# Generic fallback bank used when we can't match a specific skill
GENERIC_TECH_QUESTIONS = [
    {"q": "Walk me through how you would design a REST API for a simple e-commerce system.", "d": "medium"},
    {"q": "What is the difference between horizontal and vertical scaling?", "d": "medium"},
    {"q": "Explain the concept of version control and why it's important in team projects.", "d": "easy"},
    {"q": "How would you debug a production issue you cannot reproduce locally?", "d": "hard"},
    {"q": "What is the difference between authentication and authorization?", "d": "easy"},
]

FILLER_WORDS = {"um", "uh", "like", "basically", "actually", "you know", "sort of", "kind of"}

ROLE_KEYWORD_MAP = {
    "java developer": ["java", "spring boot", "data structures", "algorithms", "sql"],
    "python developer": ["python", "django", "fastapi", "sql"],
    "full stack developer": ["javascript", "react", "node.js", "sql", "html", "css"],
    "frontend developer": ["javascript", "react", "html", "css"],
    "backend developer": ["java", "python", "sql", "node.js", "spring boot", "fastapi"],
    "data analyst": ["sql", "data analysis", "python"],
    "data scientist": ["python", "machine learning", "data analysis", "sql"],
    "machine learning engineer": ["python", "machine learning", "algorithms"],
    "software developer": ["java", "python", "data structures", "algorithms", "sql"],
}


class MockAIProvider(AIProvider):
    name = "mock"
    simulated = True

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    # ---------- helpers ----------
    def _relevant_skills(self, target_role: str, context: str) -> List[str]:
        role_key = (target_role or "").strip().lower()
        role_defaults = ROLE_KEYWORD_MAP.get(role_key, [])
        context_lower = (context or "").lower()
        found_in_context = [skill for skill in TECH_QUESTION_BANK.keys() if skill in context_lower]
        # Prioritize skills explicitly present in the candidate's resume/context,
        # then fall back to role defaults for variety.
        ordered: List[str] = []
        for s in found_in_context + role_defaults:
            if s not in ordered:
                ordered.append(s)
        return ordered or list(TECH_QUESTION_BANK.keys())[:3]

    def _extract_project_name(self, context: str) -> str:
        match = re.search(r"project[s]?\s*[:\-]?\s*([A-Za-z0-9 ,]{3,40})", context or "", re.IGNORECASE)
        return match.group(1).strip() if match else "a recent project"

    # ---------- interface ----------
    def generate_questions(self, interview_type, target_role, context, num_questions):
        target_role = target_role or "Software Developer"
        if interview_type == "hr":
            project_name = self._extract_project_name(context)
            skills = self._relevant_skills(target_role, context)
            skill_name = skills[0] if skills else "your primary skill"
            pool = list(HR_QUESTION_BANK)
            self._rng.shuffle(pool)
            selected = pool[:num_questions]
            questions = []
            for item in selected:
                text = item["q"].format(role=target_role, project=project_name, skill=skill_name)
                questions.append({"question": text, "difficulty": "medium", "skill_tag": item["tag"]})
            return questions

        # technical
        skills = self._relevant_skills(target_role, context)
        questions = []
        skill_cycle = skills * (num_questions // max(len(skills), 1) + 1)
        used_texts = set()
        for skill in skill_cycle:
            bank = TECH_QUESTION_BANK.get(skill, GENERIC_TECH_QUESTIONS)
            pool = [item for item in bank if item["q"] not in used_texts]
            if not pool:
                continue
            choice = self._rng.choice(pool)
            used_texts.add(choice["q"])
            questions.append({"question": choice["q"], "difficulty": choice["d"], "skill_tag": skill})
            if len(questions) >= num_questions:
                break
        while len(questions) < num_questions:
            choice = self._rng.choice(GENERIC_TECH_QUESTIONS)
            if choice["q"] not in used_texts:
                used_texts.add(choice["q"])
                questions.append({"question": choice["q"], "difficulty": choice["d"], "skill_tag": "general"})
            else:
                break
        return questions[:num_questions]

    def evaluate_answer(self, interview_type, question, answer, context):
        answer = (answer or "").strip()
        words = answer.split()
        word_count = len(words)

        if word_count == 0:
            return {
                "score": 0.0,
                "strengths": [],
                "weaknesses": ["No answer was provided."],
                "feedback": "You did not provide an answer. Try to always give a structured response, "
                            "even a brief one, rather than leaving it blank.",
                "suggested_improvement": "Practice structuring answers using a framework such as STAR "
                                          "(Situation, Task, Action, Result) for HR questions, or "
                                          "explain-example-conclusion for technical questions.",
            }

        # crude keyword overlap between question and answer
        q_words = set(re.findall(r"[a-zA-Z]{4,}", question.lower()))
        a_words = set(re.findall(r"[a-zA-Z]{4,}", answer.lower()))
        overlap = len(q_words & a_words)

        filler_count = sum(answer.lower().count(fw) for fw in FILLER_WORDS)

        # length score component: rewards a reasonably detailed answer, caps out around 120 words
        length_score = min(word_count / 120, 1.0) * 40
        relevance_score = min(overlap / max(len(q_words), 1), 1.0) * 40
        clarity_penalty = min(filler_count * 3, 15)
        structure_bonus = 10 if any(w in answer.lower() for w in ["because", "for example", "such as", "first", "then", "result"]) else 0

        score = max(0.0, min(100.0, length_score + relevance_score + structure_bonus - clarity_penalty + 10))
        score = round(score, 1)

        strengths, weaknesses = [], []
        if word_count >= 40:
            strengths.append("Answer is reasonably detailed and complete.")
        else:
            weaknesses.append("Answer is quite short; add more specific detail or an example.")

        if overlap >= 2:
            strengths.append("Answer stays relevant to what was asked.")
        else:
            weaknesses.append("Answer could more directly address the specific question asked.")

        if structure_bonus:
            strengths.append("Good use of structured reasoning or examples.")
        else:
            weaknesses.append("Consider structuring the answer with a clear example or reasoning ('for example...', 'because...').")

        if filler_count > 2:
            weaknesses.append("Reduce filler words/phrases to sound more confident and concise.")

        if interview_type == "technical":
            feedback = (
                f"Your answer covers {word_count} words with {overlap} key terms overlapping the question. "
                "Focus on precise technical vocabulary and a concrete example to strengthen depth."
            )
        else:
            feedback = (
                f"Your answer communicates your point in {word_count} words. "
                "For HR interviews, aim for a concise story with a clear outcome (STAR method)."
            )

        return {
            "score": score,
            "strengths": strengths or ["Attempted the question."],
            "weaknesses": weaknesses or ["None significant - keep practicing for consistency."],
            "feedback": feedback,
            "suggested_improvement": "Add a specific, quantifiable example and tie it back directly to the question asked.",
        }

    def summarize_interview(self, interview_type, qa_pairs):
        scores = [qa["score"] for qa in qa_pairs if qa.get("score") is not None]
        overall = round(sum(scores) / len(scores), 1) if scores else 0.0
        technical = overall if interview_type == "technical" else round(overall * 0.85, 1)
        communication = overall if interview_type == "hr" else round(overall * 0.9, 1)

        all_weaknesses = []
        all_strengths = []
        for qa in qa_pairs:
            all_weaknesses.extend(qa.get("weaknesses", []))
            all_strengths.extend(qa.get("strengths", []))

        # de-duplicate while preserving order
        def dedup(seq):
            seen = set()
            out = []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        weaknesses = dedup(all_weaknesses)[:5]
        strengths = dedup(all_strengths)[:5]

        recommended_topics = []
        skill_tags = dedup([qa.get("skill_tag", "general") for qa in qa_pairs])
        for tag in skill_tags[:4]:
            recommended_topics.append(tag.replace("_", " ").title())

        if overall >= 80:
            feedback = "Strong overall performance. You communicate clearly and demonstrate solid understanding."
        elif overall >= 60:
            feedback = "Good performance with room to grow - focus on depth and specific examples in weaker answers."
        else:
            feedback = "This interview highlighted several areas to strengthen. Review the weak topics below and practice with the preparation plan."

        return {
            "overall_score": overall,
            "technical_score": technical,
            "communication_score": communication,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "feedback": feedback,
            "recommended_topics": recommended_topics,
        }

    def evaluate_code(self, problem_statement, source_code, passed, total, compile_ok):
        if not compile_ok:
            return {
                "feedback": "Your code did not compile. Review the compiler error output, check for missing "
                             "semicolons, mismatched braces, or incorrect method signatures.",
                "time_complexity_estimate": "N/A",
                "space_complexity_estimate": "N/A",
            }

        ratio = passed / total if total else 0
        loops = len(re.findall(r"\bfor\s*\(|\bwhile\s*\(", source_code))
        nested_loops = len(re.findall(r"for\s*\([^)]*\)\s*\{[^{}]*for\s*\(", source_code, re.DOTALL))
        uses_map_or_set = bool(re.search(r"HashMap|HashSet|TreeMap|TreeSet", source_code))
        uses_recursion_hint = bool(re.search(r"\breturn\s+\w+\(", source_code))

        if nested_loops:
            time_complexity = "O(n^2) - nested loops detected; consider a hash-based approach if applicable."
        elif uses_map_or_set:
            time_complexity = "O(n) - hash-based lookup detected, generally efficient."
        elif loops:
            time_complexity = "O(n) - single-pass loop detected."
        elif uses_recursion_hint:
            time_complexity = "Recursive - complexity depends on recursion depth and branching factor."
        else:
            time_complexity = "O(1) - no loops detected; likely constant-time logic."

        space_complexity = "O(n)" if uses_map_or_set else "O(1) (no significant extra data structures detected)"

        if ratio == 1:
            feedback = f"All {total} test case(s) passed. Solution appears correct for the given cases."
        elif ratio > 0:
            feedback = f"{passed}/{total} test cases passed. Review edge cases (empty input, boundary values, duplicates)."
        else:
            feedback = "No test cases passed. Re-check your logic against the sample input/output in the problem statement."

        return {
            "feedback": feedback,
            "time_complexity_estimate": time_complexity,
            "space_complexity_estimate": space_complexity,
        }

    # ---- advanced-edition methods ----
    def evaluate_rubric(self, interview_type, topic, question, answer, ideal_answer, key_points):
        """Deterministic rule-based rubric: key-point coverage, ideal-answer overlap, structure and delivery
        heuristics. This is NOT a language model; results are flagged simulated=True."""
        r = score_rubric(question, answer, ideal_answer, key_points)
        rub = r["rubric"]
        strengths, weaknesses = [], []
        for k, v in rub.items():
            label = k.replace("_", " ")
            if v["score"] >= 75:
                strengths.append(f"Strong {label}: {v['rationale']}")
            elif v["score"] < 50:
                weaknesses.append(f"Weak {label}: {v['rationale']}")
        if r["covered"]:
            strengths.append("Covered: " + ", ".join(r["covered"][:4]) + ".")
        if r["missing"]:
            weaknesses.append("Missed: " + ", ".join(r["missing"][:4]) + ".")
        if r["words"] == 0:
            feedback = "No answer was provided, so nothing could be scored."
        elif r["score"] >= 75:
            feedback = "A solid answer that covers most of what an interviewer expects. Polish the delivery and add a concrete example."
        elif r["score"] >= 50:
            feedback = "A reasonable start. Cover the missing points and back them with a short example."
        else:
            feedback = "This answer needs more depth. Review the ideal answer below and practise explaining the key points in your own words."
        improvement = (
            "Work in these points: " + "; ".join(r["missing"][:3]) + "." if r["missing"]
            else "Add a real example from your projects to make the answer memorable."
        )
        return {
            "score": r["score"], "rubric": rub, "strengths": strengths, "weaknesses": weaknesses,
            "missing_points": r["missing"], "feedback": feedback, "suggested_improvement": improvement,
            "ideal_answer": ideal_answer or "", "provider": "mock", "simulated": True,
        }

    def generate_followup(self, interview_type, question, answer, missing_points):
        if not missing_points:
            return None
        focus = missing_points[0]
        return {
            "question": f"You did not mention {focus}. Can you explain how {focus} relates to your answer?",
            "ideal_answer": "", "key_points": [{"label": focus, "terms": focus.lower().split()[:3]}],
        }

    def rag_answer(self, question, passages):
        """Extractive answer: returns the most relevant sentences from the retrieved passages, with citations."""
        from app.ai.rubric import tokens
        q = set(tokens(question))
        scored = []
        for i, p in enumerate(passages, start=1):
            for sent in re.split(r"(?<=[.!?])\s+|\n+", p.get("content", "")):
                sent = sent.strip()
                if len(sent) < 25:
                    continue
                overlap = len(q & set(tokens(sent)))
                if overlap:
                    scored.append((overlap, i, sent))
        scored.sort(key=lambda t: (-t[0], t[1]))
        if not scored:
            return {"answer": "I could not find anything about that in your uploaded documents.", "simulated": True}
        picked, seen = [], set()
        for _o, i, sent in scored[:4]:
            if sent not in seen:
                seen.add(sent)
                picked.append(f"{sent} [{i}]")
        return {"answer": " ".join(picked), "simulated": True}
