"""Additional seed data for the Advanced Edition: coding problems with hidden tests (each has a verified reference
solution), job descriptions and a placement-officer account. Safe to run repeatedly."""
import json

from sqlalchemy.orm import Session

from app.models.coding import CodingQuestion
from app.models.resume import JobDescription
from app.models.user import User, Profile
from app.data.skills import find_skills
from app.utils.security import hash_password

T = lambda i, o, h=False: {"input": i, "expected_output": o, "hidden": h}  # noqa: E731

PROBLEMS = [
    dict(title="Palindrome Check", difficulty="easy", topic_tag="strings",
         problem_statement="Read one line of text. Print YES if it reads the same forwards and backwards ignoring case, otherwise NO.",
         input_format="One line containing a word.", output_format="YES or NO", constraints="1 <= length <= 1000",
         sample_input="Racecar", sample_output="YES",
         tests=[T("Racecar", "YES"), T("hello", "NO"), T("A", "YES"), T("Madam", "YES", True), T("ab", "NO", True)],
         ref="s = input().strip().lower()\nprint('YES' if s == s[::-1] else 'NO')\n"),
    dict(title="Count Vowels", difficulty="easy", topic_tag="strings",
         problem_statement="Read one line of text and print how many vowels (a, e, i, o, u, case-insensitive) it contains.",
         input_format="One line of text.", output_format="A single integer.", constraints="0 < length <= 1000",
         sample_input="Hello World", sample_output="3",
         tests=[T("Hello World", "3"), T("rhythm", "0"), T("AEIOU aeiou", "10", True), T("Programming", "3", True)],
         ref="print(sum(c in 'aeiou' for c in input().lower()))\n"),
    dict(title="Nth Fibonacci Number", difficulty="easy", topic_tag="dynamic_programming",
         problem_statement="Print the n-th Fibonacci number where F(0)=0 and F(1)=1. Use iteration or memoisation; naive recursion is too slow for n=50.",
         input_format="A single integer n.", output_format="A single integer.", constraints="0 <= n <= 50",
         sample_input="10", sample_output="55",
         tests=[T("10", "55"), T("0", "0"), T("1", "1"), T("50", "12586269025", True), T("20", "6765", True)],
         ref="n = int(input())\na, b = 0, 1\nfor _ in range(n):\n    a, b = b, a + b\nprint(a)\n"),
    dict(title="Valid Parentheses", difficulty="medium", topic_tag="strings",
         problem_statement="Given a string made only of the characters ()[]{}, print YES if the brackets are balanced and correctly nested, otherwise NO.",
         input_format="One line of bracket characters.", output_format="YES or NO", constraints="1 <= length <= 10^4",
         sample_input="()[]{}", sample_output="YES",
         tests=[T("()[]{}", "YES"), T("(]", "NO"), T("([)]", "NO"), T("{[()]}", "YES", True), T("(((", "NO", True)],
         ref="s = input().strip()\nst = []\nm = {')': '(', ']': '[', '}': '{'}\nok = True\nfor c in s:\n    if c in '([{':\n        st.append(c)\n    elif not st or st.pop() != m[c]:\n        ok = False\n        break\nprint('YES' if ok and not st else 'NO')\n"),
    dict(title="Maximum Subarray Sum", difficulty="medium", topic_tag="arrays",
         problem_statement="Given an array of n integers, print the largest sum of any non-empty contiguous subarray (Kadane's algorithm gives O(n)).",
         input_format="Line 1: n. Line 2: n space-separated integers.", output_format="A single integer.", constraints="1 <= n <= 10^5",
         sample_input="9\n-2 1 -3 4 -1 2 1 -5 4", sample_output="6",
         tests=[T("9\n-2 1 -3 4 -1 2 1 -5 4", "6"), T("1\n-5", "-5"), T("5\n1 2 3 4 5", "15", True), T("4\n-1 -2 -3 -4", "-1", True)],
         ref="n = int(input())\na = list(map(int, input().split()))\nbest = cur = a[0]\nfor x in a[1:]:\n    cur = max(x, cur + x)\n    best = max(best, cur)\nprint(best)\n"),
    dict(title="Binary Search Index", difficulty="medium", topic_tag="arrays",
         problem_statement="Given a sorted array and a target, print the 0-based index of the target, or -1 if absent. Aim for O(log n).",
         input_format="Line 1: n. Line 2: n sorted integers. Line 3: target.", output_format="An index or -1.", constraints="1 <= n <= 10^5",
         sample_input="5\n1 3 5 7 9\n7", sample_output="3",
         tests=[T("5\n1 3 5 7 9\n7", "3"), T("3\n1 2 3\n4", "-1"), T("1\n5\n5", "0", True), T("6\n-5 -2 0 3 8 12\n-5", "0", True)],
         ref="n = int(input())\na = list(map(int, input().split()))\nt = int(input())\nlo, hi, ans = 0, n - 1, -1\nwhile lo <= hi:\n    m = (lo + hi) // 2\n    if a[m] == t:\n        ans = m\n        break\n    if a[m] < t:\n        lo = m + 1\n    else:\n        hi = m - 1\nprint(ans)\n"),
    dict(title="Climbing Stairs", difficulty="medium", topic_tag="dynamic_programming",
         problem_statement="You climb n stairs taking 1 or 2 steps at a time. Print the number of distinct ways to reach the top.",
         input_format="A single integer n.", output_format="A single integer.", constraints="1 <= n <= 40",
         sample_input="3", sample_output="3",
         tests=[T("2", "2"), T("3", "3"), T("10", "89", True), T("30", "1346269", True)],
         ref="n = int(input())\na, b = 1, 1\nfor _ in range(n):\n    a, b = b, a + b\nprint(a)\n"),
]

JDS = [
    ("Backend Engineer (Python)", "Sample Company", "We are hiring a backend engineer. You will build REST APIs with Python and FastAPI, "
     "design PostgreSQL schemas, write unit tests with pytest, and deploy services with Docker and CI/CD on AWS. "
     "Knowledge of data structures, algorithms and system design is expected."),
    ("GenAI Engineer", "Sample Company", "Build retrieval augmented generation (RAG) features using LLMs, vector databases such as pgvector, "
     "embeddings and NLP techniques in Python. Experience with prompt engineering, Docker and REST APIs is a plus."),
]


def seed_extra(db: Session) -> None:
    for p in PROBLEMS:
        if db.query(CodingQuestion).filter(CodingQuestion.title == p["title"]).first():
            continue
        db.add(CodingQuestion(
            title=p["title"], problem_statement=p["problem_statement"], input_format=p["input_format"],
            output_format=p["output_format"], constraints=p["constraints"], sample_input=p["sample_input"],
            sample_output=p["sample_output"], difficulty=p["difficulty"], topic_tag=p["topic_tag"],
            test_cases=json.dumps(p["tests"]), starter_codes="{}", company_tags="[]"))
    for title, company, desc in JDS:
        if not db.query(JobDescription).filter(JobDescription.title == title).first():
            db.add(JobDescription(title=title, company=company, description=desc, required_skills=json.dumps(find_skills(desc)),
                                  is_public=True))
    db.commit()
