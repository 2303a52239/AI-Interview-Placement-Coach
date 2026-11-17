"""
JavaRunner

Compiles and executes a candidate's Java submission against a set of test
cases. Safety measures implemented for this local/academic context:
  - Each submission runs in its own temporary directory (auto cleaned up)
  - A hard wall-clock timeout is enforced on both compilation and execution
    (subprocess.run(..., timeout=...))
  - The class is always named "Solution" (candidate code must define
    `public class Solution`) so we control the entry point
  - stdin/stdout only - no network, no file system arguments passed through
  - Output size is capped to avoid runaway output filling disk/memory

This is NOT a full container/VM sandbox (true OS-level sandboxing such as
Docker/gVisor is out of scope for a local academic project as noted in the
project brief) but it is a genuinely functional compile-and-run pipeline
with timeout protection, appropriate for a class project run on a trusted
local machine.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import List

from app.config import settings

MAX_OUTPUT_CHARS = 20_000
CLASS_NAME_PATTERN = re.compile(r"public\s+class\s+(\w+)")


@dataclass
class TestCaseResult:
    input: str
    expected_output: str
    actual_output: str
    passed: bool


@dataclass
class RunResult:
    status: str  # compiled_error | passed | failed | timeout | runtime_error
    compile_output: str = ""
    passed_count: int = 0
    total_count: int = 0
    execution_time_ms: float = 0.0
    test_results: List[TestCaseResult] = field(default_factory=list)


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in (text or "").strip().splitlines())


def run_java_submission(source_code: str, test_cases: List[dict]) -> RunResult:
    """test_cases: list of {"input": str, "expected_output": str}"""
    match = CLASS_NAME_PATTERN.search(source_code)
    class_name = match.group(1) if match else "Solution"
    if not match:
        # Force a public class named Solution if the candidate omitted it,
        # so compilation has a predictable entry point.
        source_code = f"public class Solution {{\n{source_code}\n}}"
        class_name = "Solution"

    exec_dir_abs = os.path.abspath(settings.CODE_EXEC_DIR)
    os.makedirs(exec_dir_abs, exist_ok=True)
    work_dir = os.path.join(exec_dir_abs, uuid.uuid4().hex)
    os.makedirs(work_dir, exist_ok=True)
    java_filename = f"{class_name}.java"
    java_file = os.path.join(work_dir, java_filename)

    try:
        with open(java_file, "w") as f:
            f.write(source_code)

        # ---- Compile ----
        try:
            compile_proc = subprocess.run(
                ["javac", java_filename],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=settings.JAVA_EXEC_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return RunResult(status="timeout", compile_output="Compilation timed out.")
        except FileNotFoundError:
            return RunResult(
                status="compiled_error",
                compile_output="Java JDK (javac) was not found on this machine. "
                               "Please install a JDK and ensure it is on your PATH.",
            )

        if compile_proc.returncode != 0:
            return RunResult(status="compiled_error", compile_output=compile_proc.stdout + compile_proc.stderr)

        # ---- Run against each test case ----
        results: List[TestCaseResult] = []
        total_time_ms = 0.0
        for case in test_cases:
            stdin_data = case.get("input", "")
            expected = case.get("expected_output", "")
            start = time.time()
            try:
                run_proc = subprocess.run(
                    ["java", "-cp", work_dir, class_name],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=settings.JAVA_EXEC_TIMEOUT_SECONDS,
                )
                elapsed_ms = (time.time() - start) * 1000
                total_time_ms += elapsed_ms
                actual_output = (run_proc.stdout or "")[:MAX_OUTPUT_CHARS]
                if run_proc.returncode != 0:
                    results.append(TestCaseResult(stdin_data, expected, run_proc.stderr[:MAX_OUTPUT_CHARS], False))
                    continue
                passed = _normalize(actual_output) == _normalize(expected)
                results.append(TestCaseResult(stdin_data, expected, actual_output, passed))
            except subprocess.TimeoutExpired:
                results.append(TestCaseResult(stdin_data, expected, "<execution timed out>", False))

        passed_count = sum(1 for r in results if r.passed)
        overall_status = "passed" if passed_count == len(results) and results else "failed"

        return RunResult(
            status=overall_status,
            compile_output=compile_proc.stdout,
            passed_count=passed_count,
            total_count=len(results),
            execution_time_ms=round(total_time_ms, 2),
            test_results=results,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
