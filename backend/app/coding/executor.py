"""
Multi-language code execution (Python, Java, C++).

Two backends, selected by EXECUTION_BACKEND:

* "docker" (production): every submission runs in a throw-away container with no network, a read-only root
  filesystem, dropped capabilities, no-new-privileges, an unprivileged user, and memory / CPU / PID limits.
  Compile + all test cases run inside ONE container using a generated shell script; per-test wall-clock limits
  are enforced inside with `timeout`, and a hard limit for the whole container is enforced on the host.
* "local" (development fallback ONLY): runs compilers/interpreters directly on the host with timeouts and
  POSIX resource limits. This is NOT a security boundary - never expose it to untrusted users.

Both return the same RunResult so the rest of the application does not care which one ran.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.config import settings

LANGUAGES = ("python", "java", "cpp")
CLASS_RE = re.compile(r"public\s+class\s+(\w+)")


@dataclass
class CaseResult:
    index: int
    hidden: bool
    passed: bool
    status: str           # passed | wrong_answer | timeout | runtime_error
    input: str = ""
    expected_output: str = ""
    actual_output: str = ""
    time_ms: float = 0.0


@dataclass
class RunResult:
    status: str  # compiled_error | passed | failed | timeout | runtime_error | sandbox_error
    compile_output: str = ""
    cases: List[CaseResult] = field(default_factory=list)
    sandbox: str = ""
    execution_time_ms: float = 0.0

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.cases)


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in (text or "").strip().splitlines())


def _spec(language: str, source: str) -> Dict:
    if language == "python":
        return {"file": "main.py", "compile": None, "run": "python3 main.py", "source": source}
    if language == "java":
        m = CLASS_RE.search(source)
        name = m.group(1) if m else "Solution"
        if not m:
            source = f"public class Solution {{\n{source}\n}}"
        return {"file": f"{name}.java", "compile": f"javac -encoding UTF-8 {name}.java",
                "run": f"java -Xmx{max(128, settings.SANDBOX_MEMORY_MB // 2)}m -Xss16m -cp . {name}", "source": source}
    if language == "cpp":
        return {"file": "main.cpp", "compile": "g++ -O2 -std=c++17 -o prog main.cpp", "run": "./prog", "source": source}
    raise ValueError(f"Unsupported language '{language}'. Use one of: {', '.join(LANGUAGES)}.")


def _cap(s: str) -> str:
    s = s or ""
    return s if len(s) <= settings.MAX_OUTPUT_CHARS else s[: settings.MAX_OUTPUT_CHARS] + "\n...[output truncated]"


def run_submission(language: str, source: str, tests: List[dict], time_limit: Optional[int] = None) -> RunResult:
    """tests: [{"input": str, "expected_output": str, "hidden": bool}]"""
    spec = _spec(language, source)
    limit = max(1, int(time_limit or settings.EXEC_TIMEOUT_SECONDS))
    base = os.path.abspath(settings.CODE_EXEC_DIR)
    os.makedirs(base, exist_ok=True)
    work = os.path.join(base, uuid.uuid4().hex)
    os.makedirs(work)
    try:
        with open(os.path.join(work, spec["file"]), "w", encoding="utf-8") as f:
            f.write(spec["source"])
        if settings.EXECUTION_BACKEND.lower() == "docker":
            return _run_docker(work, spec, tests, limit)
        return _run_local(work, spec, tests, limit)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------------------------------------ local (dev)
def _posix_limits():
    if os.name != "posix":
        return None
    import resource

    def apply():
        mem = settings.SANDBOX_MEMORY_MB * 1024 * 1024
        for res, val in ((resource.RLIMIT_CPU, settings.EXEC_TIMEOUT_SECONDS * 2 + 2), (resource.RLIMIT_FSIZE, 8 * 1024 * 1024)):
            try:
                resource.setrlimit(res, (val, val))
            except (ValueError, OSError):
                pass
        try:  # address-space limits break the JVM; apply only to non-Java runs
            if not os.environ.get("_NO_AS_LIMIT"):
                resource.setrlimit(resource.RLIMIT_AS, (mem * 4, mem * 4))
        except (ValueError, OSError):
            pass
    return apply


def _run_local(work: str, spec: Dict, tests: List[dict], limit: int) -> RunResult:
    res = RunResult(status="passed", sandbox="local")
    is_java = spec["run"].startswith("java")
    pre = None if is_java else _posix_limits()
    if spec["compile"]:
        try:
            cp = subprocess.run(spec["compile"].split(), cwd=work, capture_output=True, text=True,
                                timeout=settings.EXEC_COMPILE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return RunResult(status="timeout", compile_output="Compilation timed out.", sandbox="local")
        except FileNotFoundError as exc:
            return RunResult(status="sandbox_error", sandbox="local",
                             compile_output=f"Toolchain not found on this machine: {exc.filename}. Install it or use the Docker backend.")
        if cp.returncode != 0:
            return RunResult(status="compiled_error", compile_output=_cap(cp.stdout + cp.stderr), sandbox="local")
    total = 0.0
    for i, t in enumerate(tests):
        hidden = bool(t.get("hidden"))
        start = time.time()
        try:
            rp = subprocess.run(spec["run"].split(), cwd=work, input=t.get("input", ""), capture_output=True, text=True,
                                timeout=limit, preexec_fn=pre)
            ms = (time.time() - start) * 1000
            total += ms
            out = _cap(rp.stdout)
            if rp.returncode != 0:
                res.cases.append(CaseResult(i, hidden, False, "runtime_error", t.get("input", ""), t.get("expected_output", ""),
                                            _cap(rp.stderr), ms))
            else:
                ok = normalize(out) == normalize(t.get("expected_output", ""))
                res.cases.append(CaseResult(i, hidden, ok, "passed" if ok else "wrong_answer", t.get("input", ""),
                                            t.get("expected_output", ""), out, ms))
        except subprocess.TimeoutExpired:
            total += limit * 1000
            res.cases.append(CaseResult(i, hidden, False, "timeout", t.get("input", ""), t.get("expected_output", ""),
                                        "<time limit exceeded>", limit * 1000.0))
    res.execution_time_ms = round(total, 2)
    res.status = _overall(res)
    return res


def _overall(res: RunResult) -> str:
    if res.cases and all(c.passed for c in res.cases):
        return "passed"
    if any(c.status == "timeout" for c in res.cases) and not any(c.passed for c in res.cases):
        return "timeout"
    return "failed"


# ------------------------------------------------------------------------------------------------ docker
def build_docker_command(work: str, name: str, script: str = "run.sh") -> List[str]:
    return [
        "docker", "run", "--rm", "--name", name,
        "--network", "none",
        "--memory", f"{settings.SANDBOX_MEMORY_MB}m", "--memory-swap", f"{settings.SANDBOX_MEMORY_MB}m",
        "--cpus", str(settings.SANDBOX_CPUS),
        "--pids-limit", str(settings.SANDBOX_PIDS_LIMIT),
        "--read-only", "--tmpfs", "/tmp:rw,exec,size=64m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "-v", f"{work}:/work:rw", "-w", "/work",
        settings.SANDBOX_IMAGE, "sh", script,
    ]


def _script(spec: Dict, tests: List[dict], limit: int) -> str:
    lines = ["#!/bin/sh", "cd /work", "ulimit -f 4096",
             f"echo {spec['file']} > /dev/null"]
    if spec["compile"]:
        lines.append(f"timeout {settings.EXEC_COMPILE_TIMEOUT_SECONDS} {spec['compile']} > compile.out 2>&1 || "
                     "{ echo COMPILE_FAIL > status; exit 0; }")
    for i in range(len(tests)):
        lines.append(f"s=$(date +%s%N); timeout -k 1 {limit} {spec['run']} < in_{i}.txt > out_{i}.txt 2> err_{i}.txt; "
                     f"echo $? > rc_{i}.txt; e=$(date +%s%N); echo $(( (e - s) / 1000000 )) > ms_{i}.txt")
    lines.append("echo DONE > status")
    return "\n".join(lines) + "\n"


def _run_docker(work: str, spec: Dict, tests: List[dict], limit: int) -> RunResult:
    if shutil.which("docker") is None:
        return RunResult(status="sandbox_error", sandbox="docker",
                         compile_output="Docker is not available on this server. Install Docker or set EXECUTION_BACKEND=local (development only).")
    for i, t in enumerate(tests):
        with open(os.path.join(work, f"in_{i}.txt"), "w", encoding="utf-8") as f:
            f.write(t.get("input", ""))
    with open(os.path.join(work, "run.sh"), "w") as f:
        f.write(_script(spec, tests, limit))
    os.chmod(work, 0o777)  # the container runs as an unprivileged user and must be able to write results
    for fn in os.listdir(work):
        os.chmod(os.path.join(work, fn), 0o666)
    name = f"sbx-{uuid.uuid4().hex[:12]}"
    hard = settings.EXEC_COMPILE_TIMEOUT_SECONDS + limit * max(1, len(tests)) + 15
    try:
        proc = subprocess.run(build_docker_command(work, name), capture_output=True, text=True, timeout=hard)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        return RunResult(status="timeout", sandbox="docker", compile_output="Execution exceeded the total time limit.")
    if proc.returncode != 0 and not os.path.exists(os.path.join(work, "status")):
        return RunResult(status="sandbox_error", sandbox="docker",
                         compile_output=_cap("Sandbox failed to start: " + (proc.stderr or proc.stdout)))
    status_file = os.path.join(work, "status")
    st = open(status_file).read().strip() if os.path.exists(status_file) else ""
    comp = open(os.path.join(work, "compile.out")).read() if os.path.exists(os.path.join(work, "compile.out")) else ""
    if st == "COMPILE_FAIL":
        return RunResult(status="compiled_error", compile_output=_cap(comp), sandbox="docker")
    res = RunResult(status="passed", compile_output=_cap(comp), sandbox="docker")
    total = 0.0

    def rd(n):
        p = os.path.join(work, n)
        return open(p, errors="replace").read() if os.path.exists(p) else ""
    for i, t in enumerate(tests):
        hidden = bool(t.get("hidden"))
        rc = rd(f"rc_{i}.txt").strip()
        ms = float(rd(f"ms_{i}.txt").strip() or 0)
        total += ms
        out, err = _cap(rd(f"out_{i}.txt")), _cap(rd(f"err_{i}.txt"))
        exp = t.get("expected_output", "")
        if rc in ("124", "137"):
            res.cases.append(CaseResult(i, hidden, False, "timeout", t.get("input", ""), exp, "<time limit exceeded>", ms))
        elif rc != "0":
            res.cases.append(CaseResult(i, hidden, False, "runtime_error", t.get("input", ""), exp, err or f"exit code {rc}", ms))
        else:
            ok = normalize(out) == normalize(exp)
            res.cases.append(CaseResult(i, hidden, ok, "passed" if ok else "wrong_answer", t.get("input", ""), exp, out, ms))
    res.execution_time_ms = round(total, 2)
    res.status = _overall(res)
    return res
