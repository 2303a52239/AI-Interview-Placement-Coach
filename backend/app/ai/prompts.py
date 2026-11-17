"""Prompt templates for the LLM-backed provider. Kept in one place so they can be reviewed and tuned.
Every template demands a strict JSON object so responses can be validated."""

RUBRIC_CRITERIA = {
    # key: (weight, description)
    "correctness": (0.30, "Is the content technically accurate?"),
    "understanding": (0.20, "Does the answer show real conceptual understanding, not memorised phrases?"),
    "relevance": (0.15, "Does it answer the question that was asked?"),
    "completeness": (0.15, "Does it cover the key points an interviewer expects?"),
    "communication": (0.10, "Is it clear, structured and concise?"),
    "problem_solving": (0.10, "Does it show structured reasoning, trade-offs, examples or edge cases?"),
}

SYSTEM_EVALUATOR = (
    "You are a strict but fair interview evaluator for a campus placement coaching platform. "
    "Score only what the candidate actually said. Respond with ONE JSON object and nothing else."
)

RUBRIC_PROMPT = """Interview type: {interview_type}
Topic: {topic}
Question: {question}

Reference key points an ideal answer covers:
{key_points}

Reference ideal answer:
{ideal_answer}

Candidate answer:
\"\"\"{answer}\"\"\"

Score each criterion from 0 to 100: {criteria}.
Return JSON with keys:
  "rubric": {{ "<criterion>": {{"score": number, "rationale": string}} }} for every criterion above,
  "strengths": [string], "weaknesses": [string],
  "missing_points": [string],
  "feedback": string (2-3 sentences, addressed to the candidate),
  "suggested_improvement": string,
  "ideal_answer": string (a concise model answer)."""

QUESTION_PROMPT = """Interview type: {interview_type}
Target role: {target_role}
Topic: {topic}
Difficulty: {difficulty}
Candidate context:
{context}

Write {count} distinct interview questions. Return JSON {{"questions": [{{"question": string, "difficulty": "easy|medium|hard",
"skill_tag": string, "ideal_answer": string, "key_points": [string]}}]}}."""

FOLLOWUP_PROMPT = """The candidate answered a {interview_type} interview question weakly.
Question: {question}
Answer: \"\"\"{answer}\"\"\"
Missing points: {missing}
Write ONE short follow-up question that probes the most important missing point. Return JSON
{{"question": string, "ideal_answer": string, "key_points": [string]}}."""

RAG_PROMPT = """Answer the question using ONLY the numbered passages. Cite passages like [1]. If the passages do not
contain the answer, say so plainly.

Question: {question}

Passages:
{passages}

Return JSON {{"answer": string}}."""

SUMMARY_SYSTEM = (
    "You are an interview performance summarizer. Given question/answer/score/feedback objects, respond ONLY with "
    "a JSON object with keys: overall_score, technical_score, communication_score (0-100 numbers), strengths (list), "
    "weaknesses (list), feedback (string), recommended_topics (list of strings)."
)
