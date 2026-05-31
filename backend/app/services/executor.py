"""Safe Python execution sandbox — AST check + subprocess timeout."""

from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path

_BLOCKED_IMPORTS = {
    "os", "subprocess", "sys", "shutil", "socket", "ctypes",
    "multiprocessing", "pathlib", "importlib", "builtins",
    "pty", "signal", "mmap", "fcntl", "resource", "nt",
}

_BLOCKED_NAMES = {
    "exec", "eval", "open", "__import__", "compile", "input", "breakpoint",
}


def _check_safety(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in _BLOCKED_IMPORTS:
                    return f"import '{mod}' is blocked in the sandbox"

        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in _BLOCKED_IMPORTS:
                return f"from '{mod}' import is blocked in the sandbox"

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_NAMES:
                return f"'{node.func.id}()' is blocked in the sandbox"

        if isinstance(node, ast.Attribute):
            if node.attr in ("__subclasses__", "__bases__", "__builtins__", "__globals__"):
                return f"Attribute '{node.attr}' is blocked in the sandbox"

    return None


def run_python(code: str, timeout: int = 5) -> dict:
    err = _check_safety(code)
    if err:
        return {"stdout": "", "stderr": err, "exit_code": 1, "timed_out": False}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(code)
        tmp = f.name

    try:
        proc = subprocess.run(
            ["python3", "-u", tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/tmp",
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", "PYTHONPATH": ""},
        )
        return {
            "stdout": proc.stdout[:8192],
            "stderr": proc.stderr[:4096],
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Time limit exceeded ({timeout}s)",
            "exit_code": 1,
            "timed_out": True,
        }
    finally:
        Path(tmp).unlink(missing_ok=True)
