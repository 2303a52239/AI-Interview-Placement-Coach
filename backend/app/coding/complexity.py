"""Heuristic, language-aware time/space complexity estimation from source text.

This is static pattern analysis (loop nesting, recursion, sorting calls, auxiliary data structures). It is an
ESTIMATE, labelled as such, and can be wrong (for example for loops whose bounds are not n)."""
import re
from typing import Dict, List, Tuple

_LOOP_PY = re.compile(r"^\s*(for|while)\b")
_LOOP_C = re.compile(r"\b(for|while)\s*\(")
SORT_RE = re.compile(r"\bsorted\s*\(|\.sort\s*\(|Arrays\.sort|Collections\.sort|std::sort|\bsort\s*\(")
HASH_RE = {"python": re.compile(r"\{\s*\}|\bdict\s*\(|\bset\s*\(|defaultdict|Counter\(|\[\s*\]|\blist\s*\("),
           "java": re.compile(r"new\s+(HashMap|HashSet|TreeMap|TreeSet|ArrayList|LinkedList|ArrayDeque|PriorityQueue|int\[|long\[|boolean\[|String\[)"),
           "cpp": re.compile(r"\b(vector|map|unordered_map|set|unordered_set|queue|deque|priority_queue)\s*<|new\s+\w+\s*\[")}
TWO_D_RE = re.compile(r"\[\s*\w+\s*\]\s*\[\s*\w+\s*\]|vector\s*<\s*vector|\[\[|new\s+\w+\s*\[[^\]]+\]\s*\[[^\]]+\]|\*\s*\[")
MEMO_RE = re.compile(r"memo|cache|lru_cache|dp\b|dp\[|@cache", re.I)


def _max_loop_depth(language: str, lines: List[str]) -> int:
    best = 0
    if language == "python":
        stack: List[int] = []
        for ln in lines:
            if not ln.strip() or ln.strip().startswith("#"):
                continue
            indent = len(ln) - len(ln.lstrip())
            while stack and indent <= stack[-1]:
                stack.pop()
            if _LOOP_PY.match(ln):
                stack.append(indent)
                best = max(best, len(stack))
        return best
    depth, stack = 0, []
    for ln in lines:
        s = re.sub(r"//.*|\".*?\"", "", ln)
        loops_here = len(_LOOP_C.findall(s))
        for _ in range(loops_here):
            stack.append(depth)  # depth at which this loop's block starts
            best = max(best, len(stack))
        for ch in s:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                while stack and depth <= stack[-1]:
                    stack.pop()
        # single-statement loops without braces close on the same line
        if loops_here and "{" not in s and stack:
            stack.pop()
    return best


def _recursion(language: str, source: str) -> Tuple[bool, int]:
    names = re.findall(r"def\s+(\w+)\s*\(", source) if language == "python" else \
        [n for n in re.findall(r"\b(\w+)\s*\([^;{}]*\)\s*\{", source) if n not in {"if", "for", "while", "switch", "catch", "main"}]
    best = 0
    for n in set(names):
        calls = len(re.findall(r"\b" + re.escape(n) + r"\s*\(", source)) - 1  # minus the definition
        best = max(best, calls)
    return best >= 1, best


def analyze(language: str, source: str) -> Dict[str, str]:
    lines = source.splitlines()
    depth = _max_loop_depth(language, lines)
    rec, calls = _recursion(language, source)
    sorts = bool(SORT_RE.search(source))
    memo = bool(MEMO_RE.search(source))
    structures = bool(HASH_RE.get(language, HASH_RE["python"]).search(source))
    two_d = bool(TWO_D_RE.search(source))

    if rec and calls >= 2 and not memo:
        time = "O(2^n) - branching recursion without memoisation"
    elif rec and calls >= 2 and memo:
        time = "O(n) to O(n^2) - branching recursion with memoisation"
    elif rec:
        time = "O(n) - single recursion path (depth-dependent)"
    elif depth >= 3:
        time = f"O(n^{depth}) - {depth} nested loops"
    elif depth == 2:
        time = "O(n^2) - nested loops detected" + (" with sorting inside" if sorts else "") + "; consider a hash-based or sorted approach if the inputs allow it."
    elif sorts:
        time = "O(n log n) - dominated by sorting"
    elif depth == 1:
        time = "O(n) - single loop"
    else:
        time = "O(1) - no loops or recursion"

    if rec:
        space = "O(n) - recursion stack" + (" plus memo table" if memo else "")
    elif two_d:
        space = "O(n^2) - two-dimensional structure"
    elif structures or memo:
        space = "O(n) - auxiliary data structure"
    else:
        space = "O(1) - no significant extra storage"
    return {"time": time, "space": space,
            "note": "Heuristic estimate from static code patterns; it can be wrong when loop bounds are not the input size."}
